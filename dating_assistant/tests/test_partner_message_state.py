import os
import tempfile
import unittest
from unittest.mock import patch

from src.conversation_memory import add_turn
from src.models import PartnerRecord
from src.partner_store import load_partner, save_partner


class PartnerMessageStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATING_ASSISTANT_PARTNER_DIR": self.temp.name})
        self.env.start()
        save_partner(PartnerRecord(partner_id="partner_001", display_name="sample"))

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_partner_turn_updates_received_state(self):
        partner = load_partner("partner_001")
        add_turn(partner, "partner", "相手からの返信")
        state = load_partner("partner_001").message_state
        self.assertEqual(state.last_partner_message, "相手からの返信")
        self.assertTrue(state.last_received_at)
        self.assertTrue(state.awaiting_user_action)
        self.assertFalse(state.awaiting_partner_reply)
        self.assertEqual(state.next_action, "返信候補を生成する")

    def test_user_turn_updates_sent_state(self):
        partner = load_partner("partner_001")
        add_turn(partner, "user", "自分が送った文")
        state = load_partner("partner_001").message_state
        self.assertEqual(state.last_user_message, "自分が送った文")
        self.assertTrue(state.last_sent_at)
        self.assertFalse(state.awaiting_user_action)
        self.assertTrue(state.awaiting_partner_reply)
        self.assertEqual(state.next_action, "相手の返信待ち")


if __name__ == "__main__":
    unittest.main()
