"""Disabled live recent-search transport skeleton.

This module intentionally performs no network behavior. It fixes the future
implementation location while remaining fail-closed.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from x_auto_ops.credential_loader import CredentialBundle, FakeCredentialLoader
from x_auto_ops.http_client import DisabledHttpClient, HttpClient
from x_auto_ops.mock_transport import TransportResponse
from x_auto_ops.preflight_validation import PreflightValidationError, validate_recent_search_request
from x_auto_ops.request_builder import RequestBuildError, build_recent_search_request


class LiveRecentSearchTransport:
    """Future live X recent-search transport placeholder.

    The class satisfies the same transport shape as `MockRecentSearchTransport`,
    but every call is blocked until live X API access is explicitly approved.
    """

    def __init__(
        self,
        http_client: HttpClient | None = None,
        *,
        credential_bundle: CredentialBundle | None = None,
        request_config: Mapping[str, Any] | None = None,
    ) -> None:
        self.http_client = http_client or DisabledHttpClient()
        self.credential_bundle = credential_bundle or FakeCredentialLoader().load()
        self.request_config = dict(request_config or {})
        self.last_preflight_summary: str | None = None

    def send_recent_search(self, query: str) -> TransportResponse:
        request = self._build_request(query)
        validation = validate_recent_search_request(request)
        self.last_preflight_summary = validation.safe_debug_summary()
        raise RuntimeError("LiveRecentSearchTransport disabled")

    def _build_request(self, query: str):
        try:
            build_config = dict(self.request_config)
            override_method = build_config.pop("method", None)
            result = build_recent_search_request(
                query=query,
                credential_bundle=self.credential_bundle,
                config=build_config,
            )
        except RequestBuildError as exc:
            raise PreflightValidationError(str(exc)) from None

        if override_method is None:
            return result.request
        return replace(result.request, method=str(override_method))
