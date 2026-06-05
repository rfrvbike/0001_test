from __future__ import annotations

from datetime import datetime

from .activity_log import add_activity_event
from .conversation_planner import estimate_partner_temperature
from .models import ConversationTurn, PartnerRecord
from .partner_manager import save_updated_partner

VALID_SPEAKERS = {"user", "partner"}


def add_turn(partner: PartnerRecord, speaker: str, text: str) -> ConversationTurn:
    if speaker not in VALID_SPEAKERS:
        raise ValueError("speaker must be user or partner")
    turn = ConversationTurn(
        speaker=speaker,
        text=text,
        timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
    )
    partner.conversation.append(turn)
    add_activity_event(partner, "turn_added", f"{speaker}発言を追加", created_at=turn.timestamp)
    if speaker == "partner":
        partner.message_state.last_partner_message = text
        partner.message_state.last_received_at = turn.timestamp
        partner.message_state.awaiting_user_action = True
        partner.message_state.awaiting_partner_reply = False
        partner.message_state.next_action = "返信候補を生成する"
        if partner.status == "first_message_sent":
            previous = partner.status
            partner.status = "chatting"
            add_activity_event(partner, "status_updated", f"status: {previous} -> chatting")
    else:
        partner.message_state.last_user_message = text
        partner.message_state.last_sent_at = turn.timestamp
        partner.message_state.awaiting_user_action = False
        partner.message_state.awaiting_partner_reply = True
        partner.message_state.next_action = "相手の返信待ち"
    partner.analysis.partner_temperature = estimate_partner_temperature(partner.conversation)
    save_updated_partner(partner)
    return turn


def get_recent_turns(partner: PartnerRecord, limit: int = 10) -> list[ConversationTurn]:
    return list(partner.conversation[-limit:])


def get_all_turns(partner: PartnerRecord) -> list[ConversationTurn]:
    return list(partner.conversation)


def build_conversation_for_generation(partner: PartnerRecord, limit: int | None = None) -> list[ConversationTurn]:
    return get_recent_turns(partner, limit) if limit else get_all_turns(partner)
