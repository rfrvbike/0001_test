import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.models import PartnerRecord
from src.partner_store import generate_next_partner_id, list_partners, load_partner, load_partner_file, partner_exists, save_partner


class PartnerStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATING_ASSISTANT_PARTNER_DIR": self.temp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_ids_save_load_list_and_exists(self):
        self.assertEqual(generate_next_partner_id(), "partner_001")
        record = PartnerRecord(partner_id="partner_001", display_name="sample")
        save_partner(record, allow_overwrite=False)
        self.assertTrue(partner_exists("partner_001"))
        self.assertEqual(load_partner("partner_001").display_name, "sample")
        self.assertEqual([p.partner_id for p in list_partners()], ["partner_001"])
        self.assertEqual(generate_next_partner_id(), "partner_002")

    def test_create_does_not_overwrite_same_id(self):
        record = PartnerRecord(partner_id="partner_001", display_name="first")
        save_partner(record)
        with self.assertRaises(FileExistsError):
            save_partner(PartnerRecord(partner_id="partner_001", display_name="second"))
        self.assertEqual(load_partner("partner_001").display_name, "first")

    def test_sample_partner_loads(self):
        sample = Path(__file__).parents[1] / "data" / "examples" / "sample_partner_cafe_movie.yaml"
        partner = load_partner_file(sample)
        self.assertEqual(partner.partner_id, "partner_001")
        self.assertTrue(partner.profile.hobbies)

    def test_old_partner_defaults_new_state_fields(self):
        record = PartnerRecord(partner_id="partner_001", display_name="old")
        save_partner(record)
        loaded = load_partner("partner_001")
        self.assertEqual(loaded.pending_suggestions, [])
        self.assertEqual(loaded.activity_log, [])
        self.assertEqual(loaded.message_state.last_user_message, "")
        self.assertFalse(loaded.message_state.awaiting_user_action)


if __name__ == "__main__":
    unittest.main()
