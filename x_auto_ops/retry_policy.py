"""Retry decision skeleton for future paginated X reads."""

from __future__ import annotations

from dataclasses import dataclass

from x_auto_ops.http_error_mapping import HttpErrorInfo


DEFAULT_MAX_RETRY_COUNT = 3


@dataclass(frozen=True)
class RetryDecision:
    retryable: bool
    retry_after_seconds: int | None
    retry_count: int
    max_retry_count: int
    should_retry: bool


class RetryPolicy:
    """Decide whether a retry could be scheduled. It never retries itself."""

    def __init__(self, *, max_retry_count: int = DEFAULT_MAX_RETRY_COUNT) -> None:
        self.max_retry_count = max(int(max_retry_count), 0)

    def decide(
        self,
        *,
        retryable: bool,
        retry_after_seconds: int | None = None,
        retry_count: int = 0,
    ) -> RetryDecision:
        count = max(int(retry_count), 0)
        should_retry = bool(retryable) and count < self.max_retry_count
        return RetryDecision(
            retryable=bool(retryable),
            retry_after_seconds=retry_after_seconds,
            retry_count=count,
            max_retry_count=self.max_retry_count,
            should_retry=should_retry,
        )

    def decide_for_error(
        self,
        error: HttpErrorInfo,
        *,
        retry_count: int = 0,
    ) -> RetryDecision:
        return self.decide(
            retryable=error.retryable,
            retry_after_seconds=error.retry_after_seconds,
            retry_count=retry_count,
        )
