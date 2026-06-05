from src.loaders import load_target_profile, load_user_profile, load_config
from src.topic_matcher import match_topics
import unittest


class TopicMatcherTest(unittest.TestCase):
    def test_common_light_and_avoid_topics_are_classified(self):
        target = load_target_profile("data/examples/sample_target_profile.yaml")
        user = load_user_profile()
        scores = load_config("topic_scores.yaml")["topic_scores"]

        topics = match_topics(target, user, scores)

        self.assertIn("カフェ", topics["common"])
        self.assertIn("映画", topics["common"])

    def test_avoid_topics_win_even_when_mentioned(self):
        target = load_target_profile("data/examples/sample_target_profile.yaml")
        target.hobbies.append("ホテル")
        user = load_user_profile()
        scores = load_config("topic_scores.yaml")["topic_scores"]
        scores["ホテル"] = 5

        topics = match_topics(target, user, scores)

        self.assertIn("ホテル", topics["avoid"])


if __name__ == "__main__":
    unittest.main()
