import os
import tempfile
import unittest
from unittest.mock import patch

from main import build_parser, run
from src.partner_store import load_partner


class PartnerActivityLogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATING_ASSISTANT_PARTNER_DIR": self.temp.name})
        self.env.start()
        self.parser = build_parser()
        self.call("partner-create --source data/examples/sample_target_cafe_movie.yaml --display-name sample --app-name demo")

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def call(self, command):
        return run(self.parser.parse_args(command.split()))

    def event_types(self):
        return [event.event_type for event in load_partner("partner_001").activity_log]

    def test_operations_record_activity_with_unique_ids(self):
        self.assertIn("partner_created", self.event_types())
        self.call("partner-add-turn --partner-id partner_001 --speaker partner --text hello")
        self.assertIn("turn_added", self.event_types())
        self.call("partner-generate-reply --partner-id partner_001")
        self.assertIn("suggestion_created", self.event_types())
        self.call("partner-mark-sent --partner-id partner_001 --suggestion-id suggestion_001")
        self.assertIn("suggestion_sent", self.event_types())
        self.call("partner-generate-reply --partner-id partner_001")
        self.call("partner-discard-suggestion --partner-id partner_001 --suggestion-id suggestion_002")
        self.assertIn("suggestion_discarded", self.event_types())
        self.call("partner-update-status --partner-id partner_001 --status warm_chat")
        self.assertIn("status_updated", self.event_types())
        self.call("partner-note --partner-id partner_001 --text memo")
        partner = load_partner("partner_001")
        self.assertIn("note_added", [event.event_type for event in partner.activity_log])
        ids = [event.event_id for event in partner.activity_log]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(partner.notes[-1].created_at)

    def test_timeline_cli_and_limit(self):
        self.call("partner-add-turn --partner-id partner_001 --speaker partner --text hello")
        output = self.call("partner-timeline --partner-id partner_001 --limit 1")
        self.assertIn("【タイムライン】", output)
        self.assertIn("【履歴】", output)
        self.assertEqual(len(output.split("【履歴】\n", 1)[1].splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
