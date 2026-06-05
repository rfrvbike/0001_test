from __future__ import annotations

from .models import ConversationTurn


def estimate_stage(history: list[ConversationTurn], requested_stage: str) -> str:
    if requested_stage and requested_stage != "auto":
        return requested_stage
    partner_turns = [turn for turn in history if turn.speaker == "partner"]
    if not history:
        return "first_message"
    if len(partner_turns) <= 1:
        return "early_chat"
    if len(partner_turns) <= 4:
        return "friendly_chat"
    return "warm_chat"


def estimate_partner_temperature(history: list[ConversationTurn]) -> str:
    if not history:
        return "normal"
    latest_partner = next((turn.text for turn in reversed(history) if turn.speaker == "partner"), "")
    very_good_markers = ["笑", "楽しい", "嬉しい", "また話したい", "行ってみたい", "いいですね！", "ぜひ"]
    good_markers = ["！", "好きです", "よく見ます", "多いです", "いいですね", "ありますか"]
    low_markers = ["はい", "そうです", "うん", "だけ", "特にない"]
    if sum(marker in latest_partner for marker in very_good_markers) >= 2:
        return "very_good"
    if any(marker in latest_partner for marker in good_markers):
        return "good"
    content_markers = ["映画", "カフェ", "ご飯", "旅行", "仕事", "休日", "ミステリー"]
    if any(marker == latest_partner.strip("！？。 ") for marker in low_markers):
        return "low"
    if len(latest_partner.strip()) <= 8 and not any(marker in latest_partner for marker in content_markers):
        return "low"
    if latest_partner:
        return "normal"
    return "low"


def build_strategy(common: list[str], light: list[str], avoid: list[str], stage: str) -> str:
    focus = common[0] if common else (light[0] if light else "相手のプロフィール")
    parts = [f"{focus}に自然に触れ、質問は1つに絞ります。"]
    if stage == "first_message":
        parts.append("初回なので誘いは出さず、距離感を詰めすぎない文面にします。")
    if light:
        parts.append(f"{', '.join(light[:3])}は深掘りせず軽く扱います。")
    if avoid:
        parts.append(f"{', '.join(avoid[:3])}は避けます。")
    return " ".join(parts)
