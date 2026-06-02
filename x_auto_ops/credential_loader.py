"""Mock-only credential loader boundary for future X API reads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol


FAKE_BEARER_TOKEN = "FAKE_BEARER_TOKEN"
FAKE_API_KEY = "FAKE_API_KEY"
FAKE_API_SECRET = "FAKE_SECRET"


@dataclass(frozen=True)
class CredentialBundle:
    """Credential-shaped values for interface tests.

    These values are intentionally fake and must never be used for HTTP.
    """

    bearer_token: str
    api_key: str
    api_secret: str
    source: str = "FAKE"

    def safe_summary(self) -> dict[str, str]:
        return {
            "source": self.source,
            "bearer_token": "[REDACTED]",
            "api_key": "[REDACTED]",
            "api_secret": "[REDACTED]",
        }


class CredentialLoader(Protocol):
    def load(self) -> CredentialBundle:
        """Return credentials for the future live transport boundary."""


class FakeCredentialLoader:
    """Return fake credentials without reading files, env vars, or secrets."""

    def load(self) -> CredentialBundle:
        return CredentialBundle(
            bearer_token=FAKE_BEARER_TOKEN,
            api_key=FAKE_API_KEY,
            api_secret=FAKE_API_SECRET,
        )


def select_credential_loader(config: Mapping[str, Any] | None = None) -> CredentialLoader:
    """Select the credential loader without reading real credentials.

    Accepted values:

    - `fake`: returns `FakeCredentialLoader`
    - `real`: returns disabled `RealCredentialLoader`

    The real loader is fail-closed and raises when used.
    """

    values = dict(config or {})
    selected = str(
        values.get("credential_loader")
        or values.get("loader")
        or values.get("credential_source")
        or "fake"
    ).strip().lower()
    if selected == "fake":
        return FakeCredentialLoader()
    if selected == "real":
        from x_auto_ops.real_credential_loader import RealCredentialLoader

        return RealCredentialLoader()
    raise ValueError(f"unknown credential loader: {selected}")
