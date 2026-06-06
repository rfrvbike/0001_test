from __future__ import annotations

import argparse
import difflib
import json
import logging
import os
import re
import sys
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.excel_daily_poster.daily_post import DailyPostResult, run_once  # noqa: E402
from tools.excel_daily_poster.excel_queue import (  # noqa: E402
    assert_queue_writable,
    find_next_post,
    normalize_status,
    open_queue,
)
from tools.excel_daily_poster.oauth2_authorize import DEFAULT_SCOPES  # noqa: E402
from tools.excel_daily_poster.oauth2_exchange_code import (  # noqa: E402
    DEFAULT_TOKEN_PATH,
    TokenTransport,
    _post_form_with_urllib,
)
from tools.excel_daily_poster.oauth2_refresh_token import refresh_access_token  # noqa: E402
from tools.excel_daily_poster.x_client import (  # noqa: E402
    OAuth2Transport,
    OAuth2UserContextCredentials,
    OAuth2UserContextXPoster,
    TweepyXPoster,
    XApiCredentials,
    XConfigError,
    XPoster,
)


CONFIRM_MANUAL_LIVE = "I_UNDERSTAND_THIS_POSTS_ONE_REAL_X_TWEET"
SIMILAR_RECENT_POST_REASON = "similar_recent_post_detected"
DEFAULT_SIMILAR_RECENT_POST_DAYS = 30
DEFAULT_SIMILAR_RECENT_POST_THRESHOLD = 0.85


@dataclass(frozen=True)
class SimilarRecentPostCheck:
    blocked: bool
    reason_code: str = ""
    matched_line_number: int | None = None
    similarity: float = 0.0


def credentials_from_env(environ: Mapping[str, str]) -> XApiCredentials:
    """Build credentials from already-provided environment values only."""

    return XApiCredentials(
        api_key=environ.get("X_API_KEY", ""),
        api_secret=environ.get("X_API_SECRET", ""),
        access_token=environ.get("X_ACCESS_TOKEN", ""),
        access_token_secret=environ.get("X_ACCESS_TOKEN_SECRET", ""),
    ).validated()


def build_tweepy_poster_from_env(environ: Mapping[str, str]) -> TweepyXPoster:
    return TweepyXPoster(credentials_from_env(environ))


def oauth2_credentials_from_token_file(
    token_path: str | Path = DEFAULT_TOKEN_PATH,
    *,
    environ: Mapping[str, str] | None = None,
) -> OAuth2UserContextCredentials:
    data = load_oauth2_token_data(token_path)

    access_token = str(data.get("access_token", "")).strip()
    if not access_token:
        raise XConfigError("OAuth2 token file does not contain access_token")

    env = os.environ if environ is None else environ
    scope_value = str(data.get("scope", "")).strip()
    scopes = tuple(scope_value.split()) if scope_value else DEFAULT_SCOPES
    return OAuth2UserContextCredentials(
        client_id=env.get("X_OAUTH2_CLIENT_ID", ""),
        client_secret=env.get("X_OAUTH2_CLIENT_SECRET", ""),
        access_token=access_token,
        refresh_token=str(data.get("refresh_token", "")).strip(),
        scopes=scopes,
    ).validated_for_post()


