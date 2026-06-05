"""Safe diagnostic summary model for future first-live connectivity checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from x_auto_ops.http_error_mapping import HttpErrorInfo
from x_auto_ops.redaction import contains_sensitive_marker


MAX_SAFE_DEBUG_SUMMARY_LENGTH = 1024
MAX_STRING_FIELD_LENGTH = 64

SAFE_FIELD_NAMES = (
    "diagnostics_version",
    "status",
    "request_id",
    "endpoint_name",
    "method",
    "status_code",
    "query_length",
    "result_count",
    "fetched_count",
    "normalized_post_count",
    "partial_result",
    "stop_reason",
    "rate_limited",
    "retryable",
    "retry_after_seconds",
    "pagination_used",
    "next_token_present",
    "metrics_missing_count",
    "execution_time_ms",
    "rollback_completed",
)

_REQUIRED_TEXT_FIELDS = (
    "diagnostics_version",
    "status",
    "request_id",
    "endpoint_name",
    "method",
    "stop_reason",
)

_NON_NEGATIVE_INTEGER_FIELDS = (
    "query_length",
    "result_count",
    "normalized_post_count",
    "metrics_missing_count",
    "execution_time_ms",
)

_OPTIONAL_NON_NEGATIVE_INTEGER_FIELDS = (
    "status_code",
    "fetched_count",
    "retry_after_seconds",
)

_DEBUG_FIELD_ALIASES = {
    "next_token_present": "next_cursor_present",
}


class RedactedLiveSummaryValidationError(ValueError):
    """Raised when a proposed safe summary violates the output boundary."""


@dataclass(frozen=True)
class RedactedLiveSummary:
    diagnostics_version: str
    status: str
    request_id: str
    endpoint_name: str
    method: str
    query_length: int
    result_count: int
    normalized_post_count: int
    partial_result: bool
    stop_reason: str
    rate_limited: bool
    retryable: bool
    pagination_used: bool
    next_token_present: bool
    metrics_missing_count: int
    execution_time_ms: int
    rollback_completed: bool
    status_code: int | None = None
    retry_after_seconds: int | None = None
    fetched_count: int | None = None

    def __post_init__(self) -> None:
        for field_name in _REQUIRED_TEXT_FIELDS:
            _validate_safe_text(field_name, getattr(self, field_name))
        for field_name in _NON_NEGATIVE_INTEGER_FIELDS:
            _validate_non_negative_integer(field_name, getattr(self, field_name))
        for field_name in _OPTIONAL_NON_NEGATIVE_INTEGER_FIELDS:
            value = getattr(self, field_name)
            if value is not None:
                _validate_non_negative_integer(field_name, value)
        for field_name in (
            "partial_result",
            "rate_limited",
            "retryable",
            "pagination_used",
            "next_token_present",
            "rollback_completed",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise RedactedLiveSummaryValidationError(f"{field_name} must be a boolean")

    def to_safe_dict(self) -> dict[str, Any]:
        """Return the reviewed JSON-compatible allowlist only."""

        result = {field_name: getattr(self, field_name) for field_name in SAFE_FIELD_NAMES}
        for field_name, value in result.items():
            if isinstance(value, (dict, list, tuple, set)):
                raise RedactedLiveSummaryValidationError(
                    f"{field_name} must not contain nested values"
                )
            if isinstance(value, str) and contains_sensitive_marker(value):
                raise RedactedLiveSummaryValidationError("sensitive diagnostic value rejected")
        return result

    def safe_debug_summary(self) -> str:
        """Return one bounded line generated only from the safe allowlist."""

        debug_data = {
            _DEBUG_FIELD_ALIASES.get(field_name, field_name): value
            for field_name, value in self.to_safe_dict().items()
        }
        summary = json.dumps(
            debug_data,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        if "\n" in summary or "\r" in summary:
            raise RedactedLiveSummaryValidationError("safe debug summary must be one line")
        if len(summary) > MAX_SAFE_DEBUG_SUMMARY_LENGTH:
            raise RedactedLiveSummaryValidationError("safe debug summary exceeds size limit")
        if contains_sensitive_marker(summary):
            raise RedactedLiveSummaryValidationError("sensitive diagnostic value rejected")
        return summary


def build_redacted_error_summary(
    error_info: HttpErrorInfo,
    *,
    endpoint_name: str = "recent_search",
    method: str = "GET",
    query_length: int = 0,
    execution_time_ms: int = 0,
    request_id: str = "mock-error",
    rollback_completed: bool = False,
    diagnostics_version: str = "1",
) -> RedactedLiveSummary:
    """Build a safe failed-connectivity summary from mapped error metadata.

    Raw exception messages, response bodies, headers, query text, and post data
    are intentionally excluded. The stable error type is the only error detail
    that crosses into the safe summary surface.
    """

    return RedactedLiveSummary(
        diagnostics_version=diagnostics_version,
        status="error",
        request_id=request_id,
        endpoint_name=endpoint_name,
        method=method,
        status_code=error_info.status_code,
        query_length=query_length,
        result_count=0,
        fetched_count=0,
        normalized_post_count=0,
        partial_result=error_info.partial_result,
        stop_reason=error_info.error_type,
        rate_limited=error_info.error_type == "rate_limited",
        retryable=error_info.retryable,
        retry_after_seconds=error_info.retry_after_seconds,
        pagination_used=False,
        next_token_present=False,
        metrics_missing_count=0,
        execution_time_ms=execution_time_ms,
        rollback_completed=rollback_completed,
    )


def _validate_safe_text(field_name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise RedactedLiveSummaryValidationError(f"{field_name} must not be empty")
    if len(value) > MAX_STRING_FIELD_LENGTH:
        raise RedactedLiveSummaryValidationError(f"{field_name} exceeds size limit")
    if contains_sensitive_marker(value):
        raise RedactedLiveSummaryValidationError("sensitive diagnostic value rejected")


def _validate_non_negative_integer(field_name: str, value: Any) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise RedactedLiveSummaryValidationError(
            f"{field_name} must be a non-negative integer"
        )
