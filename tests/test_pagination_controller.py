from __future__ import annotations

import json
import unittest
from pathlib import Path

from x_auto_ops.buzz_read_client import BuzzFetchResult
from x_auto_ops.mock_transport import MockRecentSearchTransport, contains_sensitive_marker
from x_auto_ops.pagination_controller import (
    STOP_COMPLETED,
    STOP_MAX_PAGES_REACHED,
    STOP_MAX_RESULTS_REACHED,
    STOP_RATE_LIMITED,
    STOP_RETRY_LIMIT_REACHED,
    PaginationController,
)
from x_auto_ops.rate_limit_parser import parse_rate_limit_headers
from x_auto_ops.retry_policy import RetryPolicy
from x_auto_ops.retry_queue import RetryQueue
from x_auto_ops.x_response_normalizer import normalize_recent_search_response


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def fetch_result_from_fixture(name: str, *, query: str, genre: str = "ai_side_business") -> BuzzFetchResult:
    transport = MockRecentSearchTransport(load_fixture(name))
    response = transport.send_recent_search(query)
    rate_limit = parse_rate_limit_headers(response.headers, status_code=response.status_code)
    normalized = normalize_recent_search_response(
        response.json_body,
        source_query=query,
        source_genre=genre,
        request_window="pagination_test",
    )
    return BuzzFetchResult(
        posts=normalized.posts,
        rate_limited=rate_limit.rate_limited or normalized.rate_limited,
        retry_after_seconds=rate_limit.retry_after_seconds or normalized.retry_after_seconds,
        partial_result=normalized.partial_result,
        next_token=normalized.next_token,
        request_window=normalized.request_window,
    )


class PaginationControllerTests(unittest.TestCase):
    def test_paginates_page_1_page_2_page_last(self) -> None:
        pages = ["page_1.json", "page_2.json", "page_last.json"]
        observed_tokens: list[str | None] = []

        def fetch_page(query: str, next_token: str | None) -> BuzzFetchResult:
            observed_tokens.append(next_token)
            return fetch_result_from_fixture(pages.pop(0), query=query)

        controller = PaginationController(fetch_page=fetch_page, max_pages=5)
        result = controller.collect(query="AI lang:ja", max_results=10)

        self.assertEqual(result.pages_fetched, 3)
        self.assertEqual(len(result.posts), 3)
        self.assertEqual(result.final_next_token, "")
        self.assertFalse(result.partial_result)
        self.assertEqual(result.stopped_reason, STOP_COMPLETED)
        self.assertEqual(observed_tokens, [None, "page-two-token", "page-last-token"])

    def test_stops_when_max_results_reached(self) -> None:
        pages = ["page_1.json", "page_2.json"]

        def fetch_page(query: str, next_token: str | None) -> BuzzFetchResult:
            return fetch_result_from_fixture(pages.pop(0), query=query)

        controller = PaginationController(fetch_page=fetch_page, max_pages=5)
        result = controller.collect(query="AI lang:ja", max_results=1)

        self.assertEqual(result.pages_fetched, 1)
        self.assertEqual(len(result.posts), 1)
        self.assertEqual(result.stopped_reason, STOP_MAX_RESULTS_REACHED)
        self.assertTrue(result.partial_result)

    def test_stops_when_max_pages_reached(self) -> None:
        def fetch_page(query: str, next_token: str | None) -> BuzzFetchResult:
            return fetch_result_from_fixture("page_1.json", query=query)

        controller = PaginationController(fetch_page=fetch_page, max_pages=1)
        result = controller.collect(query="AI lang:ja", max_results=10)

        self.assertEqual(result.pages_fetched, 1)
        self.assertEqual(result.stopped_reason, STOP_MAX_PAGES_REACHED)
        self.assertTrue(result.partial_result)

    def test_rate_limited_enqueues_retry_decision(self) -> None:
        queue = RetryQueue()

        def fetch_page(query: str, next_token: str | None) -> BuzzFetchResult:
            return fetch_result_from_fixture("pipeline_rate_limited.json", query=query)

        controller = PaginationController(
            fetch_page=fetch_page,
            retry_policy=RetryPolicy(max_retry_count=3),
            retry_queue=queue,
        )
        result = controller.collect(query="AI lang:ja", max_results=10, retry_count=0)

        self.assertEqual(result.stopped_reason, STOP_RATE_LIMITED)
        self.assertTrue(result.partial_result)
        self.assertIsNotNone(result.retry_decision)
        self.assertTrue(result.retry_decision.should_retry)
        self.assertEqual(result.retry_decision.retry_after_seconds, 240)
        self.assertEqual(queue.size(), 1)

    def test_rate_limited_retry_limit_reached(self) -> None:
        queue = RetryQueue()

        def fetch_page(query: str, next_token: str | None) -> BuzzFetchResult:
            return fetch_result_from_fixture("pipeline_rate_limited.json", query=query)

        controller = PaginationController(
            fetch_page=fetch_page,
            retry_policy=RetryPolicy(max_retry_count=3),
            retry_queue=queue,
        )
        result = controller.collect(query="AI lang:ja", max_results=10, retry_count=3)

        self.assertEqual(result.stopped_reason, STOP_RETRY_LIMIT_REACHED)
        self.assertFalse(result.retry_decision.should_retry)
        self.assertEqual(queue.size(), 0)

    def test_safe_debug_summary_redacts_sensitive_next_token(self) -> None:
        def fetch_page(query: str, next_token: str | None) -> BuzzFetchResult:
            page = fetch_result_from_fixture("page_1.json", query=query)
            return BuzzFetchResult(
                posts=page.posts,
                next_token="TOKEN_SHOULD_NOT_APPEAR",
                partial_result=True,
            )

        controller = PaginationController(fetch_page=fetch_page, max_pages=1)
        result = controller.collect(query="SECRET_QUERY_SHOULD_NOT_APPEAR", max_results=10)
        summary = result.safe_debug_summary()

        self.assertFalse(contains_sensitive_marker(summary), summary)
        self.assertNotIn("TOKEN_SHOULD_NOT_APPEAR", summary)
        self.assertNotIn("SECRET_QUERY_SHOULD_NOT_APPEAR", summary)


class RetryPolicyTests(unittest.TestCase):
    def test_default_max_retry_count_is_three(self) -> None:
        policy = RetryPolicy()

        decision = policy.decide(retryable=True, retry_after_seconds=60, retry_count=2)
        blocked = policy.decide(retryable=True, retry_after_seconds=60, retry_count=3)

        self.assertEqual(decision.max_retry_count, 3)
        self.assertTrue(decision.should_retry)
        self.assertFalse(blocked.should_retry)

    def test_non_retryable_is_never_retried(self) -> None:
        policy = RetryPolicy(max_retry_count=3)
        decision = policy.decide(retryable=False, retry_after_seconds=60, retry_count=0)

        self.assertFalse(decision.should_retry)


if __name__ == "__main__":
    unittest.main()
