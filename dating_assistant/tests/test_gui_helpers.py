import os
import tempfile
import unittest
from unittest.mock import patch

from gui_helpers import (
    build_partner_label,
    build_partner_summary,
    format_conversation_history,
    format_pending_suggestions,
    format_timeline_items,
    load_partner_choices,
)
from src.models import ActivityEvent, ConversationTurn, PartnerRecord, PendingSuggestion
from src.partner_store import save_partner


class GuiHelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATING_ASSISTANT_PARTNER_DIR": self.temp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_load_partner_choices_excludes_archived_by_default(self):
        save_partner(PartnerRecord(partner_id="partner_001", display_name="active", status="first_message_suggested"))
        save_partner(PartnerRecord(partner_id="partner_002", display_name="old", status="archived"))

        self.assertEqual([partner.partner_id for partner in load_partner_choices()], ["partner_001"])
        self.assertEqual([partner.partner_id for partner in load_partner_choices(include_archived=True)], ["partner_001", "partner_002"])

    def test_build_partner_summary_contains_operational_fields(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="first_message_suggested",
            pending_suggestions=[
                PendingSuggestion("suggestion_001", "first", "hello", "2026-06-07T10:00:00+09:00"),
                PendingSuggestion("suggestion_002", "reply", "sent", "2026-06-07T10:01:00+09:00", status="sent"),
            ],
        )
        partner.analysis.partner_temperature = "normal"
        partner.message_state.next_action = "候補確認待ち"

        summary = build_partner_summary(partner)

        self.assertEqual(summary["partner_id"], "partner_001")
        self.assertEqual(summary["partner_temperature"], "normal")
        self.assertEqual(summary["next_action"], "候補確認待ち")
        self.assertEqual(summary["pending_suggestions_count"], 1)
        self.assertFalse(summary["message_state"]["awaiting_partner_reply"])

    def test_format_conversation_and_pending_suggestions_for_display(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            conversation=[
                ConversationTurn("partner", "こんばんは", "2026-06-07T10:00:00+09:00"),
                ConversationTurn("user", "こんばんは", "2026-06-07T10:01:00+09:00"),
            ],
            pending_suggestions=[
                PendingSuggestion("suggestion_001", "reply", "返信案", "2026-06-07T10:02:00+09:00"),
                PendingSuggestion("suggestion_002", "reply", "送信済み", "2026-06-07T10:03:00+09:00", status="sent"),
            ],
        )

        conversation = format_conversation_history(partner)
        suggestions = format_pending_suggestions(partner)

        self.assertEqual(conversation[0]["speaker_label"], "相手")
        self.assertEqual(conversation[1]["speaker_label"], "自分")
        self.assertEqual([suggestion["suggestion_id"] for suggestion in suggestions], ["suggestion_001"])

    def test_format_timeline_items_uses_existing_timeline_builder(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            conversation=[ConversationTurn("partner", "hello", "2026-06-07T10:00:00+09:00")],
            activity_log=[
                ActivityEvent("event_001", "partner_created", "2026-06-07T09:59:00+09:00", "partnerを作成"),
            ],
        )

        timeline = format_timeline_items(partner)

        self.assertEqual(timeline[0]["event_type"], "partner_created")
        self.assertEqual(timeline[1]["actor"], "partner")

    def test_build_partner_label_is_selectbox_friendly(self):
        partner = PartnerRecord(partner_id="partner_001", display_name="sample", status="chatting")

        self.assertEqual(build_partner_label(partner), "partner_001 / sample / chatting")


if __name__ == "__main__":
    unittest.main()
