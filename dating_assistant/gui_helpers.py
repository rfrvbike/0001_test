from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import re
from pathlib import Path
from typing import Any

from src.activity_log import add_activity_event
from src.app_core import generate
from src.conversation_planner import estimate_partner_temperature
from src.loaders import load_user_profile
from src.models import ConversationTurn, GenerationRequest, PartnerNote, PartnerRecord, TargetProfile
from src.partner_store import list_partners, load_partner
from src.partner_manager import add_partner_note, create_partner_from_target_profile, save_updated_partner
from src.real_profile_manager import (
    create_real_profile,
    detect_privacy_warnings,
    get_real_profile_dir,
    list_real_profiles,
    load_real_profile,
    validate_real_profile_label,
)
from src.suggestion_manager import add_suggestion, discard_suggestion, get_pending_suggestions, mark_suggestion_sent, mark_text_sent
from src.timeline_builder import build_timeline_events

PROFILE_PASTE_FIELD_ALIASES = {
    "display_name": "display_name",
    "name": "display_name",
    "表示名": "display_name",
    "名前": "display_name",
    "相手の表示名": "display_name",
    "app": "app_name",
    "app_name": "app_name",
    "アプリ": "app_name",
    "アプリ名": "app_name",
    "age": "age",
    "年齢": "age",
    "area": "area",
    "エリア": "area",
    "居住地": "area",
    "地域": "area",
    "profile": "profile_text",
    "profile_text": "profile_text",
    "プロフィール": "profile_text",
    "プロフィール文": "profile_text",
    "自己紹介": "profile_text",
    "interests": "interests",
    "hobbies": "interests",
    "趣味": "interests",
    "好きなこと": "interests",
    "photo": "photo_memo",
    "photo_memo": "photo_memo",
    "写真": "photo_memo",
    "写真メモ": "photo_memo",
    "印象": "photo_memo",
    "avoid_topics": "avoid_topics",
    "避けたい話題": "avoid_topics",
    "ng": "avoid_topics",
    "notes": "notes",
    "メモ": "notes",
    "その他": "notes",
    "conversation_hooks": "conversation_hooks",
    "会話に使えそうな情報": "conversation_hooks",
    "first_message_hints": "first_message_hints",
    "初回候補ヒント": "first_message_hints",
    "safety_notes": "safety_notes",
    "安全メモ": "safety_notes",
}

PROFILE_PASTE_FIELDS = [
    "display_name",
    "app_name",
    "age",
    "area",
    "profile_text",
    "interests",
    "photo_memo",
    "avoid_topics",
    "conversation_hooks",
    "first_message_hints",
    "safety_notes",
    "notes",
]

GENERATION_OBJECTIVE_OPTIONS = [
    "相手のプロフィールに触れる",
    "質問を1つ入れる",
    "共感のリアクション重視",
    "相手の趣味を広げる",
    "自分の紹介をする",
    "軽くユーモアを入れる",
    "恋愛観に軽く触れる",
    "少し大人っぽい雰囲気にする",
    "電話に誘う",
    "会う提案をする",
    "場所を指定して会う提案をする",
    "LINE交換を提案する",
]

GENERATION_TONE_OPTIONS = [
    "自然",
    "丁寧",
    "少し親しみやすい",
    "軽くユーモア",
    "落ち着いた感じ",
    "短め",
    "かなり無難",
    "少し大人っぽいが控えめ",
]

SENT_OUTCOME_STATUS_OPTIONS = [
    "未確認",
    "返信あり",
    "返信なし",
    "反応よかった",
    "話題が広がった",
    "微妙だった",
    "その他",
]

PROFILE_SAFETY_PATTERNS = {
    "メールアドレス": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "電話番号": re.compile(r"(?:\+?\d[\d -]{8,}\d)"),
}
PROFILE_SAFETY_WORDS = [
    "LINE",
    "ライン",
    "Instagram",
    "インスタ",
    "X ID",
    "Twitter",
    "住所",
    "勤務先",
    "会社名",
    "学校名",
    "大学名",
    "高校",
    "本名",
]
SPEAKER_ALIASES = {
    "自分": "user",
    "user": "user",
    "me": "user",
    "相手": "partner",
    "partner": "partner",
    "you": "partner",
}
SPEAKER_LINE_RE = re.compile(r"^\s*([^:：]+)\s*[:：]\s*(.*)$")


def load_partner_choices(include_archived: bool = False) -> list[PartnerRecord]:
    partners = list_partners()
    if not include_archived:
        partners = [partner for partner in partners if partner.status != "archived"]
    return sorted(partners, key=lambda partner: partner.partner_id)


def load_partner_for_view(partner_id: str) -> PartnerRecord:
    return load_partner(partner_id)


def build_partner_label(partner: PartnerRecord) -> str:
    name = partner.display_name or "(no display name)"
    return f"{partner.partner_id} / {name} / {partner.status}"


def build_partner_summary(partner: PartnerRecord) -> dict[str, Any]:
    pending = get_pending_suggestions(partner)
    return {
        "partner_id": partner.partner_id,
        "display_name": partner.display_name or "-",
        "status": partner.status,
        "next_action": partner.message_state.next_action or "-",
        "partner_temperature": partner.analysis.partner_temperature,
        "pending_suggestions_count": len(pending),
        "message_state": asdict(partner.message_state),
    }


def format_conversation_history(partner: PartnerRecord) -> list[dict[str, Any]]:
    rows = []
    for index, turn in enumerate(partner.conversation, start=1):
        rows.append(
            {
                "index": index,
                "speaker": turn.speaker,
                "speaker_label": "自分" if turn.speaker == "user" else "相手",
                "timestamp": turn.timestamp or "",
                "text": turn.text,
            }
        )
    return rows


