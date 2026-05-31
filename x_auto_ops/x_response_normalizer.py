"""Normalize X API-shaped JSON into the buzz read-client contract.

This module performs no network access and does not read credentials. It only
accepts already-provided JSON-like dictionaries, which lets tests use fixtures
before any live X API client exists.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from x_auto_ops.buzz_read_client import BuzzFetchResult, BuzzPost


def normalize_recent_search_response(
    response_json: Mapping[str, Any],
    source_query: str,
    source_genre: str,
    *,
    request_window: str = "recent_search",
) -> BuzzFetchResult:
    """Convert an X recent-search-like response into `BuzzFetchResult`.

    Expected X-ish input shape:

    - `data`: list of post objects
    - `includes.users`: optional author objects keyed by `id`
    - `meta.next_token`: optional pagination token

    Missing fields are tolerated and recorded in each post's
    `metrics_missing` field after conversion through `BuzzPost`.
    """

    meta = _dict(response_json.get("meta"))
    users = _users_by_id(response_json)
    fetched_at = _utc_now()

    posts: list[dict[str, Any]] = []
    for item in _list(response_json.get("data")):
        if not isinstance(item, Mapping):
            continue
        metrics = _dict(item.get("public_metrics"))
        author_id = str(item.get("author_id") or "")
        author = users.get(author_id, {})
        missing = _missing_fields(item, metrics, author)
        post = BuzzPost.from_mapping(
            {
                "post_id": item.get("id", ""),
                "author_id": author_id,
                "author_username": author.get("username", ""),
                "text": item.get("text", ""),
                "created_at": item.get("created_at", ""),
                "like_count": metrics.get("like_count", 0),
                "repost_count": metrics.get(
                    "retweet_count",
                    metrics.get("repost_count", 0),
                ),
                "reply_count": metrics.get("reply_count", 0),
                "quote_count": metrics.get("quote_count", 0),
                "impression_count": metrics.get("impression_count"),
                "source_query": source_query,
                "source_genre": source_genre,
                "fetched_at": fetched_at,
                "metrics_missing": missing,
            }
        )
        posts.append(post.as_dict())

    return BuzzFetchResult(
        posts=posts,
        rate_limited=bool(response_json.get("rate_limited", meta.get("rate_limited", False))),
        retry_after_seconds=_nullable_int(
            response_json.get("retry_after_seconds", meta.get("retry_after_seconds"))
        ),
        partial_result=bool(
            response_json.get(
                "partial_result",
                meta.get("partial_result", bool(meta.get("next_token"))),
            )
        ),
        next_token=str(meta.get("next_token") or response_json.get("next_token") or ""),
        request_window=str(response_json.get("request_window") or request_window),
    )


def _missing_fields(
    item: Mapping[str, Any],
    metrics: Mapping[str, Any],
    author: Mapping[str, Any],
) -> list[str]:
    missing: list[str] = []
    if not item.get("author_id"):
        missing.append("missing_author_id")
    if not author.get("username"):
        missing.append("missing_author_username")
    if not item.get("public_metrics"):
        missing.append("missing_public_metrics")
    if "like_count" not in metrics:
        missing.append("missing_like_count")
    if "retweet_count" not in metrics and "repost_count" not in metrics:
        missing.append("missing_repost_count")
    if "reply_count" not in metrics:
        missing.append("missing_reply_count")
    if "quote_count" not in metrics:
        missing.append("missing_quote_count")
    if "impression_count" not in metrics:
        missing.append("missing_impression_count")
    return missing


def _users_by_id(response_json: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    includes = _dict(response_json.get("includes"))
    users: dict[str, Mapping[str, Any]] = {}
    for user in _list(includes.get("users")):
        if isinstance(user, Mapping) and user.get("id"):
            users[str(user["id"])] = user
    return users


def _dict(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _nullable_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value).replace(",", ""))
    except ValueError:
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
