import unittest

from src.loaders import load_config, load_target_profile, load_user_profile
from src.message_generator import select_reply_topic
from src.models import ConversationTurn, GenerationRequest


class TopicSelectionWithHistoryTest(unittest.TestCase):
    def test_history_and_user_preference_can_break_multi_topic_tie(self):
        history = [
            ConversationTurn("user", "カフェの話が好きです。"),
            ConversationTurn("partner", "休日はよくカフェに行きます。"),
            ConversationTurn("user", "落ち着いたカフェいいですね。"),
            ConversationTurn("partner", "映画も好きですし、カフェにもよく行きます。"),
        ]
        request = GenerationRequest(
            target_profile=load_target_profile("data/examples/sample_target_cafe_movie.yaml"),
            user_profile=load_user_profile(),
            conversation_history=history,
            purpose="reply",
        )

        topic_key, display_name = select_reply_topic(
            request,
            ["カフェ", "映画"],
            load_config("reply_topic_policy.yaml"),
        )

        self.assertEqual("cafe", topic_key)
        self.assertEqual("カフェ", display_name)


if __name__ == "__main__":
    unittest.main()
