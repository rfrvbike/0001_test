"""Disabled live recent-search transport skeleton.

This module intentionally contains no HTTP client, no credential lookup, and no
network behavior. It fixes the future implementation location while remaining
fail-closed.
"""

from __future__ import annotations

from x_auto_ops.mock_transport import TransportResponse


class LiveRecentSearchTransport:
    """Future live X recent-search transport placeholder.

    The class satisfies the same transport shape as `MockRecentSearchTransport`,
    but every call is blocked until live X API access is explicitly approved.
    """

    def send_recent_search(self, query: str) -> TransportResponse:
        raise RuntimeError("LiveRecentSearchTransport disabled")
