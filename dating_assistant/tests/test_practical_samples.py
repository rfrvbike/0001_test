import unittest

from src.app_core import generate
from src.formatter import format_result
from src.loaders import load_target_profile, load_user_profile
from src.models import GenerationRequest


SAMPLES = {
    "travel_active": "data/examples/sample_target_travel_active.yaml",
    "cafe_movie": "data/examples/sample_target_cafe_movie.yaml",
    "fashion_beauty": "data/examples/sample_target_fashion_beauty.yaml",
    "drink_night": "data/examples/sample_target_drink_night.yaml",
}


def generate_first(sample_path: str):
    request = GenerationRequest(
        target_profile=load_target_profile(sample_path),
        user_profile=load_user_profile(),
        current_stage="first_message",
    )
    result = generate(request)
    return result, format_result(result)


class PracticalSamplesTest(unittest.TestCase):
    def test_travel_is_not_treated_as_deep_common_topic(self):
        result, output = generate_first(SAMPLES["travel_active"])

        self.assertNotIn("旅行", result.compatibility_topics)
        self.assertIn("旅行", result.light_only_topics)
        self.assertIn("旅行", result.light_only_topics)
        self.assertIn("深掘りせず軽く扱います", output)

    def test_travel_sample_does_not_invite_to_travel(self):
        result, output = generate_first(SAMPLES["travel_active"])
        text = "\n".join(result.message_candidates + [output])

        self.assertNotIn("旅行行きましょう", text)
        self.assertNotIn("今度旅行", text)
        self.assertIn("今回は出さない", output)

    def test_cafe_movie_recommends_cafe_or_movie(self):
        result, _ = generate_first(SAMPLES["cafe_movie"])

        self.assertTrue({"カフェ", "映画"} & set(result.compatibility_topics))

    def test_fashion_beauty_does_not_only_praise_appearance(self):
        result, _ = generate_first(SAMPLES["fashion_beauty"])
        best = result.best_message

        self.assertNotIn("外見", best)
        self.assertNotEqual(best, "おしゃれですね")
        self.assertTrue("カフェ" in best or "休日" in best or "買い物" in best)

    def test_drink_night_does_not_invite_to_risky_places_or_late_drinks(self):
        result, output = generate_first(SAMPLES["drink_night"])
        text = "\n".join(result.message_candidates + [output])

        banned = ["夜飲み", "家", "ホテル", "泊まり", "飲みに行きましょう", "遅い時間"]
        for phrase in banned:
            self.assertNotIn(phrase, text)
        self.assertIn("今回は出さない", output)

    def test_all_generate_first_outputs_include_required_sections(self):
        for sample_path in SAMPLES.values():
            with self.subTest(sample_path=sample_path):
                _, output = generate_first(sample_path)

                self.assertIn("【安全チェック結果】", output)
                self.assertIn("【一番おすすめ】", output)


if __name__ == "__main__":
    unittest.main()
