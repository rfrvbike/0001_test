"""会話スクショ自動登録(第1段階)の読み取り関数のテスト。

_parse_conversation_turns_json のJSON堅牢性はmock不要で検証し、
read_conversation_from_images はanthropicクライアントをmockして
リクエスト形状(モデル/thinking無効化/画像ブロック)と返り値を検証する。
"""

import base64
import sys
import unittest
from types import SimpleNamespace
from unittest import mock
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from src import claude_generator
from src.claude_generator import (
    CLAUDE_MODEL,
    _parse_conversation_turns_json,
    read_conversation_from_images,
)


class ParseConversationTurnsJsonTests(unittest.TestCase):
    def test_parses_clean_json_array(self):
        text = '[{"speaker": "partner", "text": "hi"}, {"speaker": "user", "text": "hello"}]'
        self.assertEqual(
            _parse_conversation_turns_json(text),
            [{"speaker": "partner", "text": "hi"}, {"speaker": "user", "text": "hello"}],
        )

    def test_strips_json_code_fence(self):
        text = '```json\n[{"speaker": "user", "text": "hey"}]\n```'
        self.assertEqual(
            _parse_conversation_turns_json(text),
            [{"speaker": "user", "text": "hey"}],
        )

    def test_strips_bare_code_fence(self):
        text = '```\n[{"speaker": "partner", "text": "yo"}]\n```'
        self.assertEqual(
            _parse_conversation_turns_json(text),
            [{"speaker": "partner", "text": "yo"}],
        )

    def test_extracts_array_surrounded_by_prose(self):
        text = 'Here is the conversation:\n[{"speaker": "partner", "text": "hi"}]\nThat is all.'
        self.assertEqual(
            _parse_conversation_turns_json(text),
            [{"speaker": "partner", "text": "hi"}],
        )

    def test_normalizes_japanese_and_unknown_speakers(self):
        text = (
            '[{"speaker": "相手", "text": "a"},'
            ' {"speaker": "自分", "text": "b"},'
            ' {"speaker": "USER", "text": "c"},'
            ' {"speaker": "bot", "text": "d"}]'
        )
        result = _parse_conversation_turns_json(text)
        self.assertEqual(
            [r["speaker"] for r in result],
            ["partner", "user", "user", "partner"],  # 未知(bot)はpartnerにフォールバック
        )

    def test_drops_rows_with_empty_text(self):
        text = '[{"speaker": "user", "text": "  "}, {"speaker": "partner", "text": "kept"}]'
        self.assertEqual(
            _parse_conversation_turns_json(text),
            [{"speaker": "partner", "text": "kept"}],
        )

    def test_raises_when_no_json_array_present(self):
        with self.assertRaises(ValueError):
            _parse_conversation_turns_json("no brackets here at all")

    def test_raises_on_malformed_json(self):
        with self.assertRaises(ValueError):
            _parse_conversation_turns_json('[{"speaker": "user", "text": ]')

    def test_raises_when_no_valid_turns(self):
        with self.assertRaises(ValueError):
            _parse_conversation_turns_json('[{"speaker": "user", "text": ""}]')


class ReadConversationFromImagesTests(unittest.TestCase):
    def _make_message(self, text):
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])

    def test_sends_expected_request_and_parses_result(self):
        images = [
            {"media_type": "image/png", "data": b"first-bytes"},
            {"media_type": "image/jpeg", "data": b"second-bytes"},
        ]
        mock_client = mock.MagicMock()
        mock_client.messages.create.return_value = self._make_message(
            '[{"speaker": "partner", "text": "hi"}, {"speaker": "user", "text": "hello"}]'
        )

        with mock.patch.object(claude_generator, "_get_api_key", return_value="test-key"), \
                mock.patch("anthropic.Anthropic", return_value=mock_client) as mock_anthropic:
            result = read_conversation_from_images(images)

        self.assertEqual(
            result,
            [{"speaker": "partner", "text": "hi"}, {"speaker": "user", "text": "hello"}],
        )
        mock_anthropic.assert_called_once_with(api_key="test-key")

        kwargs = mock_client.messages.create.call_args.kwargs
        self.assertEqual(kwargs["model"], CLAUDE_MODEL)
        self.assertEqual(kwargs["thinking"], {"type": "disabled"})

        content = kwargs["messages"][0]["content"]
        image_blocks = [b for b in content if b.get("type") == "image"]
        text_blocks = [b for b in content if b.get("type") == "text"]
        self.assertEqual(len(image_blocks), 2)
        self.assertEqual(len(text_blocks), 1)
        # 画像は時系列順・base64化されて渡る。
        self.assertEqual(image_blocks[0]["source"]["media_type"], "image/png")
        self.assertEqual(
            image_blocks[0]["source"]["data"],
            base64.b64encode(b"first-bytes").decode("ascii"),
        )
        self.assertEqual(image_blocks[1]["source"]["media_type"], "image/jpeg")

    def test_raises_when_no_images(self):
        with mock.patch.object(claude_generator, "_get_api_key", return_value="test-key"):
            with self.assertRaises(ValueError):
                read_conversation_from_images([])

    def test_raises_when_api_key_missing(self):
        with mock.patch.object(claude_generator, "_get_api_key", return_value=None):
            with self.assertRaises(ValueError):
                read_conversation_from_images([{"media_type": "image/png", "data": b"x"}])


if __name__ == "__main__":
    unittest.main()
