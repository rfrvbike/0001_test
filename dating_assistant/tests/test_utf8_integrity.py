import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_KEYWORDS = {
    "README.md": ["保存しました", "サンプル出力"],
    "reports/latest_report.md": ["安全確認", "次に改善すべき点"],
    "config/user_profile.yaml": ["カフェ", "ご飯"],
    "config/conversation_policy.yaml": ["first_message", "reply"],
    "config/flirt_policy.yaml": ["first_message", "early_chat"],
    "config/safety_policy.yaml": ["ホテル", "家"],
    "config/reply_topic_policy.yaml": ["映画", "カフェ", "fallback"],
    "outputs/examples/generate_first_cafe_movie.md": ["【一番おすすめ】", "【安全チェック結果】"],
    "outputs/examples/generate_reply_movie.md": ["【一番おすすめ】", "【安全チェック結果】"],
    "outputs/examples/generate_reply_cafe.md": ["【一番おすすめ】", "【相手の温度感】"],
    "outputs/examples/generate_reply_drink.md": ["【一番おすすめ】", "【相手の温度感】"],
    "outputs/examples/generate_reply_short.md": ["【一番おすすめ】", "【相手の温度感】"],
    "outputs/examples/generate_reply_multi_topic.md": ["【一番おすすめ】", "【相手の温度感】"],
    "data/examples/sample_conversation_short_reply.yaml": ["speaker", "カフェ"],
    "data/examples/sample_conversation_multi_topic_reply.yaml": ["speaker", "映画"],
}


class Utf8IntegrityTest(unittest.TestCase):
    def test_key_files_are_readable_as_utf8_and_contain_expected_keywords(self):
        for relative_path, keywords in EXPECTED_KEYWORDS.items():
            with self.subTest(relative_path=relative_path):
                text = (ROOT / relative_path).read_text(encoding="utf-8")
                for keyword in keywords:
                    self.assertIn(keyword, text)


if __name__ == "__main__":
    unittest.main()
