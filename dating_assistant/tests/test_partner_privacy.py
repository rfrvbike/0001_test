import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class PartnerPrivacyTests(unittest.TestCase):
    def test_readme_has_partner_privacy_warnings(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for warning in ["本名", "勤務先", "学校名", "SNS ID", "LINE ID", "最寄り駅", "スクリーンショット画像そのもの"]:
            self.assertIn(warning, text)

    def test_sample_has_no_obvious_personal_information(self):
        text = (ROOT / "data" / "examples" / "sample_partner_cafe_movie.yaml").read_text(encoding="utf-8")
        for forbidden in ["@", "LINE ID:", "勤務先:", "学校名:", "最寄り駅:"]:
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
