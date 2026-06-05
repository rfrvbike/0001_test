import os
import tempfile
import unittest
from unittest.mock import patch

from main import build_parser, run
from src.partner_store import load_partner


class RealProfileCommandTests(unittest.TestCase):
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
        self.parser = build_parser()

    def tearDown(self):
        self.env.stop()
        self.partner_temp.cleanup()
        self.real_temp.cleanup()

    def call(self, args):
        return run(self.parser.parse_args(args))

    def test_create_list_show_and_partner_create(self):
        created = self.call(
            [
                "real-profile-create",
                "--label",
                "cafe_movie_001",
                "--age",
                "30",
                "--profile-text",
                "カフェと映画が好きです。",
                "--hobby",
                "カフェ",
                "--hobby",
                "映画",
                "--photo-memo",
                "落ち着いた雰囲気",
            ]
        )
        self.assertIn("実プロフィールYAMLを作成しました", created)
        self.assertIn("partner-create", created)
        self.assertIn("cafe_movie_001", self.call(["real-profile-list"]))
        shown = self.call(["real-profile-show", "--label", "cafe_movie_001"])
        self.assertIn("カフェと映画が好きです。", shown)
        self.assertIn("- カフェ", shown)
        source = os.path.join(self.real_temp.name, "cafe_movie_001.yaml")
        shown_by_path = self.call(["real-profile-show", "--path", source])
        self.assertIn("label: cafe_movie_001", shown_by_path)
        partner_output = self.call(
            ["partner-create", "--source", source, "--display-name", "sample", "--app-name", "demo"]
        )
        self.assertIn("partner_001", partner_output)
        self.assertEqual(load_partner("partner_001").profile.hobbies, ["カフェ", "映画"])

    def test_create_prints_privacy_warning(self):
        output = self.call(
            ["real-profile-create", "--label", "warning_001", "--profile-text", "LINE IDは保存しない"]
        )
        self.assertIn("注意:", output)
        self.assertIn("LINE", output)


if __name__ == "__main__":
    unittest.main()