def format_pending_suggestions(partner: PartnerRecord) -> list[dict[str, Any]]:
    return [
        {
            "suggestion_id": suggestion.suggestion_id,
            "purpose": suggestion.purpose,
            "created_at": suggestion.created_at,
            "status": suggestion.status,
            "text": suggestion.text,
        }
        for suggestion in get_pending_suggestions(partner)
    ]


def format_partner_notes(partner: PartnerRecord) -> list[dict[str, str]]:
    return [
        {
            "index": str(index),
            "created_at": note.created_at or "",
            "text": note.text,
        }
        for index, note in enumerate(partner.notes, start=1)
        if note.text.strip()
    ]


def build_partner_note_preview(text: str) -> dict[str, Any]:
    text = text.strip()
    warnings = detect_privacy_warnings([text]) if text else []
    return {
        "保存先": "partner.notes",
        "メモ": text or "-",
        "warnings": warnings,
        "local_save_only": True,
        "auto_send": False,
    }


def add_partner_note_from_gui(partner_id: str, text: str, confirmed: bool) -> dict[str, Any]:
    text = text.strip()
    if not confirmed:
        raise ValueError("確認チェックを入れてください。")
    if not text:
        raise ValueError("相手別メモを入力してください。")
    partner = load_partner(partner_id)
    if partner.status == "archived":
        raise ValueError("archivedのpartnerにはメモを追加できません。")
    warnings = detect_privacy_warnings([text])
    add_partner_note(partner, text)
    updated = load_partner(partner_id)
    return {
        "partner_id": partner_id,
        "notes_count": len(updated.notes),
        "warnings": warnings,
    }


def format_sent_suggestions_for_outcomes(partner: PartnerRecord) -> list[dict[str, Any]]:
    sent = [suggestion for suggestion in partner.pending_suggestions if suggestion.status == "sent"]
    return [
        {
            "suggestion_id": suggestion.suggestion_id,
            "purpose": suggestion.purpose,
            "sent_at": suggestion.sent_at or "",
            "text": suggestion.text,
            "outcome_status": suggestion.outcome_status or "未確認",
            "outcome_memo": suggestion.outcome_memo or "",
            "outcome_updated_at": suggestion.outcome_updated_at or "",
        }
        for suggestion in sent
    ]


def build_sent_outcome_preview(partner: PartnerRecord, suggestion_id: str, outcome_status: str, outcome_memo: str = "") -> dict[str, Any]:
    suggestion = _find_sent_suggestion(partner, suggestion_id)
    outcome_status = outcome_status if outcome_status in SENT_OUTCOME_STATUS_OPTIONS else "未確認"
    outcome_memo = outcome_memo.strip()
    warnings = detect_privacy_warnings([outcome_memo])
    return {
        "partner_id": partner.partner_id,
        "suggestion_id": suggestion.suggestion_id,
        "送信文": suggestion.text,
        "結果ステータス": outcome_status,
        "結果メモ": outcome_memo or "-",
        "warnings": warnings,
        "local_save_only": True,
        "auto_send": False,
    }


def update_sent_outcome_from_gui(
    partner_id: str,
    suggestion_id: str,
    outcome_status: str,
    outcome_memo: str = "",
    confirmed: bool = False,
) -> dict[str, Any]:
    if not confirmed:
        raise ValueError("確認チェックを入れてください。")
    if outcome_status not in SENT_OUTCOME_STATUS_OPTIONS:
        raise ValueError(f"Invalid outcome status: {outcome_status}")
    partner = load_partner(partner_id)
    if partner.status == "archived":
        raise ValueError("archivedのpartnerには送信結果メモを追加できません。")
    suggestion = _find_sent_suggestion(partner, suggestion_id)
    outcome_memo = outcome_memo.strip()
    warnings = detect_privacy_warnings([outcome_memo])
    suggestion.outcome_status = outcome_status
    suggestion.outcome_memo = outcome_memo
    suggestion.outcome_updated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    add_activity_event(partner, "sent_outcome_updated", f"{suggestion_id} 結果: {outcome_status}", suggestion_id, suggestion.outcome_updated_at)
    save_updated_partner(partner)
    return {
        "partner_id": partner_id,
        "suggestion_id": suggestion_id,
        "outcome_status": outcome_status,
        "outcome_memo": outcome_memo,
        "warnings": warnings,
    }


def format_timeline_items(partner: PartnerRecord, limit: int = 50) -> list[dict[str, Any]]:
    events = build_timeline_events(partner)
    if limit > 0:
        events = events[-limit:]
    return [
        {
            "created_at": event.created_at or "",
            "actor": event.actor,
            "event_type": event.event_type,
            "summary": event.summary,
            "text": event.text or "",
            "related_id": event.related_id or "",
        }
        for event in events
    ]


def get_generation_mode_for_partner(partner: PartnerRecord) -> str:
    if partner.status == "archived":
        return "blocked"
    if get_pending_suggestions(partner):
        return "blocked"
    if partner.message_state.awaiting_partner_reply:
        return "blocked"
    if not partner.conversation:
        if partner.profile.profile_text.strip() or partner.profile.hobbies or partner.profile.photos_memo:
            return "first"
        return "blocked"
    latest_partner = next((turn for turn in reversed(partner.conversation) if turn.speaker == "partner"), None)
    if latest_partner and partner.message_state.awaiting_user_action:
        return "reply"
    return "blocked"


def build_generation_status_message(partner: PartnerRecord) -> str:
    pending_count = len(get_pending_suggestions(partner))
    if partner.status == "archived":
        return "archivedのため候補生成できません。"
    if pending_count:
        return "既存のpending_suggestionsがあります。確認または破棄してから生成してください。"
    if partner.message_state.awaiting_partner_reply:
        return "現在は相手の返信待ちです。新しい候補は生成しません。"
    mode = get_generation_mode_for_partner(partner)
    if mode == "first":
        return "初回メッセージ候補を生成できます。自動送信ではありません。"
    if mode == "reply":
        return "返信候補を生成できます。自動送信ではありません。"
    return "候補生成に必要なプロフィール情報または相手発話が不足しています。"


