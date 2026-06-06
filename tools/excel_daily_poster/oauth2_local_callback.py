from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.excel_daily_poster.oauth2_authorize import (  # noqa: E402
    DEFAULT_STATE_PATH,
    build_authorization_state,
    save_authorization_state,
)
from tools.excel_daily_poster.oauth2_exchange_code import (  # noqa: E402
    CONFIRM_TOKEN_EXCHANGE,
    DEFAULT_TOKEN_PATH,
    TokenTransport,
    _post_form_with_urllib,
    _redact_token_text,
    exchange_code_for_tokens,
    save_tokens,
)
from tools.excel_daily_poster.x_client import XAuthError, XConfigError  # noqa: E402


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_CALLBACK_PATH = "/callback"
DEFAULT_REDIRECT_URI = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}{DEFAULT_CALLBACK_PATH}"


@dataclass(frozen=True)
class CallbackExchangeResult:
    success: bool
    message: str
    token_path: Path | None = None


def create_authorization_url(
    *,
    client_id: str,
    redirect_uri: str,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> str:
    authorization_state = build_authorization_state(
        client_id=client_id,
        redirect_uri=redirect_uri,
    )
    save_authorization_state(authorization_state, state_path)
    return authorization_state.authorization_url


def parse_callback_params(path: str) -> dict[str, str]:
    parsed = urlparse(path)
    raw_params = parse_qs(parsed.query, keep_blank_values=True)
    return {key: values[0] if values else "" for key, values in raw_params.items()}


def exchange_callback_params(
    params: dict[str, str],
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
    token_path: str | Path = DEFAULT_TOKEN_PATH,
    transport: TokenTransport,
    client_secret: str = "",
    confirm_token_exchange: str,
) -> CallbackExchangeResult:
    if confirm_token_exchange != CONFIRM_TOKEN_EXCHANGE:
        raise XConfigError(
            "Live OAuth2 token exchange requires exact --confirm-token-exchange value"
        )

    error_value = params.get("error", "").strip()
    if error_value:
        raise XAuthError(
            _redact_token_text(
                f"OAuth2 authorization failed: {error_value}",
                [params.get("code", ""), client_secret],
            )
        )

    code = params.get("code", "").strip()
    state = params.get("state", "").strip()
    if not code:
        raise XConfigError("OAuth2 callback did not include an authorization code")
    if not state:
        raise XAuthError("OAuth2 callback did not include state")

    tokens = exchange_code_for_tokens(
        code=code,
        returned_state=state,
        state_path=state_path,
        transport=transport,
        client_secret=client_secret,
    )
    saved_path = save_tokens(tokens, token_path)
    return CallbackExchangeResult(
        success=True,
        message="OAuth2 token exchange succeeded. Tokens saved.",
        token_path=saved_path,
    )


def run_local_callback_server(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    callback_path: str = DEFAULT_CALLBACK_PATH,
    state_path: str | Path = DEFAULT_STATE_PATH,
    token_path: str | Path = DEFAULT_TOKEN_PATH,
    transport: TokenTransport = _post_form_with_urllib,
    client_secret: str = "",
    confirm_token_exchange: str,
) -> CallbackExchangeResult:
    result: CallbackExchangeResult | None = None
    captured_error: Exception | None = None

    class OAuth2CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            nonlocal result, captured_error
            parsed = urlparse(self.path)
            if parsed.path != callback_path:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found.")
                return

            try:
                params = parse_callback_params(self.path)
                result = exchange_callback_params(
                    params,
                    state_path=state_path,
                    token_path=token_path,
                    transport=transport,
                    client_secret=client_secret,
                    confirm_token_exchange=confirm_token_exchange,
                )
                self.send_response(200)
                self.end_headers()
                self.wfile.write(
                    b"OAuth2 token exchange succeeded. You can close this window."
                )
            except Exception as exc:  # pragma: no cover - exercised through caller state
                captured_error = exc
                self.send_response(400)
                self.end_headers()
                self.wfile.write(
                    b"OAuth2 token exchange failed. Check the local console."
                )

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = HTTPServer((host, port), OAuth2CallbackHandler)
    server.handle_request()
    server.server_close()

    if captured_error is not None:
        raise captured_error
    if result is None:
        raise XConfigError("OAuth2 callback server stopped without a callback")
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Receive an OAuth2 PKCE callback locally and exchange the code once.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--callback-path", default=DEFAULT_CALLBACK_PATH)
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--token-path", default=str(DEFAULT_TOKEN_PATH))
    parser.add_argument(
        "--confirm-token-exchange",
        default="",
        help=f"Required exact value: {CONFIRM_TOKEN_EXCHANGE}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    client_id = os.environ.get("X_OAUTH2_CLIENT_ID", "")
    redirect_uri = os.environ.get("X_OAUTH2_REDIRECT_URI", DEFAULT_REDIRECT_URI)
    client_secret = os.environ.get("X_OAUTH2_CLIENT_SECRET", "")
    try:
        if args.confirm_token_exchange != CONFIRM_TOKEN_EXCHANGE:
            raise XConfigError(
                "Live OAuth2 token exchange requires exact --confirm-token-exchange value"
            )
        authorization_url = create_authorization_url(
            client_id=client_id,
            redirect_uri=redirect_uri,
            state_path=args.state_path,
        )
        print("Open this authorization URL locally:")
        print(authorization_url)
        print(f"Waiting for OAuth2 callback at: http://{args.host}:{args.port}{args.callback_path}")
        print("Do not paste tokens, authorization codes, or client secrets into chat/logs.")

        result = run_local_callback_server(
            host=args.host,
            port=args.port,
            callback_path=args.callback_path,
            state_path=args.state_path,
            token_path=args.token_path,
            transport=_post_form_with_urllib,
            client_secret=client_secret,
            confirm_token_exchange=args.confirm_token_exchange,
        )
        print(f"OAuth2 token exchange succeeded. Tokens saved to: {result.token_path}")
        print("Token values were not printed.")
        return 0
    except Exception as exc:
        print(
            "ERROR: "
            + _redact_token_text(
                str(exc),
                [client_id, client_secret],
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
