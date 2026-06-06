from __future__ import annotations

import base64
import csv
import io
import json
import logging
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from tools.excel_daily_poster.daily_post import run_once
from tools.excel_daily_poster.excel_queue import (
    CsvPostQueue,
    QueueError,
    REQUIRED_COLUMNS,
    find_next_post,
)
from tools.excel_daily_poster.manual_live_post_once import (
    CONFIRM_MANUAL_LIVE,
    SIMILAR_RECENT_POST_REASON,
    assert_no_similar_recent_post,
    build_manual_poster,
    check_similar_recent_post,
    credentials_from_env,
    has_posted_today,
    normalize_for_similarity,
    oauth2_credentials_from_token_file,
    refresh_oauth2_token_file,
    run_manual_live_once,
)
from tools.excel_daily_poster.oauth2_authorize import (
    DEFAULT_SCOPES,
    build_authorization_state,
    code_challenge_for,
    save_authorization_state,
)
from tools.excel_daily_poster.oauth2_exchange_code import (
    CONFIRM_TOKEN_EXCHANGE,
    TOKEN_ENDPOINT,
    build_authorization_code_token_request,
    build_refresh_token_request,
    exchange_code_for_tokens,
    main as oauth2_exchange_main,
    save_tokens,
)
from tools.excel_daily_poster.oauth2_local_callback import (
    create_authorization_url,
    exchange_callback_params,
    parse_callback_params,
)
from tools.excel_daily_poster.oauth2_refresh_token import refresh_access_token
from tools.excel_daily_poster.x_client import (
    BlockedXPoster,
    OAuth2UserContextCredentials,
    OAuth2UserContextXPoster,
    TweepyXPoster,
    XApiCredentials,
    XAuthError,
    XClientError,
    XConfigError,
    XNetworkError,
    XPostResult,
    XPosterError,
    XRateLimitError,
    XTemporaryError,
    classify_sdk_exception,
    classify_http_status,
    require_config_value,
)


class MockPoster:
    def __init__(self, tweet_id: str = "tweet-123") -> None:
        self.tweet_id = tweet_id
        self.calls: list[str] = []

    def post(self, text: str) -> XPostResult:
        self.calls.append(text)
        return XPostResult(tweet_id=self.tweet_id, text=text)


class FailingPoster:
    def __init__(self, error: XClientError | None = None) -> None:
        self.error = error or XClientError("401 unauthorized")
        self.calls: list[str] = []

    def post(self, text: str) -> XPostResult:
        self.calls.append(text)
        raise self.error


