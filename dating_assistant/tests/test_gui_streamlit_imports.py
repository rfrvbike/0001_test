import ast
import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = APP_DIR.parent
TOOLS_DIR = ROOT_DIR / "tools"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


class GuiStreamlitImportTests(unittest.TestCase):
    def test_gui_helpers_exports_every_name_imported_by_streamlit_app(self):
        app_file = APP_DIR / "gui_streamlit_app.py"
        tree = ast.parse(app_file.read_text(encoding="utf-8"), filename=str(app_file))
        imported_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "gui_helpers":
                imported_names.extend(alias.name for alias in node.names)

        helpers = importlib.import_module("gui_helpers")
        missing = sorted(name for name in imported_names if not hasattr(helpers, name))

        self.assertEqual(missing, [])
        self.assertIn("build_profile_save_payload", imported_names)

    def test_gui_streamlit_app_imports_without_import_error(self):
        module = importlib.import_module("gui_streamlit_app")

        self.assertTrue(hasattr(module, "main"))

    def test_preflight_script_passes(self):
        preflight = importlib.import_module("check_dating_gui_imports")

        self.assertEqual(preflight.main(), 0)

    def test_partner_view_is_conversation_workspace(self):
        from streamlit.testing.v1 import AppTest
        from src.models import ConversationTurn, PartnerProfile, PartnerRecord, PendingSuggestion
        from src.partner_store import save_partner

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
                partner = PartnerRecord(
                    partner_id="partner_001",
                    display_name="ケイコさん",
                    app_name="pairs",
                    status="chatting",
                    profile=PartnerProfile(
                        age=31,
                        profile_text="カフェが好きです。",
                        hobbies=["カフェ"],
                        photos_memo=["明るい雰囲気"],
                    ),
                    conversation=[
                        ConversationTurn("user", "はじめまして。", "2026-06-09T10:00:00+09:00"),
                        ConversationTurn("partner", "よろしくお願いします。", "2026-06-09T10:05:00+09:00"),
                    ],
                    pending_suggestions=[
                        PendingSuggestion("suggestion_001", "reply", "カフェいいですね。", "2026-06-09T10:10:00+09:00")
                    ],
                )
                partner.message_state.awaiting_user_action = True
                save_partner(partner)

                at = AppTest.from_file(str(app_file), default_timeout=20)
                at.run()

                self.assertEqual(len(at.exception), 0)
                options = [str(option) for option in at.selectbox[0].options]
                self.assertTrue(any("ケイコさん" in option for option in options))
                self.assertFalse(any("partner_001" in option for option in options))
                subheaders = [item.value for item in at.subheader]
                markdowns = [item.value for item in at.markdown]
                captions = [item.value for item in at.caption]
                self.assertIn("相手と会話する", subheaders)
                self.assertIn("次に送る文を作る", subheaders)
                self.assertTrue(any("相手のプロフィール" in value for value in markdowns))
                self.assertTrue(any("会話履歴" in value for value in markdowns))
                self.assertTrue(any("候補と送信済み記録" in value for value in markdowns))
                self.assertTrue(any("自動送信" in value for value in captions))

    def test_first_run_guidance_explains_customer_flow_without_partner_data(self):
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
                at = AppTest.from_file(str(app_file), default_timeout=20)
                at.run()

                self.assertEqual(len(at.exception), 0)
                self.assertEqual(len(at.error), 0)
                visible_text = "\n".join(
                    [item.value for item in at.info]
                    + [item.value for item in at.caption]
                    + [item.value for item in at.subheader]
                    + [item.value for item in at.markdown]
                )
                self.assertIn("まず「プロフィール登録」", visible_text)
                self.assertIn("保存後", visible_text)
                self.assertIn("相手と会話する", visible_text)
                self.assertIn("初回メッセージ候補", visible_text)
                self.assertIn("自動送信", visible_text)
                self.assertNotIn("partner_id", visible_text)
                self.assertEqual(list(real_dir.glob("*.yaml")), [])
                self.assertEqual(list(partner_dir.glob("partner_*.yaml")), [])

    def test_saved_profile_management_is_customer_friendly(self):
        from streamlit.testing.v1 import AppTest
        from src.models import PartnerNote, PartnerProfile, PartnerRecord, SentRecord
        from src.partner_store import save_partner

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
                save_partner(
                    PartnerRecord(
                        partner_id="partner_001",
                        display_name="ケイコさん",
                        app_name="Pairs",
                        status="chatting",
                        updated_at="2026-06-09T10:00:00+09:00",
                        profile=PartnerProfile(
                            age=31,
                            profile_text="カフェが好きです。",
                            hobbies=["カフェ"],
                            location_hint="東京",
                        ),
                        notes=[PartnerNote("返信は夜が多い")],
                        sent_records=[SentRecord("sent_001", "custom_text", "送った文", "2026-06-09T11:00:00+09:00")],
                    )
                )

                at = AppTest.from_file(str(app_file), default_timeout=20)
                at.run()

                self.assertEqual(len(at.exception), 0)
                self.assertEqual(len(at.error), 0)
                visible_text = "\n".join(
                    [item.value for item in at.info]
                    + [item.value for item in at.caption]
                    + [item.value for item in at.subheader]
                    + [item.value for item in at.markdown]
                )
                button_labels = [button.label for button in at.button]
                selectbox_options = []
                for selectbox in at.selectbox:
                    selectbox_options.extend([str(option) for option in (getattr(selectbox, "options", []) or [])])

                self.assertIn("保存済みプロフィール管理", visible_text)
                self.assertIn("登録済みの相手一覧", visible_text)
                self.assertIn("通常の候補作成は「相手と会話する」", visible_text)
                self.assertIn("表示名やメモだけを更新します", visible_text)
                self.assertIn("完全削除ではありません", visible_text)
                self.assertIn("この相手と会話する", button_labels)
                self.assertTrue(any("ケイコさん" in option for option in selectbox_options))
                self.assertTrue(any("ケイコさん" in option and "partner_001" not in option for option in selectbox_options))

    def test_profile_registration_save_button_accepts_sparse_profiles(self):
        from streamlit.testing.v1 import AppTest
        from src.loaders import load_target_profile
        from gui_helpers import (
            PROFILE_MINIMAL_TEXT,
            PROFILE_PHOTO_ONLY_TEXT,
            filter_real_profiles_for_gui,
            format_partner_preview_for_display,
        )

        cases = [
            {
                "paste": "よろしくお願いします。",
                "profile_text": "よろしくお願いします。",
                "hobbies": [],
                "photos_memo": [],
            },
            {
                "paste": "interests:\n- カフェ",
                "profile_text": PROFILE_MINIMAL_TEXT,
                "hobbies": ["カフェ"],
                "photos_memo": [],
            },
            {
                "paste": "photo_memo:\n- 明るい雰囲気",
                "profile_text": PROFILE_PHOTO_ONLY_TEXT,
                "hobbies": [],
                "photos_memo": ["明るい雰囲気"],
            },
            {
                "paste": "display_name:\n未設定",
                "profile_text": PROFILE_MINIMAL_TEXT,
                "hobbies": [],
                "photos_memo": [],
            },
            {
                "paste": "\n".join(
                    [
                        "display_name:",
                        "未設定",
                        "",
                        "app_name:",
                        "未設定",
                        "",
                        "age:",
                        "未設定",
                        "",
                        "area:",
                        "未設定",
                        "",
                        "profile_text:",
                        "よろしくお願いします。",
                        "",
                        "interests:",
                        "-",
                        "",
                        "photo_memo:",
                        "-",
                        "",
                        "conversation_hooks:",
                        "-",
                        "",
                        "first_message_hints:",
                        "-",
                        "",
                        "avoid_topics:",
                        "-",
                        "",
                        "notes:",
                        "情報少なめ。あとで補完する。",
                        "",
                        "privacy_notes:",
                        "- 個人情報は保存しない",
                    ]
                ),
                "profile_text": "よろしくお願いします。",
                "hobbies": [],
                "photos_memo": [],
                "free_notes_contains": "情報少なめ。あとで補完する。",
            },
            {
                "paste": "label:\n2026_20_28\n\nprofile_text:\nよろしくお願いします。",
                "profile_text": "よろしくお願いします。",
                "hobbies": [],
                "photos_memo": [],
                "forbidden_label": "2026_20_28",
            },
        ]
        app_file = APP_DIR / "gui_streamlit_app.py"

        for index, case in enumerate(cases, start=1):
            with self.subTest(case=index), tempfile.TemporaryDirectory() as tmp:
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
                    at = AppTest.from_file(str(app_file), default_timeout=20)
                    at.run()
                    at.text_area[0].set_value(case["paste"])
                    at.checkbox[1].set_value(True)
                    at.button[2].click().run()

                    saved_paths = sorted(real_dir.glob("*.yaml"))
                    partner_paths = sorted(partner_dir.glob("partner_*.yaml"))
                    self.assertEqual(len(at.exception), 0)
                    self.assertEqual(len(at.error), 0)
                    self.assertGreaterEqual(len(at.warning), 1)
                    self.assertGreaterEqual(len(at.success), 2)
                    self.assertEqual(len(saved_paths), 1)
                    self.assertEqual(len(partner_paths), 1)

                    label = saved_paths[0].stem
                    self.assertTrue(label.startswith("profile_"))
                    if case.get("forbidden_label"):
                        self.assertNotEqual(label, case["forbidden_label"])
                    profile = load_target_profile(saved_paths[0])
                    self.assertEqual(profile.profile_text, case["profile_text"])
                    self.assertEqual(profile.hobbies, case["hobbies"])
                    self.assertEqual(profile.photos_memo, case["photos_memo"])
                    if case.get("free_notes_contains"):
                        self.assertIn(case["free_notes_contains"], profile.free_notes or "")
                    self.assertTrue(any(item["label"] == label for item in filter_real_profiles_for_gui(label)))

                    options = []
                    for selectbox in at.selectbox:
                        options.extend([str(option) for option in (getattr(selectbox, "options", []) or [])])
                    self.assertGreater(len(options), 0)
                    self.assertTrue(any("partner_001" not in option for option in options))
                    self.assertTrue(format_partner_preview_for_display(label, "", "pairs", "")["summary"])

    def test_customer_flow_from_sparse_profile_to_conversation_records(self):
        from streamlit.testing.v1 import AppTest
        from src.partner_store import load_partner

        app_file = APP_DIR / "gui_streamlit_app.py"
        sparse_profile = "\n".join(
            [
                "display_name:",
                "未設定",
                "",
                "profile_text:",
                "よろしくお願いします。",
                "",
                "interests:",
                "- 未設定",
                "",
                "photo_memo:",
                "- 未設定",
                "",
                "conversation_hooks:",
                "- 未設定",
                "",
                "first_message_hints:",
                "- 未設定",
                "",
                "avoid_topics:",
                "- 未設定",
            ]
        )

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
                at = AppTest.from_file(str(app_file), default_timeout=20)
                at.run()
                at.text_area[0].set_value(sparse_profile)
                at.checkbox[1].set_value(True)
                at.button[2].click().run()

                self.assertEqual(len(at.exception), 0)
                self.assertEqual(len(at.error), 0)
                self.assertGreaterEqual(len(at.warning), 1)
                self.assertEqual(len(list(real_dir.glob("*.yaml"))), 1)
                self.assertEqual(len(list(partner_dir.glob("partner_*.yaml"))), 1)

                at.button[3].click().run()
                partner = load_partner("partner_001")
                self.assertEqual(partner.display_name, "表示名未設定")
                self.assertEqual(partner.conversation, [])
                self.assertIn("表示名未設定", str(at.selectbox[0].options[0]))
                self.assertNotIn("partner_001", str(at.selectbox[0].options[0]))

                at.checkbox[2].set_value(True)
                at.button[1].click().run()
                partner = load_partner("partner_001")
                self.assertEqual(len([item for item in partner.pending_suggestions if item.status == "pending"]), 3)
                self.assertEqual(len(at.exception), 0)
                self.assertEqual(len(at.error), 0)

                at.run()
                at.checkbox[3].set_value(True)
                at.button[2].click().run()
                partner = load_partner("partner_001")
                self.assertEqual(len(partner.sent_records), 1)
                self.assertEqual(len(partner.conversation), 1)
                self.assertEqual(partner.conversation[0].speaker, "user")
                self.assertTrue(partner.message_state.awaiting_partner_reply)

                at.checkbox[4].set_value(True)
                at.button[4].click().run()
                partner = load_partner("partner_001")
                self.assertTrue(any(item.status == "discarded" for item in partner.pending_suggestions))

                at.selectbox[2].set_value(at.selectbox[2].options[1])
                at.text_area[6].set_value("返信が来た。次もカフェの話で続ける。")
                at.checkbox[5].set_value(True)
                at.button[5].click().run()
                partner = load_partner("partner_001")
                self.assertEqual(partner.sent_records[0].outcome_status, "返信あり")
                self.assertIn("カフェ", partner.sent_records[0].outcome_memo)

                at.text_area[1].set_value("partner: カフェ好きです。")
                at.run()
                self.assertEqual(len(at.exception), 0)
                self.assertEqual(len(at.error), 0)
                at.checkbox[2].set_value(True)
                at.button[1].click().run()
                partner = load_partner("partner_001")
                self.assertEqual(partner.conversation[-1].speaker, "partner")
                self.assertIn("カフェ", partner.conversation[-1].text)
                self.assertTrue(partner.message_state.awaiting_user_action)
                self.assertFalse(partner.message_state.awaiting_partner_reply)

    def test_profile_registration_save_button_blocks_only_blank_profile(self):
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
                at = AppTest.from_file(str(app_file), default_timeout=20)
                at.run()
                at.checkbox[1].set_value(True)
                at.button[2].click().run()

                self.assertEqual(len(at.exception), 0)
                self.assertGreaterEqual(len(at.error), 1)
                self.assertEqual(list(real_dir.glob("*.yaml")), [])
                self.assertEqual(list(partner_dir.glob("partner_*.yaml")), [])


if __name__ == "__main__":
    unittest.main()
