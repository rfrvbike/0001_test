import os
import tempfile
import unittest
from unittest.mock import patch

from main import build_parser, run
from src.dashboard_builder import build_partner_dashboard
from src.models import MessageState, PartnerRecord, PendingSuggestion
from src.partner_manager import archive_partner, unarchive_partner
from src.partner_store import load_partner, partner_from_mapping, save_partner


def sample_partner(partner_id="partner_001", status="chatting"):
    return PartnerRecord(
        partner_id=partner_id,
        display_name="sample",
        app_name="pairs",
        status=status,
        updated_at="2026-06-06T10:00:00+09:00",
        message_state=MessageState(awaiting_user_action=True, next_action="返信候補を確認して送る"),
        pending_suggestions=[
            PendingSuggestion("suggestion_001", "reply", "返信候補", "2026-06-06T10:01:00+09:00")
        ],
    )


class PartnerArchiveUnitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATING_ASSISTANT_PARTNER_DIR": self.temp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_archive_sets_status_next_action_and_activity_log(self):
        partner = sample_partner()
        archive_partner(partner, "検証用データ整理")

        self.assertEqual(partner.status, "archived")
        self.assertEqual(partner.message_state.next_action, "アーカイブ済み")
        self.assertFalse(partner.message_state.awaiting_user_action)
        self.assertFalse(partner.message_state.awaiting_partner_reply)
        self.assertIn("アーカイブ理由: 検証用データ整理", [note.text for note in partner.notes])
        self.assertIn("partner_archived", [event.event_type for event in partner.activity_log])
        self.assertTrue(any("検証用データ整理" in event.summary for event in partner.activity_log))

    def test_unarchive_restores_allowed_status_and_activity_log(self):
        partner = sample_partner(status="archived")
        unarchive_partner(partner, "warm_chat")

        self.assertEqual(partner.status, "warm_chat")
        self.assertEqual(partner.message_state.next_action, "アーカイブ解除済み")
        self.assertIn("partner_unarchived", [event.event_type for event in partner.activity_log])

    def test_dashboard_default_excludes_archived_and_flags_can_show_it(self):
        active = sample_partner("partner_001")
        archived = sample_partner("partner_002", status="archived")

        default = build_partner_dashboard([active, archived])
        self.assertIn("partner_001", default)
        self.assertNotIn("partner_002", default)

        included = build_partner_dashboard([active, archived], include_archived=True)
        self.assertIn("アーカイブ済み:", included)
        self.assertIn("partner_002", included)

        only = build_partner_dashboard([active, archived], archived_only=True)
        self.assertIn("アーカイブ済み:", only)
        self.assertIn("partner_002", only)
        self.assertNotIn("partner_001", only)

    def test_old_partner_yaml_without_message_state_still_loads(self):
        partner = partner_from_mapping({"partner_id": "partner_009", "display_name": "old", "status": "archived"})
        self.assertEqual(partner.status, "archived")
        self.assertEqual(partner.message_state.next_action, "")


class PartnerArchiveCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATING_ASSISTANT_PARTNER_DIR": self.temp.name})
        self.env.start()
        self.parser = build_parser()
        save_partner(sample_partner())

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def call(self, command):
        return run(self.parser.parse_args(command.split()))

    def test_archive_unarchive_cli_and_displays(self):
        archive_output = self.call("partner-archive --partner-id partner_001 --reason test")
        self.assertIn("partnerをアーカイブしました", archive_output)
        self.assertIn("status: archived", archive_output)
        self.assertIn("reason: test", archive_output)

        archived = load_partner("partner_001")
        self.assertEqual(archived.status, "archived")
        self.assertEqual(archived.message_state.next_action, "アーカイブ済み")

        default_dashboard = self.call("partner-dashboard")
        self.assertNotIn("partner_001", default_dashboard)
        include_dashboard = self.call("partner-dashboard --include-archived")
        self.assertIn("アーカイブ済み:", include_dashboard)
        self.assertIn("partner_001", include_dashboard)
        only_dashboard = self.call("partner-dashboard --archived-only")
        self.assertIn("partner_001", only_dashboard)

        show = self.call("partner-show --partner-id partner_001")
        self.assertIn("【アーカイブ】", show)
        self.assertIn("通常dashboardには表示されません", show)

        timeline = self.call("partner-timeline --partner-id partner_001 --limit all")
        self.assertIn("partnerをアーカイブ: test", timeline)

        unarchive_output = self.call("partner-unarchive --partner-id partner_001 --status paused")
        self.assertIn("partnerのアーカイブを解除しました", unarchive_output)
        self.assertIn("status: paused", unarchive_output)
        self.assertEqual(load_partner("partner_001").status, "paused")


if __name__ == "__main__":
    unittest.main()
