from src.loaders import load_config
from src.safety_reviewer import SafetyReviewer
import unittest


def reviewer():
    return SafetyReviewer(load_config("safety_policy.yaml"))


class SafetyReviewerTest(unittest.TestCase):
    def test_initial_home_or_hotel_invite_is_ng(self):
        result = reviewer().review("今度ホテルでゆっくり話しませんか？")

        self.assertEqual(result["status"], "NG")

    def test_many_questions_are_revision_recommended(self):
        result = reviewer().review("映画好きですか？カフェも好きですか？休日は何していますか？")

        self.assertEqual(result["status"], "修正推奨")

    def test_safe_message_is_ok(self):
        result = reviewer().review("カフェ巡りが好きなところが気になりました。最近よかったお店はありますか？")

        self.assertEqual(result["status"], "OK")


if __name__ == "__main__":
    unittest.main()
