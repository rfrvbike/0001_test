import os
import tempfile
import unittest
from unittest.mock import patch

from src.loaders import load_target_profile
from src.real_profile_manager import (
    create_real_profile,
    detect_privacy_warnings,
    format_real_profile,
    list_real_profiles,
    load_real_profile,
    validate_real_profile_label,
)


class RealProfileManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATING_ASSISTANT_REAL_PROFILE_DIR": self.temp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_label_validation(self):
        for label in ["cafe_movie_001", "travel-active-2", "ABC123"]:
            validate_real_profile_label(label)
        for label in ["", "日本語", "has space", "path/name", "path\\name", "name:bad"]:
            with self.assertRaises(ValueError):
                validate_real_profile_label(label)

    def test_create_is_target_profile_compatible_and_listed(self):
        path, warnings = create_real_profile(
            "cafe_movie_001",
            "カフェと映画が好きです。\n休日に出かけます。",
            age=30,
            hobbies=["カフェ", "映画"],
            photos_memo=["落ち着いた雰囲気"],
            location_hint="東京",
            relationship_goal="ゆっくり仲良くなりたい",
            free_notes="初回から誘わない",
        )
        self.assertEqual(warnings, [])
        profile = load_target_profile(path)
        self.assertEqual(profile.name_or_label, "cafe_movie_001")
        self.assertEqual(profile.hobbies, ["カフェ", "映画"])
        self.assertIn("休日に出かけます。", profile.profile_text)
        listed = list_real_profiles()
        self.assertEqual(listed[0][1].name_or_label, "cafe_movie_001")

    def test_optional_empty_fields_load_safely_and_show_formats(self):
        create_real_profile("minimal_001", "プロフィール文")
        _, profile = load_real_profile(label="minimal_001")
        self.assertEqual(profile.hobbies, [])
        self.assertEqual(profile.photos_memo, [])
        output = format_real_profile(profile)
        self.assertIn("【実プロフィールYAML】", output)
        self.assertIn("【プロフィール文】", output)
        self.assertIn("プロフィール文", output)

    def test_existing_profile_is_not_overwritten(self):
        create_real_profile("same_001", "first")
        with self.assertRaises(FileExistsError):
            create_real_profile("same_001", "second")

    def test_privacy_warning_detection(self):
        warnings = detect_privacy_warnings(["LINEで連絡", "勤務先の話"])
        self.assertIn("LINE", warnings)
        self.assertIn("勤務先", warnings)


if __name__ == "__main__":
    unittest.main()
