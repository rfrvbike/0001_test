from __future__ import annotations

import json
import unittest

from x_auto_ops.redacted_live_summary import (
    MAX_SAFE_DEBUG_SUMMARY_LENGTH,
    SAFE_FIELD_NAMES,
    RedactedLiveSummary,
    RedactedLiveSummaryValidationError,
)
from x_auto_ops.redaction import contains_sensitive_marker


def _summary(**overrides: object) -> RedactedLiveSummary:
    values: dict[str, object] = {
        "diagnostics_version": "1",
        "status": "success",
        "request_id": "request-001",
        "endpoint_name": "recent_search",
        "method": "GET",
        "query_length": 24,
        "result_count": 2,
        "normalized_post_count": 2,
        "partial_result": False,
        "stop_reason": "completed",
        "rate_limited": False,
        "retryable": False,
        "pagination_used": False,
        "next_token_present": False,
        "metrics_missing_count": 1,
        "execution_time_ms": 120,
        "rollback_completed": False,
    }
    values.update(overrides)
    return RedactedLiveSummary(**values)  # type: ignore[arg-type]


class RedactedLiveSummaryTests(unittest.TestCase):
    def test_to_safe_dict_returns_allowlist_and_json_compatible_values(self) -> None:
        safe = _summary().to_safe_dict()

        self.assertEqual(tuple(safe), SAFE_FIELD_NAMES)
        self.assertEqual(safe["endpoint_name"], "recent_search")
        self.assertEqual(safe["result_count"], 2)
        json.dumps(safe)

    def test_optional_fields_are_included_when_present(self) -> None:
        safe = _summary(status_code=200, retry_after_seconds=30, fetched_count=2).to_safe_dict()

        self.assertEqual(safe["status_code"], 200)
        self.assertEqual(safe["retry_after_seconds"], 30)
        self.assertEqual(safe["fetched_count"], 2)

    def test_optional_fields_are_none_when_absent(self) -> None:
        safe = _summary().to_safe_dict()

        self.assertIsNone(safe["status_code"])
        self.assertIsNone(safe["retry_after_seconds"])
        self.assertIsNone(safe["fetched_count"])

    def test_safe_debug_summary_is_one_line_and_bounded(self) -> None:
        debug = _summary(status_code=200).safe_debug_summary()

        self.assertNotIn("\n", debug)
        self.assertLessEqual(len(debug), MAX_SAFE_DEBUG_SUMMARY_LENGTH)
        self.assertEqual(json.loads(debug)["status_code"], 200)
        self.assertIn("next_cursor_present", debug)
        self.assertNotIn("next_token_present", debug)
        self.assertFalse(contains_sensitive_marker(debug), debug)

    def test_rejects_empty_endpoint_and_method(self) -> None:
        for field_name in ("endpoint_name", "method"):
            with self.subTest(field_name=field_name):
                with self.assertRaises(RedactedLiveSummaryValidationError):
                    _summary(**{field_name: ""})

    def test_rejects_empty_diagnostics_version(self) -> None:
        with self.assertRaises(RedactedLiveSummaryValidationError):
            _summary(diagnostics_version="")

    def test_rejects_negative_query_length_and_execution_time(self) -> None:
        for field_name in ("query_length", "result_count", "execution_time_ms"):
            with self.subTest(field_name=field_name):
                with self.assertRaises(RedactedLiveSummaryValidationError):
                    _summary(**{field_name: -1})

    def test_rejects_credential_markers_without_leaking_them_in_exception(self) -> None:
        for marker in ("Authorization", "Bearer", "API_KEY", "TOKEN", "SECRET", "COOKIE"):
            with self.subTest(marker=marker):
                with self.assertRaises(RedactedLiveSummaryValidationError) as ctx:
                    _summary(request_id=marker)
                self.assertNotIn(marker, str(ctx.exception))
                self.assertFalse(contains_sensitive_marker(str(ctx.exception)))


if __name__ == "__main__":
    unittest.main()
