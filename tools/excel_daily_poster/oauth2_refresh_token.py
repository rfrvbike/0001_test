from __future__ import annotations

"""Future OAuth 2.0 refresh-token helper.

This module intentionally does not perform real HTTP by default. It documents
and tests the payload shape needed to exchange a refresh token for a new access
token later.
"""

from pathlib import Path

from tools.excel_daily_poster.oauth2_exchange_code import (
    DEFAULT_TOKEN_PATH,
    TOKEN_ENDPOINT,
    TokenTransport,
    OAuth2TokenSet,
    build_refresh_token_request,
    _call_token_transport,
    _token_set_from_response,
)
from tools.excel_daily_poster.x_client import XConfigError


def refresh_access_token(
    *,
    client_id: str,
    refresh_token: str,
    transport: TokenTransport,
    client_secret: str = "",
    token_path: str | Path = DEFAULT_TOKEN_PATH,
) -> OAuth2TokenSet:
    """Refresh OAuth2 tokens with an injected transport only."""

    if not client_id.strip():
        raise XConfigError("Missing OAuth2 client_id")
    if not refresh_token.strip():
        raise XConfigError("Missing OAuth2 refresh_token")
    payload, headers = build_refresh_token_request(
        client_id=client_id.strip(),
        refresh_token=refresh_token.strip(),
        client_secret=client_secret,
    )
    response = _call_token_transport(
        transport,
        payload,
        headers=headers,
        extra_redaction_values=[client_secret],
    )
    return _token_set_from_response(response)


__all__ = ["TOKEN_ENDPOINT", "refresh_access_token"]
