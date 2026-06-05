import unittest

from src.app_core import generate
from src.formatter import format_result
from src.loaders import load_conversation, load_target_profile, load_user_profile
from src.loaders import load_config
from src.models import GenerationRequest


CASES = [
    ("data/examples/sample_target_cafe_movie.yaml", "data/examples/sample_conversation_movie_reply.yaml"),
    ("data/examples/sample_target_cafe_movie.yaml", "data/examples/sample_conversation_cafe_reply.yaml"),
    ("data/examples/sample_target_drink_night.yaml", "data/examples/sample_conversation_drink_reply.yaml"),
    ("data/examples/sample_target_cafe_movie.yaml", "data/examples/sample_conversation_short_reply.yaml"),
    ("data/examples/sample_target_cafe_movie.yaml", "data/examples/sample_conversation_multi_topic_reply.yaml"),
]


def reply_result(target_path: str, history_path: str):
    history = load_conversation(history_path)
    request = GenerationRequest(
        target_profile=load_target_profile(target_path),
        user_profile=load_user_profile(),
        conversation_history=history,
        purpose="reply",
        current_stage="auto",
    )
    return history, generate(request)


class ReplyNaturalnessTest(unittest.TestCase):
    def test_replies_do_not_repeat_full_partner_message(self):
        for target_path, history_path in CASES:
            with self.subTest(history_path=history_path):
                history, result = reply_result(target_path, history_path)
                partner_text = history[-1].text
                for candidate in result.message_candidates:
                    self.assertNotIn(partner_text, candidate)

    def test_replies_have_at_most_one_question(self):
        for target_path, history_path in CASES:
            _, result = reply_result(target_path, history_path)
            for candidate in result.message_candidates:
                self.assertLessEqual(candidate.count("？") + candidate.count("?"), 1)

    def test_replies_do_not_guide_to_risky_places(self):
        banned = ["家に", "ホテル", "泊まり", "夜飲み", "飲みに行きましょう"]
        for target_path, history_path in CASES:
            _, result = reply_result(target_path, history_path)
            text = "\n".join(result.message_candidates)
            for phrase in banned:
                self.assertNotIn(phrase, text)

    def test_drink_reply_stays_on_food_and_does_not_invite(self):
        _, result = reply_result("data/examples/sample_target_drink_night.yaml", "data/examples/sample_conversation_drink_reply.yaml")
        text = "\n".join(result.message_candidates)

        self.assertIn("ご飯", text)
        self.assertNotIn("行きませんか", text)

    def test_safe_question_examples_are_reflected(self):
        _, movie = reply_result("data/examples/sample_target_cafe_movie.yaml", "data/examples/sample_conversation_movie_reply.yaml")
        _, cafe = reply_result("data/examples/sample_target_cafe_movie.yaml", "data/examples/sample_conversation_cafe_reply.yaml")

        self.assertTrue(any("最近見て面白かった作品はありますか？" in candidate for candidate in movie.message_candidates))
        self.assertTrue(any("最近よかったお店はありますか？" in candidate for candidate in cafe.message_candidates))

    def test_configured_acknowledgment_and_empathy_are_reflected(self):
        policy = load_config("reply_topic_policy.yaml")["topic_keywords"]
        _, movie = reply_result("data/examples/sample_target_cafe_movie.yaml", "data/examples/sample_conversation_movie_reply.yaml")
        _, cafe = reply_result("data/examples/sample_target_cafe_movie.yaml", "data/examples/sample_conversation_cafe_reply.yaml")

        self.assertTrue(any(policy["movie"]["acknowledgment_examples"][0] in candidate for candidate in movie.message_candidates))
        self.assertTrue(any(policy["movie"]["empathy_examples"][0] in candidate for candidate in movie.message_candidates))
        self.assertTrue(any(policy["cafe"]["acknowledgment_examples"][0] in candidate for candidate in cafe.message_candidates))
        self.assertTrue(any(policy["cafe"]["empathy_examples"][0] in candidate for candidate in cafe.message_candidates))

    def test_short_reply_uses_gentle_fallback(self):
        _, result = reply_result("data/examples/sample_target_cafe_movie.yaml", "data/examples/sample_conversation_short_reply.yaml")
        text = "\n".join(result.message_candidates)

        self.assertIn("いいですね", text)
        self.assertNotIn("はい、好きです", text)
        self.assertTrue(all(candidate.count("。") <= 2 for candidate in result.message_candidates))

    def test_multi_topic_reply_focuses_on_one_safe_topic(self):
        _, result = reply_result("data/examples/sample_target_cafe_movie.yaml", "data/examples/sample_conversation_multi_topic_reply.yaml")
        best = result.best_message

        self.assertIn("カフェ", best)
        self.assertLessEqual(best.count("？") + best.count("?"), 1)
        self.assertNotIn("映画とカフェと休日", best)

    def test_formatted_reply_contains_partner_temperature(self):
        _, result = reply_result("data/examples/sample_target_cafe_movie.yaml", "data/examples/sample_conversation_movie_reply.yaml")
        output = format_result(result)

        self.assertIn("【相手の温度感】", output)
        self.assertIn(result.partner_temperature, output)

    def test_very_good_reply_stays_safe(self):
        history = [
            *load_conversation("data/examples/sample_conversation_movie_reply.yaml")[:-1],
            type(load_conversation("data/examples/sample_conversation_movie_reply.yaml")[-1])(
                speaker="partner",
                text="いいですね！私も話していて楽しいです！また話したいです。",
            ),
        ]
        request = GenerationRequest(
            target_profile=load_target_profile("data/examples/sample_target_cafe_movie.yaml"),
            user_profile=load_user_profile(),
            conversation_history=history,
            purpose="reply",
            current_stage="auto",
        )
        result = generate(request)
        text = "\n".join(result.message_candidates)

        self.assertEqual("very_good", result.partner_temperature)
        for banned in ["家に", "ホテル", "泊まり", "夜飲み"]:
            self.assertNotIn(banned, text)

    def test_formatted_reply_contains_required_sections(self):
        for target_path, history_path in CASES:
            _, result = reply_result(target_path, history_path)
            output = format_result(result)

            self.assertIn("【安全チェック結果】", output)
            self.assertIn("【一番おすすめ】", output)


if __name__ == "__main__":
    unittest.main()
