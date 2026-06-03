from __future__ import annotations

import csv
import io
import unittest

from x_auto_ops.credential_loader import FAKE_API_KEY, FAKE_BEARER_TOKEN, FakeCredentialLoader
from x_auto_ops.http_client import HttpRequest, HttpResponse
from x_auto_ops.live_recent_search_transport import LiveRecentSearchTransport
from x_auto_ops.preflight_validation import MAX_RECENT_SEARCH_QUERY_LENGTH, PreflightValidationError
from x_auto_ops.redaction import contains_sensitive_marker


class TrackingHttpClient:
    def __init__(self) -> None:
        self.calls: list[HttpRequest] = []

    def send(self, request: HttpRequest) -> HttpResponse:
        self.calls.append(request)
        return HttpResponse(status_code=200, headers={}, body_text="{}", json_body={})


def _render_csv(text: str) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["debug"])
    writer.writeheader()
    writer.writerow({"debug": text})
    return output.getvalue()


class PreflightTransportIntegrationTests(unittest.TestCase):
    def test_valid_recent_search_preflights_then_transport_stays_disabled(self) -> None:
        http_client = TrackingHttpClient()
        transport = LiveRecentSearchTransport(http_client=http_client)

        with self.assertRaises(RuntimeError) as ctx:
            transport.send_recent_search("AI lang:ja")

        self.assertEqual(str(ctx.exception), "LiveRecentSearchTransport disabled")
        self.assertEqual(http_client.calls, [])
        self.assertIsNotNone(transport.last_preflight_summary)
        self.assertIn("allowed=True", transport.last_preflight_summary or "")
        self.assertIn("query_length=10", transport.last_preflight_summary or "")

    def test_post_fails_preflight_before_transport_disabled(self) -> None:
        http_client = TrackingHttpClient()
        transport = LiveRecentSearchTransport(http_client=http_client, request_config={"method": "POST"})

        with self.assertRaises(PreflightValidationError):
            transport.send_recent_search("AI lang:ja")

        self.assertEqual(http_client.calls, [])

    def test_write_endpoint_fails_preflight_before_transport_disabled(self) -> None:
        http_client = TrackingHttpClient()
        transport = LiveRecentSearchTransport(
            http_client=http_client,
            request_config={"endpoint": "/2/tweets"},
        )

        with self.assertRaises(PreflightValidationError):
            transport.send_recent_search("AI lang:ja")

        self.assertEqual(http_client.calls, [])

    def test_query_too_long_fails_preflight_before_transport_disabled(self) -> None:
        http_client = TrackingHttpClient()
        transport = LiveRecentSearchTransport(http_client=http_client)

        with self.assertRaises(PreflightValidationError):
            transport.send_recent_search("a" * (MAX_RECENT_SEARCH_QUERY_LENGTH + 1))

        self.assertEqual(http_client.calls, [])

    def test_timeout_not_positive_fails_preflight_before_transport_disabled(self) -> None:
        http_client = TrackingHttpClient()
        transport = LiveRecentSearchTransport(
            http_client=http_client,
            request_config={"timeout_seconds": 0},
        )

        with self.assertRaises(PreflightValidationError):
            transport.send_recent_search("AI lang:ja")

        self.assertEqual(http_client.calls, [])

    def test_endpoint_allowlist_violation_fails_preflight_before_transport_disabled(self) -> None:
        http_client = TrackingHttpClient()
        transport = LiveRecentSearchTransport(
            http_client=http_client,
            request_config={"endpoint": "/2/tweets/search/all"},
        )

        with self.assertRaises(PreflightValidationError):
            transport.send_recent_search("AI lang:ja")

        self.assertEqual(http_client.calls, [])

    def test_redaction_surfaces_do_not_expose_credentials(self) -> None:
        credentials = FakeCredentialLoader().load()
        http_client = TrackingHttpClient()
        transport = LiveRecentSearchTransport(
            http_client=http_client,
            credential_bundle=credentials,
        )

        with self.assertRaises(RuntimeError) as ctx:
            transport.send_recent_search("Bearer FAKE_TOKEN Authorization API_KEY SECRET COOKIE")

        debug = transport.last_preflight_summary or ""
        report = f"preflight transport\n{debug}"
        csv_text = _render_csv(debug)
        exception_text = str(ctx.exception)
        combined = "\n".join([debug, report, csv_text, exception_text])

        self.assertNotIn(FAKE_BEARER_TOKEN, combined)
        self.assertNotIn(FAKE_API_KEY, combined)
        self.assertNotIn("Bearer", combined)
        self.assertNotIn("Authorization", combined)
        self.assertNotIn("API_KEY", combined)
        self.assertNotIn("TOKEN", combined)
        self.assertNotIn("SECRET", combined)
        self.assertNotIn("COOKIE", combined)
        self.assertFalse(contains_sensitive_marker(combined), combined)
        self.assertEqual(http_client.calls, [])


if __name__ == "__main__":
    unittest.main()
