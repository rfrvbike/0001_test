"""Redaction helpers for mock-only X API pipeline artifacts."""

from __future__ import annotations

import re
from typing import Any


SENSITIVE_MARKERS = (
    "API_KEY",
    "TOKEN",
    "BEARER",
    "SECRET",
    "COOKIE",
    "AUTHORIZATION",
)

_MARKER_PATTERN = re.compile(
    r"(?i)\b(?:API_KEY|TOKEN|BEARER|SECRET|COOKIE|AUTHORIZATION)\b"
    r"(?:\s*[:=]\s*[A-Za-z0-9._~:/+\-=]+)?"
)
_COMPACT_SECRET_PATTERN = re.compile(r"(?i)\b[A-Za-z0-9._~:/+\-=]*(?:secret|token|cookie)[A-Za-z0-9._~:/+\-=]*\b")


def redact_sensitive_text(value: Any) -> str:
    """Return text with credential-like markers removed.

    This intentionally redacts marker words even when no real credential value is
    present. Mock reports should prove that credential-shaped data cannot leak,
    not preserve diagnostic marker spelling.
    """

    text = str(value)
    text = _MARKER_PATTERN.sub("[REDACTED]", text)
    return _COMPACT_SECRET_PATTERN.sub("[REDACTED]", text)


def contains_sensitive_marker(value: Any) -> bool:
    upper = str(value).upper()
    return any(marker in upper for marker in SENSITIVE_MARKERS)


def assert_redacted(value: Any, *, context: str = "output") -> None:
    if contains_sensitive_marker(value):
        raise RuntimeError(f"credential marker detected in {context}")
