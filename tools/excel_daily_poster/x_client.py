from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, NoReturn, Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request


class XPosterError(Exception):
    """Base exception for the legacy-account X posting flow."""


class XClientError(XPosterError):
    """Base exception for X API/client errors that must stop the whole run."""


class XAuthError(XClientError):
    """Authentication or permission error, including 401 and 403 responses."""


class XRateLimitError(XClientError):
    """Rate limit error, including 429 responses."""


class XNetworkError(XClientError):
    """Network connection, DNS, timeout, or transport error."""


class XTemporaryError(XClientError):
    """Temporary X-side failure, including 5xx responses."""


class XConfigError(XClientError):
    """Missing API keys, missing .env values, or invalid poster configuration."""


@dataclass(frozen=True)
class XApiCredentials:
    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str

    def validated(self) -> XApiCredentials:
        return XApiCredentials(
            api_key=require_config_value("X_API_KEY", self.api_key),
            api_secret=require_config_value("X_API_SECRET", self.api_secret),
            access_token=require_config_value("X_ACCESS_TOKEN", self.access_token),
            access_token_secret=require_config_value(
                "X_ACCESS_TOKEN_SECRET",
                self.access_token_secret,
            ),
        )


@dataclass(frozen=True)
class OAuth2UserContextCredentials:
    client_id: str
    access_token: str
    client_secret: str = ""
    refresh_token: str = ""
    scopes: tuple[str, ...] = ()

    def validated_for_post(self) -> OAuth2UserContextCredentials:
        access_token = require_config_value(
            "X_OAUTH2_ACCESS_TOKEN",
            self.access_token,
        )
        client_id = require_config_value("X_OAUTH2_CLIENT_ID", self.client_id)
        scopes = tuple(scope.strip() for scope in self.scopes if scope.strip())
        missing_scopes = [
            scope for scope in ["tweet.read", "tweet.write", "users.read"]
            if scope not in scopes
        ]
        if missing_scopes:
            raise XConfigError(
                "OAuth 2.0 User Context token is missing required scopes: "
                f"{', '.join(missing_scopes)}"
            )
        return OAuth2UserContextCredentials(
            client_id=client_id,
            client_secret=self.client_secret.strip(),
            access_token=access_token,
            refresh_token=self.refresh_token.strip(),
            scopes=scopes,
        )


@dataclass(frozen=True)
class XPostResult:
    tweet_id: str
    text: str


class XPoster(Protocol):
    def post(self, text: str) -> XPostResult:
        ...


class BlockedXPoster:
    """Default poster that prevents accidental real API calls."""

    def post(self, text: str) -> XPostResult:
        raise XConfigError(
            "Real X API posting is intentionally disabled in this repository. "
            "Inject an approved XPoster implementation only after explicit live "
            "posting approval."
        )


ClientFactory = Callable[[XApiCredentials], Any]
OAuth2Transport = Callable[[str, dict[str, str], dict[str, str]], Any]


