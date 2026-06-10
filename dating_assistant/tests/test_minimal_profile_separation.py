import os
import tempfile
import unittest
from unittest.mock import patch

from gui_helpers import (
    PROFILE_MINIMAL_TEXT,
    PROFILE_PHOTO_ONLY_TEXT,
    ensure_conversation_partner_for_profile,
    load_partner_choices,
    save_real_profile_from_form,
)
from src.partner_store import load_partner


class MinimalProfileSeparationTests(unittest.TestCase):
    def setUp(self):
        self.temp_partners = tempfile.TemporaryDirectory()
        self.temp_profiles = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {
                "DATING_ASSISTANT_PARTNER_DIR": self.temp_partners.name,
                "DATING_ASSISTANT_REAL_PROFILE_DIR": self.temp_profiles.name,
            },
        )
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp_partners.cleanup()
        self.temp_profiles.cleanup()

    def _save_minimal_profile(self, label: str, display_name: str = "") -> None:
        save_real_profile_from_form({
            "label": label,
            "display_name": display_name,
            "profile_text": "",
            "photo_memo": "",
        })

    def _save_photo_only_profile(self, label: str, display_name: str = "") -> None:
        save_real_profile_from_form({
            "label": label,
            "display_name": display_name,
            "profile_text": "",
            "photo_memo": "明るい雰囲気",
        })

    def test_two_minimal_profiles_create_separate_partner_ids(self):
        self._save_minimal_profile("profile_person_a", display_name="人物A")
        self._save_minimal_profile("profile_person_b", display_name="人物B")

        result_a = ensure_conversation_partner_for_profile("profile_person_a")
        result_b = ensure_conversation_partner_for_profile("profile_person_b")

        self.assertTrue(result_a["created"])
        self.assertTrue(result_b["created"])
        self.assertNotEqual(result_a["partner_id"], result_b["partner_id"])

    def test_same_label_reuses_existing_partner(self):
        self._save_minimal_profile("profile_person_a")

        first = ensure_conversation_partner_for_profile("profile_person_a")
        second = ensure_conversation_partner_for_profile("profile_person_a")

        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertTrue(second["duplicate_prevented"])
        self.assertEqual(first["partner_id"], second["partner_id"])

    def test_minimal_profiles_normalized_to_same_text_but_separate_partners(self):
        self._save_minimal_profile("profile_person_a", display_name="人物A")
        self._save_minimal_profile("profile_person_b", display_name="人物B")

        result_a = ensure_conversation_partner_for_profile("profile_person_a")
        result_b = ensure_conversation_partner_for_profile("profile_person_b")
        partner_a = load_partner(result_a["partner_id"])
        partner_b = load_partner(result_b["partner_id"])

        # 両方のprofile_textは同じプレースホルダーに正規化されるが
        self.assertEqual(partner_a.profile.profile_text, PROFILE_MINIMAL_TEXT)
        self.assertEqual(partner_b.profile.profile_text, PROFILE_MINIMAL_TEXT)
        # partner_idは別々であること
        self.assertNotEqual(partner_a.partner_id, partner_b.partner_id)

    def test_photo_only_profiles_normalized_to_same_text_but_separate_partners(self):
        self._save_photo_only_profile("profile_person_c", display_name="人物C")
        self._save_photo_only_profile("profile_person_d", display_name="人物D")

        result_c = ensure_conversation_partner_for_profile("profile_person_c")
        result_d = ensure_conversation_partner_for_profile("profile_person_d")
        partner_c = load_partner(result_c["partner_id"])
        partner_d = load_partner(result_d["partner_id"])

        self.assertEqual(partner_c.profile.profile_text, PROFILE_PHOTO_ONLY_TEXT)
        self.assertEqual(partner_d.profile.profile_text, PROFILE_PHOTO_ONLY_TEXT)
        self.assertNotEqual(partner_c.partner_id, partner_d.partner_id)

    def test_minimal_profile_partner_has_no_data_from_other_profile(self):
        self._save_minimal_profile("profile_person_a")
        self._save_minimal_profile("profile_person_b")

        # display_nameを明示的に渡してパートナーを作成
        result_a = ensure_conversation_partner_for_profile("profile_person_a", display_name="人物A")
        result_b = ensure_conversation_partner_for_profile("profile_person_b", display_name="人物B")
        partner_a = load_partner(result_a["partner_id"])
        partner_b = load_partner(result_b["partner_id"])

        # 表示名が各指定のものであること
        self.assertEqual(partner_a.display_name, "人物A")
        self.assertEqual(partner_b.display_name, "人物B")
        # 会話履歴・候補・送信記録が相互混入しないこと
        self.assertEqual(partner_a.conversation, [])
        self.assertEqual(partner_b.conversation, [])
        self.assertEqual(partner_a.pending_suggestions, [])
        self.assertEqual(partner_b.pending_suggestions, [])
        self.assertEqual(partner_a.sent_records, [])
        self.assertEqual(partner_b.sent_records, [])

    def test_two_minimal_profiles_appear_as_separate_choices(self):
        self._save_minimal_profile("profile_person_a", display_name="人物A")
        self._save_minimal_profile("profile_person_b", display_name="人物B")

        ensure_conversation_partner_for_profile("profile_person_a")
        ensure_conversation_partner_for_profile("profile_person_b")

        choices = load_partner_choices()
        partner_ids = [c.partner_id for c in choices]
        self.assertEqual(len(partner_ids), 2)
        self.assertEqual(len(set(partner_ids)), 2)


if __name__ == "__main__":
    unittest.main()
