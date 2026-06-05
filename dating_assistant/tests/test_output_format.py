from src.app_core import generate
from src.formatter import format_result
from src.loaders import load_target_profile, load_user_profile
from src.models import GenerationRequest
import unittest


class OutputFormatTest(unittest.TestCase):
    def test_required_output_sections_are_present(self):
        request = GenerationRequest(
            target_profile=load_target_profile("data/examples/sample_target_profile.yaml"),
            user_profile=load_user_profile(),
            current_stage="first_message",
        )

        output = format_result(generate(request))

        self.assertIn("【相手の印象】", output)
        self.assertIn("【一番おすすめ】", output)
        self.assertIn("【安全チェック結果】", output)

    def test_best_message_is_not_empty(self):
        request = GenerationRequest(
            target_profile=load_target_profile("data/examples/sample_target_profile.yaml"),
            user_profile=load_user_profile(),
        )

        result = generate(request)

        self.assertTrue(result.best_message)
        self.assertTrue(result.safety_notes)


if __name__ == "__main__":
    unittest.main()
