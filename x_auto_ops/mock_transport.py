"""Mock transport and pipeline for future X recent-search reads.

This module never opens sockets, never reads credentials, and never touches
environment variables. It lets tests exercise the future flow from query
building to response normalization using local fixture-like dictionaries.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from x_auto_ops.buzz_read_client import BuzzFetchResult
from x_auto_ops.query_builder import RecentSearchQuery, build_recent_search_query
from x_auto_ops.rate_limit_parser import RateLimitInfo, parse_rate_limit_headers
from x_auto_ops.redaction import contains_sensitive_marker as _contains_sensitive_marker
from x_auto_ops.redaction import redact_sensitive_text
from x_auto_ops.x_response_normalizer import normalize_recent_search_response


@dataclass(frozen=True)
class TransportResponse:
    status_code: int
    headers: dict[str, str]
    json_body: dict[str, Any]


class RecentSearchTransport(Protocol):
    def send_recent_search(self, query: str) -> TransportResponse:
        """Return an HTTP-shaped response for a recent-search query."""


@dataclass(frozen=True)
class MockRecentSearchPipelineResult:
    query: RecentSearchQuery
    transport_response: TransportResponse
    rate_limit: RateLimitInfo
    fetch_result: BuzzFetchResult
    debug_log: str


class MockRecentSearchTransport:
    """Fixture-backed recent-search transport with no HTTP behavior."""

    def __init__(self, response: Mapping[str, Any]) -> None:
        self.response = response
        self.sent_queries: list[str] = []

    def send_recent_search(self, query: str) -> TransportResponse:
        self.sent_queries.append(str(query))
        return TransportResponse(
            status_code=_int(self.response.get("status_code"), default=200),
            headers={str(key): str(value) for key, value in _dict(self.response.get("headers")).items()},
            json_body=dict(_dict(self.response.get("json_body"))),
        )


def run_mock_recent_search_pipeline(
    config: Mapping[str, Any] | Any,
    transport: MockRecentSearchTransport,
) -> MockRecentSearchPipelineResult:
    """Run query -> mock transport -> headers -> normalizer as one local flow."""

    query = build_recent_search_query(config)
    response = transport.send_recent_search(query.query)
    rate_limit = parse_rate_limit_headers(response.headers, status_code=response.status_code)
    normalized = normalize_recent_search_response(
        response.json_body,
        source_query=query.query,
        source_genre=query.source_genre,
        request_window="recent_search_mock",
    )
    fetch_result = BuzzFetchResult(
        posts=normalized.posts,
        rate_limited=rate_limit.rate_limited or normalized.rate_limited,
        retry_after_seconds=rate_limit.retry_after_seconds or normalized.retry_after_seconds,
        partial_result=normalized.partial_result,
        next_token=normalized.next_token,
        request_window=normalized.request_window,
    )
    debug_log = _safe_debug_log(
        {
            "source_genre": query.source_genre,
            "query_length": len(query.query),
            "status_code": response.status_code,
            "post_count": len(fetch_result.posts),
            "rate_limited": fetch_result.rate_limited,
            "partial_result": fetch_result.partial_result,
            "next_cursor_present": bool(fetch_result.next_token),
        }
    )
    return MockRecentSearchPipelineResult(
        query=query,
        transport_response=response,
        rate_limit=rate_limit,
        fetch_result=fetch_result,
        debug_log=debug_log,
    )


def render_posts_csv_for_leak_test(posts: list[dict[str, Any]]) -> str:
    """Render a minimal CSV string for credential leak tests."""

    fields = [
        "post_id",
        "author_username",
        "text",
        "like_count",
        "repost_count",
        "reply_count",
        "quote_count",
        "impression_count",
        "metrics_missing",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in posts:
        writer.writerow({field: redact_sensitive(row.get(field, "")) for field in fields})
    return output.getvalue()


def contains_sensitive_marker(value: str) -> bool:
    return _contains_sensitive_marker(value)


def _safe_debug_log(values: Mapping[str, Any]) -> str:
    return " ".join(f"{key}={redact_sensitive(value)}" for key, value in values.items())


def redact_sensitive(value: Any) -> str:
    return redact_sensitive_text(value)


def _dict(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _int(value: Any, *, default: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default
