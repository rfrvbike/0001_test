from __future__ import annotations

import re

from .activity_log import add_activity_event, now_timestamp
from .conversation_memory import add_turn
from .models import PartnerRecord, PendingSuggestion
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
    add_activity_event(partner, "suggestion_sent", f"{suggestion_id} を送信済み", suggestion_id, suggestion.sent_at)
    if partner.status == "first_message_suggested":
        partner.status = "first_message_sent"
        add_activity_event(partner, "status_updated", "status: first_message_suggested -> first_message_sent")
    save_updated_partner(partner)
    return suggestion


def mark_text_sent(partner: PartnerRecord, text: str) -> None:
    add_turn(partner, "user", text)


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