def can_generate_suggestion(partner: PartnerRecord) -> bool:
    return get_generation_mode_for_partner(partner) in {"first", "reply"}


def generate_suggestion_for_gui(partner_id: str) -> dict[str, Any]:
    partner = load_partner(partner_id)
    mode = get_generation_mode_for_partner(partner)
    if mode not in {"first", "reply"}:
        raise ValueError(build_generation_status_message(partner))
    purpose = "first_message" if mode == "first" else "reply"
    request = GenerationRequest(
        target_profile=_target_from_partner(partner),
        user_profile=load_user_profile(),
        conversation_history=list(partner.conversation),
        purpose=purpose,
        current_stage="first_message" if mode == "first" else "auto",
    )
    result = generate(request)
    text = result.best_message
    partner.analysis.partner_temperature = result.partner_temperature
    partner.analysis.safe_topics = list(result.safe_topics)
    partner.analysis.light_only_topics = list(result.light_only_topics)
    partner.analysis.avoid_topics = list(result.avoid_topics)
    partner.analysis.next_strategy = result.recommended_strategy
    partner.analysis.last_suggested_message = text
    suggestion = add_suggestion(
        partner,
        purpose="first" if mode == "first" else "reply",
        text=text,
        source="gui-generate-first" if mode == "first" else "gui-generate-reply",
        safety_result="OK",
    )
    if mode == "first":
        partner.status = "first_message_suggested"
        save_updated_partner(partner)
    elif partner.status in {"new_profile", "first_message_sent", "first_message_suggested"}:
        partner.status = "chatting"
        save_updated_partner(partner)
    return {
        "mode": mode,
        "suggestion_id": suggestion.suggestion_id,
        "text": suggestion.text,
        "status": suggestion.status,
    }


def build_conversation_stage_summary(partner: PartnerRecord) -> dict[str, Any]:
    partner_turns = [turn for turn in partner.conversation if turn.speaker == "partner"]
    user_turns = [turn for turn in partner.conversation if turn.speaker == "user"]
    round_count = min(len(partner_turns), len(user_turns))
    latest_partner = partner_turns[-1].text if partner_turns else ""
    temperature = estimate_partner_temperature(partner.conversation) if partner.conversation else "unknown"
    if not partner.conversation:
        stage = "初回前"
        next_step = "プロフィールに触れた初回候補を作る"
    elif partner.message_state.awaiting_partner_reply:
        stage = "返信待ち"
        next_step = "相手の返信を待つ"
    elif round_count <= 1:
        stage = "1往復目"
        next_step = "共感と軽い質問で会話を続ける"
    elif round_count == 2:
        stage = "2往復目"
        next_step = "温度感を見ながら話題を少し広げる"
    elif temperature in {"good", "very_good"}:
        stage = "3往復目以降"
        next_step = "電話や軽い会う提案を検討してもよい"
    else:
        stage = "まだ雑談継続"
        next_step = "急いで誘わず、もう少し会話を続ける"
    return {
        "stage": stage,
        "round_count": round_count,
        "partner_temperature": temperature,
        "latest_partner_message": latest_partner or "-",
        "next_recommendation": next_step,
        "phone_suggestion": "2から3往復後で反応が良い場合のみ検討",
        "meet_suggestion": "電話後または十分に自然な会話後に軽く検討",
    }


def build_generation_preflight(partner: PartnerRecord, objectives: list[str] | None = None, tone: str = "", place_hint: str = "") -> dict[str, Any]:
    stage = build_conversation_stage_summary(partner)
    objectives = [item for item in (objectives or []) if item]
    warnings = []
    partner_notes = _partner_notes_text(partner)
    recent_outcomes = _recent_outcome_summaries(partner)
    if any("電話" in item for item in objectives) and stage["round_count"] < 2:
        warnings.append("電話提案はまだ早い可能性があります。2から3往復後で、相手の反応が良い場合だけ検討してください。")
    if any("会う" in item for item in objectives) and stage["round_count"] < 3:
        warnings.append("会う提案はまだ早い可能性があります。電話後、または十分に自然な会話が続いた後まで待つ方が安全です。")
    if any("LINE" in item for item in objectives) and stage["round_count"] < 2:
        warnings.append("LINE交換提案は唐突になりやすいため注意してください。LINE IDそのものは保存しないでください。")
    if (any("大人っぽい" in item for item in objectives) or "大人っぽい" in tone) and stage["round_count"] < 2:
        warnings.append("大人っぽい雰囲気は距離が近すぎる印象になりやすいため、初回や1往復目では控えめにしてください。")
    if partner_notes:
        note_text = partner_notes.lower()
        if any("電話" in item for item in objectives) and "電話" in partner_notes and any(word in partner_notes for word in ["早", "まだ", "控え"]):
            warnings.append("相手別メモ上、電話はまだ早そうです。電話提案を送る前に温度感を確認してください。")
        if any("LINE" in item for item in objectives) and "LINE" in partner_notes and any(word in partner_notes for word in ["早", "まだ", "控え"]):
            warnings.append("相手別メモ上、LINE交換はまだ早そうです。IDそのものは保存しないでください。")
        if "旅行" in partner_notes and not any("電話" in item or "会う" in item or "LINE" in item for item in objectives):
            warnings.append("相手別メモに旅行の反応が良い記録があります。自然な範囲で旅行話題を広げる候補が合いそうです。")
        if "night" in note_text or "夜" in partner_notes:
            warnings.append("相手別メモに夜の返信傾向があります。送る時間帯はユーザーが手動で判断してください。")
    return {
        "partner_id": partner.partner_id,
        "generation_mode": get_generation_mode_for_partner(partner),
        "objectives": objectives or ["指定なし"],
        "tone": tone or "自然",
        "place_hint": place_hint.strip() or "-",
        "stage": stage,
        "partner_notes": {
            "has_notes": bool(partner_notes),
            "count": len([note for note in partner.notes if note.text.strip()]),
            "summary": _truncate_for_display(partner_notes, 240) or "-",
        },
        "recent_sent_outcomes": recent_outcomes or ["-"],
        "warnings": warnings,
        "local_save_only": True,
        "auto_send": False,
    }


