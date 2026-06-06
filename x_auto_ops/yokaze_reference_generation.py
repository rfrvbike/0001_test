"""Generate yokaze_daily draft previews from reference-post analyses.

Reference posts are used as structure only. The normal flow is local/mock
generation; provider-backed generation is guarded behind an explicit opt-in
flag and this module does not create provider clients by itself.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from x_auto_ops.provider_routing import (
    ProviderClients,
    generate_post_text,
    resolve_runtime_config,
)
from x_auto_ops.reference_posts import read_jsonl


STYLE_PATTERNS = {
    "daiben",
    "joukei",
    "hitei_kaijo",
    "kioku",
    "short_yoin",
}
STYLE_PATTERN_CHOICES = STYLE_PATTERNS | {"auto"}
GENERATED_FIELDS = [
    "source_analysis_id",
    "theme",
    "target",
    "pain",
    "hidden_feeling",
    "style_pattern",
    "generated_post",
    "image_recommendation",
    "similarity_risk",
    "quality_check",
    "quality_notes",
]
IMAGE_RECOMMENDATIONS = {"none", "ambient_only", "avoid"}
SIMILARITY_RISKS = {"low", "medium", "high"}
QUALITY_LEVELS = {"low", "medium", "high"}
BROAD_OPENINGS = ["疲れている人へ", "頑張っている人へ", "傷ついた人へ"]
SELF_HELP_PHRASES = [
    "自分を大切にしましょう",
    "無理しないでください",
    "頑張りすぎないで",
    "あなたは素晴らしい",
    "明日はきっと大丈夫",
    "心を整えることが大切です",
    "してみてください",
    "することが大切です",
]
SPECIFIC_SCENE_WORDS = [
    "通知",
    "画面",
    "スマホ",
    "帰り道",
    "玄関",
    "布団",
    "部屋",
    "夜",
    "職場",
    "鍵",
    "朝",
    "会議",
    "服",
]
HIDDEN_FEELING_WORDS = [
    "本当は",
    "寂しい",
    "言えなかった",
    "飲み込む",
    "安心",
    "大事にされたい",
    "責め",
    "隠して",
    "心配",
]


@dataclass(frozen=True)
class YokazeGenerationResult:
    input_count: int
    generated_count: int
    output_path: Path
    report_path: Path
    dry_run: bool
    mock_llm: bool


def generate_yokaze_posts_from_reference(
    *,
    input_path: str | Path,
    output_path: str | Path,
    report_path: str | Path,
    top_n: int | None,
    theme: str | None,
    dry_run: bool,
    mock_llm: bool,
    style_pattern: str = "auto",
    target_ratio: Mapping[str, float] | None = None,
    max_same_pattern: int = 2,
    settings: Mapping[str, Any] | None = None,
    clients: ProviderClients | None = None,
    allow_provider_generation: bool = False,
) -> YokazeGenerationResult:
    validate_style_pattern(style_pattern)
    if max_same_pattern < 1:
        raise ValueError("--max-same-pattern must be 1 or greater")

    analyses = _load_analyses(input_path, dry_run=dry_run)
    selected = select_analyses(analyses, top_n=top_n, theme=theme)
    ratios = dict(target_ratio or {"romance": 0.7, "other": 0.3})

    generated: list[dict[str, Any]] = []
    pattern_history: list[str] = []
    for index, analysis in enumerate(selected):
        resolved_theme = normalize_theme(str(analysis.get("theme", "")), index=index)
        pattern = choose_style_pattern(
            requested=style_pattern,
            theme=resolved_theme,
            index=index,
            history=pattern_history,
            max_same_pattern=max_same_pattern,
        )
        if dry_run or mock_llm:
            item = mock_generate_yokaze_post(
                analysis,
                index=index,
                style_pattern=pattern,
            )
        else:
            if not allow_provider_generation:
                raise RuntimeError(
                    "Provider generation is disabled for the normal flow. "
                    "Run with mock_llm=True or dry_run=True."
                )
            if settings is None or clients is None:
                raise RuntimeError(
                    "Provider generation requires settings, injected clients, "
                    "and explicit allow_provider_generation=True."
                )
            item = generate_yokaze_post_with_provider(
                analysis,
                settings,
                clients,
                style_pattern=pattern,
            )
        item = normalize_generated_item(item)
        generated.append(item)
        pattern_history.append(str(item["style_pattern"]))

    generated = apply_style_repetition_quality(generated, max_same_pattern=max_same_pattern)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as fh:
        for item in generated:
            fh.write(json.dumps(item, ensure_ascii=False, sort_keys=True))
            fh.write("\n")

    report = generate_yokaze_generation_report(
        analyses=selected,
        generated=generated,
        output_path=report_path,
        target_ratio=ratios,
        max_same_pattern=max_same_pattern,
    )
    return YokazeGenerationResult(
        input_count=len(selected),
        generated_count=len(generated),
        output_path=output,
        report_path=report,
        dry_run=dry_run,
        mock_llm=mock_llm,
    )


def parse_target_ratio(value: str) -> dict[str, float]:
    ratios: dict[str, float] = {}
    for part in value.split(","):
        if not part.strip():
            continue
        if ":" not in part:
            raise ValueError("--target-ratio must look like romance:0.7,other:0.3")
        key, raw_number = part.split(":", 1)
        key = key.strip()
        if key not in {"romance", "other"}:
            raise ValueError("--target-ratio keys must be romance and other")
        number = float(raw_number.strip())
        if number < 0:
            raise ValueError("--target-ratio values must be non-negative")
        ratios[key] = number
    if not ratios:
        raise ValueError("--target-ratio is empty")
    return ratios


def select_analyses(
    analyses: list[dict[str, Any]],
    *,
    top_n: int | None,
    theme: str | None,
) -> list[dict[str, Any]]:
    rows = list(analyses)
    if theme:
        rows = [row for row in rows if normalize_theme(str(row.get("theme", ""))) == theme]
    rows.sort(key=lambda row: _int(row.get("score")), reverse=True)
    if top_n is not None:
        if top_n < 1:
            raise ValueError("--top-n must be 1 or greater")
        rows = rows[:top_n]
    return rows


def validate_style_pattern(value: str) -> None:
    if value not in STYLE_PATTERN_CHOICES:
        raise ValueError(
            "--style-pattern must be one of: "
            + ", ".join(sorted(STYLE_PATTERN_CHOICES))
        )


def choose_style_pattern(
    *,
    requested: str,
    theme: str,
    index: int,
    history: list[str],
    max_same_pattern: int,
) -> str:
    if requested != "auto":
        return requested
    if theme == "恋愛":
        cycle = ["joukei", "daiben", "kioku", "hitei_kaijo", "short_yoin"]
    else:
        cycle = ["joukei", "daiben", "hitei_kaijo", "short_yoin"]
    pattern = cycle[index % len(cycle)]
    if _would_exceed_same_pattern(history, pattern, max_same_pattern):
        for candidate in cycle:
            if not _would_exceed_same_pattern(history, candidate, max_same_pattern):
                return candidate
    return pattern


def mock_generate_yokaze_post(
    analysis: Mapping[str, Any],
    *,
    index: int = 0,
    style_pattern: str = "auto",
) -> dict[str, Any]:
    theme = normalize_theme(str(analysis.get("theme", "")), index=index)
    pattern = choose_style_pattern(
        requested=style_pattern,
        theme=theme,
        index=index,
        history=[],
        max_same_pattern=2,
    )
    target = _safe_text(analysis.get("target")) or _default_target(theme)
    pain = _safe_text(analysis.get("pain")) or _default_pain(theme)
    hidden = _safe_text(analysis.get("hidden_feeling")) or _default_hidden(theme)
    generated_post = draft_for(theme=theme, style_pattern=pattern, index=index)
    image_recommendation = image_recommendation_for(theme, pattern)
    similarity_risk = assess_similarity_risk(
        generated_post=generated_post,
        analysis=analysis,
    )
    quality_check = evaluate_quality(
        generated_post=generated_post,
        target=target,
        pain=pain,
        hidden_feeling=hidden,
        style_repetition_risk="low",
    )
    return {
        "source_analysis_id": source_analysis_id(analysis),
        "theme": theme,
        "target": target,
        "pain": pain,
        "hidden_feeling": hidden,
        "style_pattern": pattern,
        "generated_post": generated_post,
        "image_recommendation": image_recommendation,
        "similarity_risk": similarity_risk,
        "quality_check": quality_check,
        "quality_notes": build_quality_notes(generated_post, similarity_risk, quality_check),
    }


def generate_yokaze_post_with_provider(
    analysis: Mapping[str, Any],
    settings: Mapping[str, Any],
    clients: ProviderClients,
    *,
    style_pattern: str,
) -> dict[str, Any]:
    config = resolve_runtime_config(settings, "yokaze_daily")
    raw = generate_post_text(
        config,
        build_generation_prompt(analysis, style_pattern=style_pattern),
        clients,
    )
    parsed = json.loads(raw)
    return normalize_generated_item(parsed)


def build_generation_prompt(analysis: Mapping[str, Any], *, style_pattern: str) -> str:
    return (
        "Generate one original yokaze_daily draft from structure only. "
        "Do not copy, rewrite, or preserve source wording, metaphors, line "
        "breaks, or sentence order. Return JSON with keys: "
        f"{', '.join(GENERATED_FIELDS)}.\n\n"
        f"style_pattern: {style_pattern}\n"
        f"theme: {analysis.get('theme', '')}\n"
        f"target: {analysis.get('target', '')}\n"
        f"pain: {analysis.get('pain', '')}\n"
        f"hidden_feeling: {analysis.get('hidden_feeling', '')}\n"
        f"ending_type: {analysis.get('ending_type', '')}\n"
        f"avoid_phrases: {analysis.get('avoid_phrases', '')}\n"
    )


def normalize_generated_item(item: Mapping[str, Any]) -> dict[str, Any]:
    normalized = {field: item.get(field, "") for field in GENERATED_FIELDS}
    if normalized["style_pattern"] not in STYLE_PATTERNS:
        normalized["style_pattern"] = "joukei"
    if normalized["image_recommendation"] not in IMAGE_RECOMMENDATIONS:
        normalized["image_recommendation"] = "none"
    if normalized["similarity_risk"] not in SIMILARITY_RISKS:
        normalized["similarity_risk"] = "medium"
    quality = normalized.get("quality_check")
    if not isinstance(quality, dict):
        quality = evaluate_quality(
            generated_post=str(normalized.get("generated_post", "")),
            target=str(normalized.get("target", "")),
            pain=str(normalized.get("pain", "")),
            hidden_feeling=str(normalized.get("hidden_feeling", "")),
            style_repetition_risk="medium",
        )
    normalized["quality_check"] = normalize_quality_check(quality)
    normalized["quality_notes"] = str(normalized["quality_notes"])
    return normalized


def normalize_quality_check(raw: Mapping[str, Any]) -> dict[str, Any]:
    quality = {
        "target_specificity": _quality_level(raw.get("target_specificity")),
        "emotional_specificity": _quality_level(raw.get("emotional_specificity")),
        "generic_advice_risk": _quality_level(raw.get("generic_advice_risk")),
        "self_help_tone_risk": _quality_level(raw.get("self_help_tone_risk")),
        "style_repetition_risk": _quality_level(raw.get("style_repetition_risk")),
        "final_score": max(0, min(100, _int(raw.get("final_score")))),
    }
    return quality


def evaluate_quality(
    *,
    generated_post: str,
    target: str,
    pain: str,
    hidden_feeling: str,
    style_repetition_risk: str,
) -> dict[str, Any]:
    target_specificity = "high" if _has_specific_context(target + pain + generated_post) else "medium"
    emotional_specificity = (
        "high"
        if any(word in hidden_feeling + generated_post for word in HIDDEN_FEELING_WORDS)
        else "medium"
    )
    generic_advice_risk = "high" if generated_post.startswith(tuple(BROAD_OPENINGS)) else "low"
    self_help_tone_risk = (
        "high"
        if any(phrase in generated_post for phrase in SELF_HELP_PHRASES)
        else "low"
    )
    score = 70
    if target_specificity == "high":
        score += 10
    if emotional_specificity == "high":
        score += 10
    if generic_advice_risk == "high":
        score -= 35
    if self_help_tone_risk == "high":
        score -= 35
    if style_repetition_risk == "medium":
        score -= 10
    if style_repetition_risk == "high":
        score -= 20
    return {
        "target_specificity": target_specificity,
        "emotional_specificity": emotional_specificity,
        "generic_advice_risk": generic_advice_risk,
        "self_help_tone_risk": self_help_tone_risk,
        "style_repetition_risk": style_repetition_risk,
        "final_score": max(0, min(100, score)),
    }


def apply_style_repetition_quality(
    generated: list[dict[str, Any]],
    *,
    max_same_pattern: int,
) -> list[dict[str, Any]]:
    streak_pattern = ""
    streak_count = 0
    updated: list[dict[str, Any]] = []
    for item in generated:
        pattern = str(item.get("style_pattern", ""))
        if pattern == streak_pattern:
            streak_count += 1
        else:
            streak_pattern = pattern
            streak_count = 1
        risk = "low"
        if streak_count > max_same_pattern:
            risk = "high"
        elif streak_count == max_same_pattern and max_same_pattern == 1:
            risk = "medium"
        quality = dict(item["quality_check"])
        if risk != quality["style_repetition_risk"]:
            quality = evaluate_quality(
                generated_post=str(item.get("generated_post", "")),
                target=str(item.get("target", "")),
                pain=str(item.get("pain", "")),
                hidden_feeling=str(item.get("hidden_feeling", "")),
                style_repetition_risk=risk,
            )
            item = dict(item)
            item["quality_check"] = quality
            item["quality_notes"] = build_quality_notes(
                str(item.get("generated_post", "")),
                str(item.get("similarity_risk", "medium")),
                quality,
            )
        updated.append(item)
    return updated


def source_analysis_id(analysis: Mapping[str, Any]) -> str:
    handle = str(analysis.get("source_handle") or "unknown").strip()
    post_id = str(analysis.get("post_id") or "").strip()
    if post_id:
        return f"{handle}:{post_id}"
    return handle


def normalize_theme(raw_theme: str, *, index: int = 0) -> str:
    if raw_theme == "恋愛" or any(token in raw_theme for token in ["恋", "返信", "既読", "会いたい"]):
        return "恋愛"
    if raw_theme in {"仕事", "人間関係", "孤独", "疲れ", "仕事・人間関係・孤独"}:
        return "仕事・人間関係・孤独"
    if any(token in raw_theme for token in ["職場", "空気", "相談", "仕事", "孤独"]):
        return "仕事・人間関係・孤独"
    # Preserve the 70/30 direction when dry-run source text is unreadable.
    return "仕事・人間関係・孤独" if index % 10 in {7, 8, 9} else "恋愛"


def assess_similarity_risk(
    *,
    generated_post: str,
    analysis: Mapping[str, Any],
) -> str:
    source_text = str(analysis.get("source_text") or analysis.get("text") or "")
    fields_to_check = [
        source_text,
        str(analysis.get("opening_pattern", "")),
        str(analysis.get("ending_type", "")),
        str(analysis.get("yokaze_rewrite_direction", "")),
    ]
    generated_tokens = distinctive_tokens(generated_post)
    if not generated_tokens:
        return "medium"

    max_overlap = 0.0
    for text in fields_to_check:
        tokens = distinctive_tokens(text)
        if not tokens:
            continue
        overlap = len(generated_tokens & tokens) / max(len(generated_tokens), 1)
        max_overlap = max(max_overlap, overlap)

    if _same_line_shape(generated_post, source_text):
        return "high"
    if max_overlap >= 0.35:
        return "high"
    if max_overlap >= 0.18:
        return "medium"
    return "low"


def distinctive_tokens(text: str) -> set[str]:
    tokens = set(re.findall(r"[一-龥ぁ-んァ-ヶーA-Za-z0-9]{2,}", text))
    return {
        token
        for token in tokens
        if token not in {"こと", "よう", "だけ", "それ", "これ", "本当", "夜"}
    }


def build_quality_notes(
    generated_post: str,
    similarity_risk: str,
    quality_check: Mapping[str, Any],
) -> str:
    notes = []
    if quality_check["self_help_tone_risk"] == "high":
        notes.append("self-help phrase requires revision")
    else:
        notes.append("avoids broad self-help phrases")
    if quality_check["generic_advice_risk"] == "high":
        notes.append("opening is too broad")
    else:
        notes.append("opens with a specific situation")
    notes.append(f"similarity risk: {similarity_risk}")
    notes.append(f"quality score: {quality_check['final_score']}")
    return "; ".join(notes)


def generate_yokaze_generation_report(
    *,
    analyses: list[Mapping[str, Any]],
    generated: list[Mapping[str, Any]],
    output_path: str | Path,
    target_ratio: Mapping[str, float],
    max_same_pattern: int,
) -> Path:
    theme_counts = Counter(str(item.get("theme", "")) for item in generated)
    style_counts = Counter(str(item.get("style_pattern", "")) for item in generated)
    risk_counts = Counter(str(item.get("similarity_risk", "")) for item in generated)
    image_counts = Counter(str(item.get("image_recommendation", "")) for item in generated)
    love_count = theme_counts.get("恋愛", 0)
    other_count = max(len(generated) - love_count, 0)
    love_ratio = love_count / len(generated) if generated else 0.0
    other_ratio = other_count / len(generated) if generated else 0.0
    average_score = _average_quality_score(generated)
    shortage_warnings = theme_shortage_warnings(
        generated=generated,
        target_ratio=target_ratio,
    )
    repetition_warnings = style_repetition_warnings(
        generated=generated,
        max_same_pattern=max_same_pattern,
    )
    generic_high = _quality_high_items(generated, "generic_advice_risk")
    self_help_high = _quality_high_items(generated, "self_help_tone_risk")
    review_candidates = _human_review_candidates(generated)

    lines = [
        "# Yokaze Reference Generation Report",
        "",
        f"- Input analyses: {len(analyses)}",
        f"- Generated posts: {len(generated)}",
        f"- Romance ratio: {love_count}/{len(generated)} ({love_ratio:.1%})",
        f"- Other ratio: {other_count}/{len(generated)} ({other_ratio:.1%})",
        f"- Average quality score: {average_score:.1f}",
        "",
        "## Theme Counts",
    ]
    lines.extend(_counter_lines(theme_counts))
    lines.extend(["", "## Style Pattern Counts"])
    lines.extend(_counter_lines(style_counts))
    lines.extend(["", "## Similarity Risk Counts"])
    lines.extend(_counter_lines(risk_counts))
    if risk_counts.get("high", 0):
        lines.extend(["", "## High Similarity Warning"])
        lines.append("- High similarity risk exists. Human review is required before use.")
    lines.extend(["", "## Image Recommendation Counts"])
    lines.extend(_counter_lines(image_counts))
    lines.extend(["", "## Theme Ratio Warnings"])
    lines.extend(shortage_warnings or ["- No theme shortage warning."])
    lines.extend(["", "## Quality Risk Lists"])
    lines.append("### generic_advice_risk high")
    lines.extend(_candidate_lines(generic_high))
    lines.append("### self_help_tone_risk high")
    lines.extend(_candidate_lines(self_help_high))
    lines.extend(["", "## Style Repetition Warnings"])
    lines.extend(repetition_warnings or ["- No style repetition warning."])
    lines.extend(["", "## Generated Candidates"])
    for index, item in enumerate(generated, start=1):
        quality = item.get("quality_check", {})
        lines.extend(
            [
                f"### Candidate {index}",
                f"- source_analysis_id: {item.get('source_analysis_id', '')}",
                f"- theme: {item.get('theme', '')}",
                f"- style_pattern: {item.get('style_pattern', '')}",
                f"- image_recommendation: {item.get('image_recommendation', '')}",
                f"- similarity_risk: {item.get('similarity_risk', '')}",
                f"- final_score: {quality.get('final_score', '')}",
                "",
                "```text",
                str(item.get("generated_post", "")),
                "```",
                "",
            ]
        )
    lines.extend(["## Human Review Candidates"])
    lines.extend(_candidate_lines(review_candidates))
    lines.extend(
        [
            "",
            "## Human Review Points",
            "- Confirm the opening is a specific wound, not a broad address.",
            "- Confirm the draft does not copy source wording, line breaks, metaphors, or conclusions.",
            "- Confirm the ending offers only a small quiet release, not self-help advice.",
            "- Confirm image use is optional and atmosphere-only.",
        ]
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def theme_shortage_warnings(
    *,
    generated: list[Mapping[str, Any]],
    target_ratio: Mapping[str, float],
) -> list[str]:
    if not generated:
        return ["- No generated posts; theme ratio cannot be checked."]
    romance_target = float(target_ratio.get("romance", 0.7))
    other_target = float(target_ratio.get("other", 0.3))
    romance_count = sum(1 for item in generated if item.get("theme") == "恋愛")
    other_count = len(generated) - romance_count
    warnings = []
    if other_target > 0 and other_count == 0:
        warnings.append(
            "- Other-theme analyses are missing; do not fabricate other posts."
        )
    elif other_target > 0 and other_count / len(generated) < other_target * 0.5:
        warnings.append("- Other-theme generated posts are below the target ratio.")
    if romance_target > 0 and romance_count == 0:
        warnings.append("- Romance analyses are missing; yokaze's main lane is underrepresented.")
    return warnings


def style_repetition_warnings(
    *,
    generated: list[Mapping[str, Any]],
    max_same_pattern: int,
) -> list[str]:
    warnings = []
    streak_pattern = ""
    streak_count = 0
    for index, item in enumerate(generated, start=1):
        pattern = str(item.get("style_pattern", ""))
        if pattern == streak_pattern:
            streak_count += 1
        else:
            streak_pattern = pattern
            streak_count = 1
        if streak_count > max_same_pattern:
            warnings.append(
                f"- Candidate {index}: style_pattern={pattern} exceeds max_same_pattern={max_same_pattern}."
            )
    return warnings


def draft_for(*, theme: str, style_pattern: str, index: int) -> str:
    drafts = LOVE_DRAFTS if theme == "恋愛" else OTHER_DRAFTS
    pattern_drafts = drafts.get(style_pattern) or drafts["joukei"]
    return pattern_drafts[index % len(pattern_drafts)]


def image_recommendation_for(theme: str, style_pattern: str) -> str:
    if style_pattern == "short_yoin":
        return "avoid"
    if theme != "恋愛" and style_pattern == "joukei":
        return "ambient_only"
    return "none"


LOVE_DRAFTS = {
    "daiben": [
        (
            "寂しいって言えなかったのは\n"
            "強かったからじゃなくて\n"
            "重いと思われるのが怖かったから。\n\n"
            "本当は、返事より先に\n"
            "気にしてくれているって\n"
            "少しだけ感じたかったんだよね。\n\n"
            "責めたかったんじゃない。\n"
            "ひとりで不安を抱える時間が\n"
            "長すぎただけ。"
        )
    ],
    "joukei": [
        (
            "通知が鳴っていないのに\n"
            "画面を伏せたまま気にしてしまう夜がある。\n\n"
            "平気なふりをしていたのは\n"
            "困らせたくなかったからで\n"
            "本当は、少しだけ安心させてほしかったんだよね。\n\n"
            "重かったんじゃないよ。\n"
            "ひとりで待つ時間が\n"
            "長すぎただけだよ。"
        )
    ],
    "hitei_kaijo": [
        (
            "会いたいと言えなかった日の帰り道ほど\n"
            "何でもない顔が上手になる。\n\n"
            "寂しいって言ったら\n"
            "面倒に思われそうで\n"
            "言葉を飲み込むしかなかったんだよね。\n\n"
            "わがままじゃないよ。\n"
            "大事にされたい気持ちを\n"
            "静かに隠していただけ。"
        )
    ],
    "kioku": [
        (
            "雑に扱われたのに\n"
            "優しかった日のことだけ思い出してしまう夜がある。\n\n"
            "嫌いになれない自分を責めても\n"
            "それだけ本気で向き合っていた時間は\n"
            "簡単には消えないよね。\n\n"
            "足りなかったのは\n"
            "あなたの可愛さじゃなくて\n"
            "大事にする覚悟だったのかもしれない。"
        )
    ],
    "short_yoin": [
        (
            "返事がないだけで\n"
            "一日が少し遠くなる。\n\n"
            "気にしてないふりは\n"
            "もう十分したよね。\n\n"
            "大事にされたかった。\n"
            "ただ、それだけだった。"
        )
    ],
}

OTHER_DRAFTS = {
    "daiben": [
        (
            "大丈夫ですって言えたのは\n"
            "本当に大丈夫だったからじゃない。\n\n"
            "これ以上心配をかけたら\n"
            "迷惑になる気がして\n"
            "先に笑ってしまっただけ。\n\n"
            "強い人に見えた日ほど\n"
            "帰ってから崩れる理由が\n"
            "ちゃんとあったんだよ。"
        )
    ],
    "joukei": [
        (
            "玄関の鍵を閉めた瞬間に\n"
            "今日の笑顔がふっとほどける夜がある。\n\n"
            "ちゃんとして見えたのは\n"
            "余裕があったからじゃなくて\n"
            "誰にも心配をかけないようにしていただけ。\n\n"
            "だらしないんじゃないよ。\n"
            "見えないところで\n"
            "ずっと気を張っていたんだよ。"
        )
    ],
    "hitei_kaijo": [
        (
            "空気を読みすぎて疲れるのは\n"
            "気にしすぎだからじゃない。\n\n"
            "誰かの小さな表情まで拾って\n"
            "自分の言葉を後回しにしてきたから\n"
            "心が静かに擦り減っただけ。\n\n"
            "弱いんじゃないよ。\n"
            "ずっと周りを見すぎていたんだよ。"
        )
    ],
    "kioku": [
        (
            "相談しようとして\n"
            "やっぱり送れなかった文章が残っている。\n\n"
            "迷惑かなって消した言葉ほど\n"
            "本当は誰かに見つけてほしかったよね。\n\n"
            "ひとりで抱えられたんじゃない。\n"
            "ひとりで抱えるしかなかった時間が\n"
            "長かっただけ。"
        )
    ],
    "short_yoin": [
        (
            "何もしていない夜に\n"
            "焦ってしまう日がある。\n\n"
            "怠けていたんじゃない。\n\n"
            "ずっと気を張っていた心が\n"
            "やっと止まれただけ。"
        )
    ],
}

SAMPLE_ANALYSES = [
    {
        "source_handle": "mock_reference",
        "post_id": "love-reply",
        "score": "100",
        "theme": "恋愛",
        "target": "返信を待つ時間に、自分ばかり好きなのかもしれないと苦しくなる女性",
        "pain": "大事にされたいだけなのに、重いと思われそうで言えない傷",
        "hidden_feeling": "本当は責めたいのではなく、少しだけ安心させてほしかった",
    },
    {
        "source_handle": "mock_reference",
        "post_id": "work-collapse",
        "score": "90",
        "theme": "仕事・人間関係・孤独",
        "target": "職場では笑って家で崩れる女性",
        "pain": "平気な顔を続けすぎて、限界を誰にも気づかれない疲れ",
        "hidden_feeling": "本当は、ちゃんとしなくていい場所がほしかった",
    },
    {
        "source_handle": "mock_reference",
        "post_id": "read-room",
        "score": "80",
        "theme": "仕事・人間関係・孤独",
        "target": "人間関係で空気を読みすぎて疲れる女性",
        "pain": "相手の表情を拾いすぎて、自分の気持ちが後回しになる疲れ",
        "hidden_feeling": "本当は、気にしすぎだと片づけられたくなかった",
    },
    {
        "source_handle": "mock_reference",
        "post_id": "alone-consult",
        "score": "70",
        "theme": "仕事・人間関係・孤独",
        "target": "相談できず一人で抱える女性",
        "pain": "迷惑になる気がして、助けてほしいと言えない孤独",
        "hidden_feeling": "本当は、言葉にする前に気づいてほしかった",
    },
]


def _load_analyses(path: str | Path, *, dry_run: bool) -> list[dict[str, Any]]:
    input_path = Path(path)
    if input_path.exists():
        rows = read_jsonl(input_path)
        if rows:
            return rows
    if dry_run:
        return list(SAMPLE_ANALYSES)
    return []


def _quality_level(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in QUALITY_LEVELS else "medium"


def _has_specific_context(text: str) -> bool:
    return any(word in text for word in SPECIFIC_SCENE_WORDS)


def _would_exceed_same_pattern(history: list[str], pattern: str, max_same_pattern: int) -> bool:
    count = 0
    for existing in reversed(history):
        if existing != pattern:
            break
        count += 1
    return count >= max_same_pattern


def _average_quality_score(generated: list[Mapping[str, Any]]) -> float:
    if not generated:
        return 0.0
    scores = [_int((item.get("quality_check") or {}).get("final_score")) for item in generated]
    return sum(scores) / len(scores)


def _quality_high_items(
    generated: list[Mapping[str, Any]],
    key: str,
) -> list[Mapping[str, Any]]:
    return [
        item
        for item in generated
        if (item.get("quality_check") or {}).get(key) == "high"
    ]


def _human_review_candidates(generated: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [
        item
        for item in generated
        if item.get("similarity_risk") != "low"
        or _int((item.get("quality_check") or {}).get("final_score")) < 80
        or (item.get("quality_check") or {}).get("generic_advice_risk") == "high"
        or (item.get("quality_check") or {}).get("self_help_tone_risk") == "high"
        or (item.get("quality_check") or {}).get("style_repetition_risk") == "high"
    ]


def _candidate_lines(items: list[Mapping[str, Any]]) -> list[str]:
    if not items:
        return ["- none"]
    return [
        "- "
        + str(item.get("source_analysis_id", "unknown"))
        + f" / style={item.get('style_pattern', '')}"
        + f" / score={(item.get('quality_check') or {}).get('final_score', '')}"
        for item in items
    ]


def _counter_lines(counter: Counter[str]) -> list[str]:
    if not counter:
        return ["- none: 0"]
    return [f"- {key}: {value}" for key, value in sorted(counter.items())]


def _safe_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text or any(marker in text for marker in ["縺", "繧", "譛", "諱"]):
        return ""
    return text


def _default_target(theme: str) -> str:
    if theme == "恋愛":
        return "連絡を待つ時間に、自分ばかり好きなのかもしれないと苦しくなる女性"
    return "外では笑えているのに、家に帰ると急に動けなくなる女性"


def _default_pain(theme: str) -> str:
    if theme == "恋愛":
        return "大事にされたいだけなのに、重いと思われそうで言えない傷"
    return "平気な顔を続けすぎて、限界を誰にも気づかれない疲れ"


def _default_hidden(theme: str) -> str:
    if theme == "恋愛":
        return "本当は責めたいのではなく、少しだけ安心させてほしかった"
    return "本当は、ちゃんとしなくていい場所がほしかった"


def _same_line_shape(generated_post: str, source_text: str) -> bool:
    if not source_text or "\n" not in source_text:
        return False
    generated_lengths = [len(line.strip()) for line in generated_post.splitlines() if line.strip()]
    source_lengths = [len(line.strip()) for line in source_text.splitlines() if line.strip()]
    if len(generated_lengths) != len(source_lengths) or not generated_lengths:
        return False
    close = sum(
        1
        for generated, source in zip(generated_lengths, source_lengths)
        if abs(generated - source) <= 2
    )
    return close / len(generated_lengths) >= 0.7


def _int(value: Any) -> int:
    try:
        return int(str(value or "0").replace(",", ""))
    except ValueError:
        return 0
