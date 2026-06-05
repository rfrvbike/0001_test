from __future__ import annotations

from dataclasses import dataclass, field

from .activity_log import add_activity_event
from .models import PartnerRecord
from .partner_store import list_partners, save_partner


@dataclass
class BulkArchiveResult:
    archived: list[PartnerRecord] = field(default_factory=list)
    skipped: list[tuple[PartnerRecord, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def find_partners_for_bulk_archive(
    contains: str | None = None,
    status: str | None = None,
    partner_ids: list[str] | None = None,
    include_archived: bool = False,
) -> list[PartnerRecord]:
    ids = set(partner_ids or [])
    records = []
    for partner in list_partners():
        if ids and partner.partner_id not in ids:
            continue
        if contains and contains not in partner.display_name:
            continue
        if status and partner.status != status:
            continue
        if partner.status == "archived" and not include_archived:
            continue
        records.append(partner)
    return records


def bulk_archive_partners(records: list[PartnerRecord], reason: str | None = None) -> BulkArchiveResult:
    result = BulkArchiveResult()
    for partner in records:
        if partner.status == "archived":
            result.skipped.append((partner, "already archived"))
            continue
        try:
            partner.status = "archived"
            partner.message_state.awaiting_user_action = False
            partner.message_state.awaiting_partner_reply = False
            partner.message_state.next_action = "アーカイブ済み"
            summary = "一括アーカイブ"
            if reason:
                summary = f"{summary}: {reason}"
            add_activity_event(partner, "partner_bulk_archived", summary)
            save_partner(partner, allow_overwrite=True)
            result.archived.append(partner)
        except Exception as exc:  # pragma: no cover - defensive guard for partial local file failures
            result.errors.append(f"{partner.partner_id}: {exc}")
    return result

