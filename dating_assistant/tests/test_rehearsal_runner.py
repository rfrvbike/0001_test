import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from main import build_parser, run
from src.partner_store import list_partners, load_partner
from src.real_profile_manager import create_real_profile
from src.rehearsal_runner import run_real_profile_rehearsal


class RehearsalRunnerTests(unittest.TestCase):
    def setUp(self):
        self.real_temp = tempfile.TemporaryDirectory()
        self.partner_temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {
                "DATING_ASSISTANT_REAL_PROFILE_DIR": self.real_temp.name,
                "DATING_ASSISTANT_PARTNER_DIR": self.partner_temp.name,
            },
        )
        self.env.start()
        self.real_path, _ = create_real_profile(
            "rehearse_cafe_movie",
            "カフェ巡りと映画が好きです。",
            age=30,
            hobbies=["カフェ", "映画"],
            photos_memo=["落ち着いた雰囲気"],
        )
        self.parser = build_parser()

    def tearDown(self):
        self.env.stop()
        self.partner_temp.cleanup()
        self.real_temp.cleanup()

    def call(self, args):
        return run(self.parser.parse_args(args))

    def test_rehearsal_creates_partner_and_first_suggestion(self):
        output = run_real_profile_rehearsal("rehearse_cafe_movie", None, "sample", "pairs")
        self.assertIn("partner_id: partner_001", output)
        self.assertIn("【一番おすすめ】", output)
        self.assertIn("partner-mark-sent", output)
        partner = load_partner("partner_001")
        self.assertEqual(partner.status, "first_message_suggested")
        self.assertEqual(partner.pending_suggestions[0].suggestion_id, "suggestion_001")
        self.assertEqual(partner.message_state.next_action, "初回メッセージ候補を確認して送る")

    def test_rehearsal_accepts_path_and_save_output(self):
        output = self.call(
            [
                "real-profile-rehearse",
                "--path",
                str(self.real_path),
                "--display-name",
                "sample",
                "--app-name",
                "pairs",
                "--save-output",
            ]
        )
        self.assertIn("保存しました:", output)
        self.assertIn("outputs/local/real_profile_rehearse_", output)
        saved_relative = output.split("保存しました:\n", 1)[1].strip()
        (Path(__file__).parents[1] / saved_relative).unlink()

    def test_dry_run_does_not_save_partner(self):
        output = self.call(
            [
                "real-profile-rehearse",
                "--label",
                "rehearse_cafe_movie",
                "--display-name",
                "sample",
                "--app-name",
                "pairs",
                "--dry-run",
            ]
        )
        self.assertIn("dry-runのため pending_suggestions には保存していません", output)
        self.assertEqual(list_partners(), [])


if __name__ == "__main__":
    unittest.main()
