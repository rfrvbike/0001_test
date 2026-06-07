import os
import tempfile
import unittest
from unittest.mock import patch

from gui_helpers import (
    append_conversation_turns_to_partner,
    build_partner_label,
    build_partner_summary,
    build_conversation_import_preview,
    build_profile_save_preview,
    build_real_profile_from_form,
    detect_conversation_safety_warnings,
    detect_duplicate_turn_sequence,
    detect_profile_safety_warnings,
    format_conversation_history,
    format_pending_suggestions,
    format_timeline_items,
    get_real_profile_path,
    load_partner_choices,
    parse_conversation_paste,
    real_profile_exists,
    save_real_profile_from_form,
    validate_imported_turns,
    validate_profile_form,
)
from src.models import ActivityEvent, ConversationTurn, PartnerRecord, PendingSuggestion
from src.partner_store import load_partner, save_partner


class GuiHelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.real_profiles = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {
                "DATING_ASSISTANT_PARTNER_DIR": self.temp.name,
                "DATING_ASSISTANT_REAL_PROFILE_DIR": self.real_profiles.name,
            },
        )
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()
        self.real_profiles.cleanup()

    def test_load_partner_choices_excludes_archived_by_default(self):
        save_partner(PartnerRecord(partner_id="partner_001", display_name="active", status="first_message_suggested"))
        save_partner(PartnerRecord(partner_id="partner_002", display_name="old", status="archived"))

        self.assertEqual([partner.partner_id for partner in load_partner_choices()], ["partner_001"])
        self.assertEqual([partner.partner_id for partner in load_partner_choices(include_archived=True)], ["partner_001", "partner_002"])

    def test_build_partner_summary_contains_operational_fields(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="first_message_suggested",
            pending_suggestions=[
                PendingSuggestion("suggestion_001", "first", "hello", "2026-06-07T10:00:00+09:00"),
                PendingSuggestion("suggestion_002", "reply", "sent", "2026-06-07T10:01:00+09:00", status="sent"),
            ],
        )
        partner.analysis.partner_temperature = "normal"
        partner.message_state.next_action = "候補確認待ち"

        summary = build_partner_summary(partner)

        self.assertEqual(summary["partner_id"], "partner_001")
        self.assertEqual(summary["partner_temperature"], "normal")
        self.assertEqual(summary["next_action"], "候補確認待ち")
        self.assertEqual(summary["pending_suggestions_count"], 1)
        self.assertFalse(summary["message_state"]["awaiting_partner_reply"])

    def test_format_conversation_and_pending_suggestions_for_display(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            conversation=[
                ConversationTurn("partner", "こんばんは", "2026-06-07T10:00:00+09:00"),
                ConversationTurn("user", "こんばんは", "2026-06-07T10:01:00+09:00"),
            ],
            pending_suggestions=[
                PendingSuggestion("suggestion_001", "reply", "返信案", "2026-06-07T10:02:00+09:00"),
                PendingSuggestion("suggestion_002", "reply", "送信済み", "2026-06-07T10:03:00+09:00", status="sent"),
            ],
        )

        conversation = format_conversation_history(partner)
        suggestions = format_pending_suggestions(partner)

        self.assertEqual(conversation[0]["speaker_label"], "相手")
        self.assertEqual(conversation[1]["speaker_label"], "自分")
        self.assertEqual([suggestion["suggestion_id"] for suggestion in suggestions], ["suggestion_001"])

    def test_format_timeline_items_uses_existing_timeline_builder(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            conversation=[ConversationTurn("partner", "hello", "2026-06-07T10:00:00+09:00")],
            activity_log=[
                ActivityEvent("event_001", "partner_created", "2026-06-07T09:59:00+09:00", "partnerを作成"),
            ],
        )

        timeline = format_timeline_items(partner)

        self.assertEqual(timeline[0]["event_type"], "partner_created")
        self.assertEqual(timeline[1]["actor"], "partner")

    def test_build_partner_label_is_selectbox_friendly(self):
        partner = PartnerRecord(partner_id="partner_001", display_name="sample", status="chatting")

        self.assertEqual(build_partner_label(partner), "partner_001 / sample / chatting")

    def test_profile_form_builds_real_profile_data(self):
        form = {
            "label": "profile_001",
            "display_name": "sample",
            "app_name": "pairs",
            "age": "32",
            "area": "東京",
            "profile_text": "カフェが好きです。",
            "photo_memo": "自然な笑顔\n旅行写真",
            "interests": "カフェ, 映画\n散歩",
            "avoid_topics": "夜遅い予定",
            "notes": "丁寧に話す",
        }

        data = build_real_profile_from_form(form)
        preview = build_profile_save_preview(form)

        self.assertEqual(data["label"], "profile_001")
        self.assertEqual(data["age"], 32)
        self.assertEqual(data["hobbies"], ["カフェ", "映画", "散歩"])
        self.assertEqual(data["photos_memo"], ["自然な笑顔", "旅行写真"])
        self.assertEqual(data["location_hint"], "東京")
        self.assertIn("display_name: sample", data["free_notes"])
        self.assertEqual(preview["保存先label"], "profile_001")
        self.assertIn("profile_001.yaml", preview["保存先"])

    def test_profile_form_requires_core_fields(self):
        errors = validate_profile_form({"label": "", "display_name": "", "profile_text": "", "photo_memo": ""})

        self.assertIn("label は必須です。", errors)
        self.assertIn("display_name は必須です。", errors)
        self.assertIn("profile_text または photo_memo のどちらかは必須です。", errors)

    def test_profile_form_detects_safety_warnings(self):
        warnings = detect_profile_safety_warnings(
            {
                "label": "profile_001",
                "display_name": "sample",
                "profile_text": "LINEとメール sample@example.com は保存しない",
                "notes": "電話番号 090-1234-5678",
            }
        )

        self.assertIn("LINE", warnings)
        self.assertIn("メールアドレス", warnings)
        self.assertIn("電話番号", warnings)

    def test_save_real_profile_from_form_writes_local_profile_and_blocks_overwrite(self):
        form = {
            "label": "profile_001",
            "display_name": "sample",
            "profile_text": "カフェが好きです。",
            "photo_memo": "",
        }

        path, warnings = save_real_profile_from_form(form)

        self.assertEqual(warnings, [])
        self.assertTrue(path.exists())
        self.assertTrue(real_profile_exists("profile_001"))
        self.assertEqual(path, get_real_profile_path("profile_001"))
        with self.assertRaises(FileExistsError):
            save_real_profile_from_form(form)

    def test_profile_form_accepts_photo_memo_without_profile_text(self):
        form = {
            "label": "profile_002",
            "display_name": "photo only",
            "profile_text": "",
            "photo_memo": "公園の写真",
        }

        data = build_real_profile_from_form(form)

        self.assertEqual(validate_profile_form(form), [])
        self.assertEqual(data["profile_text"], "プロフィール文なし。写真メモのみ登録。")
        self.assertEqual(data["photos_memo"], ["公園の写真"])

    def test_parse_conversation_paste_supports_japanese_labels(self):
        turns, warnings = parse_conversation_paste("自分: はじめまして\n相手: カフェも好きです")

        self.assertEqual(warnings, [])
        self.assertEqual([turn["speaker"] for turn in turns], ["user", "partner"])
        self.assertEqual(turns[0]["text"], "はじめまして")

    def test_parse_conversation_paste_supports_multiline_blocks(self):
        text = "自分：\nはじめまして。\nよろしくお願いします。\n\n相手：\nこちらこそ。"

        turns, warnings = parse_conversation_paste(text)

        self.assertEqual(warnings, [])
        self.assertEqual(turns[0]["speaker"], "user")
        self.assertEqual(turns[0]["text"], "はじめまして。\nよろしくお願いします。")
        self.assertEqual(turns[1]["speaker"], "partner")

    def test_parse_conversation_paste_supports_user_partner_and_me_you(self):
        turns, warnings = parse_conversation_paste("user: hi\npartner: hello\nme: thanks\nyou: ok")

        self.assertEqual(warnings, [])
        self.assertEqual([turn["speaker"] for turn in turns], ["user", "partner", "user", "partner"])

    def test_parse_conversation_unknown_lines_warn_and_block_validation(self):
        turns, warnings = parse_conversation_paste("これは誰の発言かわからない\n自分: hello")
        errors = validate_imported_turns(turns, warnings)

        self.assertEqual([turn["speaker"] for turn in turns], ["user"])
        self.assertTrue(any("発話者を判定できない行" in warning for warning in warnings))
        self.assertTrue(any("発話者を判定できない行" in error for error in errors))

    def test_conversation_import_detects_safety_warnings_and_empty_input(self):
        warnings = detect_conversation_safety_warnings("LINEと sample@example.com と 090-1234-5678")
        empty_turns, empty_warnings = parse_conversation_paste("")

        self.assertIn("LINE", warnings)
        self.assertIn("メールアドレス", warnings)
        self.assertIn("電話番号", warnings)
        self.assertIn("会話履歴を解析できませんでした。", validate_imported_turns(empty_turns, empty_warnings))

    def test_append_conversation_turns_to_partner_keeps_existing_history(self):
        save_partner(
            PartnerRecord(
                partner_id="partner_001",
                display_name="sample",
                conversation=[ConversationTurn("partner", "既存発言", "2026-06-07T10:00:00+09:00")],
            )
        )
        turns, warnings = parse_conversation_paste("自分: はじめまして\n相手: よろしくお願いします")

        self.assertEqual(validate_imported_turns(turns, warnings), [])
        updated = append_conversation_turns_to_partner("partner_001", turns)
        stored = load_partner("partner_001")

        self.assertEqual(len(updated.conversation), 3)
        self.assertEqual(stored.conversation[0].text, "既存発言")
        self.assertEqual(stored.conversation[-1].speaker, "partner")
        self.assertEqual(stored.message_state.next_action, "返信候補を生成する")

    def test_duplicate_turn_sequence_is_detected_but_not_removed(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            conversation=[
                ConversationTurn("user", "同じ", "2026-06-07T10:00:00+09:00"),
                ConversationTurn("partner", "同じ返事", "2026-06-07T10:01:00+09:00"),
            ],
        )
        turns, _ = parse_conversation_paste("自分: 同じ\n相手: 同じ返事")

        self.assertTrue(detect_duplicate_turn_sequence(partner, turns))
        preview = build_conversation_import_preview(partner, turns, ["重複警告"])
        self.assertEqual(preview["追加予定turn数"], 2)
        self.assertIn("重複警告", preview["警告一覧"])


if __name__ == "__main__":
    unittest.main()
