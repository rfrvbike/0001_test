from __future__ import annotations

import csv
import inspect
import io
import unittest

from x_auto_ops.http_client import HttpClient, HttpRequest
from x_auto_ops.http_error_mapping import map_http_error
from x_auto_ops.live_http_client import LiveHttpClient, LiveHttpClientDisabledError
from x_auto_ops.live_recent_search_transport import LiveRecentSearchTransport
from x_auto_ops.mock_transport import contains_sensitive_marker
from x_auto_ops.redaction import redact_sensitive_text


class LiveHttpClientDisabledTests(unittest.TestCase):
    def test_live_http_client_is_constructable_and_protocol_compatible(self) -> None:
        client: HttpClient = LiveHttpClient()

        self.assertTrue(callable(client.send))

    def test_send_always_raises_disabled_error(self) -> None:
        client = LiveHttpClient()

        with self.assertRaises(LiveHttpClientDisabledError) as ctx:
            client.send(HttpRequest(method="GET", url="https://example.invalid/2/tweets/search/recent"))

        self.assertEqual(str(ctx.exception), "Live HTTP client disabled")

    def test_live_http_client_has_no_live_http_imports(self) -> None:
        module = inspect.getmodule(LiveHttpClient)
        source = inspect.getsource(module)
        forbidden = ("requests", "httpx", "urllib", "socket", "HTTPConnection", "urlopen")

        for term in forbidden:
            self.assertNotIn(term, source)

    def test_live_transport_accepts_live_http_client_but_fails_before_send(self) -> None:
        http_client = LiveHttpClient()
        transport = LiveRecentSearchTransport(http_client=http_client)

        self.assertIs(transport.http_client, http_client)
        with self.assertRaises(RuntimeError) as ctx:
            transport.send_recent_search("AI lang:ja")

        self.assertEqual(str(ctx.exception), "LiveRecentSearchTransport disabled")

    def test_live_http_client_disabled_error_maps_to_disabled_http_client(self) -> None:
        client = LiveHttpClient()
        try:
            client.send(HttpRequest(method="GET", url="https://example.invalid/2/tweets/search/recent"))
        except LiveHttpClientDisabledError as exc:
            info = map_http_error(exception=exc)
        else:  # pragma: no cover
            self.fail("LiveHttpClient unexpectedly returned")

        self.assertEqual(info.error_type, "disabled_http_client")
        self.assertFalse(info.retryable)
        self.assertFalse(info.partial_result)

    def test_disabled_error_does_not_leak_sensitive_markers(self) -> None:
        client = LiveHttpClient()
        try:
            client.send(
                HttpRequest(
                    method="GET",
                    url="https://example.invalid/2/tweets/search/recent",
                    headers={
                        "Authorization": "Bearer TOKEN_SHOULD_NOT_APPEAR",
                        "Cookie": "SECRET_COOKIE_SHOULD_NOT_APPEAR",
                    },
                )
            )
        except LiveHttpClientDisabledError as exc:
            exception_text = str(exc)
        else:  # pragma: no cover
            self.fail("LiveHttpClient unexpectedly returned")

        debug_log = redact_sensitive_text(exception_text)
        report = f"error={redact_sensitive_text(exception_text)}"
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["error"])
        writer.writeheader()
        writer.writerow({"error": redact_sensitive_text(exception_text)})
        csv_text = output.getvalue()

        combined = "\n".join([exception_text, debug_log, report, csv_text])
        self.assertFalse(contains_sensitive_marker(combined), combined)
        self.assertNotIn("TOKEN_SHOULD_NOT_APPEAR", combined)
        self.assertNotIn("SECRET_COOKIE_SHOULD_NOT_APPEAR", combined)


if __name__ == "__main__":
    unittest.main()
