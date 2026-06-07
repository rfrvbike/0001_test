from __future__ import annotations

import re

from .activity_log import add_activity_event, now_timestamp
from .conversation_memory import add_turn
from .models import PartnerRecord, PendingSuggestion, SentRecord
from .partner_manager import save_updated_partner

VALID_SUGGESTION_STATUSES = {"pending", "sent", "discarded"}


def generate_next_suggestion_id(partner: PartnerRecord) -> str:
    numbers = []
    for suggestion in partner.pending_suggestions:
        match = re.fullmatch(r"suggestion_(\d+)", suggestion.suggestion_id)
        if match:
            numbers.append(int(match.group(1)))
    return f"suggestion_{max(numbers, default=0) + 1:03d}"


def add_suggestion(
    partner: PartnerRecord,
    purpose: str,
    text: str,
    source: str,
    safety_result: str = "OK",
) -> PendingSuggestion:
    suggestion = PendingSuggestion(
        suggestion_id=generate_next_suggestion_id(partner),
        purpose=purpose,
        text=text,
        created_at=now_timestamp(),
        status="pending",
        safety_result=safety_result,
        source=source,
    )
    partner.pending_suggestions.append(suggestion)
    labels = {"first": "初回メッセージ候補を生成", "reply": "返信候補を生成", "invite": "誘い文候補を生成"}
    add_activity_event(partner, "suggestion_created", labels.get(purpose, "候補を生成"), suggestion.suggestion_id)
    partner.message_state.last_suggested_message = text
    partner.message_state.awaiting_user_action = True
    partner.message_state.awaiting_partner_reply = False
    partner.message_state.next_action = "返信候補を確認して送る"
    save_updated_partner(partner)
    return suggestion


def mark_suggestion_sent(partner: PartnerRecord, suggestion_id: str) -> PendingSuggestion:
    suggestion = find_suggestion(partner, suggestion_id)
    if suggestion.status != "pending":
        raise ValueError(f"Suggestion is not pending: {suggestion_id}")
    suggestion.status = "sent"
    suggestion.sent_at = now_timestamp()
    add_turn(partner, "user", suggestion.text)
    _add_sent_record(partner, "generated_suggestion", suggestion.text, suggestion.sent_at, source_suggestion_id=suggestion_id)
    add_activity_event(partner, "suggestion_sent", f"{suggestion_id} を送信済み", suggestion_id, suggestion.sent_at)
    if partner.status == "first_message_suggested":
        partner.status = "first_message_sent"
        add_activity_event(partner, "status_updated", "status: first_message_suggested -> first_message_sent")
    save_updated_partner(partner)
    return suggestion


def mark_text_sent(partner: PartnerRecord, text: str) -> SentRecord:
    turn = add_turn(partner, "user", text)
    record = _add_sent_record(partner, "custom_text", text, turn.timestamp or now_timestamp())
    add_activity_event(partner, "custom_text_sent", f"{record.sent_id} を手入力送信済みとして記録", record.sent_id, record.sent_at)
    save_updated_partner(partner)
    return record


def discard_suggestion(partner: PartnerRecord, suggestion_id: str) -> PendingSuggestion:
    suggestion = find_suggestion(partner, suggestion_id)
    if suggestion.status != "pending":
        raise ValueError(f"Suggestion is not pending: {suggestion_id}")
    suggestion.status = "discarded"
    suggestion.discarded_at = now_timestamp()
    add_activity_event(partner, "suggestion_discarded", f"{suggestion_id} を破棄", suggestion_id, suggestion.discarded_at)
    pending = get_pending_suggestions(partner)
    if not pending:
        if partner.message_state.awaiting_partner_reply:
            partner.message_state.awaiting_user_action = False
            partner.message_state.next_action = "相手の返信待ち"
        elif partner.message_state.last_received_at:
            partner.message_state.awaiting_user_action = True
            partner.message_state.next_action = "返信候補を生成する"
        else:
            partner.message_state.awaiting_user_action = False
            partner.message_state.next_action = ""
    save_updated_partner(partner)
    return suggestion


def find_suggestion(partner: PartnerRecord, suggestion_id: str) -> PendingSuggestion:
    for suggestion in partner.pending_suggestions:
        if suggestion.suggestion_id == suggestion_id:
            return suggestion
    raise ValueError(f"Suggestion not found: {suggestion_id}")


def get_pending_suggestions(partner: PartnerRecord) -> list[PendingSuggestion]:
    return [suggestion for suggestion in partner.pending_suggestions if suggestion.status == "pending"]


def pending_suggestion_count(partner: PartnerRecord) -> int:
    return len(get_pending_suggestions(partner))


def _add_sent_record(
    partner: PartnerRecord,
    source_type: str,
    text: str,
    sent_at: str,
    source_suggestion_id: str | None = None,
) -> SentRecord:
    if source_suggestion_id and any(record.source_suggestion_id == source_suggestion_id for record in partner.sent_records):
        return next(record for record in partner.sent_records if record.source_suggestion_id == source_suggestion_id)
    record = SentRecord(
        sent_id=_generate_next_sent_id(partner, source_type),
        source_type=source_type,
        source_suggestion_id=source_suggestion_id,
        text=text,
        sent_at=sent_at,
    )
    partner.sent_records.append(record)
    return record


def _generate_next_sent_id(partner: PartnerRecord, source_type: str) -> str:
    prefix = "sent_custom" if source_type == "custom_text" else "sent_generated"
    numbers = []
    for record in partner.sent_records:
        match = re.fullmatch(rf"{prefix}_(\d+)", record.sent_id)
        if match:
            numbers.append(int(match.group(1)))
    return f"{prefix}_{max(numbers, default=0) + 1:06d}"
