import os
import tempfile
import unittest
from unittest.mock import patch

from main import build_parser, run
from src.models import PartnerRecord
from src.partner_store import load_partner, save_partner
from src.suggestion_manager import add_suggestion, discard_suggestion


class PartnerDisplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATING_ASSISTANT_PARTNER_DIR": self.temp.name})
        self.env.start()
        self.parser = build_parser()
        save_partner(PartnerRecord(partner_id="partner_001", display_name="sample", app_name="demo"))

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def call(self, command):
        return run(self.parser.parse_args(command.split()))

    def test_list_has_next_action_and_pending_count(self):
        partner = load_partner("partner_001")
        add_suggestion(partner, "reply", "候補", "test")
        output = self.call("partner-list")
        self.assertIn("次の行動", output)
        self.assertIn("未送信候補: 1件", output)

    def test_show_has_operational_sections_and_hides_discarded(self):
        partner = load_partner("partner_001")
        add_suggestion(partner, "reply", "表示する候補", "test")
        add_suggestion(partner, "reply", "破棄する候補", "test")
        discard_suggestion(partner, "suggestion_002")
        output = self.call("partner-show --partner-id partner_001")
        self.assertIn("【現在の状態】", output)
        self.assertIn("【未送信候補】", output)
        self.assertIn("【最近の会話】", output)
        self.assertIn("表示する候補", output)
        pending_section = output.split("【未送信候補】", 1)[1].split("【最後に生成した候補】", 1)[0]
        self.assertNotIn("破棄する候補", pending_section)


if __name__ == "__main__":
    unittest.main()
