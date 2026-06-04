"""Disabled real credential loader skeleton for future backend-only X reads."""

from __future__ import annotations

from typing import Protocol

from x_auto_ops.credential_loader import CredentialBundle


class RealCredentialLoaderError(RuntimeError):
    """Base error for future real credential loading failures."""


class RealCredentialLoaderDisabledError(RuntimeError):
    """Raised while real credential loading is intentionally unavailable."""


class CredentialNotFoundError(RealCredentialLoaderError):
    """Raised when a future storage adapter cannot find credentials."""


class CredentialStorageError(RealCredentialLoaderError):
    """Raised when a future storage adapter fails internally."""


class CredentialValidationError(RealCredentialLoaderError):
    """Raised when future credential values fail validation."""


class CredentialStorageAdapter(Protocol):
    """Future backend-only storage adapter boundary.

    Current implementations must remain disabled and must not read from any
    local, process, hosted, or operating-system credential source.
    """

    def load_credentials(self) -> CredentialBundle:
        """Return a credential bundle from a future approved backend store."""


class EnvCredentialAdapter:
    """Disabled skeleton for a future backend-managed variable adapter."""

    def load_credentials(self) -> CredentialBundle:
        raise RealCredentialLoaderDisabledError("Real credential loader disabled")


class SecretManagerAdapter:
    """Disabled skeleton for a future managed secret adapter."""

    def load_credentials(self) -> CredentialBundle:
        raise RealCredentialLoaderDisabledError("Real credential loader disabled")


class FileCredentialAdapter:
    """Disabled skeleton for a future backend-local file adapter."""

    def load_credentials(self) -> CredentialBundle:
        raise RealCredentialLoaderDisabledError("Real credential loader disabled")


class OsCredentialAdapter:
    """Disabled skeleton for a future operating-system credential adapter."""

    def load_credentials(self) -> CredentialBundle:
        raise RealCredentialLoaderDisabledError("Real credential loader disabled")


class RealCredentialLoader:
    """Fail-closed real credential loader placeholder.

    This skeleton fixes the future backend-only extension point without reading
    files, environment variables, local config, tokens, cookies, or API keys.
    """

    def __init__(self, adapter: CredentialStorageAdapter | None = None) -> None:
        self.adapter = adapter

    def load(self) -> CredentialBundle:
        raise RealCredentialLoaderDisabledError("Real credential loader disabled")