def generate_suggestion_variants_for_gui(
    partner_id: str,
    objectives: list[str] | None = None,
    tone: str = "自然",
    place_hint: str = "",
) -> dict[str, Any]:
    partner = load_partner(partner_id)
    mode = get_generation_mode_for_partner(partner)
    if mode not in {"first", "reply"}:
        raise ValueError(build_generation_status_message(partner))
    purpose = "first_message" if mode == "first" else "reply"
    request = GenerationRequest(
        target_profile=_target_from_partner(partner),
        user_profile=load_user_profile(),
        conversation_history=list(partner.conversation),
        purpose=purpose,
        current_stage="first_message" if mode == "first" else "auto",
    )
    result = generate(request)
    base_candidates = _unique_candidates([result.best_message, *result.message_candidates])
    variants = []
    selected_objectives = [item for item in (objectives or []) if item]
    for index in range(3):
        base = base_candidates[index % len(base_candidates)]
        objective = selected_objectives[index % len(selected_objectives)] if selected_objectives else "質問を1つ入れる"
        text = _shape_candidate_for_objective(base, objective, tone, place_hint, mode, index)
        suggestion = add_suggestion(
            partner,
            purpose="first" if mode == "first" else "reply",
            text=text,
            source="gui-generate-variants",
            safety_result="OK",
        )
        variants.append(
            {
                "suggestion_id": suggestion.suggestion_id,
                "text": suggestion.text,
                "purpose": suggestion.purpose,
                "objective": objective,
                "tone": tone or "自然",
                "use_case": _variant_use_case(index),
                "partner_notes": _truncate_for_display(_partner_notes_text(partner), 240) or "-",
                "recent_sent_outcomes": _recent_outcome_summaries(partner),
                "safety_notes": _candidate_safety_notes(text, objective, partner),
            }
        )
    partner.analysis.partner_temperature = result.partner_temperature
    partner.analysis.safe_topics = list(result.safe_topics)
    partner.analysis.light_only_topics = list(result.light_only_topics)
    partner.analysis.avoid_topics = list(result.avoid_topics)
    partner.analysis.next_strategy = result.recommended_strategy
    partner.analysis.last_suggested_message = variants[0]["text"]
    if mode == "first":
        partner.status = "first_message_suggested"
    elif partner.status in {"new_profile", "first_message_sent", "first_message_suggested"}:
        partner.status = "chatting"
    save_updated_partner(partner)
    return {
        "mode": mode,
        "variants": variants,
        "stage": build_conversation_stage_summary(partner),
        "preflight": build_generation_preflight(partner, selected_objectives, tone, place_hint),
        "partner_notes": _truncate_for_display(_partner_notes_text(partner), 240) or "-",
        "recent_sent_outcomes": _recent_outcome_summaries(partner),
    }


def can_mark_suggestion_sent(partner: PartnerRecord, suggestion_id: str, confirmed: bool = False) -> bool:
    if partner.status == "archived" or not confirmed:
        return False
    return any(suggestion.suggestion_id == suggestion_id and suggestion.status == "pending" for suggestion in partner.pending_suggestions)


def build_mark_sent_preview(partner: PartnerRecord, suggestion_id: str | None = None, custom_text: str = "") -> dict[str, Any]:
    custom_text = custom_text.strip()
    if suggestion_id:
        suggestion = next(
            (item for item in partner.pending_suggestions if item.suggestion_id == suggestion_id and item.status == "pending"),
            None,
        )
        if suggestion is None:
            raise ValueError(f"pending suggestion not found: {suggestion_id}")
        text = suggestion.text
        source = f"suggestion_id: {suggestion_id}"
        remaining_note = "-"
    else:
        if not custom_text:
            raise ValueError("実際に送信した文を入力してください。")
        text = custom_text
        source = "custom text"
        remaining = [item.suggestion_id for item in get_pending_suggestions(partner)]
        remaining_note = " / ".join(remaining) if remaining else "-"
    return {
        "partner_id": partner.partner_id,
        "record_type": source,
        "speaker": "user",
        "text": text,
        "conversation_history": "user発話を1件追加",
        "message_state": "相手の返信待ちへ更新",
        "remaining_pending_suggestions": remaining_note,
        "local_record_only": True,
    }


def mark_suggestion_sent_from_gui(partner_id: str, suggestion_id: str, confirmed: bool) -> dict[str, Any]:
    partner = load_partner(partner_id)
    if not can_mark_suggestion_sent(partner, suggestion_id, confirmed=confirmed):
        raise ValueError("確認チェックがないか、送信済み記録できるpending suggestionではありません。")
    suggestion = mark_suggestion_sent(partner, suggestion_id)
    return {
        "partner_id": partner.partner_id,
        "suggestion_id": suggestion.suggestion_id,
        "text": suggestion.text,
        "status": suggestion.status,
        "remaining_pending_suggestions": len(get_pending_suggestions(partner)),
    }


def mark_custom_text_sent_from_gui(partner_id: str, text: str, confirmed: bool) -> dict[str, Any]:
    text = text.strip()
    if not confirmed:
        raise ValueError("確認チェックを入れてください。")
    if not text:
        raise ValueError("実際に送信した文を入力してください。")
    partner = load_partner(partner_id)
    if partner.status == "archived":
        raise ValueError("archivedのpartnerには送信済み記録できません。")
    pending_before = len(get_pending_suggestions(partner))
    mark_text_sent(partner, text)
    stored = load_partner(partner_id)
    return {
        "partner_id": stored.partner_id,
        "text": text,
        "remaining_pending_suggestions": pending_before,
        "note": "custom textで記録したため、元候補がpendingに残る場合があります。",
    }


