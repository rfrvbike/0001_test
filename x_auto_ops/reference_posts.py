"""Reference-post collection, scoring, analysis, and reporting helpers.

The helpers are local/mock/dry-run first. Live X API or provider-backed LLM
paths are guarded behind explicit opt-in flags and are not used by the normal
tooling flow.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol

from x_auto_ops.provider_routing import (
    ProviderClients,
    generate_post_text,
    resolve_runtime_config,
)


DEFAULT_LIMIT = 200
MAX_LIMIT = 200
RAW_POST_FIELDS = [
    "source_handle",
    "post_id",
    "post_url",
    "text",
    "created_at",
    "like_count",
    "repost_count",
    "reply_count",
    "quote_count",
    "impression_count",
    "category",
    "collected_at",
]
SCORED_POST_FIELDS = RAW_POST_FIELDS + ["score", "engagement_rate"]
ANALYSIS_FIELDS = [
    "source_handle",
    "post_id",
    "score",
    "target",
    "pain",
    "hidden_feeling",
    "theme",
    "structure",
    "opening_pattern",
    "emotional_flow",
    "ending_type",
    "avoid_phrases",
    "yokaze_rewrite_direction",
]


@dataclass(frozen=True)
class SourceAccount:
    handle: str
    category: str
    priority: str
    note: str


@dataclass(frozen=True)
class CollectionResult:
    account_count: int
    requested_limit: int
    estimated_posts: int
    collected_posts: int
    output_path: Path
    dry_run: bool


@dataclass(frozen=True)
class ScoreResult:
    input_count: int
    scored_count: int
    excluded_count: int
    output_path: Path


@dataclass(frozen=True)
class AnalysisResult:
    analyzed_count: int
    output_path: Path
    dry_run: bool
    mock_llm: bool


class XReferenceClient(Protocol):
    def get_user_id(self, handle: str) -> str:
        """Return an X user id for a handle."""

    def get_recent_posts(self, user_id: str, limit: int) -> list[dict[str, Any]]:
        """Return recent posts for an X user id."""


def clamp_limit(limit: int) -> int:
    if limit < 1:
        raise ValueError("--limit must be 1 or greater")
    if limit > MAX_LIMIT:
        raise ValueError(f"--limit must be {MAX_LIMIT} or less")
    return limit


def read_source_accounts(path: str | Path) -> list[SourceAccount]:
    source_path = Path(path)
    with source_path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    accounts: list[SourceAccount] = []
    for row in rows:
        handle = (row.get("handle") or "").strip().lstrip("@")
        if not handle:
            continue
        accounts.append(
            SourceAccount(
                handle=handle,
                category=(row.get("category") or "").strip(),
                priority=(row.get("priority") or "").strip(),
                note=(row.get("note") or "").strip(),
            )
        )
    return accounts


def collect_reference_posts(
    *,
    source_path: str | Path,
    output_path: str | Path,
    limit: int = DEFAULT_LIMIT,
    dry_run: bool,
    client: XReferenceClient | None = None,
    allow_live_collection: bool = False,
    now: datetime | None = None,
) -> CollectionResult:
    limit = clamp_limit(limit)
    output = Path(output_path)
    if not dry_run and not allow_live_collection:
        raise RuntimeError(
            "Live X collection is not implemented for the normal flow. "
            "Run with dry_run=True."
        )
    accounts = _accounts_for_collection(source_path, dry_run=dry_run)
    estimated_posts = len(accounts) * limit

    print(f"Target accounts: {len(accounts)}")
    print(f"Estimated posts to fetch: {estimated_posts}")

    collected_at = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    if dry_run:
        posts = _sample_raw_posts(accounts, limit, collected_at)
    else:
        if client is None:
            raise RuntimeError(
                "Live X collection requires an injected XReferenceClient and "
                "explicit allow_live_collection=True."
            )
        posts = []
        for account in accounts:
            user_id = client.get_user_id(account.handle)
            for post in client.get_recent_posts(user_id, limit):
                posts.append(_normalize_api_post(post, account, collected_at))

    write_csv(output, RAW_POST_FIELDS, posts)
    return CollectionResult(
        account_count=len(accounts),
        requested_limit=limit,
        estimated_posts=estimated_posts,
        collected_posts=len(posts),
        output_path=output,
        dry_run=dry_run,
    )


def score_reference_posts(
    *,
    input_path: str | Path,
    output_path: str | Path,
) -> ScoreResult:
    rows = read_csv(input_path)
    scored_rows: list[dict[str, Any]] = []
    excluded_count = 0
    for row in rows:
        if exclusion_reason(row):
            excluded_count += 1
            continue
        scored = dict(row)
        scored["score"] = str(calculate_score(row))
        scored["engagement_rate"] = engagement_rate(row)
        scored_rows.append(scored)

    scored_rows.sort(key=lambda row: int(row["score"]), reverse=True)
    output = Path(output_path)
    write_csv(output, SCORED_POST_FIELDS, scored_rows)
    return ScoreResult(
        input_count=len(rows),
        scored_count=len(scored_rows),
        excluded_count=excluded_count,
        output_path=output,
    )


def calculate_score(row: Mapping[str, Any]) -> int:
    return (
        _int(row.get("like_count")) +
        _int(row.get("repost_count")) * 3 +
        _int(row.get("reply_count")) * 2 +
        _int(row.get("quote_count")) * 2
    )


def engagement_rate(row: Mapping[str, Any]) -> str:
    impressions = _int(row.get("impression_count"))
    if impressions <= 0:
        return ""
    engagements = (
        _int(row.get("like_count")) +
        _int(row.get("repost_count")) +
        _int(row.get("reply_count")) +
        _int(row.get("quote_count"))
    )
    return f"{engagements / impressions:.6f}"


def exclusion_reason(row: Mapping[str, Any]) -> str | None:
    text = str(row.get("text") or "").strip()
    compact = re.sub(r"\s+", "", text)
    if not text:
        return "empty"
    if text.startswith("RT @") or text.startswith("RP @"):
        return "repost"
    if text.startswith("@"):
        return "reply"
    if re.fullmatch(r"(https?://\S+)+", compact):
        return "link_only"
    if len(compact) < 20:
        return "too_short"
    if _PROMO_RE.search(text):
        return "promotional"
    return None


def analyze_reference_posts(
    *,
    input_path: str | Path,
    output_path: str | Path,
    top_n: int,
    dry_run: bool,
    mock_llm: bool,
    settings: Mapping[str, Any] | None = None,
    clients: ProviderClients | None = None,
    allow_provider_analysis: bool = False,
) -> AnalysisResult:
    if top_n < 1:
        raise ValueError("--top-n must be 1 or greater")
    rows = read_csv(input_path)
    rows.sort(key=lambda row: _int(row.get("score")), reverse=True)
    selected = rows[:top_n]

    analyses: list[dict[str, Any]] = []
    for row in selected:
        if mock_llm or dry_run:
            analysis = mock_analyze_post(row)
        else:
            if not allow_provider_analysis:
                raise RuntimeError(
                    "Provider analysis is disabled for the normal flow. "
                    "Run with mock_llm=True or dry_run=True."
                )
            if settings is None or clients is None:
                raise RuntimeError(
                    "Provider analysis requires settings, injected clients, "
                    "and explicit allow_provider_analysis=True."
                )
            analysis = analyze_post_with_provider(row, settings, clients)
        analyses.append(analysis)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as fh:
        for analysis in analyses:
            fh.write(json.dumps(analysis, ensure_ascii=False, sort_keys=True))
            fh.write("\n")
    return AnalysisResult(len(analyses), output, dry_run=dry_run, mock_llm=mock_llm)


def mock_analyze_post(row: Mapping[str, Any]) -> dict[str, Any]:
    text = str(row.get("text") or "")
    category = str(row.get("category") or "")
    love_theme = category == "恋愛" or any(
        token in text for token in ["返信", "既読", "恋", "会いたい", "大事"]
    )
    if love_theme:
        target = "連絡や扱われ方で、自分ばかり好きだった気がしている女性"
        pain = "待つ時間が長くなるほど、自分の価値まで疑ってしまう傷"
        hidden = "本当は責めたいのではなく、少しだけ大事にされたかった"
        theme = "恋愛"
        opening = "具体的な夜の行動から入る"
    else:
        target = "外では笑って、家に帰ると気力が切れてしまう女性"
        pain = "誰にも気づかれないまま限界まで気を張っていた疲れ"
        hidden = "平気なふりをやめる場所がほしかった"
        theme = "仕事・人間関係・孤独"
        opening = "一日の終わりの身体感覚から入る"
    return {
        "source_handle": row.get("source_handle", ""),
        "post_id": row.get("post_id", ""),
        "score": str(row.get("score", "")),
        "target": target,
        "pain": pain,
        "hidden_feeling": hidden,
        "theme": theme,
        "structure": "具体状況 -> 言えなかった本音 -> 自責をほどく一文",
        "opening_pattern": opening,
        "emotional_flow": "緊張を言い当て、孤独をほどき、最後に小さな安心を置く",
        "ending_type": "断定しすぎない救い",
        "avoid_phrases": [
            "自分を大切にしましょう",
            "無理しないでください",
            "明日はきっと大丈夫",
        ],
        "yokaze_rewrite_direction": (
            "元投稿の語順や比喩は使わず、夜・スマホ・帰宅後など別の具体場面で、"
            "女性の言えなかった本音を先に置く。"
        ),
    }


def analyze_post_with_provider(
    row: Mapping[str, Any],
    settings: Mapping[str, Any],
    clients: ProviderClients,
) -> dict[str, Any]:
    config = resolve_runtime_config(settings, "yokaze_daily")
    prompt = build_analysis_prompt(row)
    raw = generate_post_text(config, prompt, clients)
    parsed = json.loads(raw)
    return {field: parsed.get(field, "") for field in ANALYSIS_FIELDS}


def build_analysis_prompt(row: Mapping[str, Any]) -> str:
    return (
        "Analyze this popular X post for structure only. Do not rewrite, copy, "
        "or preserve distinctive phrasing. Return JSON with these keys: "
        f"{', '.join(ANALYSIS_FIELDS)}.\n\n"
        f"source_handle: {row.get('source_handle', '')}\n"
        f"score: {row.get('score', '')}\n"
        f"text:\n{row.get('text', '')}"
    )


def generate_reference_report(
    *,
    raw_path: str | Path,
    scored_path: str | Path,
    analyzed_path: str | Path,
    output_path: str | Path,
) -> Path:
    raw_rows = read_csv(raw_path) if Path(raw_path).exists() else []
    scored_rows = read_csv(scored_path) if Path(scored_path).exists() else []
    analyses = read_jsonl(analyzed_path) if Path(analyzed_path).exists() else []
    account_count = len({row.get("source_handle", "") for row in raw_rows if row.get("source_handle")})
    excluded_count = max(len(raw_rows) - len(scored_rows), 0)
    love_count = sum(1 for item in analyses if item.get("theme") == "恋愛")
    other_count = max(len(analyses) - love_count, 0)
    themes = sorted({str(item.get("pain") or item.get("theme") or "") for item in analyses})

    lines = [
        "# Reference Posts Report",
        "",
        f"- Collected accounts: {account_count}",
        f"- Collected posts: {len(raw_rows)}",
        f"- Excluded posts: {excluded_count}",
        f"- Scored posts: {len(scored_rows)}",
        f"- Analyzed posts: {len(analyses)}",
        "",
        "## Top Tendencies",
        "- Specific wounds are more useful than broad encouragement.",
        "- The strongest yokaze direction is: concrete scene, hidden feeling, then a small release from self-blame.",
        "- Images should stay atmospheric and optional; text-card images remain out of scope.",
        "",
        "## Yokaze Themes",
    ]
    if themes:
        lines.extend(f"- {theme}" for theme in themes if theme)
    else:
        lines.append("- No analyzed themes yet.")
    lines.extend(
        [
            "",
            "## Mix Check",
            f"- Love analyses: {love_count}",
            f"- Other analyses: {other_count}",
            "- Target mix remains love 70% / other 30%; enforce this at generation time, not by copying source text.",
            "",
            "## Similarity Risk",
            "- Do not reuse source wording, line breaks, metaphors, or sentence order.",
            "- Use analysis as structure only: target, pain, hidden feeling, emotional flow, and ending type.",
        ]
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: str | Path, fieldnames: list[str], rows: Iterable[Mapping[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _accounts_for_collection(
    source_path: str | Path,
    *,
    dry_run: bool,
) -> list[SourceAccount]:
    path = Path(source_path)
    if dry_run and not path.exists():
        return [
            SourceAccount(
                handle="kiwamiamaama",
                category="恋愛",
                priority="high",
                note="女性向けの刺さる言葉",
            )
        ]
    accounts = read_source_accounts(path)
    if not accounts:
        raise ValueError(f"No source accounts found in {path}")
    return accounts


def _sample_raw_posts(
    accounts: list[SourceAccount],
    limit: int,
    collected_at: str,
) -> list[dict[str, str]]:
    samples = [
        (
            "1001",
            "返信が来ない夜、スマホを置いたふりをして何度も画面を見てしまう。平気な顔をしているだけで、本当はずっと待っていた。",
            421,
            71,
            26,
            18,
            18000,
        ),
        (
            "1002",
            "大切にされなかった恋ほど、自分のどこが足りなかったのかを探してしまう。でも足りなかったのは、あなたの我慢じゃなかった。",
            610,
            93,
            34,
            29,
            24000,
        ),
        (
            "1003",
            "ちゃんと笑って帰ってきた夜ほど、玄関で急に動けなくなる。だらしないんじゃなくて、誰にも見えない場所で限界だった。",
            305,
            44,
            19,
            12,
            12000,
        ),
        ("1004", "https://example.com", 50, 10, 0, 0, 3000),
    ]
    rows: list[dict[str, str]] = []
    for account in accounts:
        for index, sample in enumerate(samples[:limit]):
            post_id, text, likes, reposts, replies, quotes, impressions = sample
            rows.append(
                {
                    "source_handle": account.handle,
                    "post_id": f"{account.handle}-{post_id}",
                    "post_url": f"https://x.com/{account.handle}/status/{account.handle}-{post_id}",
                    "text": text,
                    "created_at": f"2026-05-{20 + index:02d}T21:00:00+00:00",
                    "like_count": str(likes),
                    "repost_count": str(reposts),
                    "reply_count": str(replies),
                    "quote_count": str(quotes),
                    "impression_count": str(impressions),
                    "category": account.category,
                    "collected_at": collected_at,
                }
            )
    return rows


def _normalize_api_post(
    post: Mapping[str, Any],
    account: SourceAccount,
    collected_at: str,
) -> dict[str, str]:
    metrics = post.get("public_metrics") or {}
    post_id = str(post.get("id", ""))
    return {
        "source_handle": account.handle,
        "post_id": post_id,
        "post_url": f"https://x.com/{account.handle}/status/{post_id}",
        "text": str(post.get("text", "")),
        "created_at": str(post.get("created_at", "")),
        "like_count": str(metrics.get("like_count", 0)),
        "repost_count": str(metrics.get("retweet_count", metrics.get("repost_count", 0))),
        "reply_count": str(metrics.get("reply_count", 0)),
        "quote_count": str(metrics.get("quote_count", 0)),
        "impression_count": str(metrics.get("impression_count", "")),
        "category": account.category,
        "collected_at": collected_at,
    }


def _int(value: Any) -> int:
    try:
        return int(str(value or "0").replace(",", ""))
    except ValueError:
        return 0


_PROMO_RE = re.compile(
    r"(無料|登録|LINE|セミナー|キャンペーン|購入|限定|クーポン|公式サイト)",
    re.IGNORECASE,
)
