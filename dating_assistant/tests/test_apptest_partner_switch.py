import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from src.models import PartnerProfile, PartnerRecord, PendingSuggestion
from src.partner_store import save_partner

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


def _make_partner(partner_id: str, display_name: str, suggestion_text: str) -> PartnerRecord:
    partner = PartnerRecord(
        partner_id=partner_id,
        display_name=display_name,
        app_name="pairs",
        status="first_message_suggested",
        profile=PartnerProfile(profile_text="自己紹介文"),
        pending_suggestions=[
            PendingSuggestion("suggestion_001", "reply", suggestion_text, "2026-06-11T10:00:00+09:00")
        ],
    )
    return partner


class AppTestPartnerSwitchTests(unittest.TestCase):
    def test_initial_render_shows_first_partner(self):
        from streamlit.testing.v1 import AppTest

        app_file = APP_DIR / "gui_streamlit_app.py"
        with tempfile.TemporaryDirectory() as tmp:
            real_dir = Path(tmp) / "real_profiles"
            partner_dir = Path(tmp) / "partners"
            with unittest.mock.patch.dict(
                os.environ,
                {
                    "DATING_ASSISTANT_REAL_PROFILE_DIR": str(real_dir),
                    "DATING_ASSISTANT_PARTNER_DIR": str(partner_dir),
                },
                clear=False,
            ):
                save_partner(_make_partner("partner_001", "Aさん", "Aさん専用メッセージ候補"))
                save_partner(_make_partner("partner_002", "Bさん", "Bさん専用メッセージ候補"))

                at = AppTest.from_file(str(app_file), default_timeout=20)
                at.run()

                self.assertEqual(len(at.exception), 0)
                options = [str(opt) for opt in at.selectbox[0].options]
                self.assertTrue(any("Aさん" in opt for opt in options))
                self.assertTrue(any("Bさん" in opt for opt in options))
                # 初期表示でAさんの候補が表示されること
                textarea_values = [ta.value for ta in at.text_area]
                self.assertTrue(any("Aさん専用メッセージ候補" in v for v in textarea_values))

    def test_switching_partner_shows_new_partner_content(self):
        from streamlit.testing.v1 import AppTest

        app_file = APP_DIR / "gui_streamlit_app.py"
        with tempfile.TemporaryDirectory() as tmp:
            real_dir = Path(tmp) / "real_profiles"
            partner_dir = Path(tmp) / "partners"
            with unittest.mock.patch.dict(
                os.environ,
                {
                    "DATING_ASSISTANT_REAL_PROFILE_DIR": str(real_dir),
                    "DATING_ASSISTANT_PARTNER_DIR": str(partner_dir),
                },
                clear=False,
            ):
                save_partner(_make_partner("partner_001", "Aさん", "Aさん専用メッセージ候補"))
                save_partner(_make_partner("partner_002", "Bさん", "Bさん専用メッセージ候補"))

                at = AppTest.from_file(str(app_file), default_timeout=20)
                at.run()
                self.assertEqual(len(at.exception), 0)

                # Bさんに切り替え
                b_option = next(opt for opt in at.selectbox[0].options if "Bさん" in str(opt))
                at.selectbox[0].set_value(b_option).run()

                self.assertEqual(len(at.exception), 0)
                textarea_values = [ta.value for ta in at.text_area]
                # Bさんの候補が表示されること
                self.assertTrue(any("Bさん専用メッセージ候補" in v for v in textarea_values))

    def test_switching_partner_does_not_show_previous_partner_suggestion(self):
        """同じsuggestion_idを持つ相手を切り替えても候補本文が混入しないことを確認する。"""
        from streamlit.testing.v1 import AppTest

        app_file = APP_DIR / "gui_streamlit_app.py"
        with tempfile.TemporaryDirectory() as tmp:
            real_dir = Path(tmp) / "real_profiles"
            partner_dir = Path(tmp) / "partners"
            with unittest.mock.patch.dict(
                os.environ,
                {
                    "DATING_ASSISTANT_REAL_PROFILE_DIR": str(real_dir),
                    "DATING_ASSISTANT_PARTNER_DIR": str(partner_dir),
                },
                clear=False,
            ):
                # 両者が同じsuggestion_idを持つ（旧バグ再現シナリオ）
                save_partner(_make_partner("partner_001", "Aさん", "Aさんのみ表示テキスト"))
                save_partner(_make_partner("partner_002", "Bさん", "Bさんのみ表示テキスト"))

                at = AppTest.from_file(str(app_file), default_timeout=20)
                at.run()
                self.assertEqual(len(at.exception), 0)

                b_option = next(opt for opt in at.selectbox[0].options if "Bさん" in str(opt))
                at.selectbox[0].set_value(b_option).run()
                self.assertEqual(len(at.exception), 0)

                textarea_values = [ta.value for ta in at.text_area]
                # Bさんの候補のみ表示されること
                self.assertTrue(any("Bさんのみ表示テキスト" in v for v in textarea_values))
                # Aさんの候補は表示されないこと
                self.assertFalse(any("Aさんのみ表示テキスト" in v for v in textarea_values))

    def test_repeated_partner_switches_do_not_cause_exceptions(self):
        """複数回の相手切り替えでも例外・エラーが発生しないことを確認する。"""
        from streamlit.testing.v1 import AppTest

        app_file = APP_DIR / "gui_streamlit_app.py"
        with tempfile.TemporaryDirectory() as tmp:
            real_dir = Path(tmp) / "real_profiles"
            partner_dir = Path(tmp) / "partners"
            with unittest.mock.patch.dict(
                os.environ,
                {
                    "DATING_ASSISTANT_REAL_PROFILE_DIR": str(real_dir),
                    "DATING_ASSISTANT_PARTNER_DIR": str(partner_dir),
                },
                clear=False,
            ):
                save_partner(_make_partner("partner_001", "Aさん", "Aさん専用テキスト"))
                save_partner(_make_partner("partner_002", "Bさん", "Bさん専用テキスト"))

                at = AppTest.from_file(str(app_file), default_timeout=20)
                at.run()
                self.assertEqual(len(at.exception), 0)
                self.assertEqual(len(at.error), 0)

                # Bさんに切り替え
                b_option = next(opt for opt in at.selectbox[0].options if "Bさん" in str(opt))
                at.selectbox[0].set_value(b_option).run()
                self.assertEqual(len(at.exception), 0)
                self.assertEqual(len(at.error), 0)

                # Aさんに戻す
                a_option = next(opt for opt in at.selectbox[0].options if "Aさん" in str(opt))
                at.selectbox[0].set_value(a_option).run()
                self.assertEqual(len(at.exception), 0)
                self.assertEqual(len(at.error), 0)

                # Bさんに再度切り替え
                at.selectbox[0].set_value(b_option).run()
                self.assertEqual(len(at.exception), 0)
                self.assertEqual(len(at.error), 0)


if __name__ == "__main__":
    unittest.main()
