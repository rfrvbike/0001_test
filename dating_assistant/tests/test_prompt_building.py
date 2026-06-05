from src.loaders import load_config
import unittest


class PromptBuildingTest(unittest.TestCase):
    def test_user_profile_is_loadable(self):
        profile = load_config("user_profile.yaml")

        self.assertIn("strong_topics", profile)
        self.assertIn("conversation_style", profile)

    def test_flirt_and_safety_policies_are_loadable(self):
        self.assertIn("default_flirt_level_by_stage", load_config("flirt_policy.yaml"))
        self.assertIn("safety_checks", load_config("safety_policy.yaml"))


if __name__ == "__main__":
    unittest.main()
