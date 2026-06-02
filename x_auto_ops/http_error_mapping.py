"""HTTP error mapping skeleton for future X API reads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from x_auto_ops.rate_limit_parser import parse_rate_limit_headers
from x_auto_ops.redaction import redact_sensitive_text


@dataclass(frozen=True)
class HttpErrorInfo:
    error_type: str
    status_code: int | None
    retryable: bool
    retry_after_seconds: int | None
    message: str
    redacted_message: str
    partial_result: bool


def map_http_error(
    *,
    error_type: str | None = None,
    status_code: int | None = None,
    headers: Mapping[str, Any] | None = None,
    message: Any = "",
    exception: BaseException | None = None,
) -> HttpErrorInfo:
    """Map HTTP/client failures to a stable, redacted local shape."""

    raw_message = str(message or "")
    if exception is not None:
        raw_message = str(exception)
    mapped_type = _resolve_error_type(
        requested=error_type,
        status_code=status_code,
        headers=headers,
        message=raw_message,
        exception=exception,
    )
    rate_limit = parse_rate_limit_headers(headers, status_code=status_code)
    retry_after = rate_limit.retry_after_seconds if mapped_type == "rate_limited" else None
    retryable = mapped_type in {"timeout", "network_error", "rate_limited", "server_error"}
    partial_result = mapped_type in {"timeout", "network_error", "rate_limited", "server_error"}
    redacted = redact_sensitive_text(raw_message or mapped_type)

    return HttpErrorInfo(
        error_type=mapped_type,
        status_code=status_code,
        retryable=retryable,
        retry_after_seconds=retry_after,
        message=redacted,
        redacted_message=redacted,
        partial_result=partial_result,
    )


def _resolve_error_type(
    *,
    requested: str | None,
    status_code: int | None,
    headers: Mapping[str, Any] | None,
    message: str,
    exception: BaseException | None,
) -> str:
    if requested:
        return requested
    if exception is not None and "HTTP client disabled" in str(exception):
        return "disabled_http_client"
    if parse_rate_limit_headers(headers, status_code=status_code).rate_limited:
        return "rate_limited"
    if status_code in {401, 403}:
        return "auth_error"
    if status_code == 429:
        return "rate_limited"
    if status_code is not None and status_code >= 500:
        return "server_error"
    if status_code is not None and status_code >= 400:
        return "client_error"
    lowered = message.lower()
    if "timeout" in lowered:
        return "timeout"
    if "json" in lowered and "parse" in lowered:
        return "json_parse_error"
    if "schema" in lowered:
        return "schema_error"
    if exception is not None:
        return "network_error"
    return "client_error"
