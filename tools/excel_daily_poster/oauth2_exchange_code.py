from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.excel_daily_poster.oauth2_authorize import (  # noqa: E402
    DEFAULT_STATE_PATH,
    load_authorization_state,
)
from tools.excel_daily_poster.x_client import (  # noqa: E402
    XAuthError,
    XClientError,
    XConfigError,
    XNetworkError,
    classify_http_status,
)


TOKEN_ENDPOINT = "https://api.x.com/2/oauth2/token"
DEFAULT_TOKEN_PATH = Path("data/oauth2_tokens.local.json")
CONFIRM_TOKEN_EXCHANGE = "I_UNDERSTAND_THIS_EXCHANGES_OAUTH2_TOKEN"
TokenTransport = Callable[[str, dict[str, str], dict[str, str]], dict[str, Any]]


@dataclass(frozen=True)
class OAuth2TokenSet:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int | None
    scope: str

    def redacted_dict(self) -> dict[str, object]:
        return {
            "access_token": "[REDACTED]",
            "refresh_token": "[REDACTED]" if self.refresh_token else "",
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "scope": self.scope,
        }


def exchange_code_for_tokens(
    *,
    code: str,
    returned_state: str,
    state_path: str | Path = DEFAULT_STATE_PATH,
    transport: TokenTransport,
    client_secret: str = "",
) -> OAuth2TokenSet:
    if not code.strip():
        raise XConfigError("Missing OAuth2 authorization code")
    authorization_state = load_authorization_state(state_path)
    if returned_state != authorization_state.state:
        raise XAuthError("OAuth2 state mismatch; refusing token exchange")

    payload, headers = build_authorization_code_token_request(
        client_id=authorization_state.client_id,
        code=code.strip(),
        redirect_uri=authorization_state.redirect_uri,
        code_verifier=authorization_state.code_verifier,
        client_secret=client_secret,
    )

    response = _call_token_transport(
        transport,
        payload,
        headers=headers,
        extra_redaction_values=[client_secret],
    )
    return _token_set_from_response(response)


def build_authorization_code_token_request(
    *,
    client_id: str,
    code: str,
    redirect_uri: str,
    code_verifier: str,
    client_secret: str = "",
) -> tuple[dict[str, str], dict[str, str]]:
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    headers = token_request_headers(
        client_id=client_id,
        client_secret=client_secret,
    )
    return payload, headers


def build_refresh_token_request(
    *,
    client_id: str,
    refresh_token: str,
    client_secret: str = "",
) -> tuple[dict[str, str], dict[str, str]]:
    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }
    headers = token_request_headers(
        client_id=client_id,
        client_secret=client_secret,
    )
    return payload, headers


def token_request_headers(
    *,
    client_id: str,
    client_secret: str = "",
) -> dict[str, str]:
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if client_secret.strip():
        raw = f"{client_id}:{client_secret.strip()}".encode("utf-8")
        headers["Authorization"] = (
            "Basic " + base64.b64encode(raw).decode("ascii")
        )
    return headers


