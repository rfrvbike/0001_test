"""Read-client boundary for future buzz-post collection.

The real X API client is intentionally not implemented here. The mock client is
safe for dry-run tests because it only calls an injected local post factory.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, Protocol


@dataclass(frozen=True)
class BuzzPost:
    post_id: str
    author_id: str
    author_username: str
    text: str
    created_at: str
    like_count: int
    repost_count: int
    reply_count: int
    quote_count: int
    impression_count: int | None
    source_query: str
    source_genre: str
    fetched_at: str
    metrics_missing: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> BuzzPost:
        source_genre = str(row.get("source_genre") or row.get("genre") or "")
        author_username = str(row.get("author_username") or row.get("author") or "")
        impression_value = row.get("impression_count")
        missing = list(row.get("metrics_missing") or [])
        if isinstance(row.get("metrics_missing"), str):
            missing = [item.strip() for item in str(row.get("metrics_missing")).split("|") if item.strip()]
        impression_count = _nullable_int(impression_value)
        if impression_count is None and "missing_impression_count" not in missing:
            missing.append("missing_impression_count")
        if not row.get("author_id") and "missing_author_id" not in missing:
            missing.append("missing_author_id")
        if not author_username and "missing_author_username" not in missing:
            missing.append("missing_author_username")
        if row.get("quote_count", row.get("quotes")) in {None, ""} and "missing_quote_count" not in missing:
            missing.append("missing_quote_count")
        return BuzzPost(
            post_id=str(row.get("post_id") or ""),
            author_id=str(row.get("author_id") or ""),
            author_username=author_username,
            text=str(row.get("text") or ""),
            created_at=str(row.get("created_at") or ""),
            like_count=_int(row.get("like_count", row.get("likes"))),
            repost_count=_int(row.get("repost_count", row.get("reposts"))),
            reply_count=_int(row.get("reply_count", row.get("replies"))),
            quote_count=_int(row.get("quote_count", row.get("quotes"))),
            impression_count=impression_count,
            source_query=str(row.get("source_query") or ""),
            source_genre=source_genre,
            fetched_at=str(row.get("fetched_at") or _utc_now()),
            metrics_missing=tuple(missing),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "post_id": self.post_id,
            "author_id": self.author_id,
            "author_username": self.author_username,
            "author": self.author_username,
            "text": self.text,
            "created_at": self.created_at,
            "like_count": self.like_count,
            "repost_count": self.repost_count,
            "reply_count": self.reply_count,
            "quote_count": self.quote_count,
            "impression_count": self.impression_count,
            "source_query": self.source_query,
            "source_genre": self.source_genre,
            "fetched_at": self.fetched_at,
            "metrics_missing": "|".join(self.metrics_missing),
            # Backward-compatible aliases used by the current mock collector UI/CSV.
            "genre": self.source_genre,
            "likes": self.like_count,
            "reposts": self.repost_count,
            "replies": self.reply_count,
            "quotes": self.quote_count,
        }


@dataclass(frozen=True)
class BuzzFetchResult:
    posts: list[dict[str, Any]]
    rate_limited: bool = False
    retry_after_seconds: int | None = None
    partial_result: bool = False
    next_token: str = ""
    request_window: str = "mock"


class BuzzReadClient(Protocol):
    def fetch_posts(self, config: Any) -> BuzzFetchResult:
        """Return normalized buzz posts plus rate-limit and pagination metadata."""


PostFactory = Callable[[Iterable[Any], datetime | None], list[dict[str, Any]]]


class MockBuzzReadClient:
    """Local mock read client that never touches external APIs."""

    def __init__(
        self,
        *,
        post_factory: PostFactory,
        now: datetime | None = None,
        rate_limited: bool = False,
        retry_after_seconds: int | None = None,
        partial_result: bool = False,
        next_token: str = "",
        request_window: str = "mock",
    ) -> None:
        self.post_factory = post_factory
        self.now = now
        self.rate_limited = rate_limited
        self.retry_after_seconds = retry_after_seconds
        self.partial_result = partial_result
        self.next_token = next_token
        self.request_window = request_window

    def fetch_posts(self, config: Any) -> BuzzFetchResult:
        genres = getattr(config, "genres", config)
        posts = [BuzzPost.from_mapping(row).as_dict() for row in self.post_factory(genres, self.now)]
        return BuzzFetchResult(
            posts=posts,
            rate_limited=self.rate_limited,
            retry_after_seconds=self.retry_after_seconds,
            partial_result=self.partial_result,
            next_token=self.next_token,
            request_window=self.request_window,
        )


class XApiBuzzReadClient:
    """Placeholder for a future approved X API read client."""

    def __init__(self, *, transport: Any | None = None, dry_run: bool = True) -> None:
        self.transport = transport
        self.dry_run = dry_run

    def fetch_posts(self, config: Any) -> BuzzFetchResult:
        config_dry_run = getattr(config, "dry_run", None)
        if isinstance(config, Mapping):
            config_dry_run = config.get("dry_run", config_dry_run)
        dry_run = self.dry_run if config_dry_run is None else bool(config_dry_run)
        if not dry_run:
            raise RuntimeError(
                "XApiBuzzReadClient live mode is blocked. Set dry_run=True and "
                "use mock transport until real X API access is explicitly approved."
            )
        if self.transport is not None:
            from x_auto_ops.query_builder import build_recent_search_query
            from x_auto_ops.rate_limit_parser import parse_rate_limit_headers
            from x_auto_ops.x_response_normalizer import normalize_recent_search_response

            query = build_recent_search_query(config)
            response = self.transport.send_recent_search(query.query)
            rate_limit = parse_rate_limit_headers(
                response.headers,
                status_code=response.status_code,
            )
            normalized = normalize_recent_search_response(
                response.json_body,
                source_query=query.query,
                source_genre=query.source_genre,
                request_window="recent_search_dry_run",
            )
            return BuzzFetchResult(
                posts=normalized.posts,
                rate_limited=rate_limit.rate_limited or normalized.rate_limited,
                retry_after_seconds=rate_limit.retry_after_seconds or normalized.retry_after_seconds,
                partial_result=normalized.partial_result,
                next_token=normalized.next_token,
                request_window=normalized.request_window,
            )
        raise NotImplementedError(
            "X API buzz collection is not implemented. Use MockBuzzReadClient "
            "and --dry-run until live read access is explicitly approved."
        )


def _int(value: Any) -> int:
    try:
        return int(str(value or "0"))
    except ValueError:
        return 0


def _nullable_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value).replace(",", ""))
    except ValueError:
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
