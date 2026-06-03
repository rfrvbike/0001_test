"""Recent-search-only preflight validation for future live X API reads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from x_auto_ops.http_client import HttpRequest
from x_auto_ops.redaction import redact_sensitive_text
from x_auto_ops.request_builder import DEFAULT_RECENT_SEARCH_ENDPOINT


RECENT_SEARCH_PATH = "/2/tweets/search/recent"
MAX_RECENT_SEARCH_QUERY_LENGTH = 512
ALLOWED_METHOD = "GET"


class PreflightValidationError(ValueError):
    """Raised when a prepared request is not allowed for recent search."""


@dataclass(frozen=True)
class RecentSearchAllowlistPolicy:
    allowed_methods: tuple[str, ...] = (ALLOWED_METHOD,)
    allowed_endpoints: tuple[str, ...] = (
        DEFAULT_RECENT_SEARCH_ENDPOINT,
        RECENT_SEARCH_PATH,
    )
    max_query_length: int = MAX_RECENT_SEARCH_QUERY_LENGTH
    denied_endpoint_prefixes: tuple[str, ...] = (
        "/2/dm",
        "/2/media",
    )
    denied_endpoint_exact: tuple[str, ...] = (
        "/2/tweets",
        "/2/users",
    )
    denied_endpoint_contains: tuple[str, ...] = (
        "/following",
        "/likes",
        "/liking",
        "/retweeted_by",
    )


@dataclass(frozen=True)
class ValidationResult:
    allowed: bool
    method: str
    endpoint: str
    query_length: int
    endpoint_name: str
    validation_reason: str
    header_names: tuple[str, ...] = field(default_factory=tuple)

    def safe_debug_summary(self) -> str:
        safe_header_names = tuple(redact_sensitive_text(name) for name in self.header_names)
        return (
            f"allowed={self.allowed} "
            f"method={redact_sensitive_text(self.method)} "
            f"endpoint={redact_sensitive_text(self.endpoint)} "
            f"endpoint_name={redact_sensitive_text(self.endpoint_name)} "
            f"query_length={self.query_length} "
            f"validation_reason={redact_sensitive_text(self.validation_reason)} "
            f"header_names={safe_header_names}"
        )


def validate_recent_search_request(
    request: HttpRequest,
    *,
    policy: RecentSearchAllowlistPolicy | None = None,
) -> ValidationResult:
    """Validate that a prepared request is a safe read-only recent-search call."""

    active_policy = policy or RecentSearchAllowlistPolicy()
    method = str(request.method or "").strip().upper()
    endpoint = str(request.url or "").strip()
    normalized_endpoint = _normalize_endpoint(endpoint)
    query = _extract_query(request.query_params)
    query_length = len(query)
    header_names = tuple(request.headers.keys())

    def result(reason: str) -> ValidationResult:
        return ValidationResult(
            allowed=True,
            method=method,
            endpoint=normalized_endpoint,
            query_length=query_length,
            endpoint_name="recent_search",
            validation_reason=reason,
            header_names=header_names,
        )

    if not endpoint:
        _raise("recent search endpoint is empty")
    if not method:
        _raise("recent search method is empty")
    if method not in active_policy.allowed_methods:
        _raise(f"method {method} is not allowed for recent search")
    _validate_endpoint(normalized_endpoint, active_policy)
    if not query:
        _raise("recent search query is empty")
    if query_length > active_policy.max_query_length:
        _raise(
            f"recent search query length {query_length} exceeds "
            f"{active_policy.max_query_length}"
        )
    if request.timeout_seconds <= 0:
        _raise("timeout_seconds must be a positive number")

    return result("recent search request allowed")


def _extract_query(query_params: Mapping[str, str]) -> str:
    return str(query_params.get("query") or "").strip()


def _normalize_endpoint(endpoint: str) -> str:
    endpoint_without_query = endpoint.split("?", 1)[0].strip()
    if endpoint_without_query.endswith("/") and endpoint_without_query != "/":
        endpoint_without_query = endpoint_without_query.rstrip("/")
    if endpoint_without_query.startswith("https://api.x.com"):
        return endpoint_without_query
    if endpoint_without_query.startswith("http://api.x.com"):
        return endpoint_without_query.replace("http://api.x.com", "https://api.x.com", 1)
    return endpoint_without_query


def _endpoint_path(endpoint: str) -> str:
    if endpoint.startswith("https://api.x.com"):
        path = endpoint.removeprefix("https://api.x.com")
        return path or "/"
    return endpoint


def _validate_endpoint(endpoint: str, policy: RecentSearchAllowlistPolicy) -> None:
    path = _endpoint_path(endpoint)
    if path in policy.denied_endpoint_exact:
        _raise(f"endpoint {path} is denied")
    if any(path.startswith(prefix) for prefix in policy.denied_endpoint_prefixes):
        _raise(f"endpoint {path} is denied")
    if any(fragment in path for fragment in policy.denied_endpoint_contains):
        _raise(f"endpoint {path} is denied")
    if endpoint not in policy.allowed_endpoints and path not in policy.allowed_endpoints:
        _raise(f"endpoint {path} is not allowlisted for recent search")


def _raise(message: str) -> None:
    raise PreflightValidationError(redact_sensitive_text(message))
