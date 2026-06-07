from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import re
from pathlib import Path
from typing import Any

from src.activity_log import add_activity_event
from src.conversation_planner import estimate_partner_temperature
from src.models import PartnerNote, PartnerRecord, TargetProfile
from src.partner_store import list_partners, load_partner
from src.models import ConversationTurn
from src.partner_manager import create_partner_from_target_profile, save_updated_partner
from src.real_profile_manager import (
    create_real_profile,
    detect_privacy_warnings,
    get_real_profile_dir,
    list_real_profiles,
    load_real_profile,
    validate_real_profile_label,
)
from src.suggestion_manager import get_pending_suggestions
from src.timeline_builder import build_timeline_events

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


def split_form_list(value: str) -> list[str]:
    if not value:
        return []
    normalized = value.replace(",", "\n").replace("、", "\n")
    return [item.strip() for item in normalized.splitlines() if item.strip()]


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


def load_real_profile_for_gui(label: str) -> tuple[Path, TargetProfile]:
    return load_real_profile(label=label)


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
    notes = str(form.get("notes", "")).strip()
    lines = []
    if display_name:
        lines.append(f"display_name: {display_name}")
    if app_name:
        lines.append(f"app_name: {app_name}")
    if avoid_topics:
        lines.append("avoid_topics:")
        lines.extend(f"- {item}" for item in avoid_topics)
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
