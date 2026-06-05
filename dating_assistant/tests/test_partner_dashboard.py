import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from main import build_parser, run
from src.dashboard_builder import build_partner_dashboard, classify_partner
from src.models import MessageState, PartnerAnalysis, PartnerRecord, PendingSuggestion
from src.partner_store import partner_from_mapping, save_partner


def partner(partner_id: str, status: str = "chatting", state: MessageState | None = None, pending: bool = False):
    suggestions = [PendingSuggestion("suggestion_001", "reply", "text", "2026-06-05T10:00:00+09:00")] if pending else []
    return PartnerRecord(
        partner_id=partner_id,
        display_name=f"name-{partner_id}",
        app_name="demo",
        status=status,
        updated_at=f"2026-06-05T10:0{partner_id[-1]}:00+09:00",
        analysis=PartnerAnalysis(partner_temperature="good"),
        message_state=state or MessageState(),
        pending_suggestions=suggestions,
    )


class PartnerDashboardTests(unittest.TestCase):
    def setUp(self):
        self.partners = [
            partner("partner_001", state=MessageState(awaiting_user_action=True, last_received_at="2026-06-05T09:00:00+09:00", next_action="reply")),
            partner("partner_002", pending=True),
            partner("partner_003", state=MessageState(awaiting_partner_reply=True, last_sent_at="2026-06-05T08:00:00+09:00", next_action="wait")),
            partner("partner_004", status="invite_ready"),
            partner("partner_005", status="paused"),
            partner("partner_006", status="closed"),
            partner("partner_007"),
        ]

    def test_classification(self):
        self.assertEqual(classify_partner(self.partners[0]), "needs_action")
        self.assertEqual(classify_partner(self.partners[1]), "needs_action")
        self.assertEqual(classify_partner(self.partners[2]), "waiting")
        self.assertEqual(classify_partner(self.partners[3]), "invite_ready")
        self.assertEqual(classify_partner(self.partners[4]), "paused_or_closed")
        self.assertEqual(classify_partner(self.partners[5]), "paused_or_closed")
        self.assertEqual(classify_partner(self.partners[6]), "other")

    def test_dashboard_has_categories_and_partner_details(self):
        output = build_partner_dashboard(self.partners)
        for label in ["要対応:", "返信待ち:", "誘い検討:", "停止中/終了:"]:
            self.assertIn(label, output)
        self.assertIn("partner_001", output)
        self.assertIn("name-partner_001", output)
        self.assertIn("status: chatting", output)
        self.assertIn("次の行動: reply", output)

    def test_filters(self):
        active = build_partner_dashboard(self.partners, active_only=True)
        self.assertNotIn("partner_005", active)
        self.assertNotIn("partner_006", active)
        action = build_partner_dashboard(self.partners, needs_action=True)
        self.assertIn("partner_001", action)
        self.assertIn("partner_002", action)
        self.assertNotIn("partner_003", action)
        waiting = build_partner_dashboard(self.partners, waiting=True)
        self.assertIn("partner_003", waiting)
        self.assertNotIn("partner_001", waiting)
        status = build_partner_dashboard(self.partners, status="invite_ready")
        self.assertIn("partner_004", status)
        self.assertNotIn("partner_007", status)

    def test_sort_and_old_partner(self):
        output = build_partner_dashboard(self.partners, sort_key="updated")
        self.assertLess(output.index("partner_002"), output.index("partner_001"))
        same_category = [
            partner("partner_008"),
            partner("partner_009"),
        ]
        same_category[0].updated_at = "2026-06-05T09:00:00+09:00"
        same_category[1].updated_at = "2026-06-05T10:00:00+09:00"
        sorted_output = build_partner_dashboard(same_category, sort_key="updated")
        self.assertLess(sorted_output.index("partner_008"), sorted_output.index("partner_009"))
        waiting = [
            partner("partner_010", state=MessageState(awaiting_partner_reply=True, last_sent_at="2026-06-05T10:00:00+09:00")),
            partner("partner_011", state=MessageState(awaiting_partner_reply=True, last_sent_at="2026-06-05T09:00:00+09:00")),
        ]
        sent_output = build_partner_dashboard(waiting, sort_key="sent")
        self.assertLess(sent_output.index("partner_011"), sent_output.index("partner_010"))
        action = [
            partner("partner_012", state=MessageState(awaiting_user_action=True, last_received_at="2026-06-05T10:00:00+09:00")),
            partner("partner_013", state=MessageState(awaiting_user_action=True, last_received_at="2026-06-05T09:00:00+09:00")),
        ]
        received_output = build_partner_dashboard(action, sort_key="received")
        self.assertLess(received_output.index("partner_013"), received_output.index("partner_012"))
        old = partner_from_mapping({"partner_id": "partner_008", "display_name": "old"})
        self.assertIn("partner_008", build_partner_dashboard([old]))


class PartnerDashboardCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATING_ASSISTANT_PARTNER_DIR": self.temp.name})
        self.env.start()
        self.parser = build_parser()
        save_partner(partner("partner_001", state=MessageState(awaiting_user_action=True, next_action="reply")))

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def call(self, command):
        return run(self.parser.parse_args(command.split()))

    def test_cli_filters_and_save_output(self):
        self.assertIn("partner_001", self.call("partner-dashboard"))
        self.assertIn("要対応:", self.call("partner-dashboard --needs-action"))
        self.assertIn("返信待ち:", self.call("partner-dashboard --waiting"))
        self.assertIn("partner_001", self.call("partner-dashboard --active-only"))
        saved = self.call("partner-dashboard --save-output")
        self.assertIn("outputs/local/partner_dashboard_", saved)
        saved_relative = saved.split("保存しました:\n", 1)[1].strip()
        (Path(__file__).parents[1] / saved_relative).unlink()


if __name__ == "__main__":
    unittest.main()
