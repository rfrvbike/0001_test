"""Disabled real credential loader skeleton for future backend-only X reads."""

from __future__ import annotations

from x_auto_ops.credential_loader import CredentialBundle


class RealCredentialLoaderDisabledError(RuntimeError):
    """Raised while real credential loading is intentionally unavailable."""


class RealCredentialLoader:
    """Fail-closed real credential loader placeholder.

    This skeleton fixes the future backend-only extension point without reading
    files, environment variables, local config, tokens, cookies, or API keys.
    """

    def load(self) -> CredentialBundle:
        raise RealCredentialLoaderDisabledError("Real credential loader disabled")
