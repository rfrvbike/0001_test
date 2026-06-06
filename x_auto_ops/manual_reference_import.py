"""Manual reference-post CSV import helpers.

This path is intentionally local-only. It never calls X, LLM, or any external
API; it only converts a manually collected CSV into raw_posts.csv shape.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from x_auto_ops.reference_posts import RAW_POST_FIELDS, write_csv


MANUAL_INPUT_FIELDS = [
    "source_handle",
    "post_url",
    "text",
    "created_at",
    "like_count",
    "repost_count",
    "reply_count",
    "quote_count",
    "impression_count",
    "category",
    "note",
]
COUNT_FIELDS = [
    "like_count",
    "repost_count",
    "reply_count",
    "quote_count",
    "impression_count",
]
MIN_TEXT_LENGTH = 20


@dataclass(frozen=True)
class ManualImportResult:
    input_count: int
    imported_count: int
    duplicate_count: int
    warning_count: int
    output_path: Path
    dry_run: bool
    warnings: tuple[str, ...]
    rows: tuple[dict[str, str], ...]


def import_manual_reference_posts(
    *,
    input_path: str | Path,
    output_path: str | Path,
    dry_run: bool,
    now: datetime | None = None,
) -> ManualImportResult:
    input_rows = read_manual_csv(input_path)
    collected_at = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    warnings: list[str] = []
    output_rows: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    duplicate_count = 0

    for index, row in enumerate(input_rows, start=2):
        normalized_url = normalize_url(row.get("post_url", ""))
        if not normalized_url:
            raise ValueError(f"row {index}: post_url is required")
        if normalized_url in seen_urls:
            duplicate_count += 1
            warnings.append(f"row {index}: duplicate post_url skipped: {normalized_url}")
            continue
        seen_urls.add(normalized_url)

        text = str(row.get("text") or "").strip()
        category = str(row.get("category") or "").strip()
        if not text:
            raise ValueError(f"row {index}: text is required")
        if not category:
            raise ValueError(f"row {index}: category is required")
        if len(re.sub(r"\s+", "", text)) < MIN_TEXT_LENGTH:
            warnings.append(f"row {index}: text is short and may be filtered later")

        output_rows.append(
            normalize_manual_row(
                row,
                row_number=index,
                collected_at=collected_at,
                fallback_index=len(output_rows) + 1,
                warnings=warnings,
            )
        )

    output = Path(output_path)
    if not dry_run:
        write_csv(output, RAW_POST_FIELDS, output_rows)

    return ManualImportResult(
        input_count=len(input_rows),
        imported_count=len(output_rows),
        duplicate_count=duplicate_count,
        warning_count=len(warnings),
        output_path=output,
        dry_run=dry_run,
        warnings=tuple(warnings),
        rows=tuple(output_rows),
    )


def read_manual_csv(path: str | Path) -> list[dict[str, str]]:
    input_path = Path(path)
    with input_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [field for field in ["post_url", "text", "category"] if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"missing required columns: {', '.join(missing)}")
        return list(reader)


def normalize_manual_row(
    row: Mapping[str, Any],
    *,
    row_number: int,
    collected_at: str,
    fallback_index: int,
    warnings: list[str],
) -> dict[str, str]:
    post_url = normalize_url(row.get("post_url", ""))
    source_handle = str(row.get("source_handle") or "").strip().lstrip("@")
    if not source_handle:
        source_handle = extract_handle_from_url(post_url) or "manual"
    post_id = extract_post_id_from_url(post_url)
    if not post_id:
        post_id = f"manual_{fallback_index:04d}"
        warnings.append(f"row {row_number}: post_id not found; generated {post_id}")

    normalized = {
        "source_handle": source_handle,
        "post_id": post_id,
        "post_url": post_url,
        "text": str(row.get("text") or "").strip(),
        "created_at": str(row.get("created_at") or "").strip(),
        "category": str(row.get("category") or "").strip(),
        "collected_at": collected_at,
    }
    for field in COUNT_FIELDS:
        normalized[field] = normalize_count(row.get(field))
    return normalized


def extract_post_id_from_url(url: str) -> str:
    match = re.search(r"/status(?:es)?/(\d+)", url)
    if match:
        return match.group(1)
    return ""


def extract_handle_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host not in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
        return ""
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return ""
    first = parts[0].strip().lstrip("@")
    if first.lower() in {"i", "intent", "share", "search", "hashtag"}:
        return ""
    return first


def normalize_url(value: Any) -> str:
    return str(value or "").strip()


def normalize_count(value: Any) -> str:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return "0"
    try:
        number = int(float(text))
    except ValueError:
        return "0"
    if number < 0:
        return "0"
    return str(number)
