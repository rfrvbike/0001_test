from __future__ import annotations

from datetime import datetime

from .activity_log import add_activity_event
from .models import PartnerAnalysis, PartnerNote, PartnerProfile, PartnerRecord, TargetProfile
from .partner_store import generate_next_partner_id, save_partner

VALID_PARTNER_STATUSES = {
    "new_profile",
    "first_message_suggested",
    "first_message_sent",
    "chatting",
    "warm_chat",
    "invite_ready",
    "invited",
    "scheduling",
    "met",
    "paused",
    "closed",
}


def create_partner_from_target_profile(
    target: TargetProfile,
    display_name: str,
    app_name: str = "",
) -> PartnerRecord:
    now = _now()
    partner = PartnerRecord(
        partner_id=generate_next_partner_id(),
        display_name=display_name,
        app_name=app_name,
        status="new_profile",
        created_at=now,
        updated_at=now,
        profile=PartnerProfile(
            age=target.age,
            profile_text=target.profile_text,
            hobbies=list(target.hobbies),
            photos_memo=list(target.photos_memo),
            location_hint=target.location_hint,
            relationship_goal=target.relationship_goal,
            free_notes=target.free_notes,
        ),
        analysis=PartnerAnalysis(),
    )
    add_activity_event(partner, "partner_created", "partnerを作成", created_at=now)
    save_partner(partner, allow_overwrite=False)
    return partner


def update_partner_status(partner: PartnerRecord, status: str) -> PartnerRecord:
    if status not in VALID_PARTNER_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    previous = partner.status
    partner.status = status
    if previous != status:
        add_activity_event(partner, "status_updated", f"status: {previous} -> {status}")
    return _save_updated(partner)


def add_partner_note(partner: PartnerRecord, text: str) -> PartnerRecord:
    now = _now()
    partner.notes.append(PartnerNote(text=text, created_at=now))
    add_activity_event(partner, "note_added", f"メモ追加: {text}", created_at=now)
    return _save_updated(partner)


def update_partner_analysis(partner: PartnerRecord, **updates) -> PartnerRecord:
    for key, value in updates.items():
        if key not in PartnerAnalysis.__dataclass_fields__:
            raise ValueError(f"Invalid analysis field: {key}")
        setattr(partner.analysis, key, value)
    return _save_updated(partner)


def save_updated_partner(partner: PartnerRecord) -> PartnerRecord:
    return _save_updated(partner)


def _save_updated(partner: PartnerRecord) -> PartnerRecord:
    partner.updated_at = _now()
    save_partner(partner, allow_overwrite=True)
    return partner


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
