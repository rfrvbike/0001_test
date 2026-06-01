from __future__ import annotations

import json
import unittest
from pathlib import Path

from x_auto_ops.buzz_read_client import XApiBuzzReadClient
from x_auto_ops.mock_transport import (
    MockRecentSearchTransport,
    contains_sensitive_marker,
    render_posts_csv_for_leak_test,
    run_mock_recent_search_pipeline,
)


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def base_config() -> dict:
    return {
        "source_genre": "ai_side_business",
        "search_queries": ["AI workflow", "ChatGPT"],
        "target_accounts": ["mock_builder"],
        "exclude_keywords": ["giveaway"],
    }


class MockTransportPipelineTests(unittest.TestCase):
    def test_mock_pipeline_success(self) -> None:
        transport = MockRecentSearchTransport(load_fixture("transport_success.json"))

        result = run_mock_recent_search_pipeline(base_config(), transport)

        self.assertEqual(len(result.fetch_result.posts), 1)
        self.assertEqual(result.transport_response.status_code, 200)
        self.assertFalse(result.fetch_result.rate_limited)
        self.assertEqual(result.rate_limit.remaining_requests, 19)
        self.assertIn('"AI workflow"', result.query.query)
        self.assertEqual(transport.sent_queries, [result.query.query])
        self.assertEqual(result.fetch_result.posts[0]["post_id"], "3001")
        self.assertEqual(result.fetch_result.posts[0]["source_genre"], "ai_side_business")

    def test_mock_pipeline_partial_result_and_next_token(self) -> None:
        config = {
            "source_genre": "daily",
            "search_queries": ["Sunday night coffee"],
        }
        transport = MockRecentSearchTransport(load_fixture("transport_partial.json"))

        result = run_mock_recent_search_pipeline(config, transport)

        self.assertTrue(result.fetch_result.partial_result)
        self.assertEqual(result.fetch_result.next_token, "partial-next-token")
        self.assertEqual(result.fetch_result.posts[0]["source_genre"], "daily")

    def test_mock_pipeline_rate_limited_retry_after(self) -> None:
        transport = MockRecentSearchTransport(load_fixture("transport_rate_limited.json"))

        result = run_mock_recent_search_pipeline(base_config(), transport)

        self.assertTrue(result.fetch_result.rate_limited)
        self.assertEqual(result.fetch_result.retry_after_seconds, 180)
        self.assertTrue(result.fetch_result.partial_result)
        self.assertEqual(result.fetch_result.posts, [])

    def test_mock_pipeline_records_metrics_missing(self) -> None:
        transport = MockRecentSearchTransport(load_fixture("transport_partial.json"))

        result = run_mock_recent_search_pipeline(
            {"source_genre": "daily", "search_queries": ["coffee"]},
            transport,
        )

        missing = result.fetch_result.posts[0]["metrics_missing"]
        self.assertIn("missing_quote_count", missing)
        self.assertIn("missing_impression_count", missing)

    def test_credential_markers_do_not_leak_to_debug_log_or_csv(self) -> None:
        config = {
            **base_config(),
            "api_key": "API_KEY_SHOULD_NOT_APPEAR",
            "token": "TOKEN_SHOULD_NOT_APPEAR",
            "bearer": "BEARER_SHOULD_NOT_APPEAR",
            "client_secret": "SECRET_SHOULD_NOT_APPEAR",
            "cookie": "COOKIE_SHOULD_NOT_APPEAR",
            "authorization": "AUTHORIZATION_SHOULD_NOT_APPEAR",
        }
        transport = MockRecentSearchTransport(load_fixture("transport_success.json"))

        result = run_mock_recent_search_pipeline(config, transport)
        csv_text = render_posts_csv_for_leak_test(result.fetch_result.posts)

        self.assertFalse(contains_sensitive_marker(result.debug_log), result.debug_log)
        self.assertFalse(contains_sensitive_marker(csv_text), csv_text)

    def test_x_api_read_client_blocks_non_dry_run(self) -> None:
        with self.assertRaises(RuntimeError):
            XApiBuzzReadClient(dry_run=False).fetch_posts(base_config())

        with self.assertRaises(RuntimeError):
            XApiBuzzReadClient().fetch_posts({**base_config(), "dry_run": False})


if __name__ == "__main__":
    unittest.main()
