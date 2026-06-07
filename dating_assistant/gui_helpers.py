from __future__ import annotations

from dataclasses import asdict
import re
from pathlib import Path
from typing import Any

from src.models import PartnerRecord
from src.partner_store import list_partners, load_partner
from src.real_profile_manager import (
    create_real_profile,
    detect_privacy_warnings,
    get_real_profile_dir,
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
