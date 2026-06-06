from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlencode

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.excel_daily_poster.x_client import XConfigError  # noqa: E402


AUTHORIZATION_ENDPOINT = "https://twitter.com/i/oauth2/authorize"
DEFAULT_SCOPES = ("tweet.read", "tweet.write", "users.read", "offline.access")
DEFAULT_STATE_PATH = Path("data/oauth2_state.local.json")


@dataclass(frozen=True)
class OAuth2AuthorizationState:
    client_id: str
    redirect_uri: str
    scopes: tuple[str, ...]
    state: str
    code_verifier: str
    code_challenge: str
    authorization_url: str

    def redacted_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["code_verifier"] = "[REDACTED]"
        return data


def generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)


def code_challenge_for(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def build_authorization_state(
    *,
    client_id: str,
    redirect_uri: str,
    scopes: tuple[str, ...] = DEFAULT_SCOPES,
    state: str | None = None,
    code_verifier: str | None = None,
) -> OAuth2AuthorizationState:
    client_id = _required("X_OAUTH2_CLIENT_ID", client_id)
    redirect_uri = _required("X_OAUTH2_REDIRECT_URI", redirect_uri)
    state_value = state or secrets.token_urlsafe(32)
    verifier = code_verifier or generate_code_verifier()
    challenge = code_challenge_for(verifier)
    clean_scopes = tuple(scope.strip() for scope in scopes if scope.strip())
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(clean_scopes),
        "state": state_value,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    authorization_url = f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"
    return OAuth2AuthorizationState(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scopes=clean_scopes,
        state=state_value,
        code_verifier=verifier,
        code_challenge=challenge,
        authorization_url=authorization_url,
    )


def save_authorization_state(
    authorization_state: OAuth2AuthorizationState,
    path: str | Path = DEFAULT_STATE_PATH,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(authorization_state)
    data.pop("authorization_url", None)
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def load_authorization_state(path: str | Path = DEFAULT_STATE_PATH) -> OAuth2AuthorizationState:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return build_authorization_state(
        client_id=str(data["client_id"]),
        redirect_uri=str(data["redirect_uri"]),
        scopes=tuple(data["scopes"]),
        state=str(data["state"]),
        code_verifier=str(data["code_verifier"]),
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an OAuth 2.0 PKCE authorization URL without HTTP.",
    )
    parser.add_argument("--client-id", default=os.environ.get("X_OAUTH2_CLIENT_ID", ""))
    parser.add_argument(
        "--redirect-uri",
        default=os.environ.get("X_OAUTH2_REDIRECT_URI", ""),
    )
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH))
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print the URL without writing oauth2_state.local.json.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        authorization_state = build_authorization_state(
            client_id=args.client_id,
            redirect_uri=args.redirect_uri,
        )
        if not args.no_save:
            path = save_authorization_state(authorization_state, args.state_path)
            print(f"Saved OAuth2 state to: {path}")
        print("Open this authorization URL locally:")
        print(authorization_state.authorization_url)
        print("Do not paste tokens or authorization codes into chat/logs.")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


def _required(name: str, value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise XConfigError(f"Missing required OAuth2 value: {name}")
    return cleaned


if __name__ == "__main__":
    raise SystemExit(main())