def save_tokens(tokens: OAuth2TokenSet, path: str | Path = DEFAULT_TOKEN_PATH) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "access_token": tokens.access_token,
                "refresh_token": tokens.refresh_token,
                "token_type": tokens.token_type,
                "expires_in": tokens.expires_in,
                "scope": tokens.scope,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return output_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare OAuth 2.0 code exchange. Real HTTP requires a transport wrapper.",
    )
    parser.add_argument("--code", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--token-path", default=str(DEFAULT_TOKEN_PATH))
    parser.add_argument(
        "--mock-only",
        action="store_true",
        help="Validate inputs and saved state without performing HTTP.",
    )
    parser.add_argument(
        "--exchange-live",
        action="store_true",
        help="Perform the real token exchange. Requires exact confirmation.",
    )
    parser.add_argument(
        "--confirm-token-exchange",
        default="",
        help=f"Required exact value for --exchange-live: {CONFIRM_TOKEN_EXCHANGE}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        if args.mock_only and args.exchange_live:
            raise XConfigError("Choose either --mock-only or --exchange-live, not both")

        if args.exchange_live:
            if args.confirm_token_exchange != CONFIRM_TOKEN_EXCHANGE:
                raise XConfigError(
                    "Live OAuth2 token exchange requires exact "
                    "--confirm-token-exchange value"
                )
            tokens = exchange_code_for_tokens(
                code=args.code,
                returned_state=args.state,
                state_path=args.state_path,
                transport=_post_form_with_urllib,
                client_secret=os.environ.get("X_OAUTH2_CLIENT_SECRET", ""),
            )
            path = save_tokens(tokens, args.token_path)
            print(f"OAuth2 token exchange succeeded. Tokens saved to: {path}")
            print("Token values were not printed.")
            return 0

        if not args.mock_only:
            raise XConfigError(
                "Token exchange is disabled unless --mock-only or "
                "--exchange-live with exact confirmation is provided."
            )
        authorization_state = load_authorization_state(args.state_path)
        if args.state != authorization_state.state:
            raise XAuthError("OAuth2 state mismatch; refusing token exchange")
        if not args.code.strip():
            raise XConfigError("Missing OAuth2 authorization code")
        print("OAuth2 code/state validation succeeded. No HTTP request was made.")
        print(f"Token output path would be: {args.token_path}")
    except Exception as exc:
        print(
            f"ERROR: {_redact_token_text(str(exc), [args.code, os.environ.get('X_OAUTH2_CLIENT_SECRET', '')])}",
            file=sys.stderr,
        )
        return 1
    return 0


def _call_token_transport(
    transport: TokenTransport,
    payload: dict[str, str],
    *,
    headers: dict[str, str] | None = None,
    extra_redaction_values: Any = (),
) -> dict[str, Any]:
    request_headers = headers or {"Content-Type": "application/x-www-form-urlencoded"}
    redaction_values = [
        payload.get("client_id", ""),
        payload.get("code", ""),
        payload.get("code_verifier", ""),
        payload.get("refresh_token", ""),
        payload.get("client_secret", ""),
        _authorization_header_secret(request_headers),
    ]
    redaction_values.extend(list(extra_redaction_values))
    try:
        return transport(TOKEN_ENDPOINT, request_headers, payload)
    except XClientError:
        raise
    except ConnectionError as exc:
        raise XNetworkError(_redact_token_text(str(exc), redaction_values)) from exc
    except Exception as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if isinstance(status_code, int):
            raise classify_http_status(
                status_code,
                _redact_token_text(str(exc), redaction_values),
            ) from exc
        raise XClientError(_redact_token_text(str(exc), redaction_values)) from exc


def _post_form_with_urllib(
    url: str,
    headers: dict[str, str],
    payload: dict[str, str],
) -> dict[str, Any]:
    redaction_values = list(payload.values())
    authorization_value = _authorization_header_secret(headers)
    if authorization_value:
        redaction_values.append(authorization_value)
    body = urllib_parse.urlencode(payload).encode("utf-8")
    request = urllib_request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib_request.urlopen(request, timeout=30) as response:
            status_code = getattr(response, "status", None)
            response_body = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise classify_http_status(
            exc.code,
            _redact_token_text(response_body, redaction_values),
        ) from exc
    except urllib_error.URLError as exc:
        raise XNetworkError(_redact_token_text(str(exc.reason), redaction_values)) from exc

    if isinstance(status_code, int) and status_code >= 400:
        raise classify_http_status(
            status_code,
            _redact_token_text(response_body, redaction_values),
        )
    data = json.loads(response_body or "{}")
    if not isinstance(data, dict):
        raise XClientError("OAuth2 token response was not a JSON object")
    return data


def _authorization_header_secret(headers: dict[str, str]) -> str:
    value = headers.get("Authorization", "")
    if value.startswith("Basic "):
        return value
    return ""


def _token_set_from_response(response: dict[str, Any]) -> OAuth2TokenSet:
    access_token = str(response.get("access_token", "")).strip()
    if not access_token:
        raise XClientError("OAuth2 token response did not include access_token")
    refresh_token = str(response.get("refresh_token", "")).strip()
    token_type = str(response.get("token_type", "bearer")).strip()
    expires_raw = response.get("expires_in")
    expires_in = int(expires_raw) if expires_raw is not None else None
    scope = str(response.get("scope", "")).strip()
    return OAuth2TokenSet(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type=token_type,
        expires_in=expires_in,
        scope=scope,
    )


def _redact_token_text(text: str, secrets: Any = ()) -> str:
    for marker in ["access_token", "refresh_token", "client_secret", "code_verifier"]:
        text = text.replace(marker, "[REDACTED_FIELD]")
    for secret in secrets:
        secret_text = str(secret or "")
        if secret_text:
            text = text.replace(secret_text, "[REDACTED]")
    return text


if __name__ == "__main__":
    raise SystemExit(main())
