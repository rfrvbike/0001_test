from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from x_auto_ops.query_builder import QueryBuildError, build_recent_search_query
from x_auto_ops.rate_limit_parser import parse_rate_limit_headers


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class RecentSearchQueryBuilderTests(unittest.TestCase):
    def test_builds_recent_search_query(self) -> None:
        result = build_recent_search_query(
            {
                "source_genre": "ai_side_business",
                "search_queries": ["AI", "ChatGPT", "Claude"],
            }
        )

        self.assertEqual(result.query, "(AI OR ChatGPT OR Claude) lang:ja")
        self.assertEqual(result.source_genre, "ai_side_business")

    def test_supports_target_accounts(self) -> None:
        result = build_recent_search_query(
            {
                "id": "daily",
                "search_queries": ["coffee"],
                "target_accounts": ["@daily_author", "daily_author", "life_123"],
            }
        )

        self.assertIn("coffee", result.query)
        self.assertIn("(from:daily_author OR from:life_123)", result.query)
        self.assertEqual(result.target_accounts, ("daily_author", "life_123"))

    def test_supports_exclude_keywords(self) -> None:
        result = build_recent_search_query(
            {
                "source_genre": "yokaze",
                "search_queries": ["night feeling"],
                "exclude_keywords": ["giveaway", "crypto campaign"],
            }
        )

        self.assertIn('"night feeling"', result.query)
        self.assertIn("-giveaway", result.query)
        self.assertIn('-"crypto campaign"', result.query)

    def test_removes_duplicate_keywords_case_insensitive(self) -> None:
        result = build_recent_search_query(
            {
                "search_queries": ["AI", "ai", "Claude", "Claude"],
                "target_accounts": ["@A", "a"],
                "exclude_keywords": ["spam", "SPAM"],
            }
        )

        self.assertEqual(result.search_terms, ("AI", "Claude"))
        self.assertEqual(result.target_accounts, ("A",))
        self.assertEqual(result.exclude_keywords, ("spam",))
        self.assertEqual(result.query.count("AI"), 1)

    def test_empty_query_raises(self) -> None:
        with self.assertRaises(QueryBuildError):
            build_recent_search_query({"exclude_keywords": ["spam"]})

    def test_too_long_query_raises(self) -> None:
        with self.assertRaises(QueryBuildError):
            build_recent_search_query({"search_queries": ["a" * 20]}, max_length=10)


class RateLimitHeaderParserTests(unittest.TestCase):
    fixed_now = datetime(2026, 5, 31, 0, 0, 0, tzinfo=timezone.utc)

    def test_parses_normal_headers(self) -> None:
        info = parse_rate_limit_headers(load_fixture("rate_limit_headers_normal.json"), now=self.fixed_now)

        self.assertFalse(info.rate_limited)
        self.assertEqual(info.remaining_requests, 42)
        self.assertEqual(info.reset_timestamp, 1780186200)
        self.assertIsNone(info.retry_after_seconds)

    def test_parses_retry_after_headers(self) -> None:
        info = parse_rate_limit_headers(
            load_fixture("rate_limit_headers_retry_after.json"),
            status_code=429,
            now=self.fixed_now,
        )

        self.assertTrue(info.rate_limited)
        self.assertEqual(info.retry_after_seconds, 120)
        self.assertEqual(info.remaining_requests, 0)

    def test_parses_reset_only_headers(self) -> None:
        info = parse_rate_limit_headers(load_fixture("rate_limit_headers_reset_only.json"), now=self.fixed_now)

        self.assertTrue(info.rate_limited)
        self.assertEqual(info.retry_after_seconds, 600)
        self.assertEqual(info.reset_timestamp, 1780186200)

    def test_missing_headers_are_safe(self) -> None:
        info = parse_rate_limit_headers({}, now=self.fixed_now)

        self.assertFalse(info.rate_limited)
        self.assertIsNone(info.retry_after_seconds)
        self.assertIsNone(info.remaining_requests)
        self.assertIsNone(info.reset_timestamp)

    def test_invalid_header_values_are_safe(self) -> None:
        info = parse_rate_limit_headers(
            {
                "Retry-After": "not-a-number",
                "x-rate-limit-remaining": "many",
                "x-rate-limit-reset": "later",
            },
            now=self.fixed_now,
        )

        self.assertFalse(info.rate_limited)
        self.assertIsNone(info.retry_after_seconds)
        self.assertIsNone(info.remaining_requests)
        self.assertIsNone(info.reset_timestamp)


if __name__ == "__main__":
    unittest.main()
