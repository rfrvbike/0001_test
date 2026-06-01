from __future__ import annotations

import inspect
import unittest

from x_auto_ops.buzz_read_client import XApiBuzzReadClient
from x_auto_ops.credential_loader import FakeCredentialLoader
from x_auto_ops.live_mode_gate import assert_live_mode_allowed
from x_auto_ops.live_recent_search_transport import LiveRecentSearchTransport
from x_auto_ops.mock_transport import RecentSearchTransport, TransportResponse


class LiveRecentSearchTransportDisabledTests(unittest.TestCase):
    def test_live_recent_search_transport_is_protocol_compatible(self) -> None:
        transport: RecentSearchTransport = LiveRecentSearchTransport()

        self.assertTrue(callable(transport.send_recent_search))

    def test_live_recent_search_transport_send_is_disabled(self) -> None:
        transport = LiveRecentSearchTransport()

        with self.assertRaises(RuntimeError) as ctx:
            transport.send_recent_search("AI lang:ja")

        self.assertEqual(str(ctx.exception), "LiveRecentSearchTransport disabled")

    def test_live_recent_search_transport_has_no_http_client_imports(self) -> None:
        source = inspect.getsource(LiveRecentSearchTransport)
        module = inspect.getmodule(LiveRecentSearchTransport)
        module_source = inspect.getsource(module)

        forbidden = ("requests", "httpx", "urllib", "urlopen", "HTTPConnection")
        for term in forbidden:
            self.assertNotIn(term, source)
            self.assertNotIn(term, module_source)

    def test_x_api_client_accepts_live_transport_but_transport_fails_closed(self) -> None:
        client = XApiBuzzReadClient(transport=LiveRecentSearchTransport(), dry_run=True)

        with self.assertRaises(RuntimeError) as ctx:
            client.fetch_posts(
                {
                    "source_genre": "ai_side_business",
                    "search_queries": ["AI workflow"],
                }
            )

        self.assertEqual(str(ctx.exception), "LiveRecentSearchTransport disabled")

    def test_live_mode_gate_blocks_before_disabled_transport(self) -> None:
        credentials = FakeCredentialLoader().load()
        transport = LiveRecentSearchTransport()

        with self.assertRaises(RuntimeError) as ctx:
            assert_live_mode_allowed(
                {
                    "dry_run": False,
                    "live_mode": True,
                    "credential_source": credentials.source,
                }
            )
            transport.send_recent_search("AI lang:ja")

        self.assertEqual(str(ctx.exception), "live mode disabled")

    def test_transport_response_shape_remains_importable(self) -> None:
        response = TransportResponse(status_code=200, headers={}, json_body={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers, {})
        self.assertEqual(response.json_body, {})


if __name__ == "__main__":
    unittest.main()