class TweepyXPoster:
    """Future real X poster with injectable client creation.

    This class is intentionally not used by default. Tests inject a fake
    client_factory, so no real SDK call or network access is required.
    """

    def __init__(
        self,
        credentials: XApiCredentials,
        *,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.credentials = credentials.validated()
        self.client_factory = client_factory or _build_tweepy_client

    def post(self, text: str) -> XPostResult:
        validate_post_text(text)
        try:
            client = self.client_factory(self.credentials)
            response = client.create_tweet(text=text)
            tweet_id = _extract_tweet_id(response)
        except XClientError:
            raise
        except Exception as exc:
            raise classify_sdk_exception(exc, self.credentials) from exc
        return XPostResult(tweet_id=tweet_id, text=text)


class OAuth2UserContextXPoster:
    """Future OAuth 2.0 User Context poster for POST /2/tweets.

    This class is not used by default. Tests inject a fake transport so no real
    HTTP request is made.
    """

    endpoint = "https://api.x.com/2/tweets"

    def __init__(
        self,
        credentials: OAuth2UserContextCredentials,
        *,
        transport: OAuth2Transport | None = None,
    ) -> None:
        self.credentials = credentials.validated_for_post()
        self.transport = transport or _post_json_with_urllib

    def post(self, text: str) -> XPostResult:
        validate_post_text(text)
        headers = {
            "Authorization": f"Bearer {self.credentials.access_token}",
            "Content-Type": "application/json",
        }
        payload = {"text": text}
        try:
            response = self.transport(self.endpoint, headers, payload)
            tweet_id = _extract_tweet_id(response)
        except XClientError:
            raise
        except Exception as exc:
            raise classify_sdk_exception(exc, self.credentials) from exc
        return XPostResult(tweet_id=tweet_id, text=text)


def validate_post_text(text: str) -> None:
    body = text.strip()
    if not body:
        raise ValueError("post_text is empty")
    if len(body) > 280:
        raise ValueError(f"post_text exceeds 280 characters: {len(body)}")


def classify_http_status(status_code: int, message: str = "") -> XClientError:
    """Map an X API HTTP status to the system-level exception hierarchy."""

    detail = f"X API returned HTTP {status_code}"
    if message:
        detail = f"{detail}: {message}"

    if status_code in {401, 403}:
        return XAuthError(detail)
    if status_code == 429:
        return XRateLimitError(detail)
    if 500 <= status_code <= 599:
        return XTemporaryError(detail)
    return XClientError(detail)


def raise_for_http_status(status_code: int, message: str = "") -> NoReturn:
    """Raise a classified X API exception for a failed HTTP response."""

    raise classify_http_status(status_code, message)


def require_config_value(name: str, value: str | None) -> str:
    """Validate one required future X API config value without reading .env."""

    if value is None or not value.strip():
        raise XConfigError(f"Missing required X API config value: {name}")
    return value


def classify_sdk_exception(
    exc: Exception,
    credentials: XApiCredentials | OAuth2UserContextCredentials | None = None,
) -> XClientError:
    """Translate future SDK/HTTP exceptions into the poster error hierarchy."""

    safe_message = _redact_secrets(str(exc), credentials)
    status_code = _extract_status_code(exc)
    if status_code is not None:
        return classify_http_status(status_code, safe_message)

    text = f"{exc.__class__.__name__} {safe_message}".lower()
    if any(token in text for token in ["unauthorized", "forbidden"]):
        return XAuthError(safe_message)
    if any(token in text for token in ["rate limit", "ratelimit", "too many requests"]):
        return XRateLimitError(safe_message)
    if any(
        token in text
        for token in [
            "timeout",
            "timed out",
            "connection",
            "network",
            "dns",
            "name resolution",
            "temporary failure in name resolution",
        ]
    ):
        return XNetworkError(safe_message)
    if any(token in text for token in ["temporar", "service unavailable", "bad gateway"]):
        return XTemporaryError(safe_message)
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return XNetworkError(safe_message)
    return XClientError(safe_message)


def _build_tweepy_client(credentials: XApiCredentials) -> Any:
    try:
        import tweepy  # type: ignore[import-not-found]
    except ImportError as exc:
        raise XConfigError(
            "tweepy is not installed. Real posting remains unavailable until "
            "dependencies are reviewed and installed with explicit approval."
        ) from exc

    return tweepy.Client(
        consumer_key=credentials.api_key,
        consumer_secret=credentials.api_secret,
        access_token=credentials.access_token,
        access_token_secret=credentials.access_token_secret,
    )


def _post_json_with_urllib(
    url: str,
    headers: dict[str, str],
    payload: dict[str, str],
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib_request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib_request.urlopen(request, timeout=30) as response:
            status_code = getattr(response, "status", None)
            response_body = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        raise classify_http_status(exc.code, exc.reason) from exc
    except urllib_error.URLError as exc:
        raise XNetworkError(str(exc.reason)) from exc

    if isinstance(status_code, int) and status_code >= 400:
        raise classify_http_status(status_code, response_body)
    data = json.loads(response_body or "{}")
    if not isinstance(data, dict):
        raise XClientError("X API response was not a JSON object")
    return data


def _extract_tweet_id(response: Any) -> str:
    if isinstance(response, dict):
        data = response.get("data")
    else:
        data = getattr(response, "data", None)
    if isinstance(data, dict):
        tweet_id = data.get("id")
    else:
        tweet_id = getattr(data, "id", None)
    if tweet_id is None:
        raise XClientError("X API response did not include tweet id")
    return str(tweet_id)


def _extract_status_code(exc: Exception) -> int | None:
    for owner in [exc, getattr(exc, "response", None)]:
        if owner is None:
            continue
        status_code = getattr(owner, "status_code", None)
        if isinstance(status_code, int):
            return status_code
        status = getattr(owner, "status", None)
        if isinstance(status, int):
            return status
    return None


def _redact_secrets(
    text: str,
    credentials: XApiCredentials | OAuth2UserContextCredentials | None,
) -> str:
    if credentials is None:
        return text
    redacted = text
    for secret in _credential_secrets(credentials):
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def _credential_secrets(
    credentials: XApiCredentials | OAuth2UserContextCredentials,
) -> tuple[str, ...]:
    if isinstance(credentials, XApiCredentials):
        return (
            credentials.api_key,
            credentials.api_secret,
            credentials.access_token,
            credentials.access_token_secret,
        )
    return (
        credentials.access_token,
        credentials.refresh_token,
        credentials.client_secret,
    )
