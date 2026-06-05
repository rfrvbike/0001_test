import unittest

from src.conversation_planner import estimate_partner_temperature
from src.models import ConversationTurn


class PartnerTemperatureTest(unittest.TestCase):
    def test_short_plain_reply_is_low(self):
        self.assertEqual("low", estimate_partner_temperature([ConversationTurn("partner", "はい")]))

    def test_concrete_positive_reply_is_good(self):
        text = "映画館好きです！最近はミステリーをよく見ます。"
        self.assertEqual("good", estimate_partner_temperature([ConversationTurn("partner", text)]))

    def test_warm_reply_is_very_good(self):
        text = "いいですね！私も話していて楽しいです！また話したいです。"
        self.assertEqual("very_good", estimate_partner_temperature([ConversationTurn("partner", text)]))

    def test_plain_reply_is_normal(self):
        self.assertEqual("normal", estimate_partner_temperature([ConversationTurn("partner", "映画はたまに見ます。")]))


if __name__ == "__main__":
    unittest.main()