def load_oauth2_token_data(token_path: str | Path = DEFAULT_TOKEN_PATH) -> dict[str, object]:
    path = Path(token_path)
    if not path.exists():
        raise XConfigError(f"OAuth2 token file was not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise XConfigError(f"OAuth2 token file is not valid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise XConfigError(f"OAuth2 token file must contain a JSON object: {path}")
    return data


def refresh_oauth2_token_file(
    token_path: str | Path = DEFAULT_TOKEN_PATH,
    *,
    environ: Mapping[str, str] | None = None,
    transport: TokenTransport = _post_form_with_urllib,
) -> None:
    data = load_oauth2_token_data(token_path)
    refresh_token = str(data.get("refresh_token", "")).strip()
    if not refresh_token:
        raise XConfigError("OAuth2 token file does not contain refresh_token")

    env = os.environ if environ is None else environ
    tokens = refresh_access_token(
        client_id=env.get("X_OAUTH2_CLIENT_ID", ""),
        client_secret=env.get("X_OAUTH2_CLIENT_SECRET", ""),
        refresh_token=refresh_token,
        transport=transport,
    )
    updated = {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token or refresh_token,
        "token_type": tokens.token_type,
        "expires_in": tokens.expires_in,
        "scope": tokens.scope or str(data.get("scope", "")).strip(),
    }
    path = Path(token_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(updated, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def build_oauth2_poster_from_token_file(
    token_path: str | Path = DEFAULT_TOKEN_PATH,
    *,
    environ: Mapping[str, str] | None = None,
    transport: OAuth2Transport | None = None,
    refresh_before_post: bool = True,
    refresh_transport: TokenTransport = _post_form_with_urllib,
) -> OAuth2UserContextXPoster:
    if refresh_before_post:
        refresh_oauth2_token_file(
            token_path,
            environ=environ,
            transport=refresh_transport,
        )
    return OAuth2UserContextXPoster(
        oauth2_credentials_from_token_file(token_path, environ=environ),
        transport=transport,
    )


def build_manual_poster(
    *,
    auth: str,
    environ: Mapping[str, str] | None = None,
    oauth2_token_path: str | Path = DEFAULT_TOKEN_PATH,
    oauth2_transport: OAuth2Transport | None = None,
    oauth2_refresh_transport: TokenTransport = _post_form_with_urllib,
    skip_oauth2_refresh: bool = False,
) -> XPoster:
    if auth == "oauth1":
        return build_tweepy_poster_from_env(os.environ if environ is None else environ)
    if auth == "oauth2":
        return build_oauth2_poster_from_token_file(
            oauth2_token_path,
            environ=os.environ if environ is None else environ,
            transport=oauth2_transport,
            refresh_before_post=not skip_oauth2_refresh,
            refresh_transport=oauth2_refresh_transport,
        )
    raise XConfigError(f"Unsupported manual live auth mode: {auth}")


def has_posted_today(queue_path: str | Path, *, today: date | None = None) -> bool:
    effective_today = today or date.today()
    today_text = effective_today.isoformat()
    rows, _fieldnames = open_queue(queue_path).read()
    for row in rows:
        if normalize_status(row.get("status", "")) != "posted":
            continue
        posted_at = str(row.get("posted_at", "")).strip()
        if posted_at.startswith(today_text) or today_text in posted_at:
            return True
    return False


def similar_recent_post_settings(
    environ: Mapping[str, str] | None = None,
) -> tuple[bool, int, float]:
    env = os.environ if environ is None else environ
    enabled = env.get("SIMILAR_RECENT_POST_CHECK_ENABLED", "YES").strip().upper()
    days_text = env.get(
        "SIMILAR_RECENT_POST_DAYS",
        str(DEFAULT_SIMILAR_RECENT_POST_DAYS),
    ).strip()
    threshold_text = env.get(
        "SIMILAR_RECENT_POST_THRESHOLD",
        str(DEFAULT_SIMILAR_RECENT_POST_THRESHOLD),
    ).strip()
    return (
        enabled not in {"NO", "FALSE", "0", "OFF"},
        int(days_text or DEFAULT_SIMILAR_RECENT_POST_DAYS),
        float(threshold_text or DEFAULT_SIMILAR_RECENT_POST_THRESHOLD),
    )


def check_similar_recent_post(
    rows: list[dict[str, str]],
    candidate_text: str,
    *,
    today: date | None = None,
    days: int = DEFAULT_SIMILAR_RECENT_POST_DAYS,
    threshold: float = DEFAULT_SIMILAR_RECENT_POST_THRESHOLD,
) -> SimilarRecentPostCheck:
    normalized_candidate = normalize_for_similarity(candidate_text)
    if not normalized_candidate:
        return SimilarRecentPostCheck(False)

    effective_today = today or date.today()
    earliest = effective_today - timedelta(days=days)
    for index, row in enumerate(rows):
        if normalize_status(row.get("status", "")) != "posted":
            continue
        posted_date = recent_posted_date(row)
        if posted_date is None or posted_date < earliest or posted_date > effective_today:
            continue
        posted_text = normalize_for_similarity(str(row.get("post_text", "")))
        if not posted_text:
            continue
        similarity = 1.0 if posted_text == normalized_candidate else difflib.SequenceMatcher(
            None,
            normalized_candidate,
            posted_text,
        ).ratio()
        if similarity >= threshold:
            return SimilarRecentPostCheck(
                True,
                SIMILAR_RECENT_POST_REASON,
                index + 2,
                similarity,
            )
    return SimilarRecentPostCheck(False)


def normalize_for_similarity(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text.strip()).lower()
    normalized = re.sub(r"\s+", " ", normalized)
    chars: list[str] = []
    for char in normalized:
        category = unicodedata.category(char)
        if category.startswith(("L", "N")):
            chars.append(char)
        elif char.isspace():
            chars.append(" ")
    return re.sub(r"\s+", " ", "".join(chars)).strip()


def recent_posted_date(row: Mapping[str, str]) -> date | None:
    for key in ["posted_at", "last_posted_at"]:
        value = str(row.get(key, "")).strip()
        if not value:
            continue
        match = re.search(r"\d{4}-\d{2}-\d{2}", value)
        if not match:
            continue
        try:
            return datetime.strptime(match.group(0), "%Y-%m-%d").date()
        except ValueError:
            continue
    return None


def assert_no_similar_recent_post(
    queue_path: str | Path,
    *,
    today: date | None = None,
    environ: Mapping[str, str] | None = None,
    logger: logging.Logger | None = None,
) -> None:
    enabled, days, threshold = similar_recent_post_settings(environ)
    if not enabled:
        return
    rows, _fieldnames = open_queue(queue_path).read()
    candidate = find_next_post(rows, today=today)
    if candidate is None:
        return
    check = check_similar_recent_post(
        rows,
        candidate.post_text,
        today=today,
        days=days,
        threshold=threshold,
    )
    if not check.blocked:
        return
    detail = (
        f"reason_code={SIMILAR_RECENT_POST_REASON} "
        f"matched_line={check.matched_line_number} "
        f"similarity={check.similarity:.3f}"
    )
    if logger is not None:
        logger.warning("excel_daily_poster_blocked %s", detail)
    raise XConfigError(detail)


def run_manual_live_once(
    queue_path: str | Path,
    *,
    confirm: str,
    auth: str = "oauth1",
    environ: Mapping[str, str] | None = None,
    oauth2_token_path: str | Path = DEFAULT_TOKEN_PATH,
    oauth2_transport: OAuth2Transport | None = None,
    oauth2_refresh_transport: TokenTransport = _post_form_with_urllib,
    skip_oauth2_refresh: bool = False,
    today: date | None = None,
    poster: XPoster | None = None,
    logger: logging.Logger | None = None,
) -> DailyPostResult:
    """Run the one-row live path only after an explicit typed confirmation."""

    if confirm != CONFIRM_MANUAL_LIVE:
        raise XConfigError(
            "Manual live posting requires --confirm "
            f"{CONFIRM_MANUAL_LIVE!r}. No X poster was created."
        )

    if has_posted_today(queue_path, today=today):
        message = "Today already has a posted row. Skip posting."
        if logger is not None:
            logger.info(message)
        print(message)
        return DailyPostResult(None, None, "live", False)

    if poster is None:
        assert_no_similar_recent_post(
            queue_path,
            today=today,
            environ=os.environ if environ is None else environ,
            logger=logger,
        )
        assert_queue_writable(queue_path)

    active_poster = poster or build_manual_poster(
        auth=auth,
        environ=os.environ if environ is None else environ,
        oauth2_token_path=oauth2_token_path,
        oauth2_transport=oauth2_transport,
        oauth2_refresh_transport=oauth2_refresh_transport,
        skip_oauth2_refresh=skip_oauth2_refresh,
    )
    return run_once(
        queue_path,
        dry_run=False,
        poster=active_poster,
        logger=logger,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Manual one-row live poster for the legacy X account. "
            "This is not used by the scheduler."
        )
    )
    parser.add_argument(
        "--queue",
        default="data/manual_account_posts.csv",
        help="Path to the CSV or XLSX post queue.",
    )
    parser.add_argument(
        "--confirm",
        default="",
        help=f"Required exact value: {CONFIRM_MANUAL_LIVE}",
    )
    parser.add_argument(
        "--auth",
        choices=["oauth1", "oauth2"],
        default="oauth1",
        help="Manual live auth mode. Defaults to OAuth 1.0a for compatibility.",
    )
    parser.add_argument(
        "--use-oauth2",
        action="store_true",
        help="Use OAuth 2.0 User Context token file for this manual one-row run.",
    )
    parser.add_argument(
        "--oauth2-token-path",
        default=str(DEFAULT_TOKEN_PATH),
        help="Path to the Git-ignored OAuth2 token JSON file.",
    )
    parser.add_argument(
        "--skip-oauth2-refresh",
        action="store_true",
        help="Debug only: use the saved OAuth2 access token without refreshing first.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = parse_args(argv or sys.argv[1:])

    try:
        result = run_manual_live_once(
            args.queue,
            confirm=args.confirm,
            auth="oauth2" if args.use_oauth2 else args.auth,
            oauth2_token_path=args.oauth2_token_path,
            skip_oauth2_refresh=args.skip_oauth2_refresh,
            logger=logging.getLogger("excel_daily_poster.manual_live"),
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if result.selected_row is None:
        print("No eligible post row found.")
    else:
        print(f"Manual live post completed for row: {result.selected_row}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
