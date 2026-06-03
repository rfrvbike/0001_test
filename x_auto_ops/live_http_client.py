"""Disabled live HTTP client skeleton for future X API reads."""

from __future__ import annotations

from x_auto_ops.http_client import HttpRequest, HttpResponse


class LiveHttpClientDisabledError(RuntimeError):
    """Raised while the live HTTP client is intentionally unavailable."""


class LiveHttpClient:
    """Future live HTTP implementation point.

    The class matches the `HttpClient` protocol but performs no network work.
    It remains fail-closed until live X API reads are explicitly approved.
    """

    def send(self, request: HttpRequest) -> HttpResponse:
        raise LiveHttpClientDisabledError("Live HTTP client disabled")
