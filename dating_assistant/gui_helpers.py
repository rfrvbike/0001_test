from __future__ import annotations

from dataclasses import asdict
from typing import Any

from src.models import PartnerRecord
from src.partner_store import list_partners, load_partner
from src.suggestion_manager import get_pending_suggestions
from src.timeline_builder import build_timeline_events


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