class WriteFailingCsvPostQueue(CsvPostQueue):
    def write(self, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
        raise PermissionError("secret-access-token secret-refresh-token secret-client-secret")


class FakeResponse:
    def __init__(self, tweet_id: str) -> None:
        self.data = {"id": tweet_id}


class FakeXClient:
    def __init__(self, result: FakeResponse | Exception) -> None:
        self.result = result
        self.calls: list[str] = []

    def create_tweet(self, *, text: str) -> FakeResponse:
        self.calls.append(text)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeHttpError(Exception):
    def __init__(self, status_code: int, message: str = "api error") -> None:
        super().__init__(message)
        self.response = type("Response", (), {"status_code": status_code})()


class FakeOAuth2Transport:
    def __init__(self, result: dict[str, object] | Exception) -> None:
        self.result = result
        self.calls: list[tuple[str, dict[str, str], dict[str, str]]] = []

    def __call__(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, str],
    ) -> dict[str, object]:
        self.calls.append((url, headers, payload))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeTokenTransport:
    def __init__(self, result: dict[str, object] | Exception) -> None:
        self.result = result
        self.calls: list[tuple[str, dict[str, str], dict[str, str]]] = []

    def __call__(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, str],
    ) -> dict[str, object]:
        self.calls.append((url, headers, payload))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class ExcelDailyPosterTests(unittest.TestCase):
    REPO_ROOT = Path(__file__).resolve().parents[1]

    def test_blank_pending_and_retry_statuses_are_candidates(self) -> None:
        for status in ["", "pending", "retry"]:
            with self.subTest(status=status):
                selected = find_next_post(
                    [self.row(f"text {status}", status)],
                    today=date(2026, 5, 16),
                )
                self.assertIsNotNone(selected)
                self.assertEqual(selected.status, status)

    def test_non_candidate_statuses_are_not_selected(self) -> None:
        for status in ["posted", "skipped", "error", "content_error", "system_error"]:
            with self.subTest(status=status):
                selected = find_next_post(
                    [self.row("ignored", status)],
                    today=date(2026, 5, 16),
                )
                self.assertIsNone(selected)

    def test_skips_future_scheduled_date(self) -> None:
        rows = [
            self.row("future", "pending", "2026-05-17"),
            self.row("today", "pending", "2026-05-16"),
        ]

        selected = find_next_post(rows, today=date(2026, 5, 16))

        self.assertIsNotNone(selected)
        self.assertEqual(selected.post_text, "today")

    def test_dry_run_does_not_update_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "posts.csv"
            self.write_rows(
                path,
                [
                    self.row("x" * 281, "pending"),
                    self.row("dry run text", "pending"),
                ],
            )
            before = path.read_bytes()

            result = run_once(path, dry_run=True, today=date(2026, 5, 16))

            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(result.changed_queue)
            self.assertEqual(result.post_text, "dry run text")
            self.assertEqual(result.content_error_rows, (2,))

    def test_live_success_updates_csv_with_mocked_x_api(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "posts.csv"
            self.write_rows(path, [self.row("live text", "pending")])
            poster = MockPoster(tweet_id="tweet-999")

            result = run_once(
                path,
                dry_run=False,
                poster=poster,
                today=date(2026, 5, 16),
            )

            rows = self.read_rows(path)
            self.assertEqual(poster.calls, ["live text"])
            self.assertTrue(result.changed_queue)
            self.assertEqual(rows[0]["status"], "posted")
            self.assertEqual(rows[0]["tweet_id"], "tweet-999")
            self.assertTrue(rows[0]["posted_at"])
            self.assertEqual(rows[0]["error"], "")

    def test_too_long_row_becomes_content_error_and_next_valid_row_posts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "posts.csv"
            self.write_rows(
                path,
                [
                    self.row("x" * 281, "pending"),
                    self.row("valid text", "retry"),
                ],
            )
            poster = MockPoster(tweet_id="tweet-abc")

            result = run_once(
                path,
                dry_run=False,
                poster=poster,
                today=date(2026, 5, 16),
            )

            rows = self.read_rows(path)
            self.assertEqual(poster.calls, ["valid text"])
            self.assertEqual(result.content_error_rows, (2,))
            self.assertEqual(rows[0]["status"], "content_error")
            self.assertIn("280", rows[0]["error"])
            self.assertEqual(rows[1]["status"], "posted")

    def test_broken_scheduled_date_becomes_content_error_and_next_row_posts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "posts.csv"
            self.write_rows(
                path,
                [
                    self.row("bad date", "pending", "2026/05/16"),
                    self.row("valid after bad date", "pending"),
                ],
            )
            poster = MockPoster(tweet_id="tweet-date")

            run_once(path, dry_run=False, poster=poster, today=date(2026, 5, 16))

            rows = self.read_rows(path)
            self.assertEqual(poster.calls, ["valid after bad date"])
            self.assertEqual(rows[0]["status"], "content_error")
            self.assertIn("scheduled_date", rows[0]["error"])
            self.assertEqual(rows[1]["status"], "posted")

    def test_success_stops_after_one_post(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "posts.csv"
            self.write_rows(
                path,
                [
                    self.row("first valid", "pending"),
                    self.row("second valid", "pending"),
                ],
            )
            poster = MockPoster()

            run_once(path, dry_run=False, poster=poster, today=date(2026, 5, 16))

            rows = self.read_rows(path)
            self.assertEqual(poster.calls, ["first valid"])
            self.assertEqual(rows[0]["status"], "posted")
            self.assertEqual(rows[1]["status"], "pending")

    def test_api_error_stops_without_trying_next_row_or_writing_content_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "posts.csv"
            self.write_rows(
                path,
                [
                    self.row("x" * 281, "pending"),
                    self.row("api will fail", "pending"),
                    self.row("must not be tried", "pending"),
                ],
            )
            before = path.read_bytes()
            poster = FailingPoster()

            with self.assertRaises(XClientError):
                run_once(path, dry_run=False, poster=poster, today=date(2026, 5, 16))

            self.assertEqual(poster.calls, ["api will fail"])
            self.assertEqual(path.read_bytes(), before)

    def test_classified_x_api_errors_stop_without_touching_queue(self) -> None:
        error_cases = [
            XAuthError("401 unauthorized"),
            XRateLimitError("429 rate limit"),
            XNetworkError("network timeout"),
            XTemporaryError("x temporary failure"),
            XConfigError("missing api key"),
        ]

        for error in error_cases:
            with self.subTest(error=type(error).__name__):
                with tempfile.TemporaryDirectory() as temp_dir:
                    path = Path(temp_dir) / "posts.csv"
                    self.write_rows(
                        path,
                        [
                            self.row("will fail", "pending"),
                            self.row("must not be tried", "pending"),
                        ],
                    )
                    before = path.read_bytes()
                    poster = FailingPoster(error)

                    with self.assertRaises(type(error)):
                        run_once(
                            path,
                            dry_run=False,
                            poster=poster,
                            today=date(2026, 5, 16),
                        )

                    self.assertEqual(poster.calls, ["will fail"])
                    self.assertEqual(path.read_bytes(), before)

    def test_x_api_http_status_classification(self) -> None:
        self.assertIsInstance(classify_http_status(401), XAuthError)
        self.assertIsInstance(classify_http_status(403), XAuthError)
        self.assertIsInstance(classify_http_status(429), XRateLimitError)
        self.assertIsInstance(classify_http_status(500), XTemporaryError)
        self.assertIsInstance(classify_http_status(503), XTemporaryError)
        self.assertIsInstance(classify_http_status(400), XClientError)

    def test_x_exception_hierarchy_and_blocked_default(self) -> None:
        for exc_type in [
            XClientError,
            XAuthError,
            XRateLimitError,
            XNetworkError,
            XTemporaryError,
            XConfigError,
        ]:
            with self.subTest(exc_type=exc_type.__name__):
                self.assertTrue(issubclass(exc_type, XPosterError))

        with self.assertRaises(XConfigError):
            BlockedXPoster().post("must not post")

    def test_missing_config_value_is_system_error(self) -> None:
        with self.assertRaises(XConfigError):
            require_config_value("X_API_KEY", "")

        self.assertEqual(require_config_value("X_API_KEY", "abc"), "abc")

    def test_real_x_poster_missing_config_is_config_error(self) -> None:
        with self.assertRaises(XConfigError):
            TweepyXPoster(
                XApiCredentials(
                    api_key="",
                    api_secret="secret",
                    access_token="token",
                    access_token_secret="token-secret",
                ),
                client_factory=lambda credentials: FakeXClient(FakeResponse("unused")),
            )

    def test_real_x_poster_success_returns_tweet_id_with_mocked_client(self) -> None:
        fake_client = FakeXClient(FakeResponse("tweet-777"))

        poster = TweepyXPoster(
            self.credentials(),
            client_factory=lambda credentials: fake_client,
        )
        result = poster.post("hello from mock")

        self.assertEqual(fake_client.calls, ["hello from mock"])
        self.assertEqual(result.tweet_id, "tweet-777")
        self.assertEqual(result.text, "hello from mock")

    def test_real_x_poster_maps_auth_http_errors(self) -> None:
        for status_code in [401, 403]:
            with self.subTest(status_code=status_code):
                poster = self.poster_with_error(FakeHttpError(status_code))
                with self.assertRaises(XAuthError):
                    poster.post("auth failure")

    def test_real_x_poster_maps_rate_limit_http_error(self) -> None:
        poster = self.poster_with_error(FakeHttpError(429))

        with self.assertRaises(XRateLimitError):
            poster.post("rate limited")

    def test_real_x_poster_maps_temporary_http_errors(self) -> None:
        for status_code in [500, 503]:
            with self.subTest(status_code=status_code):
                poster = self.poster_with_error(FakeHttpError(status_code))
                with self.assertRaises(XTemporaryError):
                    poster.post("temporary failure")

    def test_real_x_poster_maps_network_errors(self) -> None:
        poster = self.poster_with_error(TimeoutError("request timed out"))

        with self.assertRaises(XNetworkError):
            poster.post("network failure")

    def test_real_x_poster_redacts_credentials_from_sdk_error_messages(self) -> None:
        credentials = XApiCredentials(
            api_key="secret-api-key",
            api_secret="secret-api-secret",
            access_token="secret-access-token",
            access_token_secret="secret-access-token-secret",
        )
        poster = TweepyXPoster(
            credentials,
            client_factory=lambda ignored: FakeXClient(
                FakeHttpError(
                    401,
                    "failed with secret-api-key secret-api-secret "
                    "secret-access-token secret-access-token-secret",
                )
            ),
        )

        with self.assertRaises(XAuthError) as caught:
            poster.post("redaction check")

        message = str(caught.exception)
        self.assertIn("[REDACTED]", message)
        self.assertNotIn("secret-api-key", message)
        self.assertNotIn("secret-api-secret", message)
        self.assertNotIn("secret-access-token", message)
        self.assertNotIn("secret-access-token-secret", message)

    def test_config_errors_do_not_include_secret_values(self) -> None:
        error = classify_sdk_exception(
            RuntimeError("connection failed with secret-access-token"),
            XApiCredentials(
                api_key="secret-api-key",
                api_secret="secret-api-secret",
                access_token="secret-access-token",
                access_token_secret="secret-access-token-secret",
            ),
        )

        self.assertNotIn("secret-access-token", str(error))

    def test_daily_post_default_poster_remains_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "posts.csv"
            self.write_rows(path, [self.row("default blocked", "pending")])
            before = path.read_bytes()

            with self.assertRaises(XConfigError):
                run_once(path, dry_run=False, today=date(2026, 5, 16))

            self.assertEqual(path.read_bytes(), before)

    def test_oauth2_user_context_missing_access_token_is_config_error(self) -> None:
        with self.assertRaises(XConfigError):
            OAuth2UserContextXPoster(
                OAuth2UserContextCredentials(
                    client_id="client-id",
                    access_token="",
                    scopes=("tweet.read", "tweet.write", "users.read"),
                ),
                transport=FakeOAuth2Transport({"data": {"id": "unused"}}),
            )

    def test_oauth2_user_context_missing_scope_is_config_error(self) -> None:
        with self.assertRaises(XConfigError):
            OAuth2UserContextXPoster(
                OAuth2UserContextCredentials(
                    client_id="client-id",
                    access_token="access-token",
                    scopes=("tweet.read", "users.read"),
                ),
                transport=FakeOAuth2Transport({"data": {"id": "unused"}}),
            )

    def test_oauth2_user_context_success_posts_with_bearer_token_using_mock_transport(self) -> None:
        transport = FakeOAuth2Transport({"data": {"id": "oauth2-tweet-1"}})
        poster = OAuth2UserContextXPoster(
            self.oauth2_credentials(),
            transport=transport,
        )

        result = poster.post("oauth2 mocked post")

        self.assertEqual(result.tweet_id, "oauth2-tweet-1")
        self.assertEqual(result.text, "oauth2 mocked post")
        self.assertEqual(len(transport.calls), 1)
        url, headers, payload = transport.calls[0]
        self.assertEqual(url, "https://api.x.com/2/tweets")
        self.assertEqual(headers["Authorization"], "Bearer oauth2-access-token")
        self.assertEqual(payload, {"text": "oauth2 mocked post"})

    def test_oauth2_user_context_maps_http_errors(self) -> None:
        cases = [
            (401, XAuthError),
            (403, XAuthError),
            (429, XRateLimitError),
            (500, XTemporaryError),
        ]
        for status_code, error_type in cases:
            with self.subTest(status_code=status_code):
                poster = OAuth2UserContextXPoster(
                    self.oauth2_credentials(),
                    transport=FakeOAuth2Transport(FakeHttpError(status_code)),
                )
                with self.assertRaises(error_type):
                    poster.post("oauth2 error")

    def test_oauth2_user_context_maps_network_error(self) -> None:
        poster = OAuth2UserContextXPoster(
            self.oauth2_credentials(),
            transport=FakeOAuth2Transport(ConnectionError("dns failure")),
        )

        with self.assertRaises(XNetworkError):
            poster.post("oauth2 network error")

    def test_oauth2_user_context_redacts_tokens_from_error_messages(self) -> None:
        poster = OAuth2UserContextXPoster(
            OAuth2UserContextCredentials(
                client_id="client-id",
                client_secret="oauth2-client-secret",
                access_token="oauth2-access-token",
                refresh_token="oauth2-refresh-token",
                scopes=("tweet.read", "tweet.write", "users.read", "offline.access"),
            ),
            transport=FakeOAuth2Transport(
                FakeHttpError(
                    403,
                    "oauth2-access-token oauth2-refresh-token oauth2-client-secret",
                )
            ),
        )

        with self.assertRaises(XAuthError) as caught:
            poster.post("oauth2 redaction")

        message = str(caught.exception)
        self.assertIn("[REDACTED]", message)
        self.assertNotIn("oauth2-access-token", message)
        self.assertNotIn("oauth2-refresh-token", message)
        self.assertNotIn("oauth2-client-secret", message)

    def test_oauth2_authorization_url_contains_required_scopes_and_pkce_values(self) -> None:
        authorization_state = build_authorization_state(
            client_id="client-id",
            redirect_uri="http://127.0.0.1:8765/callback",
            state="fixed-state",
            code_verifier="fixed-code-verifier",
        )
        query = parse_qs(urlparse(authorization_state.authorization_url).query)

        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["client_id"], ["client-id"])
        self.assertEqual(query["redirect_uri"], ["http://127.0.0.1:8765/callback"])
        self.assertEqual(query["state"], ["fixed-state"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(
            query["code_challenge"],
            [code_challenge_for("fixed-code-verifier")],
        )
        scopes = set(query["scope"][0].split())
        self.assertTrue(set(DEFAULT_SCOPES).issubset(scopes))
        self.assertTrue(authorization_state.code_verifier)
        self.assertTrue(authorization_state.code_challenge)
        self.assertTrue(authorization_state.state)

    def test_oauth2_state_mismatch_blocks_token_exchange(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "oauth2_state.local.json"
            save_authorization_state(
                build_authorization_state(
                    client_id="client-id",
                    redirect_uri="http://127.0.0.1/callback",
                    state="expected-state",
                    code_verifier="verifier",
                ),
                state_path,
            )

            with self.assertRaises(XAuthError):
                exchange_code_for_tokens(
                    code="auth-code",
                    returned_state="wrong-state",
                    state_path=state_path,
                    transport=FakeTokenTransport({}),
                )

    def test_oauth2_code_exchange_uses_mock_transport_and_saves_tokens_locally(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "oauth2_state.local.json"
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            save_authorization_state(
                build_authorization_state(
                    client_id="client-id",
                    redirect_uri="http://127.0.0.1/callback",
                    state="expected-state",
                    code_verifier="verifier",
                ),
                state_path,
            )
            transport = FakeTokenTransport(
                {
                    "access_token": "access-token",
                    "refresh_token": "refresh-token",
                    "token_type": "bearer",
                    "expires_in": 7200,
                    "scope": "tweet.read tweet.write users.read offline.access",
                }
            )

            tokens = exchange_code_for_tokens(
                code="auth-code",
                returned_state="expected-state",
                state_path=state_path,
                transport=transport,
            )
            save_tokens(tokens, token_path)

            self.assertEqual(tokens.access_token, "access-token")
            self.assertEqual(tokens.refresh_token, "refresh-token")
            self.assertEqual(len(transport.calls), 1)
            url, headers, payload = transport.calls[0]
            self.assertEqual(url, TOKEN_ENDPOINT)
            self.assertEqual(headers["Content-Type"], "application/x-www-form-urlencoded")
            self.assertEqual(payload["grant_type"], "authorization_code")
            self.assertEqual(payload["code_verifier"], "verifier")
            saved = json.loads(token_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["access_token"], "access-token")

    def test_oauth2_token_exchange_with_client_secret_uses_basic_auth_header(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "oauth2_state.local.json"
            save_authorization_state(
                build_authorization_state(
                    client_id="client-id",
                    redirect_uri="http://127.0.0.1/callback",
                    state="expected-state",
                    code_verifier="verifier",
                ),
                state_path,
            )
            transport = FakeTokenTransport({"access_token": "access-token"})

            exchange_code_for_tokens(
                code="auth-code",
                returned_state="expected-state",
                state_path=state_path,
                transport=transport,
                client_secret="client-secret",
            )

            _, headers, payload = transport.calls[0]
            expected = base64.b64encode(b"client-id:client-secret").decode("ascii")
            self.assertEqual(headers["Authorization"], f"Basic {expected}")
            self.assertNotIn("client_secret", payload)

    def test_oauth2_token_exchange_without_client_secret_omits_basic_auth_header(self) -> None:
        payload, headers = build_authorization_code_token_request(
            client_id="client-id",
            code="auth-code",
            redirect_uri="http://127.0.0.1/callback",
            code_verifier="verifier",
        )

        self.assertNotIn("Authorization", headers)
        self.assertNotIn("client_secret", payload)

    def test_oauth2_refresh_with_client_secret_uses_basic_auth_header(self) -> None:
        payload, headers = build_refresh_token_request(
            client_id="client-id",
            refresh_token="refresh-token",
            client_secret="client-secret",
        )

        expected = base64.b64encode(b"client-id:client-secret").decode("ascii")
        self.assertEqual(headers["Authorization"], f"Basic {expected}")
        self.assertNotIn("client_secret", payload)
        self.assertEqual(payload["refresh_token"], "refresh-token")

    def test_oauth2_exchange_cli_without_confirm_does_not_exchange(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "oauth2_state.local.json"
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            save_authorization_state(
                build_authorization_state(
                    client_id="client-id",
                    redirect_uri="http://127.0.0.1/callback",
                    state="expected-state",
                    code_verifier="verifier",
                ),
                state_path,
            )
            stdout = io.StringIO()
            stderr = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = oauth2_exchange_main(
                    [
                        "--code",
                        "auth-code",
                        "--state",
                        "expected-state",
                        "--state-path",
                        str(state_path),
                        "--token-path",
                        str(token_path),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertFalse(token_path.exists())
            self.assertIn("disabled", stderr.getvalue())
            self.assertNotIn("auth-code", stderr.getvalue())

    def test_oauth2_exchange_live_cli_can_be_mocked_and_does_not_print_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "oauth2_state.local.json"
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            save_authorization_state(
                build_authorization_state(
                    client_id="client-id",
                    redirect_uri="http://127.0.0.1/callback",
                    state="expected-state",
                    code_verifier="verifier",
                ),
                state_path,
            )
            stdout = io.StringIO()
            stderr = io.StringIO()

            with patch(
                "tools.excel_daily_poster.oauth2_exchange_code._post_form_with_urllib",
                return_value={
                    "access_token": "access-token",
                    "refresh_token": "refresh-token",
                    "token_type": "bearer",
                    "expires_in": 7200,
                },
            ):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = oauth2_exchange_main(
                        [
                            "--code",
                            "auth-code",
                            "--state",
                            "expected-state",
                            "--state-path",
                            str(state_path),
                            "--token-path",
                            str(token_path),
                            "--exchange-live",
                            "--confirm-token-exchange",
                            CONFIRM_TOKEN_EXCHANGE,
                        ]
                    )

            self.assertEqual(exit_code, 0)
            output = stdout.getvalue() + stderr.getvalue()
            self.assertIn("Tokens saved", output)
            self.assertNotIn("access-token", output)
            self.assertNotIn("refresh-token", output)
            self.assertNotIn("auth-code", output)
            saved = json.loads(token_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["access_token"], "access-token")
            self.assertEqual(saved["refresh_token"], "refresh-token")

    def test_oauth2_exchange_errors_redact_code_and_client_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "oauth2_state.local.json"
            save_authorization_state(
                build_authorization_state(
                    client_id="client-id",
                    redirect_uri="http://127.0.0.1/callback",
                    state="expected-state",
                    code_verifier="verifier",
                ),
                state_path,
            )

            with self.assertRaises(XAuthError) as caught:
                exchange_code_for_tokens(
                    code="secret-auth-code",
                    returned_state="expected-state",
                    state_path=state_path,
                    transport=FakeTokenTransport(
                        FakeHttpError(
                            401,
                            "secret-auth-code secret-client-secret code_verifier",
                        )
                    ),
                    client_secret="secret-client-secret",
                )

            message = str(caught.exception)
            self.assertIn("[REDACTED]", message)
            self.assertNotIn("secret-auth-code", message)
            self.assertNotIn("secret-client-secret", message)
            self.assertNotIn("code_verifier", message)
            self.assertNotIn("client-id", message)

    def test_oauth2_unauthorized_client_error_is_auth_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "oauth2_state.local.json"
            save_authorization_state(
                build_authorization_state(
                    client_id="client-id",
                    redirect_uri="http://127.0.0.1/callback",
                    state="expected-state",
                    code_verifier="verifier",
                ),
                state_path,
            )

            with self.assertRaises(XAuthError) as caught:
                exchange_code_for_tokens(
                    code="secret-auth-code",
                    returned_state="expected-state",
                    state_path=state_path,
                    transport=FakeTokenTransport(
                        FakeHttpError(
                            401,
                            '{"error":"unauthorized_client","error_description":"Missing valid authorization header"}',
                        )
                    ),
                    client_secret="secret-client-secret",
                )

            self.assertIn("unauthorized_client", str(caught.exception))
            self.assertNotIn("secret-auth-code", str(caught.exception))
            self.assertNotIn("secret-client-secret", str(caught.exception))

    def test_oauth2_token_redacted_dict_hides_token_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "oauth2_state.local.json"
            save_authorization_state(
                build_authorization_state(
                    client_id="client-id",
                    redirect_uri="http://127.0.0.1/callback",
                    state="expected-state",
                    code_verifier="verifier",
                ),
                state_path,
            )
            tokens = exchange_code_for_tokens(
                code="auth-code",
                returned_state="expected-state",
                state_path=state_path,
                transport=FakeTokenTransport(
                    {
                        "access_token": "access-token",
                        "refresh_token": "refresh-token",
                        "token_type": "bearer",
                    }
                ),
            )

            redacted = tokens.redacted_dict()
            self.assertEqual(redacted["access_token"], "[REDACTED]")
            self.assertEqual(redacted["refresh_token"], "[REDACTED]")

    def test_oauth2_refresh_uses_mock_transport_only(self) -> None:
        transport = FakeTokenTransport(
            {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "token_type": "bearer",
            }
        )

        tokens = refresh_access_token(
            client_id="client-id",
            refresh_token="refresh-token",
            transport=transport,
        )

        self.assertEqual(tokens.access_token, "new-access-token")
        self.assertEqual(len(transport.calls), 1)
        _, _, payload = transport.calls[0]
        self.assertEqual(payload["grant_type"], "refresh_token")
        self.assertEqual(payload["refresh_token"], "refresh-token")

    def test_oauth2_refresh_transport_receives_basic_auth_when_secret_present(self) -> None:
        transport = FakeTokenTransport({"access_token": "new-access-token"})

        refresh_access_token(
            client_id="client-id",
            refresh_token="refresh-token",
            client_secret="client-secret",
            transport=transport,
        )

        _, headers, payload = transport.calls[0]
        expected = base64.b64encode(b"client-id:client-secret").decode("ascii")
        self.assertEqual(headers["Authorization"], f"Basic {expected}")
        self.assertNotIn("client_secret", payload)

    def test_oauth2_local_callback_parses_code_and_state(self) -> None:
        params = parse_callback_params(
            "/callback?code=auth-code&state=returned-state"
        )

        self.assertEqual(params["code"], "auth-code")
        self.assertEqual(params["state"], "returned-state")

    def test_oauth2_local_callback_state_mismatch_does_not_exchange(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "oauth2_state.local.json"
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            save_authorization_state(
                build_authorization_state(
                    client_id="client-id",
                    redirect_uri="http://127.0.0.1:8765/callback",
                    state="expected-state",
                    code_verifier="verifier",
                ),
                state_path,
            )
            transport = FakeTokenTransport({"access_token": "access-token"})

            with self.assertRaises(XAuthError):
                exchange_callback_params(
                    {"code": "auth-code", "state": "wrong-state"},
                    state_path=state_path,
                    token_path=token_path,
                    transport=transport,
                    confirm_token_exchange=CONFIRM_TOKEN_EXCHANGE,
                )

            self.assertEqual(transport.calls, [])
            self.assertFalse(token_path.exists())

    def test_oauth2_local_callback_missing_code_does_not_exchange(self) -> None:
        transport = FakeTokenTransport({"access_token": "access-token"})

        with self.assertRaises(XConfigError):
            exchange_callback_params(
                {"state": "expected-state"},
                transport=transport,
                confirm_token_exchange=CONFIRM_TOKEN_EXCHANGE,
            )

        self.assertEqual(transport.calls, [])

    def test_oauth2_local_callback_access_denied_does_not_exchange(self) -> None:
        transport = FakeTokenTransport({"access_token": "access-token"})

        with self.assertRaises(XAuthError):
            exchange_callback_params(
                {"error": "access_denied", "code": "auth-code"},
                transport=transport,
                confirm_token_exchange=CONFIRM_TOKEN_EXCHANGE,
            )

        self.assertEqual(transport.calls, [])

    def test_oauth2_local_callback_exchanges_with_fake_transport_and_saves_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "oauth2_state.local.json"
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            create_authorization_url(
                client_id="client-id",
                redirect_uri="http://127.0.0.1:8765/callback",
                state_path=state_path,
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))["state"]
            transport = FakeTokenTransport(
                {
                    "access_token": "access-token",
                    "refresh_token": "refresh-token",
                    "token_type": "bearer",
                }
            )

            result = exchange_callback_params(
                {"code": "auth-code", "state": state},
                state_path=state_path,
                token_path=token_path,
                transport=transport,
                client_secret="client-secret",
                confirm_token_exchange=CONFIRM_TOKEN_EXCHANGE,
            )

            self.assertTrue(result.success)
            self.assertEqual(result.token_path, token_path)
            self.assertEqual(len(transport.calls), 1)
            _, headers, payload = transport.calls[0]
            expected = base64.b64encode(b"client-id:client-secret").decode("ascii")
            self.assertEqual(headers["Authorization"], f"Basic {expected}")
            self.assertEqual(payload["code"], "auth-code")
            saved = json.loads(token_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["access_token"], "access-token")
            self.assertEqual(saved["refresh_token"], "refresh-token")

    def test_oauth2_local_callback_redacts_sensitive_values_from_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "oauth2_state.local.json"
            save_authorization_state(
                build_authorization_state(
                    client_id="client-id",
                    redirect_uri="http://127.0.0.1:8765/callback",
                    state="expected-state",
                    code_verifier="secret-code-verifier",
                ),
                state_path,
            )

            with self.assertRaises(XAuthError) as caught:
                exchange_callback_params(
                    {"code": "secret-auth-code", "state": "expected-state"},
                    state_path=state_path,
                    transport=FakeTokenTransport(
                        FakeHttpError(
                            401,
                            "secret-auth-code secret-client-secret secret-code-verifier",
                        )
                    ),
                    client_secret="secret-client-secret",
                    confirm_token_exchange=CONFIRM_TOKEN_EXCHANGE,
                )

            message = str(caught.exception)
            self.assertNotIn("secret-auth-code", message)
            self.assertNotIn("secret-client-secret", message)
            self.assertNotIn("secret-code-verifier", message)

    def test_oauth2_local_token_and_state_files_are_ignored(self) -> None:
        gitignore = (self.REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("data/oauth2_*.local.json", gitignore)
        self.assertIn("data/*token*.local.json", gitignore)
        self.assertIn("data/*secret*.local.json", gitignore)

    def test_manual_live_wrapper_requires_exact_confirmation_before_posting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "posts.csv"
            self.write_rows(path, [self.row("manual test", "pending")])
            before = path.read_bytes()
            poster = MockPoster()

            with self.assertRaises(XConfigError):
                run_manual_live_once(path, confirm="wrong", poster=poster)

            self.assertEqual(poster.calls, [])
            self.assertEqual(path.read_bytes(), before)

    def test_manual_live_wrapper_missing_env_config_is_config_error(self) -> None:
        with self.assertRaises(XConfigError):
            credentials_from_env({})

    def test_oauth2_credentials_can_be_loaded_from_token_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            token_path.write_text(
                json.dumps(
                    {
                        "access_token": "oauth2-access-token",
                        "refresh_token": "oauth2-refresh-token",
                        "scope": "tweet.read tweet.write users.read offline.access",
                    }
                ),
                encoding="utf-8",
            )

            credentials = oauth2_credentials_from_token_file(
                token_path,
                environ={"X_OAUTH2_CLIENT_ID": "client-id"},
            )

            self.assertEqual(credentials.access_token, "oauth2-access-token")
            self.assertEqual(credentials.refresh_token, "oauth2-refresh-token")
            self.assertIn("tweet.write", credentials.scopes)

    def test_oauth2_token_file_missing_is_config_error(self) -> None:
        with self.assertRaises(XConfigError):
            oauth2_credentials_from_token_file(
                "missing-oauth2_tokens.local.json",
                environ={"X_OAUTH2_CLIENT_ID": "client-id"},
            )

    def test_oauth2_token_file_missing_access_token_is_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            token_path.write_text(
                json.dumps({"refresh_token": "oauth2-refresh-token"}),
                encoding="utf-8",
            )

            with self.assertRaises(XConfigError):
                oauth2_credentials_from_token_file(
                    token_path,
                    environ={"X_OAUTH2_CLIENT_ID": "client-id"},
                )

    def test_oauth2_token_value_is_not_in_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            token_path.write_text(
                json.dumps(
                    {
                        "access_token": "secret-oauth2-access-token",
                        "refresh_token": "secret-oauth2-refresh-token",
                        "scope": "tweet.read tweet.write users.read offline.access",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(XConfigError) as caught:
                oauth2_credentials_from_token_file(token_path, environ={})

            message = str(caught.exception)
            self.assertNotIn("secret-oauth2-access-token", message)
            self.assertNotIn("secret-oauth2-refresh-token", message)

    def test_manual_live_wrapper_uses_oauth2_only_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            token_path.write_text(
                json.dumps(
                    {
                        "access_token": "oauth2-access-token",
                        "scope": "tweet.read tweet.write users.read offline.access",
                    }
                ),
                encoding="utf-8",
            )
            transport = FakeOAuth2Transport({"data": {"id": "oauth2-manual-1"}})

            poster = build_manual_poster(
                auth="oauth2",
                environ={"X_OAUTH2_CLIENT_ID": "client-id"},
                oauth2_token_path=token_path,
                oauth2_transport=transport,
                skip_oauth2_refresh=True,
            )
            result = poster.post("manual oauth2 test")

            self.assertEqual(result.tweet_id, "oauth2-manual-1")
            self.assertEqual(len(transport.calls), 1)
            _, headers, _ = transport.calls[0]
            self.assertEqual(headers["Authorization"], "Bearer oauth2-access-token")

            with self.assertRaises(XConfigError):
                build_manual_poster(
                    auth="oauth1",
                    environ={},
                    oauth2_token_path=token_path,
                    oauth2_transport=transport,
                )

    def test_oauth2_token_file_refresh_updates_saved_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            token_path.write_text(
                json.dumps(
                    {
                        "access_token": "old-access-token",
                        "refresh_token": "old-refresh-token",
                        "scope": "tweet.read tweet.write users.read offline.access",
                    }
                ),
                encoding="utf-8",
            )
            refresh_transport = FakeTokenTransport(
                {
                    "access_token": "new-access-token",
                    "refresh_token": "new-refresh-token",
                    "token_type": "bearer",
                    "expires_in": 7200,
                    "scope": "tweet.read tweet.write users.read offline.access",
                }
            )

            refresh_oauth2_token_file(
                token_path,
                environ={"X_OAUTH2_CLIENT_ID": "client-id"},
                transport=refresh_transport,
            )

            saved = json.loads(token_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["access_token"], "new-access-token")
            self.assertEqual(saved["refresh_token"], "new-refresh-token")
            self.assertEqual(saved["expires_in"], 7200)
            _, headers, payload = refresh_transport.calls[0]
            self.assertEqual(payload["grant_type"], "refresh_token")
            self.assertEqual(payload["refresh_token"], "old-refresh-token")
            self.assertNotIn("Authorization", headers)

    def test_oauth2_refresh_missing_refresh_token_is_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            token_path.write_text(
                json.dumps({"access_token": "old-access-token"}),
                encoding="utf-8",
            )

            with self.assertRaises(XConfigError):
                refresh_oauth2_token_file(
                    token_path,
                    environ={"X_OAUTH2_CLIENT_ID": "client-id"},
                    transport=FakeTokenTransport({"access_token": "new-access-token"}),
                )

    def test_manual_live_oauth2_refreshes_before_posting_with_new_access_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "posts.csv"
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            self.write_rows(queue_path, [self.row("oauth2 refreshed post", "pending")])
            token_path.write_text(
                json.dumps(
                    {
                        "access_token": "old-access-token",
                        "refresh_token": "old-refresh-token",
                        "scope": "tweet.read tweet.write users.read offline.access",
                    }
                ),
                encoding="utf-8",
            )
            refresh_transport = FakeTokenTransport(
                {
                    "access_token": "new-access-token",
                    "refresh_token": "new-refresh-token",
                    "token_type": "bearer",
                    "expires_in": 7200,
                    "scope": "tweet.read tweet.write users.read offline.access",
                }
            )
            post_transport = FakeOAuth2Transport({"data": {"id": "oauth2-refreshed-1"}})

            result = run_manual_live_once(
                queue_path,
                confirm=CONFIRM_MANUAL_LIVE,
                auth="oauth2",
                environ={"X_OAUTH2_CLIENT_ID": "client-id"},
                oauth2_token_path=token_path,
                oauth2_transport=post_transport,
                oauth2_refresh_transport=refresh_transport,
            )

            self.assertEqual(result.selected_row, 2)
            self.assertEqual(len(refresh_transport.calls), 1)
            self.assertEqual(len(post_transport.calls), 1)
            _, post_headers, _ = post_transport.calls[0]
            self.assertEqual(post_headers["Authorization"], "Bearer new-access-token")
            saved = json.loads(token_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["access_token"], "new-access-token")

    def test_manual_live_oauth2_refresh_failure_does_not_post(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "posts.csv"
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            self.write_rows(queue_path, [self.row("must not post", "pending")])
            token_path.write_text(
                json.dumps(
                    {
                        "access_token": "old-access-token",
                        "refresh_token": "secret-refresh-token",
                        "scope": "tweet.read tweet.write users.read offline.access",
                    }
                ),
                encoding="utf-8",
            )
            refresh_transport = FakeTokenTransport(
                FakeHttpError(401, "secret-refresh-token secret-client-secret")
            )
            post_transport = FakeOAuth2Transport({"data": {"id": "must-not-post"}})

            with self.assertRaises(XAuthError) as caught:
                run_manual_live_once(
                    queue_path,
                    confirm=CONFIRM_MANUAL_LIVE,
                    auth="oauth2",
                    environ={
                        "X_OAUTH2_CLIENT_ID": "client-id",
                        "X_OAUTH2_CLIENT_SECRET": "secret-client-secret",
                    },
                    oauth2_token_path=token_path,
                    oauth2_transport=post_transport,
                    oauth2_refresh_transport=refresh_transport,
                )

            self.assertEqual(post_transport.calls, [])
            message = str(caught.exception)
            self.assertNotIn("secret-refresh-token", message)
            self.assertNotIn("secret-client-secret", message)

    def test_manual_live_wrapper_posts_one_row_with_mocked_poster(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "posts.csv"
            self.write_rows(
                path,
                [
                    self.row("manual first", "pending"),
                    self.row("manual second", "pending"),
                ],
            )
            poster = MockPoster(tweet_id="manual-1")

            result = run_manual_live_once(
                path,
                confirm=CONFIRM_MANUAL_LIVE,
                poster=poster,
            )

            rows = self.read_rows(path)
            self.assertEqual(poster.calls, ["manual first"])
            self.assertEqual(result.selected_row, 2)
            self.assertEqual(rows[0]["status"], "posted")
            self.assertEqual(rows[0]["tweet_id"], "manual-1")
            self.assertEqual(rows[1]["status"], "pending")

    def test_manual_live_oauth2_posts_one_row_with_fake_transport(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "posts.csv"
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            self.write_rows(
                queue_path,
                [
                    self.row("oauth2 first", "pending"),
                    self.row("oauth2 second", "pending"),
                ],
            )
            token_path.write_text(
                json.dumps(
                    {
                        "access_token": "oauth2-access-token",
                        "refresh_token": "oauth2-refresh-token",
                        "scope": "tweet.read tweet.write users.read offline.access",
                    }
                ),
                encoding="utf-8",
            )
            refresh_transport = FakeTokenTransport(
                {
                    "access_token": "oauth2-new-access-token",
                    "refresh_token": "oauth2-new-refresh-token",
                    "scope": "tweet.read tweet.write users.read offline.access",
                }
            )
            transport = FakeOAuth2Transport({"data": {"id": "oauth2-live-1"}})

            result = run_manual_live_once(
                queue_path,
                confirm=CONFIRM_MANUAL_LIVE,
                auth="oauth2",
                environ={"X_OAUTH2_CLIENT_ID": "client-id"},
                oauth2_token_path=token_path,
                oauth2_transport=transport,
                oauth2_refresh_transport=refresh_transport,
            )

            rows = self.read_rows(queue_path)
            self.assertEqual(result.selected_row, 2)
            self.assertEqual(len(transport.calls), 1)
            self.assertEqual(rows[0]["status"], "posted")
            self.assertEqual(rows[0]["tweet_id"], "oauth2-live-1")
            self.assertEqual(rows[1]["status"], "pending")

    def test_manual_live_oauth2_requires_confirmation_before_reading_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "posts.csv"
            token_path = Path(temp_dir) / "missing.json"
            self.write_rows(queue_path, [self.row("oauth2 blocked", "pending")])

            with self.assertRaises(XConfigError):
                run_manual_live_once(
                    queue_path,
                    confirm="wrong",
                    auth="oauth2",
                    environ={"X_OAUTH2_CLIENT_ID": "client-id"},
                    oauth2_token_path=token_path,
                    oauth2_transport=FakeOAuth2Transport({"data": {"id": "nope"}}),
                )

    def test_manual_live_oauth2_api_error_stops_without_next_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "posts.csv"
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            self.write_rows(
                queue_path,
                [
                    self.row("oauth2 fails", "pending"),
                    self.row("must not post", "pending"),
                ],
            )
            token_path.write_text(
                json.dumps(
                    {
                        "access_token": "oauth2-access-token",
                        "refresh_token": "oauth2-refresh-token",
                        "scope": "tweet.read tweet.write users.read offline.access",
                    }
                ),
                encoding="utf-8",
            )
            before = queue_path.read_bytes()
            refresh_transport = FakeTokenTransport(
                {
                    "access_token": "oauth2-new-access-token",
                    "refresh_token": "oauth2-new-refresh-token",
                    "scope": "tweet.read tweet.write users.read offline.access",
                }
            )
            transport = FakeOAuth2Transport(FakeHttpError(429))

            with self.assertRaises(XRateLimitError):
                run_manual_live_once(
                    queue_path,
                    confirm=CONFIRM_MANUAL_LIVE,
                    auth="oauth2",
                    environ={"X_OAUTH2_CLIENT_ID": "client-id"},
                    oauth2_token_path=token_path,
                    oauth2_transport=transport,
                    oauth2_refresh_transport=refresh_transport,
                )

            self.assertEqual(len(transport.calls), 1)
            self.assertEqual(queue_path.read_bytes(), before)

    def test_one_post_per_day_guard_detects_today_posted_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "posts.csv"
            self.write_rows(
                queue_path,
                [
                    {
                        **self.row("already posted", "posted"),
                        "posted_at": "2026-05-23T21:45:00",
                    },
                    self.row("must wait", "pending"),
                ],
            )

            self.assertTrue(has_posted_today(queue_path, today=date(2026, 5, 23)))
            self.assertFalse(has_posted_today(queue_path, today=date(2026, 5, 24)))

    def test_one_post_per_day_guard_skips_before_refresh_or_post(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "posts.csv"
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            self.write_rows(
                queue_path,
                [
                    {
                        **self.row("already posted", "posted"),
                        "posted_at": "2026-05-23T21:45:00",
                    },
                    self.row("must not post", "pending"),
                ],
            )
            token_path.write_text(
                json.dumps(
                    {
                        "access_token": "old-access-token",
                        "refresh_token": "old-refresh-token",
                        "scope": "tweet.read tweet.write users.read offline.access",
                    }
                ),
                encoding="utf-8",
            )
            before = queue_path.read_bytes()
            refresh_transport = FakeTokenTransport({"access_token": "new-access-token"})
            post_transport = FakeOAuth2Transport({"data": {"id": "must-not-post"}})

            result = run_manual_live_once(
                queue_path,
                confirm=CONFIRM_MANUAL_LIVE,
                auth="oauth2",
                environ={"X_OAUTH2_CLIENT_ID": "client-id"},
                oauth2_token_path=token_path,
                oauth2_transport=post_transport,
                oauth2_refresh_transport=refresh_transport,
                today=date(2026, 5, 23),
            )

            self.assertIsNone(result.selected_row)
            self.assertEqual(refresh_transport.calls, [])
            self.assertEqual(post_transport.calls, [])
            self.assertEqual(queue_path.read_bytes(), before)

    def test_one_post_per_day_guard_allows_next_candidate_when_no_today_post(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "posts.csv"
            self.write_rows(
                queue_path,
                [
                    {
                        **self.row("old posted", "posted"),
                        "posted_at": "2026-05-22T21:45:00",
                    },
                    self.row("today candidate", "pending"),
                ],
            )

            selected = find_next_post(
                self.read_rows(queue_path),
                today=date(2026, 5, 23),
            )

            self.assertFalse(has_posted_today(queue_path, today=date(2026, 5, 23)))
            self.assertIsNotNone(selected)
            self.assertEqual(selected.post_text, "today candidate")

    def test_similarity_normalization_absorbs_width_and_punctuation(self) -> None:
        self.assertEqual(
            normalize_for_similarity(" Ｈｅｌｌｏ！！  投稿、テスト "),
            "hello 投稿テスト",
        )

    def test_similar_recent_guard_blocks_exact_recent_match(self) -> None:
        rows = [
            {
                **self.row("同じ投稿文です", "posted"),
                "posted_at": "2026-05-10T22:00:00",
            },
            self.row("同じ投稿文です", "pending"),
        ]

        check = check_similar_recent_post(
            rows,
            "同じ投稿文です",
            today=date(2026, 5, 23),
        )

        self.assertTrue(check.blocked)
        self.assertEqual(check.reason_code, SIMILAR_RECENT_POST_REASON)
        self.assertEqual(check.matched_line_number, 2)
        self.assertEqual(check.similarity, 1.0)

    def test_similar_recent_guard_blocks_above_threshold(self) -> None:
        rows = [
            {
                **self.row("夜にゆっくり深呼吸して気持ちを整える投稿です", "posted"),
                "posted_at": "2026-05-10",
            }
        ]

        check = check_similar_recent_post(
            rows,
            "夜にゆっくり深呼吸して気持ちを整える投稿です。",
            today=date(2026, 5, 23),
            threshold=0.85,
        )

        self.assertTrue(check.blocked)

    def test_similar_recent_guard_ignores_old_posted_rows(self) -> None:
        rows = [
            {
                **self.row("似ている投稿文です", "posted"),
                "posted_at": "2026-04-01T22:00:00",
            }
        ]

        check = check_similar_recent_post(
            rows,
            "似ている投稿文です",
            today=date(2026, 5, 23),
            days=30,
        )

        self.assertFalse(check.blocked)

    def test_similar_recent_guard_uses_today_posted_rows(self) -> None:
        rows = [
            {
                **self.row("今日投稿済みの似た文です", "posted"),
                "posted_at": "2026-05-23T21:00:00",
            }
        ]

        check = check_similar_recent_post(
            rows,
            "今日投稿済みの似た文です",
            today=date(2026, 5, 23),
        )

        self.assertTrue(check.blocked)

    def test_similar_recent_guard_ignores_blank_posted_at(self) -> None:
        rows = [self.row("日付なしの投稿済み文です", "posted")]

        check = check_similar_recent_post(
            rows,
            "日付なしの投稿済み文です",
            today=date(2026, 5, 23),
        )

        self.assertFalse(check.blocked)

    def test_similar_recent_guard_ignores_non_posted_rows(self) -> None:
        rows = [
            {
                **self.row("pendingは比較対象外です", "pending"),
                "posted_at": "2026-05-10",
            }
        ]

        check = check_similar_recent_post(
            rows,
            "pendingは比較対象外です",
            today=date(2026, 5, 23),
        )

        self.assertFalse(check.blocked)

    def test_similar_recent_guard_respects_threshold(self) -> None:
        rows = [
            {
                **self.row("abcde", "posted"),
                "posted_at": "2026-05-10",
            }
        ]

        blocked = check_similar_recent_post(
            rows,
            "abcdf",
            today=date(2026, 5, 23),
            threshold=0.75,
        )
        allowed = check_similar_recent_post(
            rows,
            "abcdf",
            today=date(2026, 5, 23),
            threshold=0.95,
        )

        self.assertTrue(blocked.blocked)
        self.assertFalse(allowed.blocked)

    def test_manual_live_oauth2_similar_recent_block_stops_before_refresh_or_post(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "posts.csv"
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            self.write_rows(
                queue_path,
                [
                    {
                        **self.row("近い内容の投稿です", "posted"),
                        "posted_at": "2026-05-10T22:00:00",
                    },
                    self.row("近い内容の投稿です。", "pending"),
                    self.row("別の投稿なら進めるはずですが進まない", "pending"),
                ],
            )
            token_path.write_text(
                json.dumps(
                    {
                        "access_token": "old-access-token",
                        "refresh_token": "old-refresh-token",
                        "scope": "tweet.read tweet.write users.read offline.access",
                    }
                ),
                encoding="utf-8",
            )
            before = queue_path.read_bytes()
            refresh_transport = FakeTokenTransport({"access_token": "new-access-token"})
            post_transport = FakeOAuth2Transport({"data": {"id": "must-not-post"}})

            with self.assertRaises(XConfigError) as caught:
                run_manual_live_once(
                    queue_path,
                    confirm=CONFIRM_MANUAL_LIVE,
                    auth="oauth2",
                    environ={"X_OAUTH2_CLIENT_ID": "client-id"},
                    oauth2_token_path=token_path,
                    oauth2_transport=post_transport,
                    oauth2_refresh_transport=refresh_transport,
                    today=date(2026, 5, 23),
                )

            self.assertIn(SIMILAR_RECENT_POST_REASON, str(caught.exception))
            self.assertEqual(refresh_transport.calls, [])
            self.assertEqual(post_transport.calls, [])
            self.assertEqual(queue_path.read_bytes(), before)

    def test_similar_recent_guard_can_be_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "posts.csv"
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            self.write_rows(
                queue_path,
                [
                    {
                        **self.row("同じ文です", "posted"),
                        "posted_at": "2026-05-10T22:00:00",
                    },
                    self.row("同じ文です", "pending"),
                ],
            )
            token_path.write_text(
                json.dumps(
                    {
                        "access_token": "old-access-token",
                        "refresh_token": "old-refresh-token",
                        "scope": "tweet.read tweet.write users.read offline.access",
                    }
                ),
                encoding="utf-8",
            )
            refresh_transport = FakeTokenTransport(
                {
                    "access_token": "new-access-token",
                    "refresh_token": "new-refresh-token",
                    "scope": "tweet.read tweet.write users.read offline.access",
                }
            )
            post_transport = FakeOAuth2Transport({"data": {"id": "posted-with-disabled-check"}})

            result = run_manual_live_once(
                queue_path,
                confirm=CONFIRM_MANUAL_LIVE,
                auth="oauth2",
                environ={
                    "X_OAUTH2_CLIENT_ID": "client-id",
                    "SIMILAR_RECENT_POST_CHECK_ENABLED": "NO",
                },
                oauth2_token_path=token_path,
                oauth2_transport=post_transport,
                oauth2_refresh_transport=refresh_transport,
                today=date(2026, 5, 23),
            )

            self.assertEqual(result.selected_row, 3)
            self.assertEqual(len(refresh_transport.calls), 1)
            self.assertEqual(len(post_transport.calls), 1)

    def test_manual_live_oauth2_unwritable_csv_stops_before_refresh_or_post(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "posts.csv"
            token_path = Path(temp_dir) / "oauth2_tokens.local.json"
            self.write_rows(queue_path, [self.row("locked csv", "pending")])
            token_path.write_text(
                json.dumps(
                    {
                        "access_token": "old-access-token",
                        "refresh_token": "old-refresh-token",
                        "scope": "tweet.read tweet.write users.read offline.access",
                    }
                ),
                encoding="utf-8",
            )
            refresh_transport = FakeTokenTransport({"access_token": "new-access-token"})
            post_transport = FakeOAuth2Transport({"data": {"id": "must-not-post"}})

            with patch(
                "tools.excel_daily_poster.excel_queue.CsvPostQueue.assert_writable",
                side_effect=QueueError("Post queue is not writable. Close Excel."),
            ):
                with self.assertRaises(QueueError) as caught:
                    run_manual_live_once(
                        queue_path,
                        confirm=CONFIRM_MANUAL_LIVE,
                        auth="oauth2",
                        environ={"X_OAUTH2_CLIENT_ID": "client-id"},
                        oauth2_token_path=token_path,
                        oauth2_transport=post_transport,
                        oauth2_refresh_transport=refresh_transport,
                        today=date(2026, 5, 24),
                    )

            self.assertIn("Close Excel", str(caught.exception))
            self.assertEqual(refresh_transport.calls, [])
            self.assertEqual(post_transport.calls, [])

    def test_live_csv_update_failure_logs_manual_recovery_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "posts.csv"
            self.write_rows(queue_path, [self.row("writeback fails", "pending")])
            poster = MockPoster(tweet_id="tweet-writeback-1")
            logger = logging.getLogger("test_csv_recovery")
            stream = io.StringIO()
            handler = logging.StreamHandler(stream)
            logger.handlers = [handler]
            logger.setLevel(logging.INFO)
            logger.propagate = False

            with patch(
                "tools.excel_daily_poster.daily_post.open_queue",
                return_value=WriteFailingCsvPostQueue(queue_path),
            ):
                with self.assertRaises(QueueError) as caught:
                    run_once(
                        queue_path,
                        dry_run=False,
                        poster=poster,
                        today=date(2026, 5, 24),
                        logger=logger,
                    )

            log_text = stream.getvalue()
            message = str(caught.exception)
            self.assertEqual(poster.calls, ["writeback fails"])
            self.assertIn("csv_update_failed_after_post", log_text)
            self.assertIn("row_number=2", log_text)
            self.assertIn("tweet_id=tweet-writeback-1", log_text)
            self.assertIn("posted_at=", log_text)
            self.assertIn("Manual recovery is required", message)
            self.assertIn("row 2", message)
            self.assertIn("tweet_id=tweet-writeback-1", message)
            self.assertNotIn("secret-access-token", log_text + message)
            self.assertNotIn("secret-refresh-token", log_text + message)
            self.assertNotIn("secret-client-secret", log_text + message)

    def test_csv_temp_file_preflight_blocks_posting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "posts.csv"
            self.write_rows(queue_path, [self.row("tmp exists", "pending")])
            queue_path.with_suffix(".csv.tmp").write_text("stale", encoding="utf-8")

            with self.assertRaises(QueueError) as caught:
                CsvPostQueue(queue_path).assert_writable()

            self.assertIn("temp file already exists", str(caught.exception))

    def test_assert_similar_recent_post_uses_environment_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "posts.csv"
            self.write_rows(
                queue_path,
                [
                    {
                        **self.row("環境変数で見る投稿", "posted"),
                        "posted_at": "2026-05-01",
                    },
                    self.row("環境変数で見る投稿", "pending"),
                ],
            )

            with self.assertRaises(XConfigError):
                assert_no_similar_recent_post(
                    queue_path,
                    today=date(2026, 5, 23),
                    environ={
                        "SIMILAR_RECENT_POST_CHECK_ENABLED": "YES",
                        "SIMILAR_RECENT_POST_DAYS": "30",
                        "SIMILAR_RECENT_POST_THRESHOLD": "0.85",
                    },
                )

    def test_manual_live_example_bat_contains_no_real_key_placeholders_only(self) -> None:
        text = (
            self.REPO_ROOT / "scripts" / "manual_live_post_once.example.bat"
        ).read_text(encoding="utf-8")

        self.assertIn("REPLACE_WITH_API_KEY", text)
        self.assertIn("manual_live_post_once.local.bat", text)
        self.assertIn("Refusing to run", text)
        self.assertNotIn("your_api_key_here", text.lower())
        self.assertNotIn("your_api_secret_here", text.lower())
        self.assertNotIn("your_access_token_here", text.lower())

    def test_oauth2_live_runner_example_refuses_to_run_as_is(self) -> None:
        text = (
            self.REPO_ROOT / "scripts" / "run_excel_daily_post_oauth2_live.example.bat"
        ).read_text(encoding="utf-8")

        self.assertIn("RUN_OAUTH2_LIVE_EXAMPLE=NO", text)
        self.assertIn("Refusing to run", text)
        self.assertIn("run_excel_daily_post_oauth2_live.local.bat", text)
        self.assertIn("--use-oauth2", text)
        self.assertIn("I_UNDERSTAND_THIS_POSTS_ONE_REAL_X_TWEET", text)
        self.assertIn("data\\oauth2_tokens.local.json", text)
        self.assertIn("data\\manual_account_posts.csv", text)
        self.assertIn("logs\\excel_daily_poster_oauth2_live.log", text)
        self.assertIn("RANDOM_DELAY_MINUTES_MAX=120", text)
        self.assertIn("SIMILAR_RECENT_POST_CHECK_ENABLED=YES", text)
        self.assertIn("SIMILAR_RECENT_POST_DAYS=30", text)
        self.assertIn("SIMILAR_RECENT_POST_THRESHOLD=0.85", text)
        self.assertIn("Get-Random -Minimum 0 -Maximum ($max + 1)", text)
        self.assertIn("Random delay:", text)
        self.assertIn("X_OAUTH2_CLIENT_ID", text)
        self.assertIn("X_OAUTH2_CLIENT_SECRET", text)
        self.assertIn("X_OAUTH2_REDIRECT_URI", text)
        self.assertNotIn("--dry-run", text)
        self.assertNotIn("your_", text.lower())

    def test_oauth2_live_task_registration_example_is_safe_and_targets_local_bat(self) -> None:
        text = (
            self.REPO_ROOT
            / "scripts"
            / "register_excel_daily_post_oauth2_live_task.example.bat"
        ).read_text(encoding="utf-8")

        self.assertIn("REGISTER_OAUTH2_LIVE_TASK_EXAMPLE=NO", text)
        self.assertIn("Refusing to register", text)
        self.assertIn("X OAuth2 Daily Poster", text)
        self.assertIn("run_excel_daily_post_oauth2_live.local.bat", text)
        self.assertIn("/SC DAILY", text)
        self.assertIn("/ST 21:30", text)
        self.assertIn("schtasks /Create", text)

    def test_power_check_bat_is_read_only(self) -> None:
        text = (
            self.REPO_ROOT / "scripts" / "check_power_settings.example.bat"
        ).read_text(encoding="utf-8")

        self.assertIn("powercfg /getactivescheme", text)
        self.assertIn("powercfg /query", text)
        self.assertIn("powercfg /waketimers", text)
        self.assertNotIn("powercfg /change", text)
        self.assertNotIn("schtasks /Create", text)

    def test_set_ac_no_sleep_example_is_locked_and_changes_only_ac_standby(self) -> None:
        text = (
            self.REPO_ROOT / "scripts" / "set_ac_no_sleep.example.bat"
        ).read_text(encoding="utf-8")

        self.assertIn("ENABLE_AC_NO_SLEEP_EXAMPLE=NO", text)
        self.assertIn("Refusing to change power settings", text)
        self.assertIn("set_ac_no_sleep.local.bat", text)
        self.assertIn("powercfg /change standby-timeout-ac 0", text)
        self.assertNotIn("standby-timeout-dc", text)
        self.assertNotIn("hibernate-timeout-ac 0", text)

    def test_restore_ac_sleep_example_is_locked_and_sets_ac_sleep_30(self) -> None:
        text = (
            self.REPO_ROOT / "scripts" / "restore_ac_sleep_30min.example.bat"
        ).read_text(encoding="utf-8")

        self.assertIn("RESTORE_AC_SLEEP_30MIN_EXAMPLE=NO", text)
        self.assertIn("Refusing to change power settings", text)
        self.assertIn("restore_ac_sleep_30min.local.bat", text)
        self.assertIn("powercfg /change standby-timeout-ac 30", text)
        self.assertNotIn("standby-timeout-dc", text)

    def test_oauth2_live_runner_is_documented_as_local_only(self) -> None:
        docs = (
            self.REPO_ROOT / "docs" / "excel_daily_poster.md"
        ).read_text(encoding="utf-8")

        self.assertIn("After Manual OAuth 2.0 Success", docs)
        self.assertIn("run_excel_daily_post_oauth2_live.example.bat", docs)
        self.assertIn("run_excel_daily_post_oauth2_live.local.bat", docs)
        self.assertIn("data/oauth2_tokens.local.json", docs)
        self.assertIn("X_OAUTH2_CLIENT_ID", docs)
        self.assertIn("once per day", docs)
        self.assertIn("several days", docs)
        self.assertIn("yokaze_daily", docs)
        self.assertIn("Daily Automation with Windows Task Scheduler", docs)
        self.assertIn("Night Random Posting Window", docs)
        self.assertIn("One Post Per Day Guard", docs)
        self.assertIn("21:30", docs)
        self.assertIn("23:30", docs)
        self.assertIn("Today already has a posted row. Skip posting.", docs)
        self.assertIn("Similar Recent Post Guard", docs)
        self.assertIn("similar_recent_post_detected", docs)
        self.assertIn("SIMILAR_RECENT_POST_THRESHOLD", docs)
        self.assertIn("Windows Sleep Settings for Daily Automation", docs)
        self.assertIn("powercfg /change standby-timeout-ac 0", docs)
        self.assertIn("powercfg /change standby-timeout-ac 30", docs)
        self.assertIn("check_power_settings.example.bat", docs)
        self.assertIn("Task Scheduler Conditions tab", docs)

    def test_manual_account_posts_example_has_required_headers_and_bom(self) -> None:
        path = self.REPO_ROOT / "data" / "manual_account_posts.csv.example"
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        first_line = text.splitlines()[0]

        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(first_line.split(","), REQUIRED_COLUMNS)

    def test_manual_account_posts_example_selection_order(self) -> None:
        path = self.REPO_ROOT / "data" / "manual_account_posts.csv.example"
        rows = self.read_rows(path)

        first = find_next_post(rows, today=date(2026, 5, 17))

        self.assertIsNotNone(first)
        self.assertEqual(first.csv_line_number, 2)
        self.assertEqual(first.post_text, "ここに1日目の投稿文を入力してください")

        rows[0]["status"] = "posted"
        second = find_next_post(rows, today=date(2026, 5, 17))

        self.assertIsNotNone(second)
        self.assertEqual(second.csv_line_number, 3)
        self.assertEqual(second.post_text, "ここに2日目の投稿文を入力してください")

        rows[1]["status"] = "posted"
        none_until_future = find_next_post(rows, today=date(2026, 5, 17))

        self.assertIsNone(none_until_future)

    def test_docs_describe_one_row_per_day_csv_format(self) -> None:
        docs = (
            self.REPO_ROOT / "docs" / "excel_daily_poster.md"
        ).read_text(encoding="utf-8")

        self.assertIn("One-Row-Per-Day CSV Format", docs)
        self.assertIn("UTF-8 with BOM", docs)
        self.assertIn("Paste post text vertically into column A", docs)
        self.assertIn("Save as CSV UTF-8", docs)
        self.assertIn("At most one row can be posted successfully per run", docs)
        self.assertIn("Start with 10 to 20 rows", docs)

    def test_scheduled_runner_remains_dry_run_only(self) -> None:
        text = (
            self.REPO_ROOT / "scripts" / "run_excel_daily_post.bat"
        ).read_text(encoding="utf-8")

        self.assertIn("--dry-run", text)
        self.assertNotIn("--live", text)
        self.assertNotIn("manual_live_post_once.py", text)
        self.assertNotIn("--use-oauth2", text)

    def test_task_registration_does_not_call_live_wrapper(self) -> None:
        text = (
            self.REPO_ROOT / "scripts" / "register_excel_daily_post_task.bat"
        ).read_text(encoding="utf-8")

        self.assertIn("run_excel_daily_post.bat", text)
        self.assertNotIn("manual_live_post_once.py", text)
        self.assertNotIn("run_excel_daily_post_oauth2_live", text)
        self.assertNotIn("--live", text)

    def test_local_secret_and_queue_files_are_ignored_and_documented(self) -> None:
        gitignore = (self.REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        docs = (
            self.REPO_ROOT / "docs" / "excel_daily_poster.md"
        ).read_text(encoding="utf-8")

        self.assertIn(".env", gitignore)
        self.assertIn("*.local.bat", gitignore)
        self.assertIn("data/manual_account_posts.csv", gitignore)
        self.assertIn("logs/", gitignore)
        self.assertIn("`data/manual_account_posts.csv` is ignored by Git", docs)
        self.assertIn("manual_live_post_once.local.bat", docs)

    def test_live_only_writes_content_error_when_no_valid_rows_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "posts.csv"
            self.write_rows(path, [self.row("", "pending")])
            before = path.read_bytes()

            dry_result = run_once(path, dry_run=True, today=date(2026, 5, 16))
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(dry_result.content_error_rows, (2,))

            live_result = run_once(path, dry_run=False, poster=MockPoster())
            rows = self.read_rows(path)
            self.assertTrue(live_result.changed_queue)
            self.assertEqual(rows[0]["status"], "content_error")
            self.assertIn("empty", rows[0]["error"])

    @staticmethod
    def row(
        post_text: str,
        status: str,
        scheduled_date: str = "",
    ) -> dict[str, str]:
        return {
            "post_text": post_text,
            "status": status,
            "scheduled_date": scheduled_date,
            "posted_at": "",
            "tweet_id": "",
            "error": "",
        }

    @staticmethod
    def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def read_rows(path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    @staticmethod
    def credentials() -> XApiCredentials:
        return XApiCredentials(
            api_key="api-key",
            api_secret="api-secret",
            access_token="access-token",
            access_token_secret="access-token-secret",
        )

    @staticmethod
    def oauth2_credentials() -> OAuth2UserContextCredentials:
        return OAuth2UserContextCredentials(
            client_id="client-id",
            client_secret="client-secret",
            access_token="oauth2-access-token",
            refresh_token="oauth2-refresh-token",
            scopes=("tweet.read", "tweet.write", "users.read", "offline.access"),
        )

    @classmethod
    def poster_with_error(cls, error: Exception) -> TweepyXPoster:
        return TweepyXPoster(
            cls.credentials(),
            client_factory=lambda credentials: FakeXClient(error),
        )


if __name__ == "__main__":
    unittest.main()
