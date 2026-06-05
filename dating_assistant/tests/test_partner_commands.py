import os
import tempfile
import unittest
from unittest.mock import patch

from main import build_parser, run


class PartnerCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATING_ASSISTANT_PARTNER_DIR": self.temp.name})
        self.env.start()
        self.parser = build_parser()
        self.source = "data/examples/sample_target_cafe_movie.yaml"

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def call(self, command):
        return run(self.parser.parse_args(command.split()))

    def test_create_list_show_and_add_turn(self):
        created = self.call(f"partner-create --source {self.source} --display-name sample --app-name demo")
        self.assertIn("partner_001", created)
        self.assertIn("sample", self.call("partner-list"))
        self.assertIn("display_name: sample", self.call("partner-show --partner-id partner_001"))
        added = self.call("partner-add-turn --partner-id partner_001 --speaker partner --text hello")
        self.assertIn("会話を追加しました", added)
        self.assertIn("hello", self.call("partner-show --partner-id partner_001"))

    def test_invalid_speaker_is_rejected(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args("partner-add-turn --partner-id partner_001 --speaker invalid --text hello".split())


if __name__ == "__main__":
    unittest.main()
