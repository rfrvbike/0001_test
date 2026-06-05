import os
import tempfile
import unittest
from unittest.mock import patch

from main import build_parser, run
from src.conversation_memory import add_turn
from src.partner_manager import create_partner_from_target_profile
from src.partner_store import get_partner_dir, load_partner
from src.loaders import load_target_profile


class PartnerGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATING_ASSISTANT_PARTNER_DIR": self.temp.name})
        self.env.start()
        self.parser = build_parser()
        self.partner = create_partner_from_target_profile(
            load_target_profile("data/examples/sample_target_cafe_movie.yaml"), "sample", "demo"
        )

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def call(self, command):
        return run(self.parser.parse_args(command.split()))

    def test_first_generation_has_sections_and_updates_analysis(self):
        output = self.call("partner-generate-first --partner-id partner_001")
        self.assertIn("【一番おすすめ】", output)
        self.assertIn("【安全チェック結果】", output)
        stored = load_partner("partner_001")
        self.assertTrue(stored.analysis.last_suggested_message)
        self.assertEqual(stored.pending_suggestions[0].purpose, "first")
        self.assertEqual(stored.status, "first_message_suggested")

    def test_reply_uses_history_and_updates_last_suggestion(self):
        add_turn(self.partner, "partner", "最近は映画をよく見ます")
        output = self.call("partner-generate-reply --partner-id partner_001")
        self.assertIn("映画", output)
        self.assertIn("【相手の温度感】", output)
        self.assertTrue(load_partner("partner_001").analysis.last_suggested_message)

    def test_partner_directory_is_overridden(self):
        self.assertEqual(get_partner_dir(), __import__("pathlib").Path(self.temp.name))


if __name__ == "__main__":
    unittest.main()
