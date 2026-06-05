import unittest

from src.loaders import load_config


class ReplyTopicPolicyTest(unittest.TestCase):
    def test_reply_topic_policy_is_loadable(self):
        policy = load_config("reply_topic_policy.yaml")

        self.assertIn("topic_keywords", policy)
        self.assertIn("fallback", policy)

    def test_required_topics_are_defined_with_keywords(self):
        topics = load_config("reply_topic_policy.yaml")["topic_keywords"]

        for key in ["movie", "cafe", "food", "travel", "fashion_beauty", "drink"]:
            with self.subTest(key=key):
                self.assertIn(key, topics)
                self.assertTrue(topics[key]["keywords"])
                self.assertTrue(topics[key]["acknowledgment_examples"])
                self.assertTrue(topics[key]["empathy_examples"])
                self.assertTrue(topics[key]["safe_question_examples"])

    def test_fallback_definitions_exist(self):
        fallback = load_config("reply_topic_policy.yaml")["fallback"]

        self.assertIn("short_reply", fallback)
        self.assertIn("multiple_topics", fallback)
        self.assertTrue(fallback["short_reply"]["safe_question_examples"])

    def test_temperature_priority_is_defined(self):
        policy = load_config("reply_topic_policy.yaml")

        for key in ["low", "normal", "good", "very_good"]:
            self.assertIn(key, policy["temperature_style"])


if __name__ == "__main__":
    unittest.main()
