"""Complete mock-only recent-search pipeline for pre-live X API testing."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from x_auto_ops.buzz_read_client import BuzzFetchResult, XApiBuzzReadClient
from x_auto_ops.credential_loader import CredentialLoader, FakeCredentialLoader
from x_auto_ops.live_mode_gate import assert_live_mode_allowed
from x_auto_ops.mock_buzz_collector import (
    DEFAULT_CONFIG_PATH,
    filter_posts,
    load_buzz_collection_config,
    write_posts_csv,
)
from x_auto_ops.mock_transport import (
    MockRecentSearchTransport,
    RecentSearchTransport,
)
from x_auto_ops.query_builder import build_recent_search_query
from x_auto_ops.redaction import assert_redacted, redact_sensitive_text
from x_auto_ops.retry_queue import RetryQueue, RetryTask


DEFAULT_PIPELINE_OUTPUT_PATH = Path("data/mock_recent_search_pipeline_posts.csv")
DEFAULT_PIPELINE_REPORT_PATH = Path("reports/mock_recent_search_pipeline_report.md")
DEFAULT_PIPELINE_FIXTURE_PATH = Path("tests/fixtures/pipeline_success.json")


@dataclass(frozen=True)
class DryRunRecentSearchPipelineResult:
    fetch_result: BuzzFetchResult
    ranked_rows: list[dict[str, Any]]
    output_path: Path
    report_path: Path
    debug_log: str
    retry_queue: RetryQueue
    credential_source: str


def run_dry_run_recent_search_pipeline(
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    output_path: str | Path = DEFAULT_PIPELINE_OUTPUT_PATH,
    report_path: str | Path = DEFAULT_PIPELINE_REPORT_PATH,
    transport: RecentSearchTransport,
    source_genre: str | None = None,
    dry_run: bool = True,
    retry_queue: RetryQueue | None = None,
    credential_loader: CredentialLoader | None = None,
) -> DryRunRecentSearchPipelineResult:
    """Run the full mock read -> classify -> rank -> CSV -> report path."""

    if not dry_run:
        raise RuntimeError("dry-run recent search pipeline blocks dry_run=False")

    credentials = (credential_loader or FakeCredentialLoader()).load()
    assert_live_mode_allowed(
        {
            "dry_run": dry_run,
            "live_mode": False,
            "credential_source": credentials.source,
        }
    )
    config = load_buzz_collection_config(config_path)
    genre = _select_genre(config.genres, source_genre)
    query = build_recent_search_query(genre)
    client = XApiBuzzReadClient(transport=transport, dry_run=True)
    fetch_result = client.fetch_posts(genre)
    queue = retry_queue or RetryQueue()
    retry_tasks: list[RetryTask] = []
    if fetch_result.rate_limited:
        retry_tasks.append(
            queue.enqueue(
                query.query,
                fetch_result.retry_after_seconds,
                retry_count=0,
            )
        )
    ranked_rows = filter_posts(fetch_result.posts, config.genres)
    output = write_posts_csv(output_path, ranked_rows)
    report = write_pipeline_report(
        report_path,
        query=query.query,
        source_genre=query.source_genre,
        fetch_result=fetch_result,
        rows=ranked_rows,
        retry_queue_size=queue.size(),
        retry_tasks=retry_tasks,
        credential_source=credentials.source,
    )
    debug_log = _safe_pipeline_debug(
        {
            "source_genre": query.source_genre,
            "query_length": len(query.query),
            "post_count": len(fetch_result.posts),
            "ranked_count": len(ranked_rows),
            "rate_limited": fetch_result.rate_limited,
            "retry_after_seconds": fetch_result.retry_after_seconds,
            "partial_result": fetch_result.partial_result,
            "next_cursor_present": bool(fetch_result.next_token),
            "retry_queue_size": queue.size(),
            "redaction_status": "ok",
            "credential_source": credentials.source,
            "live_mode_gate": "dry_run_allowed",
        }
    )
    return DryRunRecentSearchPipelineResult(
        fetch_result=fetch_result,
        ranked_rows=ranked_rows,
        output_path=output,
        report_path=report,
        debug_log=debug_log,
        retry_queue=queue,
        credential_source=credentials.source,
    )


def load_mock_transport_fixture(path: str | Path) -> MockRecentSearchTransport:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return MockRecentSearchTransport(data)


def write_pipeline_report(
    path: str | Path,
    *,
    query: str,
    source_genre: str,
    fetch_result: BuzzFetchResult,
    rows: list[Mapping[str, Any]],
    retry_queue_size: int = 0,
    retry_tasks: list[RetryTask] | None = None,
    credential_source: str = "FAKE",
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    missing_counts = Counter()
    for row in rows:
        for item in str(row.get("metrics_missing") or "").split("|"):
            if item.strip():
                missing_counts[item.strip()] += 1

    lines = [
        "# Mock Recent Search Pipeline Report",
        "",
        "Mock-only dry-run report. No X API call, credential lookup, `.env` read, or posting was performed.",
        "",
        "## Query",
        f"- query: {redact_sensitive_text(query)}",
        f"- source_genre: {redact_sensitive_text(source_genre)}",
        "",
        "## Fetch Summary",
        f"- post_count: {len(fetch_result.posts)}",
        f"- ranked_count: {len(rows)}",
        f"- rate_limited: {fetch_result.rate_limited}",
        f"- retry_after_seconds: {fetch_result.retry_after_seconds}",
        f"- partial_result: {fetch_result.partial_result}",
        f"- next_cursor_present: {bool(fetch_result.next_token)}",
        f"- retry_queue_size: {retry_queue_size}",
        f"- rate_limited_count: {1 if fetch_result.rate_limited else 0}",
        f"- redaction_status: ok",
        f"- credential_loader: {redact_sensitive_text(credential_source)}",
        f"- live_mode_gate: dry_run_allowed",
        "",
        "## Top Posts",
    ]
    top_rows = sorted(rows, key=lambda row: int(row.get("buzz_score") or 0), reverse=True)[:5]
    if not top_rows:
        lines.append("- No posts ranked.")
    for row in top_rows:
        lines.append(
            "- "
            f"{redact_sensitive_text(row.get('post_id'))} / "
            f"{redact_sensitive_text(row.get('detected_genre'))} / "
            f"buzz_score {row.get('buzz_score')} / "
            f"rank {row.get('rank_in_genre')}"
        )

    lines.extend(["", "## Metrics Missing Summary"])
    if not missing_counts:
        lines.append("- none: 0")
    for key, count in sorted(missing_counts.items()):
        lines.append(f"- {redact_sensitive_text(key)}: {count}")

    lines.extend(["", "## Retry Tasks"])
    tasks = retry_tasks or []
    if not tasks:
        lines.append("- none: 0")
    for task in tasks:
        lines.append(
            "- "
            f"query={redact_sensitive_text(task.query)} / "
            f"retry_after_seconds={task.retry_after_seconds} / "
            f"retry_count={task.retry_count}"
        )

    text = "\n".join(lines) + "\n"
    assert_redacted(text, context="pipeline report")
    output.write_text(text, encoding="utf-8")
    return output


def _select_genre(genres: list[Any], source_genre: str | None) -> Any:
    if not genres:
        raise ValueError("at least one genre is required")
    if source_genre is None:
        return genres[0]
    for genre in genres:
        if genre.id == source_genre:
            return genre
    raise ValueError(f"unknown source_genre: {source_genre}")


def _safe_pipeline_debug(values: Mapping[str, Any]) -> str:
    text = " ".join(f"{key}={redact_sensitive_text(value)}" for key, value in values.items())
    assert_redacted(text, context="pipeline debug log")
    return text