def can_discard_suggestion(partner: PartnerRecord, suggestion_id: str, confirmed: bool = False) -> bool:
    if partner.status == "archived" or not confirmed:
        return False
    return any(suggestion.suggestion_id == suggestion_id and suggestion.status == "pending" for suggestion in partner.pending_suggestions)


def build_discard_suggestion_preview(partner: PartnerRecord, suggestion_id: str, reason: str = "") -> dict[str, Any]:
    suggestion = next(
        (item for item in partner.pending_suggestions if item.suggestion_id == suggestion_id and item.status == "pending"),
        None,
    )
    if suggestion is None:
        raise ValueError(f"pending suggestion not found: {suggestion_id}")
    remaining = [item.suggestion_id for item in get_pending_suggestions(partner) if item.suggestion_id != suggestion_id]
    return {
        "partner_id": partner.partner_id,
        "discard_target": suggestion_id,
        "purpose": suggestion.purpose,
        "reason": reason.strip() or "GUIから未使用候補として破棄",
        "conversation_history": "変更しない",
        "message_state": "既存discard処理に従ってnext_actionを再計算",
        "remaining_pending_suggestions": " / ".join(remaining) if remaining else "-",
        "local_record_only": True,
    }


def discard_suggestion_from_gui(partner_id: str, suggestion_id: str, confirmed: bool, reason: str = "") -> dict[str, Any]:
    partner = load_partner(partner_id)
    if not can_discard_suggestion(partner, suggestion_id, confirmed=confirmed):
        raise ValueError("確認チェックがないか、破棄できるpending suggestionではありません。")
    conversation_count_before = len(partner.conversation)
    suggestion = discard_suggestion(partner, suggestion_id)
    stored = load_partner(partner_id)
    return {
        "partner_id": stored.partner_id,
        "suggestion_id": suggestion.suggestion_id,
        "status": suggestion.status,
        "discard_reason": reason.strip() or "GUIから未使用候補として破棄",
        "conversation_history_unchanged": len(stored.conversation) == conversation_count_before,
        "remaining_pending_suggestions": len(get_pending_suggestions(stored)),
        "next_action": stored.message_state.next_action,
    }


def split_form_list(value: str) -> list[str]:
    if not value:
        return []
    normalized = value.replace(",", "\n").replace("、", "\n")
    return [item.strip() for item in normalized.splitlines() if item.strip()]


def build_profile_form_from_paste(text: str) -> tuple[dict[str, Any], list[str]]:
    extracted = {field: "" for field in PROFILE_PASTE_FIELDS}
    warnings = []
    current_field: str | None = None
    unknown_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        field, value = _split_profile_paste_line(line)
        if field:
            current_field = field
            if value:
                extracted[field] = _append_profile_field_value(extracted[field], value)
            continue
        if current_field in {"profile_text", "photo_memo", "interests", "avoid_topics", "conversation_hooks", "first_message_hints", "safety_notes", "notes"}:
            cleaned = line[2:].strip() if line.startswith(("- ", "・")) else line
            extracted[current_field] = _append_profile_field_value(extracted[current_field], cleaned)
        else:
            unknown_lines.append(line)
    if unknown_lines and not extracted["profile_text"]:
        extracted["profile_text"] = "\n".join(unknown_lines)
    elif unknown_lines:
        extracted["notes"] = _append_profile_field_value(extracted["notes"], "\n".join(unknown_lines))
    safety_warnings = detect_profile_safety_warnings(extracted)
    if safety_warnings:
        warnings.append("保存前に見直してください: " + " / ".join(safety_warnings))
    return extracted, warnings


def merge_profile_form_with_paste(form: dict[str, Any], pasted_form: dict[str, Any]) -> dict[str, Any]:
    merged = dict(form)
    for key, value in pasted_form.items():
        if key == "label":
            continue
        if key not in merged or not str(merged.get(key, "")).strip():
            merged[key] = value
    return merged


def build_profile_paste_preview(text: str) -> dict[str, Any]:
    extracted, warnings = build_profile_form_from_paste(text)
    extracted_fields = {key: extracted.get(key) or "未抽出" for key in PROFILE_PASTE_FIELDS}
    missing_fields = [key for key, value in extracted.items() if not value]
    return {
        "extracted_fields": extracted_fields,
        "missing_fields": missing_fields,
        "warnings": warnings,
        "review_notes": [
            "抽出できなかった項目や違う項目は、保存前に下の入力欄で修正できます。",
            "スクリーンショット画像や顔写真そのものではなく、読み取ったテキストと印象メモだけを保存します。",
            "本名、勤務先、学校名、LINE ID、SNS ID、住所、電話番号、メールアドレスは保存しないでください。",
        ],
        "manual_review_required": True,
        "saves_images": False,
        "auto_send": False,
    }


def validate_profile_form(form: dict[str, Any]) -> list[str]:
    errors = []
    label = str(form.get("label", "")).strip()
    display_name = str(form.get("display_name", "")).strip()
    profile_text = str(form.get("profile_text", "")).strip()
    photo_memo = str(form.get("photo_memo", "")).strip()
    if not label:
        errors.append("label は必須です。")
    else:
        try:
            validate_real_profile_label(label)
        except ValueError:
            errors.append("label は英数字・ハイフン・アンダースコアのみで入力してください。")
    if not display_name:
        errors.append("display_name は必須です。")
    if not profile_text and not photo_memo:
        errors.append("profile_text または photo_memo のどちらかは必須です。")
    return errors


