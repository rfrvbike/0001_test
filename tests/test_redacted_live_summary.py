from __future__ import annotations

import json
import unittest

from x_auto_ops.http_error_mapping import map_http_error
from x_auto_ops.redacted_live_summary import (
    MAX_SAFE_DEBUG_SUMMARY_LENGTH,
    SAFE_FIELD_NAMES,
    RedactedLiveSummary,
    RedactedLiveSummaryValidationError,
    build_redacted_error_summary,
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

    def test_build_redacted_error_summary_maps_supported_error_types(self) -> None:
        cases = {
            "auth_error": map_http_error(status_code=401, message="auth failed"),
            "timeout": map_http_error(error_type="timeout", message="request timeout"),
            "network_error": map_http_error(exception=OSError("connection reset")),
            "rate_limited": map_http_error(
                status_code=429,
                headers={"Retry-After": "90"},
                message="too many requests",
            ),
            "server_error": map_http_error(status_code=503, message="service down"),
            "client_error": map_http_error(status_code=400, message="bad request"),
            "json_parse_error": map_http_error(
                error_type="json_parse_error",
                message="json parse failed",
            ),
            "schema_error": map_http_error(
                error_type="schema_error",
                message="schema mismatch",
            ),
            "disabled_http_client": map_http_error(
                exception=RuntimeError("HTTP client disabled")
            ),
        }

        for error_type, info in cases.items():
            with self.subTest(error_type=error_type):
                summary = build_redacted_error_summary(
                    info,
                    endpoint_name="recent_search",
                    method="GET",
                    query_length=88,
                    execution_time_ms=15,
                    request_id="error-test",
                )
                safe = summary.to_safe_dict()
                debug = summary.safe_debug_summary()

                self.assertEqual(safe["status"], "error")
                self.assertEqual(safe["stop_reason"], error_type)
                self.assertEqual(safe["status_code"], info.status_code)
                self.assertEqual(safe["query_length"], 88)
                self.assertEqual(safe["result_count"], 0)
                self.assertEqual(safe["fetched_count"], 0)
                self.assertEqual(safe["normalized_post_count"], 0)
                self.assertEqual(safe["partial_result"], info.partial_result)
                self.assertEqual(safe["retryable"], info.retryable)
                self.assertEqual(safe["retry_after_seconds"], info.retry_after_seconds)
                self.assertEqual(safe["rate_limited"], error_type == "rate_limited")
                self.assertFalse(safe["pagination_used"])
                self.assertFalse(safe["next_token_present"])
                self.assertEqual(safe["metrics_missing_count"], 0)
                json.dumps(safe)
                self.assertLessEqual(len(debug), MAX_SAFE_DEBUG_SUMMARY_LENGTH)
                self.assertFalse(contains_sensitive_marker(debug), debug)

    def test_build_redacted_error_summary_excludes_raw_error_details(self) -> None:
        info = map_http_error(
            status_code=500,
            message=(
                "raw body API_KEY=abc TOKEN=def SECRET=ghi COOKIE=jkl "
                "AUTHORIZATION=Bearer mno query=(AI workflow) post_id=4001 "
                "author_id=801 username=pipeline_ai_top"
            ),
        )

        summary = build_redacted_error_summary(info, query_length=88)
        safe_values = list(summary.to_safe_dict().values())
        combined = json.dumps(safe_values, ensure_ascii=True) + summary.safe_debug_summary()

        for blocked in (
            "raw body",
            "abc",
            "def",
            "ghi",
            "jkl",
            "mno",
            "AI workflow",
            "4001",
            "801",
            "pipeline_ai_top",
            "Authorization",
            "Bearer",
            "API_KEY",
            "TOKEN",
            "SECRET",
            "COOKIE",
        ):
            self.assertNotIn(blocked, combined)
        self.assertFalse(contains_sensitive_marker(combined), combined)


if __name__ == "__main__":
    unittest.main()
