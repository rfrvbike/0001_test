from __future__ import annotations

import csv
import io
import unittest

from x_auto_ops.credential_loader import FAKE_API_KEY, FAKE_BEARER_TOKEN
from x_auto_ops.http_client import HttpRequest
from x_auto_ops.preflight_validation import (
    MAX_RECENT_SEARCH_QUERY_LENGTH,
    RECENT_SEARCH_PATH,
    PreflightValidationError,
    RecentSearchAllowlistPolicy,
    validate_recent_search_request,
)
from x_auto_ops.redaction import contains_sensitive_marker
from x_auto_ops.request_builder import DEFAULT_RECENT_SEARCH_ENDPOINT


def _request(
    *,
    method: str = "GET",
    endpoint: str = DEFAULT_RECENT_SEARCH_ENDPOINT,
    query: str = "AI lang:ja",
    timeout_seconds: float = 10.0,
) -> HttpRequest:
    return HttpRequest(
        method=method,
        url=endpoint,
        headers={
            "Authorization": f"Bearer {FAKE_BEARER_TOKEN}",
            "X-Debug": FAKE_API_KEY,
        },
        query_params={"query": query},
        timeout_seconds=timeout_seconds,
    )


def _render_csv(text: str) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["debug"])
    writer.writeheader()
    writer.writerow({"debug": text})
    return output.getvalue()


class PreflightValidationTests(unittest.TestCase):
    def test_allows_get_recent_search_absolute_endpoint(self) -> None:
        result = validate_recent_search_request(_request())

        self.assertTrue(result.allowed)
        self.assertEqual(result.method, "GET")
        self.assertEqual(result.endpoint, DEFAULT_RECENT_SEARCH_ENDPOINT)
        self.assertEqual(result.endpoint_name, "recent_search")
        self.assertEqual(result.query_length, len("AI lang:ja"))
        self.assertEqual(result.validation_reason, "recent search request allowed")

    def test_allows_get_recent_search_path_endpoint_and_512_char_query(self) -> None:
        query = "a" * MAX_RECENT_SEARCH_QUERY_LENGTH

        result = validate_recent_search_request(_request(endpoint=RECENT_SEARCH_PATH, query=query))

        self.assertTrue(result.allowed)
        self.assertEqual(result.endpoint, RECENT_SEARCH_PATH)
        self.assertEqual(result.query_length, MAX_RECENT_SEARCH_QUERY_LENGTH)

    def test_rejects_non_get_methods(self) -> None:
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                with self.assertRaises(PreflightValidationError):
                    validate_recent_search_request(_request(method=method))

    def test_rejects_write_endpoints(self) -> None:
        denied_endpoints = (
            "/2/tweets",
            "/2/users",
            "/2/dm/events",
            "/2/media/upload",
            "/2/users/123/following",
            "/2/users/123/likes",
            "/2/tweets/123/liking",
            "/2/tweets/123/retweeted_by",
        )

        for endpoint in denied_endpoints:
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(PreflightValidationError):
                    validate_recent_search_request(_request(endpoint=endpoint))

    def test_rejects_empty_query_too_long_query_empty_endpoint_and_bad_timeout(self) -> None:
        with self.assertRaises(PreflightValidationError):
            validate_recent_search_request(_request(query=""))
        with self.assertRaises(PreflightValidationError):
            validate_recent_search_request(_request(query="a" * (MAX_RECENT_SEARCH_QUERY_LENGTH + 1)))
        with self.assertRaises(PreflightValidationError):
            validate_recent_search_request(_request(endpoint=""))
        with self.assertRaises(PreflightValidationError):
            validate_recent_search_request(_request(timeout_seconds=0))

    def test_rejects_not_allowlisted_read_like_endpoint(self) -> None:
        with self.assertRaises(PreflightValidationError):
            validate_recent_search_request(_request(endpoint="/2/tweets/search/all"))

    def test_policy_can_override_query_length(self) -> None:
        policy = RecentSearchAllowlistPolicy(max_query_length=3)

        with self.assertRaises(PreflightValidationError):
            validate_recent_search_request(_request(query="abcd"), policy=policy)

    def test_safe_debug_summary_does_not_leak_credentials_or_markers(self) -> None:
        result = validate_recent_search_request(
            _request(query="Bearer FAKE_TOKEN Authorization API_KEY SECRET COOKIE")
        )

        debug = result.safe_debug_summary()
        report = f"preflight\n{debug}"
        csv_text = _render_csv(debug)

        combined = "\n".join([debug, report, csv_text])
        self.assertNotIn(FAKE_BEARER_TOKEN, combined)
        self.assertNotIn(FAKE_API_KEY, combined)
        self.assertNotIn("Bearer", combined)
        self.assertNotIn("Authorization", combined)
        self.assertNotIn("API_KEY", combined)
        self.assertNotIn("TOKEN", combined)
        self.assertNotIn("SECRET", combined)
        self.assertNotIn("COOKIE", combined)
        self.assertFalse(contains_sensitive_marker(combined), combined)

    def test_exception_redacts_sensitive_endpoint_and_method_values(self) -> None:
        request = _request(
            method="POST Authorization",
            endpoint="/2/tweets?token=FAKE_TOKEN_SECRET",
        )

        with self.assertRaises(PreflightValidationError) as ctx:
            validate_recent_search_request(request)

        exception_text = str(ctx.exception)
        self.assertNotIn("Authorization", exception_text)
        self.assertNotIn("TOKEN", exception_text)
        self.assertNotIn("SECRET", exception_text)
        self.assertFalse(contains_sensitive_marker(exception_text), exception_text)


if __name__ == "__main__":
    unittest.main()