def detect_profile_safety_warnings(form: dict[str, Any]) -> list[str]:
    texts = [str(value) for value in form.values() if value is not None]
    warnings = set(detect_privacy_warnings(texts))
    joined = "\n".join(texts)
    joined_lower = joined.lower()
    for word in PROFILE_SAFETY_WORDS:
        if word.lower() in joined_lower:
            warnings.add(word)
    for label, pattern in PROFILE_SAFETY_PATTERNS.items():
        if pattern.search(joined):
            warnings.add(label)
    return sorted(warnings)


def build_real_profile_from_form(form: dict[str, Any]) -> dict[str, Any]:
    photo_items = split_form_list(str(form.get("photo_memo", "")))
    profile_text = str(form.get("profile_text", "")).strip()
    if not profile_text and photo_items:
        profile_text = "プロフィール文なし。写真メモのみ登録。"
    free_notes = _build_free_notes(form)
    return {
        "label": str(form.get("label", "")).strip(),
        "profile_text": profile_text,
        "age": _parse_optional_int(form.get("age")),
        "hobbies": split_form_list(str(form.get("interests", ""))),
        "photos_memo": photo_items,
        "location_hint": _empty_to_none(str(form.get("area", "")).strip()),
        "relationship_goal": None,
        "free_notes": free_notes,
    }


def build_profile_save_preview(form: dict[str, Any]) -> dict[str, Any]:
    data = build_real_profile_from_form(form)
    return {
        "保存先label": data["label"],
        "display_name": str(form.get("display_name", "")).strip() or "-",
        "app_name": str(form.get("app_name", "")).strip() or "-",
        "age": data["age"],
        "area": data["location_hint"] or "-",
        "profile_text": data["profile_text"],
        "photo_memo": data["photos_memo"],
        "interests": data["hobbies"],
        "avoid_topics": split_form_list(str(form.get("avoid_topics", ""))),
        "conversation_hooks": split_form_list(str(form.get("conversation_hooks", ""))),
        "first_message_hints": split_form_list(str(form.get("first_message_hints", ""))),
        "safety_notes": split_form_list(str(form.get("safety_notes", ""))),
        "notes": str(form.get("notes", "")).strip() or "-",
        "保存先": str(get_real_profile_path(data["label"])),
    }


def get_real_profile_path(label: str) -> Path:
    validate_real_profile_label(label)
    return get_real_profile_dir() / f"{label}.yaml"


def real_profile_exists(label: str) -> bool:
    return get_real_profile_path(label).exists()


def save_real_profile_from_form(form: dict[str, Any]) -> tuple[Path, list[str]]:
    errors = validate_profile_form(form)
    if errors:
        raise ValueError("\n".join(errors))
    data = build_real_profile_from_form(form)
    return create_real_profile(**data)


def list_real_profiles_for_gui() -> list[dict[str, Any]]:
    profiles = []
    for path, profile in list_real_profiles():
        label = profile.name_or_label or path.stem
        profiles.append(
            {
                "label": label,
                "path": path,
                "display_label": f"{label} / age:{profile.age or '-'} / hobbies:{', '.join(profile.hobbies[:3]) if profile.hobbies else '-'}",
            }
        )
    return profiles


def filter_real_profiles_for_gui(query: str = "") -> list[dict[str, Any]]:
    query = query.strip().lower()
    profiles = list_real_profiles_for_gui()
    if not query:
        return profiles
    return [profile for profile in profiles if query in profile["display_label"].lower() or query in profile["label"].lower()]


def load_real_profile_for_gui(label: str) -> tuple[Path, TargetProfile]:
    return load_real_profile(label=label)


def build_real_profile_summary_for_gui(label: str) -> dict[str, Any]:
    path, profile = load_real_profile_for_gui(label)
    return {
        "label": label,
        "path": str(path),
        "age": profile.age or "-",
        "area": profile.location_hint or "-",
        "profile_text": profile.profile_text,
        "interests": profile.hobbies,
        "photo_memo": profile.photos_memo,
        "free_notes": profile.free_notes or "-",
    }


def find_existing_partners_for_profile(label: str) -> list[dict[str, str]]:
    _path, profile = load_real_profile_for_gui(label)
    matches = []
    for partner in list_partners():
        if partner.profile.profile_text == profile.profile_text and partner.profile.hobbies == profile.hobbies:
            matches.append(
                {
                    "partner_id": partner.partner_id,
                    "display_name": partner.display_name,
                    "status": partner.status,
                }
            )
    return matches


def build_partner_creation_preview(label: str, display_name: str, app_name: str = "", source_memo: str = "") -> dict[str, Any]:
    path, profile = load_real_profile_for_gui(label)
    return {
        "source_real_profile": label,
        "source_path": str(path),
        "display_name": display_name.strip() or profile.name_or_label or label,
        "app_name": app_name.strip() or "-",
        "source_memo": source_memo.strip() or "-",
        "status": "new_profile",
        "next_action": "初回候補生成待ち",
        "conversation_history": "空",
        "pending_suggestions": "空",
        "profile_summary": {
            "age": profile.age,
            "hobbies": profile.hobbies,
            "location_hint": profile.location_hint,
            "profile_text_chars": len(profile.profile_text),
        },
        "保存先": "data/local/partners/<next partner_id>.yaml",
    }


def save_partner_from_profile(label: str, display_name: str, app_name: str = "", source_memo: str = "") -> PartnerRecord:
    _path, profile = load_real_profile_for_gui(label)
    chosen_display_name = display_name.strip() or profile.name_or_label or label
    partner = create_partner_from_target_profile(profile, display_name=chosen_display_name, app_name=app_name.strip())
    partner.message_state.next_action = "初回候補生成待ち"
    if source_memo.strip():
        partner.notes.append(
            PartnerNote(text=f"source memo: {source_memo.strip()}", created_at=partner.created_at)
        )
    save_updated_partner(partner)
    return partner


