"""Parse rate-limit headers without performing network requests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Mapping


@dataclass(frozen=True)
class RateLimitInfo:
    rate_limited: bool
    retry_after_seconds: int | None = None
    remaining_requests: int | None = None
    reset_timestamp: int | None = None


def parse_rate_limit_headers(
    headers: Mapping[str, Any] | None,
    *,
    status_code: int | None = None,
    now: datetime | None = None,
) -> RateLimitInfo:
    """Parse X-style rate-limit headers into a stable local shape."""

    normalized = {str(key).lower(): value for key, value in (headers or {}).items()}
    remaining = _nullable_int(normalized.get("x-rate-limit-remaining"))
    reset_timestamp = _nullable_int(normalized.get("x-rate-limit-reset"))
    retry_after = _parse_retry_after(normalized.get("retry-after"), now=now)

    reset_implies_wait = status_code == 429 or remaining == 0
    if retry_after is None and reset_timestamp is not None and reset_implies_wait:
        retry_after = _seconds_until(reset_timestamp, now=now)

    rate_limited = status_code == 429 or remaining == 0 or retry_after is not None

    return RateLimitInfo(
        rate_limited=rate_limited,
        retry_after_seconds=retry_after,
        remaining_requests=remaining,
        reset_timestamp=reset_timestamp,
    )


def _parse_retry_after(value: Any, *, now: datetime | None) -> int | None:
    if value is None or value == "":
        return None
    seconds = _nullable_int(value)
    if seconds is not None:
        return max(seconds, 0)
    try:
        retry_at = parsedate_to_datetime(str(value))
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    return max(int((retry_at - current).total_seconds()), 0)


def _seconds_until(reset_timestamp: int, *, now: datetime | None) -> int:
    current = now or datetime.now(timezone.utc)
    return max(int(reset_timestamp - current.timestamp()), 0)


def _nullable_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value).replace(",", ""))
    except ValueError:
        return None
