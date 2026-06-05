import os
import tempfile
import unittest
from unittest.mock import patch

from main import build_parser, run
from src.conversation_memory import add_turn
from src.loaders import load_target_profile
from src.partner_manager import create_partner_from_target_profile
from src.partner_store import load_partner
from src.suggestion_manager import add_suggestion


class PartnerSuggestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATING_ASSISTANT_PARTNER_DIR": self.temp.name})
        self.env.start()
        self.parser = build_parser()
        create_partner_from_target_profile(load_target_profile("data/examples/sample_target_cafe_movie.yaml"), "sample", "demo")

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def call(self, command):
        return run(self.parser.parse_args(command.split()))

    def test_generation_adds_numbered_pending_suggestion_and_last_message(self):
        self.call("partner-generate-reply --partner-id partner_001")
        partner = load_partner("partner_001")
        self.assertEqual(partner.pending_suggestions[0].suggestion_id, "suggestion_001")
        self.assertEqual(partner.pending_suggestions[0].status, "pending")
        self.assertEqual(partner.pending_suggestions[0].text, partner.message_state.last_suggested_message)

    def test_mark_sent_updates_suggestion_and_conversation(self):
        partner = load_partner("partner_001")
        add_suggestion(partner, "reply", "送信候補です", "test")
        output = self.call("partner-mark-sent --partner-id partner_001 --suggestion-id suggestion_001")
        stored = load_partner("partner_001")
        self.assertIn("送信済みにしました", output)
        self.assertEqual(stored.pending_suggestions[0].status, "sent")
        self.assertEqual(stored.conversation[-1].speaker, "user")
        self.assertEqual(stored.conversation[-1].text, "送信候補です")

    def test_discard_and_direct_text_sent(self):
        partner = load_partner("partner_001")
        add_suggestion(partner, "reply", "使わない候補", "test")
        self.call("partner-discard-suggestion --partner-id partner_001 --suggestion-id suggestion_001")
        self.assertEqual(load_partner("partner_001").pending_suggestions[0].status, "discarded")
        self.call("partner-mark-sent --partner-id partner_001 --text 実際に送った文")
        stored = load_partner("partner_001")
        self.assertEqual(stored.conversation[-1].text, "実際に送った文")
        self.assertEqual(stored.message_state.last_user_message, "実際に送った文")

    def test_invite_generation_saves_suggestion_when_ready(self):
        partner = load_partner("partner_001")
        add_turn(partner, "partner", "カフェが好きです。")
        add_turn(partner, "user", "いいですね。")
        add_turn(partner, "partner", "休日に友達と行くことが多いです。")
        self.call("partner-generate-invite --partner-id partner_001")
        stored = load_partner("partner_001")
        self.assertEqual(stored.pending_suggestions[-1].purpose, "invite")
        self.assertEqual(stored.pending_suggestions[-1].status, "pending")


if __name__ == "__main__":
    unittest.main()
