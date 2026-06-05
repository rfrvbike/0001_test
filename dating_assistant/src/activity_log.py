from __future__ import annotations

import re
from datetime import datetime

from .models import ActivityEvent, PartnerRecord


def add_activity_event(
    partner: PartnerRecord,
    event_type: str,
    summary: str,
    related_id: str | None = None,
    created_at: str | None = None,
) -> ActivityEvent:
    event = ActivityEvent(
        event_id=generate_next_event_id(partner),
        event_type=event_type,
        created_at=created_at or now_timestamp(),
        summary=summary,
        related_id=related_id,
    )
    partner.activity_log.append(event)
    return event


def generate_next_event_id(partner: PartnerRecord) -> str:
    numbers = []
    for event in partner.activity_log:
        match = re.fullmatch(r"event_(\d+)", event.event_id)
        if match:
            numbers.append(int(match.group(1)))
    return f"event_{max(numbers, default=0) + 1:03d}"


def now_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
