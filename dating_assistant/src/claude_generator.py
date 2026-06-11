from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from .models import PartnerRecord
from .partner_manager import save_updated_partner
from .partner_store import load_partner
from .suggestion_manager import add_suggestion

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def _get_api_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip()
    return None


def is_api_key_configured() -> bool:
    return bool(_get_api_key())


def _build_system_prompt(partner: PartnerRecord, tone: str, objectives: list[str]) -> str:
    profile_text = partner.profile.profile_text or "プロフィール情報なし"

    conversation_lines = []
    for turn in partner.conversation[-10:]:
        label = "自分" if turn.speaker == "user" else "相手"
        conversation_lines.append(f"{label}: {turn.text}")
    conversation_history = "\n".join(conversation_lines) if conversation_lines else "会話履歴なし"

    style_parts = []
    if tone:
        style_parts.append(f"雰囲気: {tone}")
    if objectives:
        style_parts.append("目的: " + "、".join(objectives))
    reply_style = "、".join(style_parts) if style_parts else "自然な返信"

    return (
        "あなたはマッチングアプリの返信を考えるアシスタントです。\n"
        "以下の情報をもとに、自然で魅力的な返信候補を3件考えてください。\n\n"
        f"【相手のプロフィール】\n{profile_text}\n\n"
        f"【会話履歴】\n{conversation_history}\n\n"
        f"【返信スタイル】\n{reply_style}\n\n"
        "【ルール】\n"
        "- 返信は1〜3文程度の自然な長さにする\n"
        "- 相手の最後のメッセージに対して適切に返す\n"
        "- 質問には答え、自然に会話を広げる\n"
        "- テンプレート感が出ないようにする\n"
        "- 絵文字は控えめに使う\n"
        "- 自動送信ではないため、送信前にユーザーが確認する\n\n"
        "候補1・候補2・候補3の形式で返してください。"
    )


def _parse_candidates(response_text: str) -> list[str]:
    parts = re.split(r"候補[１-３1-3][\s:：]", response_text)
    candidates = [p.strip() for p in parts[1:] if p.strip()]
    return candidates[:3] if candidates else [response_text.strip()]


def generate_reply_candidates_for_gui(
    partner_id: str,
    objectives: list[str] | None = None,
    tone: str = "自然",
    place_hint: str = "",
) -> dict[str, Any]:
    api_key = _get_api_key()
    if not api_key:
        raise ValueError(
            "APIキーが設定されていません。"
            ".envファイルにANTHROPIC_API_KEYを設定してください。"
        )

    try:
        import anthropic
    except ImportError:
        raise ValueError(
            "anthropicライブラリがインストールされていません。"
            "pip install anthropic を実行してください。"
        )

    partner = load_partner(partner_id)
    selected_objectives = [o for o in (objectives or []) if o]
    all_objectives = selected_objectives[:]
    if place_hint:
        all_objectives.append(f"場所: {place_hint}")

    system_prompt = _build_system_prompt(partner, tone, all_objectives)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": "返信候補を3件生成してください。"}],
            system=system_prompt,
        )
        response_text = message.content[0].text
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
            raise ValueError(
                "APIキーが正しくありません。.envファイルのANTHROPIC_API_KEYを確認してください。"
            )
        if "rate_limit" in error_msg.lower():
            raise ValueError(
                "APIのレート制限に達しました。しばらく待ってから再試行してください。"
            )
        if "overload" in error_msg.lower():
            raise ValueError(
                "APIサーバーが一時的に混雑しています。しばらく待ってから再試行してください。"
            )
        raise ValueError(f"API呼び出しに失敗しました: {error_msg}")

    raw_candidates = _parse_candidates(response_text)

    mode = "first" if not partner.conversation else "reply"
    purpose = "first" if mode == "first" else "reply"
    title_labels = ["候補A", "候補B", "候補C"]
    use_cases = ["自然な返信", "会話を広げる", "距離を縮める"]

    variants = []
    for index, text in enumerate(raw_candidates):
        suggestion = add_suggestion(partner, purpose=purpose, text=text, source="claude-api")
        variants.append({
            "suggestion_id": suggestion.suggestion_id,
            "text": suggestion.text,
            "purpose": suggestion.purpose,
            "objective": selected_objectives[index % len(selected_objectives)] if selected_objectives else "自然な返信",
            "tone": tone or "自然",
            "title": title_labels[index],
            "use_case": use_cases[index],
            "aim": "相手との会話を続ける",
            "conversation_stage": "-",
            "temperature": "-",
            "compatibility": "-",
            "next_recommendation": "-",
            "partner_notes": "-",
            "recent_sent_outcomes": [],
            "safety_notes": [],
            "quality_check": [],
        })

    if mode == "first":
        partner.status = "first_message_suggested"
    elif partner.status in {"new_profile", "first_message_sent", "first_message_suggested"}:
        partner.status = "chatting"
    save_updated_partner(partner)

    return {"mode": mode, "variants": variants}
