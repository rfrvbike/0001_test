"""HTTP client interface skeleton for future X API reads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class HttpRequest:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    query_params: dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = 10.0


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    body_text: str = ""
    json_body: dict[str, Any] = field(default_factory=dict)


class HttpClient(Protocol):
    def send(self, request: HttpRequest) -> HttpResponse:
        """Send one prepared request and return an HTTP-shaped response."""


class DisabledHttpClient:
    """Fail-closed client used until real X API access is approved."""

    def send(self, request: HttpRequest) -> HttpResponse:
        raise RuntimeError("HTTP client disabled")
