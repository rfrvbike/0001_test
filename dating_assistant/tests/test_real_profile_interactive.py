import os
import tempfile
import unittest
from unittest.mock import patch

from main import build_parser, run
from src.real_profile_manager import (
    build_real_profile_preview,
    list_real_profiles,
    prompt_list,
    prompt_multiline,
    run_interactive_real_profile_create,
)


class RealProfileInteractiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATING_ASSISTANT_REAL_PROFILE_DIR": self.temp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_prompt_multiline_and_list(self):
        lines = iter(["1行目", "2行目", ""])
        output = []
        self.assertEqual(prompt_multiline("プロフィール文", lambda _: next(lines), output.append), "1行目\n2行目")
        items = iter(["カフェ", "映画", ""])
        self.assertEqual(prompt_list("趣味", lambda _: next(items), output.append), ["カフェ", "映画"])

    def test_preview_contains_core_fields(self):
        preview = build_real_profile_preview(
            "cafe_movie_001",
            30,
            "プロフィール文",
            ["カフェ"],
            ["写真メモ"],
            "東京",
            "ゆっくり",
            "補足",
        )
        for text in ["cafe_movie_001", "プロフィール文", "- カフェ", "- 写真メモ", "東京", "補足"]:
            self.assertIn(text, preview)

    def test_interactive_saves_only_when_confirmed_yes(self):
        inputs = iter(
            [
                "cafe_movie_001",
                "30",
                "カフェ巡りが好きです。",
                "",
                "カフェ",
                "映画",
                "",
                "落ち着いた雰囲気",
                "",
                "東京",
                "ゆっくり仲良くなりたい",
                "初回は誘わない",
                "",
                "y",
            ]
        )
        output = run_interactive_real_profile_create(input_func=lambda _: next(inputs), output_func=lambda _: None)
        self.assertIn("実プロフィールYAMLを作成しました", output)
        self.assertEqual(list_real_profiles()[0][1].name_or_label, "cafe_movie_001")

    def test_interactive_cancels_on_no_or_empty_confirmation(self):
        base_inputs = [
            "cancel_001",
            "",
            "プロフィール文",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        inputs = iter(base_inputs + ["n"])
        output = run_interactive_real_profile_create(input_func=lambda _: next(inputs), output_func=lambda _: None)
        self.assertEqual(output, "保存をキャンセルしました。")
        self.assertEqual(list_real_profiles(), [])
        inputs = iter(base_inputs + [""])
        output = run_interactive_real_profile_create(input_func=lambda _: next(inputs), output_func=lambda _: None)
        self.assertEqual(output, "保存をキャンセルしました。")

    def test_interactive_detects_warning_and_rejects_empty_profile_text(self):
        inputs = iter(["warning_001", "", "LINEを交換", "", "", "", "", "", "", "y"])
        messages = []
        output = run_interactive_real_profile_create(input_func=lambda _: next(inputs), output_func=messages.append)
        self.assertIn("実プロフィールYAMLを作成しました", output)
        self.assertTrue(any("LINE" in message for message in messages))
        inputs = iter(["empty_001", "", "", "", "", "", ""])
        output = run_interactive_real_profile_create(input_func=lambda _: next(inputs), output_func=lambda _: None)
        self.assertEqual(output, "プロフィール文が空のため保存しませんでした。")

    def test_interactive_reprompts_invalid_label_and_age(self):
        inputs = iter(
            [
                "bad label",
                "good_label",
                "abc",
                "31",
                "プロフィール文",
                "",
                "",
                "",
                "",
                "",
                "",
                "y",
            ]
        )
        output = run_interactive_real_profile_create(input_func=lambda _: next(inputs), output_func=lambda _: None)
        self.assertIn("good_label.yaml", output)

    def test_existing_argument_mode_still_works(self):
        parser = build_parser()
        output = run(
            parser.parse_args(
                [
                    "real-profile-create",
                    "--label",
                    "arg_mode_001",
                    "--profile-text",
                    "カフェが好きです。",
                    "--hobby",
                    "カフェ",
                ]
            )
        )
        self.assertIn("arg_mode_001.yaml", output)


if __name__ == "__main__":
    unittest.main()
