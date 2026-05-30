"""Mock-only genre buzz collection helpers.

This module intentionally has no X API client, no token loading, and no
environment-variable access. It generates deterministic local mock posts so the
future collection pipeline can be tested without external traffic.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


DEFAULT_CONFIG_PATH = Path("data/x_buzz_genres.json.example")
DEFAULT_OUTPUT_PATH = Path("data/mock_buzz_posts.csv")
DEFAULT_REPORT_PATH = Path("reports/mock_buzz_report.md")

CSV_FIELDS = [
    "genre",
    "post_id",
    "author",
    "text",
    "likes",
    "reposts",
    "replies",
    "quotes",
    "score",
    "created_at",
]

DEFAULT_SCORE_WEIGHTS = {
    "likes": 1,
    "reposts": 3,
    "replies": 2,
    "quotes": 2,
}


@dataclass(frozen=True)
class GenreConfig:
    id: str
    label: str
    keywords: tuple[str, ...]
    min_likes: int
    min_reposts: int
    min_replies: int
    min_quotes: int
    days_back: int
    score_weights: dict[str, int]


@dataclass(frozen=True)
class MockBuzzResult:
    generated_count: int
    filtered_count: int
    output_path: Path
    report_path: Path
    dry_run: bool


def load_genre_config(path: str | Path = DEFAULT_CONFIG_PATH) -> list[GenreConfig]:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    defaults = data.get("defaults") or {}
    default_weights = {
        **DEFAULT_SCORE_WEIGHTS,
        **dict(defaults.get("score_weights") or {}),
    }

    genres: list[GenreConfig] = []
    for row in data.get("genres") or []:
        genre_id = str(row.get("id") or "").strip()
        if not genre_id:
            raise ValueError("genre id is required")
        keywords = tuple(str(item).strip() for item in row.get("keywords") or [] if str(item).strip())
        if not keywords:
            raise ValueError(f"genre {genre_id} must define at least one keyword")
        genres.append(
            GenreConfig(
                id=genre_id,
                label=str(row.get("label") or genre_id).strip(),
                keywords=keywords,
                min_likes=_int(row.get("min_likes", defaults.get("min_likes", 0))),
                min_reposts=_int(row.get("min_reposts", defaults.get("min_reposts", 0))),
                min_replies=_int(row.get("min_replies", defaults.get("min_replies", 0))),
                min_quotes=_int(row.get("min_quotes", defaults.get("min_quotes", 0))),
                days_back=_int(row.get("days_back", defaults.get("days_back", 7))),
                score_weights={
                    **default_weights,
                    **dict(row.get("score_weights") or {}),
                },
            )
        )
    if not genres:
        raise ValueError("at least one genre is required")
    return genres


def calculate_score(post: Mapping[str, Any], weights: Mapping[str, int] | None = None) -> int:
    active_weights = weights or DEFAULT_SCORE_WEIGHTS
    return (
        _int(post.get("likes")) * _int(active_weights.get("likes", 1))
        + _int(post.get("reposts")) * _int(active_weights.get("reposts", 3))
        + _int(post.get("replies")) * _int(active_weights.get("replies", 2))
        + _int(post.get("quotes")) * _int(active_weights.get("quotes", 2))
    )


def generate_mock_posts(genres: Iterable[GenreConfig], now: datetime | None = None) -> list[dict[str, Any]]:
    base_now = now or datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    for genre_index, genre in enumerate(genres):
        keyword = genre.keywords[0]
        samples = [
            {
                "suffix": "top",
                "likes": genre.min_likes + 320,
                "reposts": genre.min_reposts + 45,
                "replies": genre.min_replies + 12,
                "quotes": genre.min_quotes + 9,
                "age_days": min(max(genre.days_back - 1, 0), 2),
            },
            {
                "suffix": "steady",
                "likes": genre.min_likes + 40,
                "reposts": genre.min_reposts + 5,
                "replies": genre.min_replies,
                "quotes": genre.min_quotes,
                "age_days": 1,
            },
            {
                "suffix": "low",
                "likes": max(genre.min_likes - 1, 0),
                "reposts": genre.min_reposts,
                "replies": genre.min_replies,
                "quotes": genre.min_quotes,
                "age_days": 1,
            },
            {
                "suffix": "old",
                "likes": genre.min_likes + 900,
                "reposts": genre.min_reposts + 100,
                "replies": genre.min_replies + 30,
                "quotes": genre.min_quotes + 20,
                "age_days": genre.days_back + 2,
            },
        ]
        for sample_index, sample in enumerate(samples, start=1):
            created_at = base_now - timedelta(days=int(sample["age_days"]), hours=sample_index)
            rows.append(
                {
                    "genre": genre.id,
                    "post_id": f"mock-{genre.id}-{sample['suffix']}",
                    "author": f"mock_author_{genre_index + 1}",
                    "text": f"Mock {genre.label} buzz post about {keyword} ({sample['suffix']}).",
                    "likes": sample["likes"],
                    "reposts": sample["reposts"],
                    "replies": sample["replies"],
                    "quotes": sample["quotes"],
                    "created_at": created_at.isoformat(timespec="seconds"),
                }
            )
    return rows


def filter_posts(
    posts: Iterable[Mapping[str, Any]],
    genres: Iterable[GenreConfig],
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    genre_map = {genre.id: genre for genre in genres}
    base_now = now or datetime.now(timezone.utc)
    filtered: list[dict[str, Any]] = []
    for post in posts:
        genre = genre_map.get(str(post.get("genre") or ""))
        if genre is None:
            continue
        created_at = _parse_datetime(str(post.get("created_at") or ""))
        if created_at is None:
            continue
        age = base_now - created_at
        if age > timedelta(days=genre.days_back):
            continue
        if _int(post.get("likes")) < genre.min_likes:
            continue
        if _int(post.get("reposts")) < genre.min_reposts:
            continue
        if _int(post.get("replies")) < genre.min_replies:
            continue
        if _int(post.get("quotes")) < genre.min_quotes:
            continue
        row = dict(post)
        row["score"] = calculate_score(row, genre.score_weights)
        filtered.append(row)
    filtered.sort(key=lambda row: (str(row["genre"]), -_int(row["score"]), str(row["post_id"])))
    return filtered


def write_posts_csv(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})
    return output


def write_report(path: str | Path, rows: list[Mapping[str, Any]], genres: list[GenreConfig]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Mock Buzz Report",
        "",
        "Mock-only dry-run report. No X API call, token access, `.env` edit, or posting was performed.",
        "",
        "## Genre Summary",
    ]
    for genre in genres:
        genre_rows = [row for row in rows if row.get("genre") == genre.id]
        avg_score = _average([_int(row.get("score")) for row in genre_rows])
        lines.append(f"- {genre.id}: {len(genre_rows)} posts, average score {avg_score:.1f}")

    lines.extend(["", "## Top Posts"])
    top_rows = sorted(rows, key=lambda row: _int(row.get("score")), reverse=True)[:10]
    if not top_rows:
        lines.append("- No posts passed filters.")
    for row in top_rows:
        lines.append(
            f"- {row.get('genre')} / {row.get('post_id')} / score {row.get('score')} / "
            f"{row.get('author')}"
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def collect_mock_buzz_posts(
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    dry_run: bool,
    now: datetime | None = None,
) -> MockBuzzResult:
    if not dry_run:
        raise RuntimeError("mock buzz collector only supports --dry-run")
    genres = load_genre_config(config_path)
    generated = generate_mock_posts(genres, now=now)
    filtered = filter_posts(generated, genres, now=now)
    output = write_posts_csv(output_path, filtered)
    report = write_report(report_path, filtered, genres)
    return MockBuzzResult(
        generated_count=len(generated),
        filtered_count=len(filtered),
        output_path=output,
        report_path=report,
        dry_run=True,
    )


def _int(value: Any) -> int:
    try:
        return int(str(value or "0"))
    except ValueError:
        return 0


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _average(values: list[int]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
