"""Pagination controller skeleton for future X recent-search reads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from x_auto_ops.buzz_read_client import BuzzFetchResult
from x_auto_ops.redaction import redact_sensitive_text
from x_auto_ops.retry_policy import RetryDecision, RetryPolicy
from x_auto_ops.retry_queue import RetryQueue


STOP_COMPLETED = "completed"
STOP_MAX_RESULTS_REACHED = "max_results_reached"
STOP_MAX_PAGES_REACHED = "max_pages_reached"
STOP_NO_NEXT_TOKEN = "no_next_token"
STOP_RATE_LIMITED = "rate_limited"
STOP_TRANSPORT_ERROR = "transport_error"
STOP_RETRY_LIMIT_REACHED = "retry_limit_reached"

PageFetcher = Callable[[str, str | None], BuzzFetchResult]


@dataclass(frozen=True)
class PaginationState:
    current_page: int = 0
    next_token: str = ""
    fetched_count: int = 0
    max_results: int = 100
    page_count: int = 0
    partial_result: bool = False


@dataclass(frozen=True)
class PaginationResult:
    posts: list[dict]
    pages_fetched: int
    final_next_token: str
    partial_result: bool
    stopped_reason: str
    retry_decision: RetryDecision | None = None

    def safe_debug_summary(self) -> str:
        return (
            f"pages_fetched={self.pages_fetched} "
            f"post_count={len(self.posts)} "
            f"final_cursor={redact_sensitive_text(self.final_next_token)} "
            f"partial_result={self.partial_result} "
            f"stopped_reason={redact_sensitive_text(self.stopped_reason)}"
        )


class PaginationController:
    """Drive mock pagination without performing transport work itself."""

    def __init__(
        self,
        *,
        fetch_page: PageFetcher,
        retry_policy: RetryPolicy | None = None,
        retry_queue: RetryQueue | None = None,
        max_pages: int = 10,
    ) -> None:
        self.fetch_page = fetch_page
        self.retry_policy = retry_policy or RetryPolicy()
        self.retry_queue = retry_queue or RetryQueue()
        self.max_pages = max(int(max_pages), 1)

    def collect(
        self,
        *,
        query: str,
        max_results: int,
        initial_next_token: str | None = None,
        retry_count: int = 0,
    ) -> PaginationResult:
        query_text = str(query)
        limit = max(int(max_results), 0)
        posts: list[dict] = []
        next_token = str(initial_next_token or "")
        pages_fetched = 0
        partial_result = False
        retry_decision: RetryDecision | None = None

        while pages_fetched < self.max_pages and len(posts) < limit:
            try:
                page = self.fetch_page(query_text, next_token or None)
            except Exception:
                decision = self.retry_policy.decide(
                    retryable=True,
                    retry_after_seconds=None,
                    retry_count=retry_count,
                )
                if decision.should_retry:
                    self.retry_queue.enqueue(query_text, decision.retry_after_seconds, retry_count=retry_count)
                return PaginationResult(
                    posts=posts,
                    pages_fetched=pages_fetched,
                    final_next_token=next_token,
                    partial_result=True,
                    stopped_reason=STOP_TRANSPORT_ERROR,
                    retry_decision=decision,
                )

            pages_fetched += 1
            partial_result = partial_result or bool(page.partial_result)
            if page.rate_limited:
                decision = self.retry_policy.decide(
                    retryable=True,
                    retry_after_seconds=page.retry_after_seconds,
                    retry_count=retry_count,
                )
                if decision.should_retry:
                    self.retry_queue.enqueue(
                        query_text,
                        decision.retry_after_seconds,
                        retry_count=retry_count,
                    )
                    reason = STOP_RATE_LIMITED
                else:
                    reason = STOP_RETRY_LIMIT_REACHED
                return PaginationResult(
                    posts=posts,
                    pages_fetched=pages_fetched,
                    final_next_token=page.next_token or next_token,
                    partial_result=True,
                    stopped_reason=reason,
                    retry_decision=decision,
                )

            remaining = max(limit - len(posts), 0)
            posts.extend(list(page.posts)[:remaining])
            next_token = str(page.next_token or "")
            if len(posts) >= limit:
                return PaginationResult(
                    posts=posts,
                    pages_fetched=pages_fetched,
                    final_next_token=next_token,
                    partial_result=partial_result or bool(next_token),
                    stopped_reason=STOP_MAX_RESULTS_REACHED,
                )
            if not next_token:
                return PaginationResult(
                    posts=posts,
                    pages_fetched=pages_fetched,
                    final_next_token="",
                    partial_result=False,
                    stopped_reason=STOP_COMPLETED,
                )

        return PaginationResult(
            posts=posts,
            pages_fetched=pages_fetched,
            final_next_token=next_token,
            partial_result=True,
            stopped_reason=STOP_MAX_PAGES_REACHED,
        )
