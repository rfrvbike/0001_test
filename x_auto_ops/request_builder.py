"""HTTP request builder skeleton for future X recent-search reads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from x_auto_ops.credential_loader import CredentialBundle
from x_auto_ops.http_client import HttpRequest
from x_auto_ops.query_builder import RecentSearchQuery
from x_auto_ops.redaction import redact_sensitive_text


DEFAULT_RECENT_SEARCH_ENDPOINT = "https://api.x.com/2/tweets/search/recent"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_USER_AGENT = "x-auto-ops-runtime/0.1 dry-run-prelive"


class RequestBuildError(ValueError):
    """Raised when an HTTP request cannot be built safely."""


@dataclass(frozen=True)
class RequestBuildResult:
    endpoint_name: str
    request: HttpRequest
    query: str
    query_params: dict[str, str]
    header_names: tuple[str, ...]
    timeout_seconds: float

    def safe_debug_summary(self) -> str:
        safe_header_names = tuple(redact_sensitive_text(name) for name in self.header_names)
        return (
            f"endpoint_name={redact_sensitive_text(self.endpoint_name)} "
            f"query_length={len(self.query)} "
            f"query_param_names={tuple(self.query_params.keys())} "
            f"header_names={safe_header_names} "
            f"timeout_seconds={self.timeout_seconds}"
        )


def build_recent_search_request(
    *,
    query: str | RecentSearchQuery,
    credential_bundle: CredentialBundle,
    config: Mapping[str, Any] | None = None,
) -> RequestBuildResult:
    """Build a prepared recent-search request without sending it."""

    values = dict(config or {})
    query_text = _query_text(query)
    if "endpoint" in values:
        endpoint = str(values.get("endpoint") or "").strip()
    else:
        endpoint = DEFAULT_RECENT_SEARCH_ENDPOINT
    timeout_seconds = _timeout(values.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
    if not query_text:
        raise RequestBuildError("recent search request query is empty")
    if not endpoint:
        raise RequestBuildError("recent search endpoint is empty")

    query_params = {
        "query": query_text,
        "tweet.fields": str(
            values.get(
                "tweet_fields",
                "created_at,public_metrics,author_id",
            )
        ),
        "expansions": str(values.get("expansions", "author_id")),
        "user.fields": str(values.get("user_fields", "username")),
    }
    headers = {
        "Authorization": f"Bearer {credential_bundle.bearer_token}",
        "User-Agent": str(values.get("user_agent") or DEFAULT_USER_AGENT),
        "Accept": "application/json",
    }
    request = HttpRequest(
        method="GET",
        url=endpoint,
        headers=headers,
        query_params=query_params,
        timeout_seconds=timeout_seconds,
    )
    return RequestBuildResult(
        endpoint_name="recent_search",
        request=request,
        query=query_text,
        query_params=dict(query_params),
        header_names=tuple(headers.keys()),
        timeout_seconds=timeout_seconds,
    )


def _query_text(query: str | RecentSearchQuery) -> str:
    if isinstance(query, RecentSearchQuery):
        return query.query.strip()
    return str(query or "").strip()


def _timeout(value: Any) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        raise RequestBuildError("timeout_seconds must be a positive number") from None
    if timeout <= 0:
        raise RequestBuildError("timeout_seconds must be a positive number")
    return timeout
