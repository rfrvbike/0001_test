import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.models import PartnerRecord
from src.partner_store import get_skipped_partner_files, list_partners, save_partner


class PartnerStoreResilienceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATING_ASSISTANT_PARTNER_DIR": self.temp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def _write_file(self, name: str, content: str) -> Path:
        path = Path(self.temp.name) / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_corrupt_json_does_not_crash_list_partners(self):
        save_partner(PartnerRecord(partner_id="partner_001", display_name="正常"))
        self._write_file("partner_002.yaml", "{ this is not valid json !!!")

        partners = list_partners()

        self.assertEqual(len(partners), 1)
        self.assertEqual(partners[0].partner_id, "partner_001")

    def test_corrupt_file_is_reported_in_skipped_list(self):
        save_partner(PartnerRecord(partner_id="partner_001", display_name="正常"))
        self._write_file("partner_002.yaml", "{ this is not valid json !!!")

        list_partners()
        skipped = get_skipped_partner_files()

        self.assertIn("partner_002.yaml", skipped)
        self.assertNotIn("partner_001.yaml", skipped)

    def test_partner_without_id_field_does_not_crash_list_partners(self):
        self._write_file(
            "partner_001.yaml",
            json.dumps({"display_name": "IDなし", "status": "new_profile"}, ensure_ascii=False),
        )

        partners = list_partners()
        skipped = get_skipped_partner_files()

        self.assertEqual(len(partners), 0)
        self.assertIn("partner_001.yaml", skipped)

    def test_multiple_corrupt_files_all_skipped_valid_ones_returned(self):
        save_partner(PartnerRecord(partner_id="partner_001", display_name="正常1"))
        save_partner(PartnerRecord(partner_id="partner_003", display_name="正常2"))
        self._write_file("partner_002.yaml", "not json at all")
        self._write_file("partner_004.yaml", json.dumps({}))

        partners = list_partners()
        skipped = get_skipped_partner_files()

        self.assertEqual({p.partner_id for p in partners}, {"partner_001", "partner_003"})
        self.assertIn("partner_002.yaml", skipped)
        self.assertIn("partner_004.yaml", skipped)

    def test_empty_file_does_not_crash_list_partners(self):
        save_partner(PartnerRecord(partner_id="partner_001", display_name="正常"))
        self._write_file("partner_002.yaml", "")

        partners = list_partners()

        self.assertEqual(len(partners), 1)
        self.assertEqual(partners[0].partner_id, "partner_001")

    def test_skipped_list_resets_on_each_list_partners_call(self):
        self._write_file("partner_001.yaml", "bad json")
        list_partners()
        self.assertIn("partner_001.yaml", get_skipped_partner_files())

        # 破損ファイルを削除して再度呼ぶとスキップリストがリセットされること
        (Path(self.temp.name) / "partner_001.yaml").unlink()
        save_partner(PartnerRecord(partner_id="partner_002", display_name="正常"))
        list_partners()
        self.assertEqual(get_skipped_partner_files(), [])


if __name__ == "__main__":
    unittest.main()