def parse_conversation_paste(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    turns: list[dict[str, Any]] = []
    warnings: list[str] = []
    current: dict[str, Any] | None = None
    unknown_lines: list[str] = []

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        match = SPEAKER_LINE_RE.match(line)
        if match:
            label = match.group(1).strip()
            content = match.group(2).strip()
            speaker = SPEAKER_ALIASES.get(label.lower()) or SPEAKER_ALIASES.get(label)
            if speaker:
                if current:
                    _append_parsed_turn(turns, current)
                current = {"speaker": speaker, "text": content, "line_no": line_no, "source_label": label}
            else:
                unknown_lines.append(f"{line_no}: {raw_line}")
                if current:
                    current["text"] = f"{current['text']}\n{raw_line}".strip()
            continue

        if current:
            current["text"] = f"{current['text']}\n{raw_line}".strip()
        else:
            unknown_lines.append(f"{line_no}: {raw_line}")

    if current:
        _append_parsed_turn(turns, current)
    if unknown_lines:
        warnings.append("発話者を判定できない行があります: " + " / ".join(unknown_lines[:5]))
    return turns, warnings


def validate_imported_turns(turns: list[dict[str, Any]], warnings: list[str] | None = None) -> list[str]:
    errors = list(warnings or [])
    if not turns:
        errors.append("会話履歴を解析できませんでした。")
    for index, turn in enumerate(turns, start=1):
        if turn.get("speaker") not in {"user", "partner"}:
            errors.append(f"{index}件目のspeakerが不正です。")
        if not str(turn.get("text", "")).strip():
            errors.append(f"{index}件目の本文が空です。")
    return errors


def detect_conversation_safety_warnings(text: str) -> list[str]:
    return detect_profile_safety_warnings({"conversation": text})


def build_conversation_import_preview(partner: PartnerRecord, turns: list[dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
    return {
        "対象partner_id": partner.partner_id,
        "display_name": partner.display_name,
        "追加予定turn数": len(turns),
        "speakerごとの発話数": {
            "user": sum(1 for turn in turns if turn.get("speaker") == "user"),
            "partner": sum(1 for turn in turns if turn.get("speaker") == "partner"),
        },
        "turns": [
            {"index": index, "speaker": turn["speaker"], "text": turn["text"]}
            for index, turn in enumerate(turns, start=1)
        ],
        "警告一覧": warnings,
        "保存先": f"data/local/partners/{partner.partner_id}.yaml",
    }


def detect_duplicate_turn_sequence(partner: PartnerRecord, turns: list[dict[str, Any]]) -> bool:
    if not turns or len(partner.conversation) < len(turns):
        return False
    recent = partner.conversation[-len(turns) :]
    return all(
        existing.speaker == turn.get("speaker") and existing.text == str(turn.get("text", ""))
        for existing, turn in zip(recent, turns)
    )


def append_conversation_turns_to_partner(partner_id: str, turns: list[dict[str, Any]]) -> PartnerRecord:
    errors = validate_imported_turns(turns)
    if errors:
        raise ValueError("\n".join(errors))
    partner = load_partner(partner_id)
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    for turn in turns:
        speaker = str(turn["speaker"])
        text = str(turn["text"]).strip()
        partner.conversation.append(ConversationTurn(speaker=speaker, text=text, timestamp=timestamp))
        add_activity_event(partner, "turn_added", f"{speaker}発言をインポート", created_at=timestamp)
        _update_message_state_from_turn(partner, speaker, text, timestamp)
    partner.analysis.partner_temperature = estimate_partner_temperature(partner.conversation)
    return save_updated_partner(partner)


def _parse_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    return int(text) if text else None


def _empty_to_none(value: str) -> str | None:
    return value if value else None


def _build_free_notes(form: dict[str, Any]) -> str | None:
    display_name = str(form.get("display_name", "")).strip()
    app_name = str(form.get("app_name", "")).strip()
    avoid_topics = split_form_list(str(form.get("avoid_topics", "")))
    conversation_hooks = split_form_list(str(form.get("conversation_hooks", "")))
    first_message_hints = split_form_list(str(form.get("first_message_hints", "")))
    safety_notes = split_form_list(str(form.get("safety_notes", "")))
    notes = str(form.get("notes", "")).strip()
    lines = []
    if display_name:
        lines.append(f"display_name: {display_name}")
    if app_name:
        lines.append(f"app_name: {app_name}")
    if avoid_topics:
        lines.append("avoid_topics:")
        lines.extend(f"- {item}" for item in avoid_topics)
    if conversation_hooks:
        lines.append("conversation_hooks:")
        lines.extend(f"- {item}" for item in conversation_hooks)
    if first_message_hints:
        lines.append("first_message_hints:")
        lines.extend(f"- {item}" for item in first_message_hints)
    if safety_notes:
        lines.append("safety_notes:")
        lines.extend(f"- {item}" for item in safety_notes)
    if notes:
        lines.append("notes:")
        lines.append(notes)
    return "\n".join(lines) if lines else None


def _append_parsed_turn(turns: list[dict[str, Any]], current: dict[str, Any]) -> None:
    text = str(current.get("text", "")).strip()
    if text:
        turns.append(
            {
                "speaker": current["speaker"],
                "text": text,
                "line_no": current["line_no"],
                "source_label": current["source_label"],
            }
        )


def _update_message_state_from_turn(partner: PartnerRecord, speaker: str, text: str, timestamp: str) -> None:
    if speaker == "partner":
        partner.message_state.last_partner_message = text
        partner.message_state.last_received_at = timestamp
        partner.message_state.awaiting_user_action = True
        partner.message_state.awaiting_partner_reply = False
        partner.message_state.next_action = "返信候補を生成する"
        if partner.status == "first_message_sent":
            previous = partner.status
            partner.status = "chatting"
            add_activity_event(partner, "status_updated", f"status: {previous} -> chatting", created_at=timestamp)
    else:
        partner.message_state.last_user_message = text
        partner.message_state.last_sent_at = timestamp
        partner.message_state.awaiting_user_action = False
        partner.message_state.awaiting_partner_reply = True
        partner.message_state.next_action = "相手の返信待ち"


def _target_from_partner(partner: PartnerRecord) -> TargetProfile:
    profile = partner.profile
    return TargetProfile(
        name_or_label=partner.display_name,
        age=profile.age,
        profile_text=profile.profile_text,
        hobbies=list(profile.hobbies),
        photos_memo=list(profile.photos_memo),
        location_hint=profile.location_hint,
        relationship_goal=profile.relationship_goal,
        free_notes=profile.free_notes,
    )


def _split_profile_paste_line(line: str) -> tuple[str | None, str]:
    match = re.match(r"^\s*([^:：]+)\s*[:：]\s*(.*)$", line)
    if not match:
        return None, ""
    raw_key = match.group(1).strip().lower()
    field = PROFILE_PASTE_FIELD_ALIASES.get(raw_key) or PROFILE_PASTE_FIELD_ALIASES.get(match.group(1).strip())
    return field, match.group(2).strip() if field else ""


def _append_profile_field_value(current: Any, value: str) -> str:
    value = value.strip()
    if not value:
        return str(current or "")
    current_text = str(current or "").strip()
    return f"{current_text}\n{value}" if current_text else value


def _unique_candidates(candidates: list[str]) -> list[str]:
    unique = []
    for candidate in candidates:
        text = candidate.strip()
        if text and text not in unique:
            unique.append(text)
    return unique or ["はじめまして。プロフィールを見て、話してみたいなと思いました。休日はどんな過ごし方が多いですか？"]


def _shape_candidate_for_objective(base: str, objective: str, tone: str, place_hint: str, mode: str, index: int) -> str:
    place = place_hint.strip()
    if "電話" in objective:
        return "メッセージだと少し伝わりにくいので、タイミングが合えば短く電話で話してみませんか？"
    if "LINE" in objective:
        return "このままアプリでも大丈夫ですが、話しやすければLINEに移っても大丈夫です。無理なければで大丈夫です。"
    if "場所" in objective and place:
        return f"話していて雰囲気が合いそうだなと思いました。よかったら今度、{place}あたりで軽くお茶でも行けたら嬉しいです。"
    if "会う" in objective:
        return "話していて雰囲気が合いそうだなと思いました。よかったら今度、軽くお茶でも行けたら嬉しいです。"
    if "自分の紹介" in objective:
        return _trim_for_gui(f"{base} 自分も近い雰囲気の話題は好きなので、ゆるく話せたら嬉しいです。")
    if "ユーモア" in objective or "ユーモア" in tone:
        return _trim_for_gui(f"{base} ちょっとだけ気になって、つい聞きたくなりました。")
    if "大人" in objective or "大人" in tone:
        return _trim_for_gui(base.replace("嬉しいです。", "嬉しいです。落ち着いて話せる感じもいいなと思いました。"))
    if "短め" in tone:
        return _trim_for_gui(base, 90)
    if index == 1:
        return _trim_for_gui(base.replace("気になりました", "印象に残りました"))
    if index == 2:
        return _trim_for_gui(base.replace("最近", "休日は"))
    return _trim_for_gui(base)


def _trim_for_gui(text: str, max_len: int = 160) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _variant_use_case(index: int) -> str:
    return ["候補A: 一番無難。迷ったらこれ。", "候補B: 少し距離を縮める用。", "候補C: 相手の反応が良いとき用。"][index % 3]


def _candidate_safety_notes(text: str, objective: str, partner: PartnerRecord | None = None) -> list[str]:
    notes = ["自動送信ではありません。送信前に人間が確認してください。"]
    if "電話" in objective or "会う" in objective or "LINE" in objective:
        notes.append("会話の温度感が低い場合は送らないでください。")
    if "LINE" in objective:
        notes.append("LINE IDそのものは保存しないでください。")
    if "大人っぽい" in objective:
        notes.append("下ネタや身体的表現に寄せず、控えめにしてください。")
    if partner:
        partner_notes = _partner_notes_text(partner)
        if "旅行" in partner_notes:
            notes.append("相手別メモに旅行話題の反応記録があります。無理なく広げられるか確認してください。")
        if "電話" in objective and "電話" in partner_notes and any(word in partner_notes for word in ["早", "まだ", "控え"]):
            notes.append("相手別メモ上、電話はまだ早そうです。")
    if text.count("？") + text.count("?") > 1:
        notes.append("質問が複数あります。1つに減らすと自然です。")
    return notes


def _find_sent_suggestion(partner: PartnerRecord, suggestion_id: str):
    for suggestion in partner.pending_suggestions:
        if suggestion.suggestion_id == suggestion_id and suggestion.status == "sent":
            return suggestion
    raise ValueError(f"sent suggestion not found: {suggestion_id}")


def _partner_notes_text(partner: PartnerRecord) -> str:
    return "\n".join(note.text.strip() for note in partner.notes if note.text.strip())


def _recent_outcome_summaries(partner: PartnerRecord, limit: int = 3) -> list[str]:
    sent = [suggestion for suggestion in partner.pending_suggestions if suggestion.status == "sent"]
    summaries = []
    for suggestion in sent[-limit:]:
        status = suggestion.outcome_status or "未確認"
        memo = suggestion.outcome_memo.strip()
        detail = f"{suggestion.suggestion_id}: {status}"
        if memo:
            detail += f" / {_truncate_for_display(memo, 80)}"
        summaries.append(detail)
    return summaries


def _truncate_for_display(text: str, max_length: int) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= max_length else compact[: max_length - 3] + "..."
