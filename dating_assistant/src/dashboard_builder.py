from __future__ import annotations

from .models import PartnerRecord
from .suggestion_manager import pending_suggestion_count

CATEGORY_ORDER = ["needs_action", "invite_ready", "waiting", "other", "paused_or_closed"]
CATEGORY_LABELS = {
    "needs_action": "要対応",
    "invite_ready": "誘い検討",
    "waiting": "返信待ち",
    "other": "その他進行中",
    "paused_or_closed": "停止中/終了",
    "archived": "アーカイブ済み",
}


def classify_partner(record: PartnerRecord) -> str:
    if record.status == "archived":
        return "archived"
    if record.status in {"paused", "closed"}:
        return "paused_or_closed"
    if record.message_state.awaiting_user_action or pending_suggestion_count(record) > 0:
        return "needs_action"
    if record.status == "invite_ready":
        return "invite_ready"
    if record.message_state.awaiting_partner_reply:
        return "waiting"
    return "other"


def build_partner_dashboard(
    partners: list[PartnerRecord],
    active_only: bool = False,
    status: str | None = None,
    needs_action: bool = False,
    waiting: bool = False,
    include_archived: bool = False,
    archived_only: bool = False,
    sort_key: str = "updated",
) -> str:
    filtered = [
        partner
        for partner in partners
        if not (active_only and partner.status in {"paused", "closed", "archived"})
        and not (not include_archived and not archived_only and partner.status == "archived" and status != "archived")
        and not (archived_only and partner.status != "archived")
        and not (status and partner.status != status)
        and not (needs_action and classify_partner(partner) != "needs_action")
        and not (waiting and classify_partner(partner) != "waiting")
    ]
    if archived_only:
        categories = ["archived"]
    elif needs_action:
        categories = ["needs_action"]
    elif waiting:
        categories = ["waiting"]
    else:
        categories = CATEGORY_ORDER + (["archived"] if include_archived or status == "archived" else [])
    sections = ["【partnerダッシュボード】"]
    for category in categories:
        category_partners = [partner for partner in filtered if classify_partner(partner) == category]
        category_partners.sort(key=lambda partner: _sort_value(partner, sort_key))
        if category == "needs_action":
            category_partners.sort(key=lambda partner: pending_suggestion_count(partner) == 0)
        sections.append(_format_category(CATEGORY_LABELS[category], category, category_partners))
    return "\n\n".join(sections)


def _format_category(label: str, category: str, partners: list[PartnerRecord]) -> str:
    if not partners:
        return f"{label}:\n- なし"
    blocks = []
    for index, partner in enumerate(partners, 1):
        state = partner.message_state
        lines = [
            f"{index}. {partner.partner_id}  {partner.display_name}  {partner.app_name or '-'}",
            f"   status: {partner.status} / 温度感: {partner.analysis.partner_temperature}",
        ]
        if category == "needs_action":
            lines.extend(
                [
                    f"   未送信候補: {pending_suggestion_count(partner)}件",
                    f"   最終受信: {state.last_received_at or '-'}",
                    f"   次の行動: {state.next_action or '-'}",
                ]
            )
        elif category == "waiting":
            lines.extend([f"   最終送信: {state.last_sent_at or '-'}", f"   次の行動: {state.next_action or '-'}"])
        elif category == "invite_ready":
            lines.extend([f"   最終受信: {state.last_received_at or '-'}", f"   次の行動: {state.next_action or '-'}"])
        elif category == "other":
            lines.extend([f"   最終更新: {partner.updated_at or '-'}", f"   次の行動: {state.next_action or '-'}"])
        elif category == "archived":
            lines.extend([f"   最終更新: {partner.updated_at or '-'}", f"   次の行動: {state.next_action or '-'}"])
        blocks.append("\n".join(lines))
    return f"{label}:\n" + "\n\n".join(blocks)


def _sort_value(partner: PartnerRecord, sort_key: str) -> tuple[bool, str, str]:
    value = {
        "updated": partner.updated_at,
        "received": partner.message_state.last_received_at,
        "sent": partner.message_state.last_sent_at,
    }[sort_key]
    return (not bool(value), value or "", partner.partner_id)
