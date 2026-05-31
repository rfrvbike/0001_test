from __future__ import annotations

import json
import unittest
from pathlib import Path

from x_auto_ops.buzz_read_client import XApiBuzzReadClient
from x_auto_ops.x_response_normalizer import normalize_recent_search_response


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class XResponseNormalizerTests(unittest.TestCase):
    def test_minimal_fixture_normalizes_without_optional_fields(self) -> None:
        result = normalize_recent_search_response(
            load_fixture("recent_search_response_minimal.json"),
            source_query="minimal",
            source_genre="daily",
        )

        self.assertEqual(len(result.posts), 1)
        post = result.posts[0]
        self.assertEqual(post["post_id"], "1001")
        self.assertEqual(post["source_query"], "minimal")
        self.assertEqual(post["source_genre"], "daily")
        self.assertIsNone(post["impression_count"])
        self.assertIn("missing_author_id", post["metrics_missing"])
        self.assertIn("missing_author_username", post["metrics_missing"])
        self.assertIn("missing_public_metrics", post["metrics_missing"])

    def test_metrics_fixture_normalizes_public_metrics_and_author(self) -> None:
        result = normalize_recent_search_response(
            load_fixture("recent_search_response_with_metrics.json"),
            source_query="ai side business",
            source_genre="ai_side_business",
        )

        post = result.posts[0]
        self.assertEqual(post["author_id"], "501")
        self.assertEqual(post["author_username"], "mock_ai_author")
        self.assertEqual(post["like_count"], 120)
        self.assertEqual(post["repost_count"], 30)
        self.assertEqual(post["reply_count"], 8)
        self.assertEqual(post["quote_count"], 6)
        self.assertEqual(post["impression_count"], 15000)
        self.assertEqual(post["metrics_missing"], "")

    def test_missing_metrics_fixture_records_missing_fields(self) -> None:
        result = normalize_recent_search_response(
            load_fixture("recent_search_response_missing_metrics.json"),
            source_query="daily coffee",
            source_genre="daily",
        )

        first, second = result.posts
        self.assertEqual(first["quote_count"], 0)
        self.assertIn("missing_quote_count", first["metrics_missing"])
        self.assertIn("missing_impression_count", first["metrics_missing"])
        self.assertEqual(second["like_count"], 0)
        self.assertIn("missing_public_metrics", second["metrics_missing"])
        self.assertIn("missing_author_username", second["metrics_missing"])

    def test_partial_fixture_preserves_rate_limit_and_pagination_metadata(self) -> None:
        result = normalize_recent_search_response(
            load_fixture("recent_search_response_partial.json"),
            source_query="night relationship",
            source_genre="yokaze",
        )

        self.assertTrue(result.rate_limited)
        self.assertEqual(result.retry_after_seconds, 900)
        self.assertTrue(result.partial_result)
        self.assertEqual(result.next_token, "next-page-token")
        self.assertEqual(result.request_window, "15min")

    def test_x_api_placeholder_still_does_not_call_api(self) -> None:
        with self.assertRaises(NotImplementedError):
            XApiBuzzReadClient().fetch_posts({})


if __name__ == "__main__":
    unittest.main()
