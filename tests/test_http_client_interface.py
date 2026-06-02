from __future__ import annotations

import inspect
import unittest

from x_auto_ops.http_client import (
    DisabledHttpClient,
    HttpClient,
    HttpRequest,
    HttpResponse,
)
from x_auto_ops.live_recent_search_transport import LiveRecentSearchTransport


class HttpClientInterfaceTests(unittest.TestCase):
    def test_http_request_shape(self) -> None:
        request = HttpRequest(
            method="GET",
            url="https://example.invalid/2/tweets/search/recent",
            headers={"Accept": "application/json"},
            query_params={"query": "AI lang:ja"},
            timeout_seconds=5.0,
        )

        self.assertEqual(request.method, "GET")
        self.assertEqual(request.url, "https://example.invalid/2/tweets/search/recent")
        self.assertEqual(request.headers["Accept"], "application/json")
        self.assertEqual(request.query_params["query"], "AI lang:ja")
        self.assertEqual(request.timeout_seconds, 5.0)

    def test_http_response_shape(self) -> None:
        response = HttpResponse(
            status_code=200,
            headers={"x-rate-limit-remaining": "1"},
            body_text='{"data":[]}',
            json_body={"data": []},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-rate-limit-remaining"], "1")
        self.assertEqual(response.body_text, '{"data":[]}')
        self.assertEqual(response.json_body, {"data": []})

    def test_disabled_http_client_send_is_disabled(self) -> None:
        client: HttpClient = DisabledHttpClient()

        with self.assertRaises(RuntimeError) as ctx:
            client.send(HttpRequest(method="GET", url="https://example.invalid"))

        self.assertEqual(str(ctx.exception), "HTTP client disabled")

    def test_live_transport_accepts_disabled_http_client_and_fails_closed(self) -> None:
        http_client = DisabledHttpClient()
        transport = LiveRecentSearchTransport(http_client=http_client)

        self.assertIs(transport.http_client, http_client)
        with self.assertRaises(RuntimeError) as ctx:
            transport.send_recent_search("AI lang:ja")

        self.assertEqual(str(ctx.exception), "LiveRecentSearchTransport disabled")

    def test_http_client_and_live_transport_have_no_live_http_imports(self) -> None:
        modules = [
            inspect.getmodule(DisabledHttpClient),
            inspect.getmodule(LiveRecentSearchTransport),
        ]
        forbidden = ("requests", "httpx", "urllib", "urlopen", "HTTPConnection")
        for module in modules:
            source = inspect.getsource(module)
            for term in forbidden:
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
