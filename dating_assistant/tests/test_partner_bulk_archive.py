import os
import tempfile
import unittest
from unittest.mock import patch

from main import build_parser, run
from src.bulk_partner_actions import bulk_archive_partners, find_partners_for_bulk_archive
from src.dashboard_builder import build_partner_dashboard
from src.models import MessageState, PartnerRecord
from src.partner_store import load_partner, save_partner


def sample_partner(partner_id, display_name, status="chatting"):
    return PartnerRecord(
        partner_id=partner_id,
        display_name=display_name,
        app_name="pairs",
        status=status,
        updated_at="2026-06-06T10:00:00+09:00",
        message_state=MessageState(awaiting_user_action=True, next_action="返信候補を確認する"),
    )


class PartnerBulkArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATING_ASSISTANT_PARTNER_DIR": self.temp.name})
        self.env.start()
        self.parser = build_parser()
        save_partner(sample_partner("partner_001", "運用テスト: カフェ映画の人", "chatting"))
        save_partner(sample_partner("partner_002", "運用テスト: 旅行好きの人", "paused"))
        save_partner(sample_partner("partner_003", "通常サンプル", "chatting"))
        save_partner(sample_partner("partner_004", "運用テスト: 既存archive", "archived"))

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def call(self, args):
        return run(self.parser.parse_args(args))

    def test_find_by_contains_excludes_archived_by_default(self):
        partners = find_partners_for_bulk_archive(contains="運用テスト")
        self.assertEqual(["partner_001", "partner_002"], [partner.partner_id for partner in partners])

    def test_find_by_status(self):
        partners = find_partners_for_bulk_archive(status="paused")
        self.assertEqual(["partner_002"], [partner.partner_id for partner in partners])

    def test_find_by_multiple_partner_ids(self):
        partners = find_partners_for_bulk_archive(partner_ids=["partner_001", "partner_003"])
        self.assertEqual(["partner_001", "partner_003"], [partner.partner_id for partner in partners])

    def test_include_archived_can_show_already_archived_partners(self):
        partners = find_partners_for_bulk_archive(contains="運用テスト", include_archived=True)
        self.assertIn("partner_004", [partner.partner_id for partner in partners])

    def test_dry_run_cli_does_not_change_partner_yaml(self):
        output = self.call(["partner-bulk-archive", "--contains", "運用テスト", "--dry-run"])
        self.assertIn("dry-run", output)
        self.assertIn("partner_001", output)
        self.assertEqual(load_partner("partner_001").status, "chatting")
        self.assertEqual(load_partner("partner_001").activity_log, [])

    def test_apply_archives_partners_and_records_activity_log(self):
        output = self.call(
            [
                "partner-bulk-archive",
                "--partner-id",
                "partner_001",
                "--apply",
                "--reason",
                "作業No.31 検証用partner整理",
            ]
        )
        archived = load_partner("partner_001")
        self.assertIn("更新件数: 1", output)
        self.assertEqual(archived.status, "archived")
        self.assertEqual(archived.message_state.next_action, "アーカイブ済み")
        self.assertFalse(archived.message_state.awaiting_user_action)
        self.assertIn("partner_bulk_archived", [event.event_type for event in archived.activity_log])
        self.assertTrue(any("作業No.31" in event.summary for event in archived.activity_log))

    def test_already_archived_partner_is_skipped_on_apply(self):
        result = bulk_archive_partners([load_partner("partner_004")], reason="test")
        self.assertEqual(result.archived, [])
        self.assertEqual(len(result.skipped), 1)
        self.assertEqual(load_partner("partner_004").activity_log, [])

    def test_apply_without_filter_is_blocked(self):
        with self.assertRaises(ValueError):
            self.call(["partner-bulk-archive", "--apply"])

    def test_dashboard_filters_still_work_after_bulk_archive(self):
        self.call(["partner-bulk-archive", "--partner-id", "partner_001", "--apply"])
        partners = [load_partner("partner_001"), load_partner("partner_002")]

        default = build_partner_dashboard(partners)
        self.assertNotIn("partner_001", default)
        self.assertIn("partner_002", default)

        included = build_partner_dashboard(partners, include_archived=True)
        self.assertIn("partner_001", included)
        only = build_partner_dashboard(partners, archived_only=True)
        self.assertIn("partner_001", only)
        self.assertNotIn("partner_002", only)


if __name__ == "__main__":
    unittest.main()

