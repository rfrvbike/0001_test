from __future__ import annotations

import unittest

from x_auto_ops.http_client import DisabledHttpClient, HttpRequest
from x_auto_ops.http_error_mapping import HttpErrorInfo, map_http_error
from x_auto_ops.mock_transport import contains_sensitive_marker


class HttpErrorMappingTests(unittest.TestCase):
    def test_timeout_maps_retryable_partial(self) -> None:
        info = map_http_error(error_type="timeout", message="request timeout")

        self.assertEqual(info.error_type, "timeout")
        self.assertTrue(info.retryable)
        self.assertTrue(info.partial_result)

    def test_network_error_maps_retryable_partial(self) -> None:
        info = map_http_error(exception=OSError("connection reset"))

        self.assertEqual(info.error_type, "network_error")
        self.assertTrue(info.retryable)
        self.assertTrue(info.partial_result)

    def test_auth_status_maps_auth_error(self) -> None:
        for status_code in (401, 403):
            info = map_http_error(status_code=status_code, message="auth failed")

            self.assertEqual(info.error_type, "auth_error")
            self.assertEqual(info.status_code, status_code)
            self.assertFalse(info.retryable)
            self.assertFalse(info.partial_result)

    def test_429_maps_rate_limited_with_retry_after(self) -> None:
        info = map_http_error(
            status_code=429,
            headers={"Retry-After": "120"},
            message="too many requests",
        )

        self.assertEqual(info.error_type, "rate_limited")
        self.assertTrue(info.retryable)
        self.assertEqual(info.retry_after_seconds, 120)
        self.assertTrue(info.partial_result)

    def test_retry_after_header_maps_rate_limited_without_429(self) -> None:
        info = map_http_error(
            status_code=200,
            headers={"Retry-After": "30"},
            message="retry later",
        )

        self.assertEqual(info.error_type, "rate_limited")
        self.assertEqual(info.retry_after_seconds, 30)

    def test_500_maps_server_error(self) -> None:
        info = map_http_error(status_code=503, message="service unavailable")

        self.assertEqual(info.error_type, "server_error")
        self.assertTrue(info.retryable)
        self.assertTrue(info.partial_result)

    def test_400_maps_client_error(self) -> None:
        info = map_http_error(status_code=400, message="bad request")

        self.assertEqual(info.error_type, "client_error")
        self.assertFalse(info.retryable)
        self.assertFalse(info.partial_result)

    def test_json_parse_error_maps_non_retryable(self) -> None:
        info = map_http_error(error_type="json_parse_error", message="json parse failed")

        self.assertEqual(info.error_type, "json_parse_error")
        self.assertFalse(info.retryable)
        self.assertFalse(info.partial_result)

    def test_schema_error_maps_non_retryable(self) -> None:
        info = map_http_error(error_type="schema_error", message="schema mismatch")

        self.assertEqual(info.error_type, "schema_error")
        self.assertFalse(info.retryable)
        self.assertFalse(info.partial_result)

    def test_disabled_http_client_maps_non_retryable(self) -> None:
        client = DisabledHttpClient()
        try:
            client.send(HttpRequest(method="GET", url="https://example.invalid"))
        except RuntimeError as exc:
            info = map_http_error(exception=exc)
        else:  # pragma: no cover
            self.fail("DisabledHttpClient unexpectedly returned")

        self.assertIsInstance(info, HttpErrorInfo)
        self.assertEqual(info.error_type, "disabled_http_client")
        self.assertFalse(info.retryable)
        self.assertFalse(info.partial_result)

    def test_credential_markers_are_redacted_from_error_messages(self) -> None:
        info = map_http_error(
            status_code=500,
            message=(
                "failed with API_KEY=abc TOKEN=def SECRET=ghi "
                "COOKIE=jkl AUTHORIZATION=Bearer mno"
            ),
        )

        self.assertFalse(contains_sensitive_marker(info.message), info.message)
        self.assertFalse(contains_sensitive_marker(info.redacted_message), info.redacted_message)
        self.assertNotIn("abc", info.redacted_message)
        self.assertNotIn("def", info.redacted_message)


if __name__ == "__main__":
    unittest.main()
