"""Read-client boundary for future buzz-post collection.

The real X API client is intentionally not implemented here. The mock client is
safe for dry-run tests because it only calls an injected local post factory.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Iterable, Mapping, Protocol


@dataclass(frozen=True)
class BuzzPost:
    genre: str
    post_id: str
    author: str
    text: str
    likes: int
    reposts: int
    replies: int
    quotes: int
    created_at: str

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> BuzzPost:
        return BuzzPost(
            genre=str(row.get("genre") or ""),
            post_id=str(row.get("post_id") or ""),
            author=str(row.get("author") or ""),
            text=str(row.get("text") or ""),
            likes=_int(row.get("likes")),
            reposts=_int(row.get("reposts")),
            replies=_int(row.get("replies")),
            quotes=_int(row.get("quotes")),
            created_at=str(row.get("created_at") or ""),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "genre": self.genre,
            "post_id": self.post_id,
            "author": self.author,
            "text": self.text,
            "likes": self.likes,
            "reposts": self.reposts,
            "replies": self.replies,
            "quotes": self.quotes,
            "created_at": self.created_at,
        }


class BuzzReadClient(Protocol):
    def fetch_posts(self, config: Any) -> list[dict[str, Any]]:
        """Return normalized buzz-post dictionaries."""


PostFactory = Callable[[Iterable[Any], datetime | None], list[dict[str, Any]]]


class MockBuzzReadClient:
    """Local mock read client that never touches external APIs."""

    def __init__(
        self,
        *,
        post_factory: PostFactory,
        now: datetime | None = None,
    ) -> None:
        self.post_factory = post_factory
        self.now = now

    def fetch_posts(self, config: Any) -> list[dict[str, Any]]:
        genres = getattr(config, "genres", config)
        return [BuzzPost.from_mapping(row).as_dict() for row in self.post_factory(genres, self.now)]


class XApiBuzzReadClient:
    """Placeholder for a future approved X API read client."""

    def fetch_posts(self, config: Any) -> list[dict[str, Any]]:
        raise NotImplementedError(
            "X API buzz collection is not implemented. Use MockBuzzReadClient "
            "and --dry-run until live read access is explicitly approved."
        )


def _int(value: Any) -> int:
    try:
        return int(str(value or "0"))
    except ValueError:
        return 0
