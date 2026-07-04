"""補足メモ・文体サンプルのwidget keyが内容基準で安定していることの検証。

#2: チェックボックス/削除ボタンのkeyをindex基準から内容基準
(_content_widget_key)へ変更した。index基準だと項目削除でindexがずれ、
session_stateのチェック状態が別項目に紐づいてしまうため。
"""

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from gui_streamlit_app import _content_widget_key


def _index_widget_key(prefix: str, index: int) -> str:
    """比較用の旧実装（index基準）。内容基準への回帰でこの壊れ方に戻らないことを示す。"""
    return f"{prefix}_{index}"


class ContentWidgetKeyStabilityTests(unittest.TestCase):
    def test_same_content_yields_same_key(self):
        self.assertEqual(
            _content_widget_key("supplement_chk", "no-alcohol"),
            _content_widget_key("supplement_chk", "no-alcohol"),
        )

    def test_different_content_yields_different_key(self):
        self.assertNotEqual(
            _content_widget_key("supplement_chk", "no-alcohol"),
            _content_widget_key("supplement_chk", "no-car"),
        )

    def test_chk_and_del_are_separate_keys_for_same_content(self):
        content = "no-alcohol"
        self.assertNotEqual(
            _content_widget_key("supplement_chk", content),
            _content_widget_key("supplement_del", content),
        )

    def test_prefixes_stay_distinct_across_features(self):
        content = "sample-text"
        keys = {
            _content_widget_key("supplement_chk", content),
            _content_widget_key("supplement_del", content),
            _content_widget_key("style_chk", content),
            _content_widget_key("style_del", content),
        }
        self.assertEqual(len(keys), 4)

    def test_content_key_preserves_checked_state_after_deletion(self):
        """先頭項目を削除してindexがずれても、内容基準keyならチェック状態が保たれる。"""
        items = ["alpha", "beta", "gamma"]

        # gamma(index=2)をチェックした状態をsession_stateに保存する想定。
        session_state = {_content_widget_key("supplement_chk", "gamma"): True}

        # 先頭のalphaを削除 → gammaはindex=1に繰り上がる。
        items.pop(0)
        self.assertEqual(items, ["beta", "gamma"])

        # 内容基準keyはindexに依存しないので、gammaのチェックはgammaに残る。
        beta_checked = session_state.get(_content_widget_key("supplement_chk", "beta"), False)
        gamma_checked = session_state.get(_content_widget_key("supplement_chk", "gamma"), False)
        self.assertFalse(beta_checked)
        self.assertTrue(gamma_checked)

    def test_index_key_corrupts_checked_state_after_deletion(self):
        """対比: 旧index基準keyだと削除でチェック状態が別項目に化ける。"""
        items = ["alpha", "beta", "gamma"]

        # gamma(index=2)をチェックした状態をindex基準keyで保存。
        session_state = {_index_widget_key("supplement_chk", items.index("gamma")): True}

        # 先頭のalphaを削除 → gammaはindex=1に繰り上がる。
        items.pop(0)
        self.assertEqual(items, ["beta", "gamma"])

        # index基準だとgammaの新しいkey(index=1)は未チェック、
        # 元のTrue(index=2)はもうどの項目にも対応しない → チェックが失われる。
        gamma_checked = session_state.get(
            _index_widget_key("supplement_chk", items.index("gamma")), False
        )
        self.assertFalse(gamma_checked)  # gammaのチェックが壊れている

        # さらに悪いことに、残ったindex=2のTrueは範囲外の幽霊状態として残存する。
        self.assertTrue(session_state.get(_index_widget_key("supplement_chk", 2), False))


if __name__ == "__main__":
    unittest.main()
