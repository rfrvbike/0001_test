"""Mock-only genre buzz collection helpers.

This module intentionally has no X API client, no token loading, and no
environment-variable access. It generates deterministic local mock posts so the
future collection pipeline can be tested without external traffic.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from x_auto_ops.buzz_read_client import BuzzFetchResult, BuzzReadClient, MockBuzzReadClient


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
    "impression_count",
    "score",
    "score_source",
    "metrics_missing",
    "detected_genre",
    "genre_score",
    "genre_reason",
    "buzz_score",
    "rank_in_genre",
    "created_at",
]

DEFAULT_SCORE_WEIGHTS = {
    "likes": 1,
    "reposts": 3,
    "replies": 2,
    "quotes": 2,
    "impressions": 0.01,
}


@dataclass(frozen=True)
class GenreConfig:
    id: str
    label: str
    keywords: tuple[str, ...]
    detection_keywords: tuple[str, ...]
    min_likes: int
    min_reposts: int
    min_replies: int
    min_quotes: int
    min_buzz_score: int
    days_back: int
    max_results_per_genre: int
    include_impressions_if_available: bool
    search_queries: tuple[str, ...]
    target_accounts: tuple[str, ...]
    exclude_keywords: tuple[str, ...]
    score_weights: dict[str, int]
    min_genre_score: int
    tie_break_priority: tuple[str, ...]


@dataclass(frozen=True)
class BuzzCollectionConfig:
    genres: list[GenreConfig]
    min_genre_score: int
    tie_break_priority: tuple[str, ...]


@dataclass(frozen=True)
class GenreDetection:
    genre: str
    score: int
    reason: str


@dataclass(frozen=True)
class MockBuzzResult:
    generated_count: int
    filtered_count: int
    output_path: Path
    report_path: Path
    dry_run: bool


def load_genre_config(path: str | Path = DEFAULT_CONFIG_PATH) -> list[GenreConfig]:
    return load_buzz_collection_config(path).genres


def load_buzz_collection_config(path: str | Path = DEFAULT_CONFIG_PATH) -> BuzzCollectionConfig:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    defaults = data.get("defaults") or {}
    default_weights = {
        **DEFAULT_SCORE_WEIGHTS,
        **dict(defaults.get("score_weights") or {}),
    }
    min_genre_score = _int(data.get("min_genre_score", 1))
    raw_priority = data.get("tie_break_priority") or []
    tie_break_priority = tuple(str(item).strip() for item in raw_priority if str(item).strip())

    genres: list[GenreConfig] = []
    for row in data.get("genres") or []:
        genre_id = str(row.get("id") or "").strip()
        if not genre_id:
            raise ValueError("genre id is required")
        keywords = tuple(str(item).strip() for item in row.get("keywords") or [] if str(item).strip())
        if not keywords:
            raise ValueError(f"genre {genre_id} must define at least one keyword")
        detection_keywords = tuple(
            str(item).strip()
            for item in row.get("detection_keywords", keywords) or []
            if str(item).strip()
        )
        genres.append(
            GenreConfig(
                id=genre_id,
                label=str(row.get("label") or genre_id).strip(),
                keywords=keywords,
                detection_keywords=detection_keywords,
                min_likes=_int(row.get("min_likes", defaults.get("min_likes", 0))),
                min_reposts=_int(row.get("min_reposts", defaults.get("min_reposts", 0))),
                min_replies=_int(row.get("min_replies", defaults.get("min_replies", 0))),
                min_quotes=_int(row.get("min_quotes", defaults.get("min_quotes", 0))),
                min_buzz_score=_int(row.get("min_buzz_score", defaults.get("min_buzz_score", 0))),
                days_back=_int(row.get("days_back", defaults.get("days_back", 7))),
                max_results_per_genre=_int(
                    row.get("max_results_per_genre", defaults.get("max_results_per_genre", 100))
                ),
                include_impressions_if_available=bool(
                    row.get(
                        "include_impressions_if_available",
                        defaults.get("include_impressions_if_available", True),
                    )
                ),
                search_queries=_tuple(row.get("search_queries", keywords)),
                target_accounts=_tuple(row.get("target_accounts", [])),
                exclude_keywords=_tuple(row.get("exclude_keywords", [])),
                score_weights={
                    **default_weights,
                    **dict(row.get("score_weights") or {}),
                },
                min_genre_score=min_genre_score,
                tie_break_priority=tie_break_priority,
            )
        )
    if not genres:
        raise ValueError("at least one genre is required")
    if not tie_break_priority:
        tie_break_priority = tuple(genre.id for genre in genres)
        genres = [
            GenreConfig(
                id=genre.id,
                label=genre.label,
                keywords=genre.keywords,
                detection_keywords=genre.detection_keywords,
                min_likes=genre.min_likes,
                min_reposts=genre.min_reposts,
                min_replies=genre.min_replies,
                min_quotes=genre.min_quotes,
                min_buzz_score=genre.min_buzz_score,
                days_back=genre.days_back,
                max_results_per_genre=genre.max_results_per_genre,
                include_impressions_if_available=genre.include_impressions_if_available,
                search_queries=genre.search_queries,
                target_accounts=genre.target_accounts,
                exclude_keywords=genre.exclude_keywords,
                score_weights=genre.score_weights,
                min_genre_score=genre.min_genre_score,
                tie_break_priority=tie_break_priority,
            )
            for genre in genres
        ]
    return BuzzCollectionConfig(genres, min_genre_score, tie_break_priority)


def calculate_score(post: Mapping[str, Any], weights: Mapping[str, int] | None = None) -> int:
    return calculate_buzz_score(post, weights)[0]


def calculate_buzz_score(post: Mapping[str, Any], weights: Mapping[str, int] | None = None) -> tuple[int, str]:
    active_weights = weights or DEFAULT_SCORE_WEIGHTS
    base_score = (
        _int(post.get("like_count", post.get("likes"))) * _number(active_weights.get("likes", 1))
        + _int(post.get("repost_count", post.get("reposts"))) * _number(active_weights.get("reposts", 3))
        + _int(post.get("reply_count", post.get("replies"))) * _number(active_weights.get("replies", 2))
        + _int(post.get("quote_count", post.get("quotes"))) * _number(active_weights.get("quotes", 2))
    )
    impression_count = _nullable_int(post.get("impression_count"))
    if impression_count is None:
        return int(round(base_score)), "engagement_fallback"
    score = base_score + impression_count * _number(active_weights.get("impressions", 0))
    return int(round(score)), "impression_adjusted"


def detect_genre(text: str, genres: Iterable[GenreConfig]) -> GenreDetection:
    genre_list = list(genres)
    normalized = text.lower()
    min_genre_score = genre_list[0].min_genre_score if genre_list else 1
    tie_break_priority = genre_list[0].tie_break_priority if genre_list else ()
    genre_order = {genre.id: index for index, genre in enumerate(genre_list)}
    priority_order = {genre_id: index for index, genre_id in enumerate(tie_break_priority)}

    scored: list[tuple[GenreConfig, int, list[str]]] = []
    for genre in genre_list:
        matches = [keyword for keyword in genre.detection_keywords if _keyword_matches(normalized, keyword)]
        scored.append((genre, len(matches), matches))

    best_score = max((score for _, score, _ in scored), default=0)
    if best_score < min_genre_score:
        return GenreDetection(
            "unknown",
            best_score,
            f"genre score {best_score} below min_genre_score {min_genre_score}",
        )

    candidates = [(genre, matches) for genre, score, matches in scored if score == best_score]
    candidates.sort(
        key=lambda item: (
            priority_order.get(item[0].id, len(priority_order) + genre_order.get(item[0].id, 9999)),
            genre_order.get(item[0].id, 9999),
            item[0].id,
        )
    )
    best_genre, best_matches = candidates[0]
    reason = f"matched: {', '.join(best_matches)}"
    if len(candidates) > 1:
        tied = ", ".join(genre.id for genre, _ in candidates)
        reason = f"{reason}; tie among {tied}; selected by tie_break_priority"
    return GenreDetection(best_genre.id, best_score, reason)


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
        text_by_suffix = {
            "top": {
                "yokaze": "A hurt woman spends a lonely night after a relationship, needing quiet support and healing.",
                "ai_side_business": "Non-engineer AI workflow turns a new paper into side business automation and monetization ideas.",
                "daily": "Sunday night coffee in a small room before work, a daily life habit with a small joke.",
            },
            "steady": {
                "yokaze": "Yokaze note for someone feeling lonely at night after trying hard in a relationship.",
                "ai_side_business": "AI productivity automation helps a side business summarize papers before work.",
                "daily": "Daily coffee, room reset, and a light joke before work starts.",
            },
            "low": {
                "yokaze": "Low reach hurt relationship night post.",
                "ai_side_business": "Low reach AI automation side business post.",
                "daily": "Low reach daily coffee room post.",
            },
            "old": {
                "yokaze": "Old yokaze lonely night relationship healing post.",
                "ai_side_business": "Old AI side business automation paper post.",
                "daily": "Old daily Sunday night coffee post.",
            },
        }
        for sample_index, sample in enumerate(samples, start=1):
            created_at = base_now - timedelta(days=int(sample["age_days"]), hours=sample_index)
            rows.append(
                {
                    "genre": genre.id,
                    "post_id": f"mock-{genre.id}-{sample['suffix']}",
                    "author": f"mock_author_{genre_index + 1}",
                    "text": text_by_suffix[str(sample["suffix"])].get(
                        genre.id,
                        f"Mock {genre.label} buzz post about {keyword} ({sample['suffix']}).",
                    ),
                    "likes": sample["likes"],
                    "reposts": sample["reposts"],
                    "replies": sample["replies"],
                    "quotes": sample["quotes"],
                    "impression_count": _mock_impression_count(str(sample["suffix"]), int(sample["likes"])),
                    "author_id": f"mock_author_id_{genre_index + 1}",
                    "author_username": f"mock_author_{genre_index + 1}",
                    "source_query": genre.search_queries[0] if genre.search_queries else keyword,
                    "source_genre": genre.id,
                    "fetched_at": base_now.isoformat(timespec="seconds"),
                    "created_at": created_at.isoformat(timespec="seconds"),
                }
            )
    rows.extend(_mixed_mock_posts(base_now))
    return rows


def filter_posts(
    posts: Iterable[Mapping[str, Any]],
    genres: Iterable[GenreConfig],
    now: datetime | None = None,
    genre_filter: str | None = None,
) -> list[dict[str, Any]]:
    genre_list = list(genres)
    genre_map = {genre.id: genre for genre in genre_list}
    base_now = now or datetime.now(timezone.utc)
    filtered: list[dict[str, Any]] = []
    for post in posts:
        detection = detect_genre(str(post.get("text") or ""), genre_list)
        if genre_filter and detection.genre != genre_filter:
            continue
        genre = genre_map.get(detection.genre)
        created_at = _parse_datetime(str(post.get("created_at") or ""))
        if created_at is None:
            continue
        max_days_back = genre.days_back if genre is not None else _max_days_back(genre_list)
        if base_now - created_at > timedelta(days=max_days_back):
            continue
        if genre is not None:
            if _int(post.get("likes")) < genre.min_likes:
                continue
            if _int(post.get("reposts")) < genre.min_reposts:
                continue
            if _int(post.get("replies")) < genre.min_replies:
                continue
            if _int(post.get("quotes")) < genre.min_quotes:
                continue
        row = dict(post)
        weights = genre.score_weights if genre is not None else DEFAULT_SCORE_WEIGHTS
        buzz_score, score_source = calculate_buzz_score(row, weights)
        if genre is not None and buzz_score < genre.min_buzz_score:
            continue
        row["score"] = buzz_score
        row["score_source"] = score_source
        row["metrics_missing"] = _metrics_missing(row)
        row["detected_genre"] = detection.genre
        row["genre_score"] = detection.score
        row["genre_reason"] = detection.reason
        row["buzz_score"] = buzz_score
        filtered.append(row)
    return rank_posts_by_genre(filtered)


def rank_posts_by_genre(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("detected_genre") or "unknown"), []).append(dict(row))

    ranked: list[dict[str, Any]] = []
    for genre in sorted(grouped):
        genre_rows = sorted(
            grouped[genre],
            key=lambda row: (-_int(row.get("buzz_score")), str(row.get("post_id"))),
        )
        for index, row in enumerate(genre_rows, start=1):
            row["rank_in_genre"] = index
            ranked.append(row)
    return ranked


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
        genre_rows = [row for row in rows if row.get("detected_genre") == genre.id]
        avg_score = _average([_int(row.get("buzz_score")) for row in genre_rows])
        lines.append(f"- {genre.id}: {len(genre_rows)} posts, average score {avg_score:.1f}")
    unknown_rows = [row for row in rows if row.get("detected_genre") == "unknown"]
    lines.append(f"- unknown: {len(unknown_rows)} posts")

    lines.extend(["", "## Genre Rankings"])
    for genre_id in [genre.id for genre in genres] + ["unknown"]:
        genre_rows = [row for row in rows if row.get("detected_genre") == genre_id]
        lines.append(f"",)
        lines.append(f"### {genre_id}")
        if not genre_rows:
            lines.append("- No posts.")
            continue
        for row in sorted(genre_rows, key=lambda item: _int(item.get("rank_in_genre")))[:5]:
            lines.append(
                f"- #{row.get('rank_in_genre')} {row.get('post_id')} / "
                f"buzz_score {row.get('buzz_score')} / {row.get('author')}"
            )

    lines.extend(["", "## Genre Detection Reason Examples"])
    for row in rows[:8]:
        lines.append(
            f"- {row.get('post_id')}: {row.get('detected_genre')} "
            f"({row.get('genre_reason')})"
        )

    lines.extend(["", "## Buzz Score Top Posts"])
    top_rows = sorted(rows, key=lambda row: _int(row.get("buzz_score")), reverse=True)[:10]
    if not top_rows:
        lines.append("- No posts passed filters.")
    for row in top_rows:
        lines.append(
            f"- {row.get('detected_genre')} / {row.get('post_id')} / "
            f"buzz_score {row.get('buzz_score')} / rank {row.get('rank_in_genre')} / {row.get('author')}"
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def collect_mock_buzz_posts(
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    dry_run: bool,
    genre_filter: str | None = None,
    read_client: BuzzReadClient | None = None,
    now: datetime | None = None,
) -> MockBuzzResult:
    if not dry_run:
        raise RuntimeError("mock buzz collector only supports --dry-run")
    config = load_buzz_collection_config(config_path)
    genres = config.genres
    if genre_filter and genre_filter not in {genre.id for genre in genres}:
        raise ValueError(f"unknown genre filter: {genre_filter}")
    client = read_client or MockBuzzReadClient(post_factory=generate_mock_posts, now=now)
    fetch_result = client.fetch_posts(config)
    generated = _fetch_posts(fetch_result)
    filtered = filter_posts(generated, genres, now=now, genre_filter=genre_filter)
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


def _number(value: Any) -> float:
    try:
        return float(str(value or "0"))
    except ValueError:
        return 0.0


def _nullable_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value).replace(",", ""))
    except ValueError:
        return None


def _tuple(values: Any) -> tuple[str, ...]:
    return tuple(str(item).strip() for item in values or [] if str(item).strip())


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


def _keyword_matches(normalized_text: str, keyword: str) -> bool:
    normalized_keyword = keyword.lower()
    if re.fullmatch(r"[a-z0-9]+", normalized_keyword):
        return re.search(rf"\b{re.escape(normalized_keyword)}\b", normalized_text) is not None
    return normalized_keyword in normalized_text


def _max_days_back(genres: Iterable[GenreConfig]) -> int:
    values = [genre.days_back for genre in genres]
    if not values:
        return 7
    return max(values)


def _fetch_posts(fetch_result: BuzzFetchResult | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(fetch_result, BuzzFetchResult):
        return fetch_result.posts
    return fetch_result


def _metrics_missing(row: Mapping[str, Any]) -> str:
    explicit = str(row.get("metrics_missing") or "")
    values = [item.strip() for item in explicit.split("|") if item.strip()]
    if _nullable_int(row.get("impression_count")) is None and "impression_count" not in values:
        values.append("impression_count")
    if "quote_count" in row and row.get("quote_count") in {None, ""} and "quote_count" not in values:
        values.append("quote_count")
    return "|".join(values)


def _mock_impression_count(suffix: str, likes: int) -> int | None:
    if suffix == "steady":
        return None
    return likes * 25


def _mixed_mock_posts(base_now: datetime) -> list[dict[str, Any]]:
    return [
        {
            "genre": "mixed",
            "post_id": "mock-mixed-yokaze-ai",
            "author": "mock_author_mixed",
            "text": (
                "A lonely night after a relationship, but AI automation also helped "
                "summarize one paper for tomorrow."
            ),
            "likes": 680,
            "reposts": 44,
            "replies": 15,
            "quotes": 10,
            "impression_count": 32000,
            "author_id": "mock_author_mixed_id",
            "author_username": "mock_author_mixed",
            "source_query": "night relationship ai automation",
            "source_genre": "mixed",
            "fetched_at": base_now.isoformat(timespec="seconds"),
            "created_at": (base_now - timedelta(days=1, hours=5)).isoformat(timespec="seconds"),
        },
        {
            "genre": "mixed",
            "post_id": "mock-mixed-ai-daily",
            "author": "mock_author_mixed",
            "text": (
                "Coffee before work, then a non-engineer AI workflow for side business "
                "automation and productivity."
            ),
            "likes": 520,
            "reposts": 45,
            "replies": 12,
            "quotes": 8,
            "impression_count": None,
            "metrics_missing": "impression_count",
            "author_id": "mock_author_mixed_id",
            "author_username": "mock_author_mixed",
            "source_query": "coffee ai workflow",
            "source_genre": "mixed",
            "fetched_at": base_now.isoformat(timespec="seconds"),
            "created_at": (base_now - timedelta(days=1, hours=6)).isoformat(timespec="seconds"),
        },
        {
            "genre": "unknown_seed",
            "post_id": "mock-unknown-general",
            "author": "mock_author_unknown",
            "text": "A plain update about a desk and a random number with no useful topic signal.",
            "likes": 500,
            "reposts": 22,
            "replies": 8,
            "quotes": 6,
            "impression_count": None,
            "metrics_missing": "impression_count",
            "author_id": "",
            "author_username": "",
            "source_query": "unknown mock query",
            "source_genre": "unknown_seed",
            "fetched_at": base_now.isoformat(timespec="seconds"),
            "created_at": (base_now - timedelta(days=1, hours=7)).isoformat(timespec="seconds"),
        },
    ]
