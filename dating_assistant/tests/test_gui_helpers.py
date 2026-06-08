import os
import tempfile
import unittest
from unittest.mock import patch

from gui_helpers import (
    GENERATION_OBJECTIVE_OPTIONS,
    append_conversation_turns_to_partner,
    build_partner_label,
    build_partner_creation_preview,
    build_conversation_stage_summary,
    build_generation_status_message,
    build_generation_preflight,
    build_discard_suggestion_preview,
    build_mark_sent_preview,
    build_partner_note_preview,
    build_profile_form_from_paste,
    build_profile_label_candidate,
    build_profile_paste_preview,
    build_sent_outcome_preview,
    build_partner_summary,
    build_conversation_import_preview,
    build_conversation_import_failure_guidance,
    build_partner_operational_display,
    apply_profile_label_candidate,
    build_profile_ocr_failure_guidance,
    build_profile_ocr_privacy_notes,
    build_profile_ocr_text_preview,
    build_profile_display_sections,
    build_profile_save_payload,
    build_profile_save_preview,
    build_real_profile_summary_for_gui,
    can_generate_suggestion,
    can_discard_suggestion,
    can_mark_suggestion_sent,
    build_real_profile_from_form,
    detect_conversation_safety_warnings,
    detect_duplicate_turn_sequence,
    detect_profile_safety_warnings,
    format_conversation_history,
    format_list_or_empty,
    format_partner_preview_for_display,
    format_partner_notes,
    format_pending_suggestions,
    format_sent_suggestions_for_outcomes,
    format_timeline_items,
    get_profile_ocr_environment_status,
    extract_profile_text_from_image,
    generate_suggestion_variants_for_gui,
    generate_suggestion_for_gui,
    filter_real_profiles_for_gui,
    find_existing_partners_for_profile,
    summarize_existing_partner_candidates,
    get_generation_mode_for_partner,
    discard_suggestion_from_gui,
    get_real_profile_path,
    list_real_profiles_for_gui,
    load_real_profile_for_gui,
    load_partner_choices,
    merge_profile_form_with_paste,
    mark_custom_text_sent_from_gui,
    mark_suggestion_sent_from_gui,
    parse_conversation_paste,
    real_profile_exists,
    save_partner_from_profile,
    save_real_profile_from_form,
    SENT_OUTCOME_STATUS_OPTIONS,
    split_form_list,
    add_partner_note_from_gui,
    update_sent_outcome_from_gui,
    validate_imported_turns,
    validate_profile_form,
)
from src.models import ActivityEvent, ConversationTurn, MessageState, PartnerNote, PartnerProfile, PartnerRecord, PendingSuggestion, SentRecord
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

    def test_partner_operational_display_uses_japanese_labels_without_raw_message_state(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="chatting",
            profile=PartnerProfile(profile_text="カフェが好きです。", hobbies=["カフェ"]),
            conversation=[ConversationTurn("partner", "カフェ好きです", "2026-06-07T10:00:00+09:00")],
            message_state=MessageState(awaiting_user_action=True, next_action="返信候補を確認して送る"),
        )
        partner.analysis.partner_temperature = "normal"

        display = build_partner_operational_display(partner)

        self.assertIn({"label": "表示名", "value": "sample"}, display["basic"])
        self.assertIn({"label": "こちらの対応待ち", "value": "はい"}, display["conversation"])
        self.assertIn({"label": "未送信候補", "value": "なし"}, display["conversation"])
        self.assertNotIn("message_state", display["basic"])
        self.assertNotIn("awaiting_user_action", str(display["basic"]))
        self.assertIn("message_state", display["detail"])

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

    def test_partner_notes_can_be_saved_loaded_and_warn_on_privacy_words(self):
        partner = PartnerRecord(partner_id="partner_001", display_name="sample", status="chatting")
        save_partner(partner)

        preview = build_partner_note_preview("旅行の話題に反応がよい。LINE交換はまだ早そう。")
        result = add_partner_note_from_gui("partner_001", "旅行の話題に反応がよい。電話はまだ早そう。", confirmed=True)
        loaded = load_partner("partner_001")
        notes = format_partner_notes(loaded)

        self.assertTrue(preview["warnings"])
        self.assertEqual(result["notes_count"], 1)
        self.assertEqual(notes[0]["text"], "旅行の話題に反応がよい。電話はまだ早そう。")
        self.assertEqual(loaded.conversation, [])
        self.assertEqual(loaded.pending_suggestions, [])

    def test_partner_notes_empty_state_and_generation_preflight_reference_notes(self):
        partner = PartnerRecord(partner_id="partner_001", display_name="sample", status="chatting")
        self.assertEqual(format_partner_notes(partner), [])

        partner.notes.append(PartnerNote("返信は夜が多い。旅行の話題に反応がよい。電話はまだ早そう。", "2026-06-07T10:00:00+09:00"))
        preflight = build_generation_preflight(partner, ["電話に誘う"], "自然", "")
        warnings = "\n".join(preflight["warnings"])

        self.assertTrue(preflight["partner_notes"]["has_notes"])
        self.assertIn("旅行", preflight["partner_notes"]["summary"])
        self.assertIn("電話はまだ早そう", warnings)

    def test_sent_outcome_memo_can_be_saved_loaded_and_shown_in_preflight(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="chatting",
            pending_suggestions=[
                PendingSuggestion(
                    "suggestion_001",
                    "reply",
                    "旅行の話、楽しそうですね。",
                    "2026-06-07T10:00:00+09:00",
                    status="sent",
                    sent_at="2026-06-07T10:01:00+09:00",
                )
            ],
        )
        save_partner(partner)

        preview = build_sent_outcome_preview(partner, "legacy_generated_suggestion_001", "話題が広がった", "旅行の話題は反応よかった。")
        result = update_sent_outcome_from_gui("partner_001", "legacy_generated_suggestion_001", "話題が広がった", "旅行の話題は反応よかった。", confirmed=True)
        loaded = load_partner("partner_001")
        outcomes = format_sent_suggestions_for_outcomes(loaded)
        preflight = build_generation_preflight(loaded, ["質問を1つ入れる"], "自然", "")

        self.assertIn("話題が広がった", SENT_OUTCOME_STATUS_OPTIONS)
        self.assertEqual(preview["sent_id"], "legacy_generated_suggestion_001")
        self.assertEqual(preview["結果ステータス"], "話題が広がった")
        self.assertEqual(result["outcome_status"], "話題が広がった")
        self.assertEqual(result["source_type"], "generated_suggestion")
        self.assertEqual(outcomes[0]["outcome_memo"], "旅行の話題は反応よかった。")
        self.assertIn("legacy_generated_suggestion_001: 話題が広がった", preflight["recent_sent_outcomes"][0])
        self.assertEqual(len(loaded.conversation), 0)
        self.assertEqual(loaded.pending_suggestions[0].status, "sent")
        self.assertEqual(loaded.sent_records[0].source_suggestion_id, "suggestion_001")

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

    def test_profile_paste_builds_form_and_preview(self):
        pasted = "\n".join(
            [
                "表示名: sample",
                "アプリ: pairs",
                "年齢: 31",
                "エリア: Tokyo",
                "自己紹介: カフェと映画が好きです。",
                "趣味: カフェ, 映画",
                "写真メモ: 自然な笑顔",
                "会話に使えそうな情報: 休日の話",
                "初回候補ヒント: いきなり誘わない",
                "安全メモ: 本名は保存しない",
            ]
        )
        extracted, warnings = build_profile_form_from_paste(pasted)
        form = merge_profile_form_with_paste({"label": "profile_003", "display_name": "", "profile_text": ""}, extracted)
        data = build_real_profile_from_form(form)
        preview = build_profile_paste_preview(pasted)

        self.assertTrue(any("本名" in warning for warning in warnings))
        self.assertEqual(form["display_name"], "sample")
        self.assertEqual(data["age"], 31)
        self.assertEqual(data["location_hint"], "Tokyo")
        self.assertEqual(data["hobbies"], ["カフェ", "映画"])
        self.assertIn("conversation_hooks:", data["free_notes"])
        self.assertEqual(preview["auto_send"], False)
        self.assertEqual(preview["extracted_fields"]["display_name"], "sample")
        self.assertIn("avoid_topics", preview["missing_fields"])
        self.assertTrue(preview["manual_review_required"])

    def test_profile_paste_supports_structured_chatgpt_format(self):
        pasted = """label:
nozomi_001

display_name:
のぞみ

app_name:
未設定

age:
未設定

area：
未設定

profile_text:
はじめまして。
プロフィールを見ていただき、ありがとうございます。

interests:
* 自然が好き
* 食事が好き
* 旅行が好き

photo_memo:
* 落ち着いた雰囲気
* やわらかい印象

conversation_hooks:
* 自然の話
* 食事の話
* 休日の過ごし方

first_message_hints:
* 自然や食事の話題から入る
* 返信しやすい質問を1つ入れる

avoid_topics:
* 未設定

notes:
未設定

privacy_notes:
* 個人情報は保存しない
"""
        extracted, warnings = build_profile_form_from_paste(pasted)
        preview = build_profile_paste_preview(pasted)
        form = merge_profile_form_with_paste({"label": "", "display_name": "", "profile_text": ""}, extracted)
        errors = validate_profile_form(form)

        self.assertEqual(extracted["label"], "nozomi_001")
        self.assertEqual(extracted["display_name"], "のぞみ")
        self.assertEqual(extracted["app_name"], "")
        self.assertEqual(extracted["age"], "")
        self.assertEqual(extracted["area"], "")
        self.assertEqual(extracted["profile_text"], "はじめまして。\nプロフィールを見ていただき、ありがとうございます。")
        self.assertEqual(split_form_list(extracted["interests"]), ["自然が好き", "食事が好き", "旅行が好き"])
        self.assertEqual(split_form_list(extracted["photo_memo"]), ["落ち着いた雰囲気", "やわらかい印象"])
        self.assertEqual(split_form_list(extracted["conversation_hooks"]), ["自然の話", "食事の話", "休日の過ごし方"])
        self.assertEqual(split_form_list(extracted["first_message_hints"]), ["自然や食事の話題から入る", "返信しやすい質問を1つ入れる"])
        self.assertEqual(extracted["avoid_topics"], "")
        self.assertEqual(extracted["notes"], "")
        self.assertEqual(split_form_list(extracted["safety_notes"]), ["個人情報は保存しない"])
        self.assertNotIn("privacy_notes", extracted["profile_text"])
        self.assertNotIn("interests", extracted["profile_text"])
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(preview["summary"][0]["value"], "nozomi_001")
        self.assertEqual(preview["profile_text"], extracted["profile_text"])
        self.assertEqual(preview["required_missing_fields"], [])
        self.assertIn("detail", preview)
        self.assertNotIn("path", preview)

    def test_profile_label_candidate_prefers_explicit_label(self):
        pasted = "label:\nnozomi_001\n\ndisplay_name:\nのぞみ\n\nprofile_text:\nこんにちは"
        extracted, _warnings = build_profile_form_from_paste(pasted)
        form, meta = apply_profile_label_candidate(extracted)
        preview = build_profile_paste_preview(pasted)

        self.assertEqual(form["label"], "nozomi_001")
        self.assertEqual(meta["label_source"], "貼り付け内容または入力欄から取得")
        self.assertEqual(preview["label_meta"]["label_source"], "貼り付け内容から取得")
        self.assertEqual(preview["summary"][0]["value"], "nozomi_001")

    def test_profile_label_candidate_generates_safe_generic_label_for_japanese_name(self):
        from datetime import datetime

        candidate = build_profile_label_candidate("のぞみ / LINE", now=datetime(2026, 6, 8, 12, 34, 56), existing_labels=set())

        self.assertEqual(candidate["label"], "profile_20260608_123456")
        self.assertEqual(candidate["label_source"], "自動候補")
        self.assertNotIn("のぞみ", candidate["label"])
        self.assertNotIn("/", candidate["label"])
        self.assertNotIn("LINE", candidate["label"])

    def test_profile_label_candidate_uses_ascii_display_name_and_deduplicates(self):
        from datetime import datetime

        existing = {"cafe_friend_20260608_123456", "cafe_friend_20260608_123456_001"}
        candidate = build_profile_label_candidate("Cafe Friend!!", now=datetime(2026, 6, 8, 12, 34, 56), existing_labels=existing)

        self.assertEqual(candidate["label"], "cafe_friend_20260608_123456_002")
        self.assertNotIn(" ", candidate["label"])
        self.assertNotIn("!", candidate["label"])

    def test_profile_paste_without_label_gets_editable_candidate_in_preview(self):
        from datetime import datetime

        pasted = "表示名:\nテストさん\n\n自己紹介:\n自然と食事が好きです。\n\n趣味・興味:\n* 自然\n* 食事"
        extracted, _warnings = build_profile_form_from_paste(pasted)
        candidate = build_profile_label_candidate(extracted["display_name"], now=datetime(2026, 6, 8, 12, 34, 56), existing_labels=set())
        preview = build_profile_paste_preview(pasted, label_candidate=candidate)
        form, meta = apply_profile_label_candidate(extracted, candidate)

        self.assertEqual(form["label"], "profile_20260608_123456")
        self.assertEqual(meta["label_source"], "自動候補")
        self.assertEqual(preview["label_meta"]["label_source"], "自動候補")
        self.assertEqual(preview["summary"][0]["value"], "profile_20260608_123456")
        self.assertIn("label種別", [row["label"] for row in preview["summary"]])
        self.assertEqual(preview["required_missing_fields"], [])

    def test_profile_save_payload_with_label_candidate_passes_validation(self):
        from datetime import datetime

        pasted = "display_name:\nテストさん\n\nprofile_text:\n自然と食事が好きです。\n\ninterests:\n* 自然\n* 食事"
        extracted, _warnings = build_profile_form_from_paste(pasted)
        candidate = build_profile_label_candidate(
            extracted["display_name"],
            now=datetime(2026, 6, 8, 12, 34, 56),
            existing_labels=set(),
        )
        form, label_meta, errors = build_profile_save_payload(
            {"label": "", "display_name": "", "profile_text": "", "photo_memo": ""},
            extracted,
            candidate,
        )

        self.assertEqual(errors, [])
        self.assertEqual(form["label"], "profile_20260608_123456")
        self.assertEqual(form["display_name"], "テストさん")
        self.assertEqual(form["profile_text"], "自然と食事が好きです。")
        self.assertEqual(split_form_list(form["interests"]), ["自然", "食事"])
        self.assertEqual(label_meta["label"], "profile_20260608_123456")

    def test_empty_form_fields_do_not_clear_extracted_values(self):
        extracted = {
            "label": "",
            "display_name": "テストさん",
            "profile_text": "自然が好きです。",
            "photo_memo": "落ち着いた雰囲気",
            "interests": "自然\n食事",
        }
        form, _label_meta, errors = build_profile_save_payload(
            {
                "label": "manual_label",
                "display_name": "",
                "profile_text": "",
                "photo_memo": "",
                "interests": "",
            },
            extracted,
        )

        self.assertEqual(errors, [])
        self.assertEqual(form["label"], "manual_label")
        self.assertEqual(form["display_name"], "テストさん")
        self.assertEqual(form["profile_text"], "自然が好きです。")
        self.assertEqual(form["photo_memo"], "落ち着いた雰囲気")
        self.assertEqual(form["interests"], "自然\n食事")

    def test_profile_ocr_preview_warns_and_never_marks_image_saved(self):
        preview = build_profile_ocr_text_preview("LINEと sample@example.com は保存しない")
        notes = build_profile_ocr_privacy_notes()
        guidance = build_profile_ocr_failure_guidance()

        self.assertFalse(preview["auto_save"])
        self.assertFalse(preview["image_saved"])
        self.assertIn("LINE", preview["warnings"])
        self.assertIn("メールアドレス", preview["warnings"])
        self.assertIn("画像そのものは保存しません", notes)
        self.assertIn("OCR環境が未設定", guidance["考えられる理由"])

    def test_profile_ocr_missing_engine_fails_without_breaking_gui(self):
        result = extract_profile_text_from_image(object())

        self.assertFalse(result["ok"])
        self.assertEqual(result["engine"], "pytesseract")
        self.assertIn("text", result)
        self.assertTrue(result["errors"])

    def test_profile_ocr_environment_status_is_optional_and_safe(self):
        status = get_profile_ocr_environment_status()

        self.assertIn(status["summary"], {"設定済み", "未設定"})
        self.assertIn("pytesseract", status)
        self.assertIn("tesseract", status)
        self.assertIn("japanese", status)
        self.assertIn("english", status)
        self.assertIn("messages", status)
        self.assertIn("テキスト貼り付け", status["alternatives"])

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

    def test_save_real_profile_from_structured_paste_reads_back_and_displays(self):
        form = {
            "label": "profile_yaml_safe",
            "display_name": "sample",
            "profile_text": "自然が好きです: カフェも好きです。\n- 休日は散歩します。\n\"落ち着いた雰囲気\"です 😊",
            "photo_memo": "明るい雰囲気: 屋外\n- 笑顔",
            "interests": "自然: 散歩\n- カフェ巡り\n\"映画\"",
            "conversation_hooks": "自然: 公園の話\n食事: 好きなお店",
            "first_message_hints": "質問は1つ: 休日の過ごし方",
            "avoid_topics": "- 強い誘い\n連絡先交換: 早すぎる",
            "safety_notes": "実データは保存しない\n画像そのものは保存しない",
            "notes": "notes:\n- コロン: ハイフン - 引用符 \" を含む長文",
            "area": "東京: 西側",
        }

        path, warnings = save_real_profile_from_form(form)
        _loaded_path, profile = load_real_profile_for_gui("profile_yaml_safe")
        display = build_profile_display_sections("profile_yaml_safe")
        partner = save_partner_from_profile("profile_yaml_safe", "sample", "pairs", "")

        self.assertTrue(path.exists())
        self.assertEqual(warnings, [])
        self.assertEqual(profile.profile_text, form["profile_text"])
        self.assertIn("自然: 散歩", profile.hobbies)
        self.assertIn("- カフェ巡り", profile.hobbies)
        self.assertIn("明るい雰囲気: 屋外", profile.photos_memo)
        self.assertIn("conversation_hooks:", profile.free_notes)
        self.assertIn("自然: 公園の話", profile.free_notes)
        self.assertEqual(display["profile_text"], form["profile_text"])
        self.assertEqual(partner.profile.profile_text, form["profile_text"])
        self.assertEqual(partner.conversation, [])

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
        guidance = build_conversation_import_failure_guidance()

        self.assertIn("LINE", warnings)
        self.assertIn("メールアドレス", warnings)
        self.assertIn("電話番号", warnings)
        self.assertIn("会話履歴を解析できませんでした。", validate_imported_turns(empty_turns, empty_warnings))
        self.assertIn("自分/相手のラベルが一致していない", guidance["考えられる理由"])
        self.assertIn("1発言ずつ手動追加してください", guidance["対処"][-1])

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

    def test_list_and_load_real_profiles_for_gui(self):
        save_real_profile_from_form(
            {
                "label": "profile_001",
                "display_name": "sample",
                "profile_text": "カフェが好きです。",
                "photo_memo": "",
                "interests": "カフェ",
            }
        )

        profiles = list_real_profiles_for_gui()
        path, profile = load_real_profile_for_gui("profile_001")

        self.assertEqual(profiles[0]["label"], "profile_001")
        self.assertIn("profile_001", profiles[0]["display_label"])
        self.assertTrue(path.name.endswith("profile_001.yaml"))
        self.assertEqual(profile.profile_text, "カフェが好きです。")

    def test_filter_profile_summary_and_existing_partner_match(self):
        save_real_profile_from_form(
            {
                "label": "profile_cafe",
                "display_name": "sample",
                "profile_text": "カフェが好きです。",
                "photo_memo": "自然な笑顔",
                "interests": "カフェ",
                "area": "Tokyo",
            }
        )
        partner = save_partner_from_profile("profile_cafe", "sample", "pairs", "")

        filtered = filter_real_profiles_for_gui("cafe")
        summary = build_real_profile_summary_for_gui("profile_cafe")
        matches = find_existing_partners_for_profile("profile_cafe")

        self.assertEqual(filtered[0]["label"], "profile_cafe")
        self.assertEqual(summary["area"], "Tokyo")
        self.assertEqual(matches[0]["partner_id"], partner.partner_id)

    def test_profile_display_sections_hide_internal_path_and_format_lists(self):
        save_real_profile_from_form(
            {
                "label": "profile_cafe",
                "display_name": "sample",
                "profile_text": "カフェが好きです。",
                "photo_memo": "カフェでの写真あり\n落ち着いた雰囲気",
                "interests": "カフェ\n映画",
                "area": "Tokyo",
                "conversation_hooks": "好きなカフェ\n最近見た映画",
                "avoid_topics": "",
                "safety_notes": "個人情報は保存しない",
            }
        )

        display = build_profile_display_sections("profile_cafe")

        self.assertEqual(display["title"], "選択中のプロフィール")
        self.assertNotIn("path", display)
        self.assertNotIn("source_path", str(display))
        self.assertIn({"label": "エリア", "value": "Tokyo"}, display["summary"])
        section_map = {section["title"]: section["items"] for section in display["sections"]}
        self.assertEqual(section_map["趣味"], ["カフェ", "映画"])
        self.assertEqual(section_map["写真メモ"], ["カフェでの写真あり", "落ち着いた雰囲気"])
        self.assertEqual(section_map["会話に使えそうな話題"], ["好きなカフェ", "最近見た映画"])
        self.assertEqual(section_map["避けた方がよい話題"], ["未設定"])
        self.assertEqual(section_map["安全メモ"], ["個人情報は保存しない"])

    def test_format_list_or_empty_handles_blank_values(self):
        self.assertEqual(format_list_or_empty([]), ["未設定"])
        self.assertEqual(format_list_or_empty("", empty="なし"), ["なし"])
        self.assertEqual(format_list_or_empty("カフェ\n映画"), ["カフェ", "映画"])

    def test_partner_preview_display_and_existing_candidate_summary_are_readable(self):
        save_real_profile_from_form(
            {
                "label": "profile_001",
                "display_name": "sample",
                "profile_text": "カフェが好きです。",
                "photo_memo": "",
                "interests": "カフェ",
                "area": "東京",
            }
        )
        partner = save_partner_from_profile("profile_001", "sample", "pairs", "")

        preview = format_partner_preview_for_display("profile_001", "表示名", "pairs", "")
        candidates = summarize_existing_partner_candidates("profile_001")

        self.assertEqual(preview["title"], "作成されるpartner")
        self.assertIn({"label": "表示名", "value": "表示名"}, preview["summary"])
        self.assertIn("実際の送信は行われません", preview["cautions"])
        self.assertNotIn("source_path", str(preview))
        self.assertEqual(candidates[0]["partner_id"], partner.partner_id)
        self.assertEqual(candidates[0]["表示名"], "sample")
        self.assertIn("重複作成", candidates[0]["操作のヒント"])

    def test_build_partner_creation_preview_does_not_copy_full_profile_text(self):
        save_real_profile_from_form(
            {
                "label": "profile_001",
                "display_name": "sample",
                "profile_text": "長いプロフィール本文です。",
                "photo_memo": "",
                "interests": "カフェ",
                "area": "東京",
            }
        )

        preview = build_partner_creation_preview("profile_001", "表示名", "pairs", "初回作成")

        self.assertEqual(preview["source_real_profile"], "profile_001")
        self.assertEqual(preview["display_name"], "表示名")
        self.assertEqual(preview["app_name"], "pairs")
        self.assertEqual(preview["status"], "new_profile")
        self.assertEqual(preview["conversation_history"], "空")
        self.assertEqual(preview["pending_suggestions"], "空")
        self.assertNotIn("長いプロフィール本文です。", str(preview))

    def test_save_partner_from_profile_generates_next_id_and_initializes_empty_state(self):
        save_partner(PartnerRecord(partner_id="partner_001", display_name="archived", status="archived"))
        save_real_profile_from_form(
            {
                "label": "profile_001",
                "display_name": "sample",
                "profile_text": "カフェが好きです。",
                "photo_memo": "",
                "interests": "カフェ",
                "app_name": "pairs",
            }
        )

        partner = save_partner_from_profile("profile_001", "表示名", "pairs", "メモ")
        stored = load_partner(partner.partner_id)

        self.assertEqual(partner.partner_id, "partner_002")
        self.assertEqual(stored.display_name, "表示名")
        self.assertEqual(stored.app_name, "pairs")
        self.assertEqual(stored.conversation, [])
        self.assertEqual(stored.pending_suggestions, [])
        self.assertEqual(stored.message_state.next_action, "初回候補生成待ち")
        self.assertTrue(any(event.event_type == "partner_created" for event in stored.activity_log))

    def test_generation_mode_allows_first_message_for_new_profile(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="new_profile",
            profile=PartnerProfile(profile_text="カフェが好きです。", hobbies=["カフェ"]),
        )

        self.assertEqual(get_generation_mode_for_partner(partner), "first")
        self.assertTrue(can_generate_suggestion(partner))
        self.assertIn("初回メッセージ候補", build_generation_status_message(partner))

    def test_generation_mode_allows_reply_when_partner_waits_for_user(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="chatting",
            conversation=[ConversationTurn("partner", "カフェ好きです", "2026-06-07T10:00:00+09:00")],
            message_state=MessageState(awaiting_user_action=True),
        )

        self.assertEqual(get_generation_mode_for_partner(partner), "reply")
        self.assertTrue(can_generate_suggestion(partner))
        self.assertIn("返信候補", build_generation_status_message(partner))

    def test_generation_mode_blocks_pending_waiting_reply_and_archived(self):
        pending = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            pending_suggestions=[PendingSuggestion("suggestion_001", "reply", "text", "2026-06-07T10:00:00+09:00")],
        )
        waiting = PartnerRecord(
            partner_id="partner_002",
            display_name="sample",
            message_state=MessageState(awaiting_partner_reply=True),
        )
        archived = PartnerRecord(partner_id="partner_003", display_name="sample", status="archived")

        self.assertEqual(get_generation_mode_for_partner(pending), "blocked")
        self.assertFalse(can_generate_suggestion(pending))
        self.assertIn("pending_suggestions", build_generation_status_message(pending))
        self.assertEqual(get_generation_mode_for_partner(waiting), "blocked")
        self.assertFalse(can_generate_suggestion(waiting))
        self.assertIn("相手の返信待ち", build_generation_status_message(waiting))
        self.assertEqual(get_generation_mode_for_partner(archived), "blocked")
        self.assertFalse(can_generate_suggestion(archived))
        self.assertIn("archived", build_generation_status_message(archived))

    def test_generate_suggestion_for_gui_saves_first_and_reply_without_external_api(self):
        first = PartnerRecord(
            partner_id="partner_001",
            display_name="first",
            status="new_profile",
            profile=PartnerProfile(profile_text="カフェが好きです。", hobbies=["カフェ"]),
        )
        reply = PartnerRecord(
            partner_id="partner_002",
            display_name="reply",
            status="chatting",
            profile=PartnerProfile(profile_text="カフェが好きです。", hobbies=["カフェ"]),
            conversation=[ConversationTurn("partner", "カフェもご飯も好きです", "2026-06-07T10:00:00+09:00")],
            message_state=MessageState(awaiting_user_action=True),
        )
        save_partner(first)
        save_partner(reply)

        first_result = generate_suggestion_for_gui("partner_001")
        reply_result = generate_suggestion_for_gui("partner_002")
        first_stored = load_partner("partner_001")
        reply_stored = load_partner("partner_002")

        self.assertEqual(first_result["mode"], "first")
        self.assertEqual(first_stored.status, "first_message_suggested")
        self.assertEqual(first_stored.pending_suggestions[0].purpose, "first")
        self.assertEqual(reply_result["mode"], "reply")
        self.assertEqual(reply_stored.pending_suggestions[0].purpose, "reply")
        self.assertEqual(reply_stored.message_state.next_action, "返信候補を確認して送る")

    def test_generate_suggestion_variants_saves_three_pending_suggestions(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="chatting",
            profile=PartnerProfile(profile_text="カフェが好きです。", hobbies=["カフェ"]),
            conversation=[
                ConversationTurn("partner", "カフェもご飯も好きです", "2026-06-07T10:00:00+09:00"),
                ConversationTurn("user", "いいですね", "2026-06-07T10:01:00+09:00"),
                ConversationTurn("partner", "休日によく行きます", "2026-06-07T10:02:00+09:00"),
            ],
            message_state=MessageState(awaiting_user_action=True),
        )
        save_partner(partner)

        preflight = build_generation_preflight(partner, ["質問を1つ入れる"], "自然", "")
        result = generate_suggestion_variants_for_gui("partner_001", ["質問を1つ入れる", "軽くユーモアを入れる"], "自然", "")
        stored = load_partner("partner_001")

        self.assertEqual(preflight["auto_send"], False)
        self.assertEqual(len(result["variants"]), 3)
        self.assertEqual(len([item for item in stored.pending_suggestions if item.status == "pending"]), 3)
        self.assertTrue(all(item.purpose == "reply" for item in stored.pending_suggestions))
        self.assertEqual([item["title"].split(":")[0] for item in result["variants"]], ["候補A", "候補B", "候補C"])
        self.assertIn("stage", result)
        self.assertIn("conversation_stage", result)
        self.assertIn("temperature", result)
        self.assertIn("next_recommendation", result)
        self.assertTrue(all("conversation_stage" in item for item in result["variants"]))
        self.assertTrue(all("temperature" in item for item in result["variants"]))
        self.assertTrue(all("aim" in item for item in result["variants"]))
        self.assertTrue(all("quality_check" in item for item in result["variants"]))

    def test_generation_preflight_emphasizes_early_risky_objectives(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="chatting",
            profile=PartnerProfile(profile_text="カフェが好きです。", hobbies=["カフェ"]),
            conversation=[
                ConversationTurn("partner", "カフェもご飯も好きです", "2026-06-07T10:00:00+09:00"),
            ],
            message_state=MessageState(awaiting_user_action=True),
        )

        preflight = build_generation_preflight(
            partner,
            ["電話に誘う", "会う提案をする", "LINE交換を提案する", "少し大人っぽい雰囲気にする"],
            "少し大人っぽいが控えめ",
            "",
        )
        warnings = "\n".join(preflight["warnings"])

        self.assertGreater(GENERATION_OBJECTIVE_OPTIONS.index("電話に誘う"), GENERATION_OBJECTIVE_OPTIONS.index("質問を1つ入れる"))
        self.assertIn("電話提案はまだ早い", warnings)
        self.assertIn("会う提案はまだ早い", warnings)
        self.assertIn("LINE交換提案は唐突", warnings)
        self.assertIn("大人っぽい雰囲気", warnings)
        self.assertEqual(preflight["line_exchange"]["status"], "まだ早い")
        self.assertEqual(preflight["adult_topic"]["status"], "まだ早い")
        self.assertEqual(preflight["conversation_stage"], "1往復目")
        self.assertIn("action_judgements", preflight)
        self.assertFalse(preflight["auto_send"])

    def test_first_message_variants_do_not_include_invites_or_line_exchange(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="new_profile",
            profile=PartnerProfile(profile_text="カフェと映画が好きです。", hobbies=["カフェ", "映画"]),
        )
        save_partner(partner)

        result = generate_suggestion_variants_for_gui(
            "partner_001",
            ["電話に誘う", "会う提案をする", "LINE交換を提案する"],
            "自然",
            "",
        )
        texts = "\n".join(item["text"] for item in result["variants"])

        self.assertNotIn("電話", texts)
        self.assertNotIn("LINE", texts)
        self.assertNotIn("お茶でも", texts)
        self.assertTrue(all(item["text"].count("？") <= 1 for item in result["variants"]))
        self.assertTrue(all("品質" not in item["text"] for item in result["variants"]))
        self.assertEqual([item["title"].split(":")[0] for item in result["variants"]], ["候補A", "候補B", "候補C"])

    def test_early_phone_objective_uses_safe_reply_and_quality_warning(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="chatting",
            profile=PartnerProfile(profile_text="旅行が好きです。", hobbies=["旅行"]),
            conversation=[ConversationTurn("partner", "旅行好きです", "2026-06-07T10:00:00+09:00")],
            message_state=MessageState(awaiting_user_action=True),
        )
        save_partner(partner)

        result = generate_suggestion_variants_for_gui("partner_001", ["電話に誘う"], "自然", "")
        variant = result["variants"][0]

        self.assertNotIn("電話で話して", variant["text"])
        self.assertTrue(any("電話に誘うはまだ早い" in item for item in variant["quality_check"]))
        self.assertTrue(any("電話に誘う: まだ早い" in item for item in variant["safety_notes"]))

    def test_phone_meet_line_and_adult_candidates_are_soft_when_allowed(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="chatting",
            profile=PartnerProfile(profile_text="カフェと旅行が好きです。", hobbies=["カフェ", "旅行"]),
            conversation=[
                ConversationTurn("partner", "旅行好きですか？", "2026-06-07T10:00:00+09:00"),
                ConversationTurn("user", "好きです", "2026-06-07T10:01:00+09:00"),
                ConversationTurn("partner", "自然が多い場所が好きです", "2026-06-07T10:02:00+09:00"),
                ConversationTurn("user", "いいですね", "2026-06-07T10:03:00+09:00"),
                ConversationTurn("partner", "カフェもよく行きますか？", "2026-06-07T10:04:00+09:00"),
                ConversationTurn("user", "行きます", "2026-06-07T10:05:00+09:00"),
                ConversationTurn("partner", "話しやすいです", "2026-06-07T10:06:00+09:00"),
                ConversationTurn("user", "自分もです", "2026-06-07T10:07:00+09:00"),
                ConversationTurn("partner", "また話したいです", "2026-06-07T10:08:00+09:00"),
            ],
            sent_records=[
                SentRecord(
                    sent_id="sent_generated_000001",
                    source_type="generated_suggestion",
                    text="旅行の話題",
                    sent_at="2026-06-07T10:03:00+09:00",
                    outcome_status="反応よかった",
                    outcome_memo="自然に話が続いた",
                )
            ],
            message_state=MessageState(awaiting_user_action=True),
        )
        save_partner(partner)

        phone = generate_suggestion_variants_for_gui("partner_001", ["電話に誘う"], "自然", "")["variants"][0]["text"]
        partner = load_partner("partner_001")
        partner.pending_suggestions.clear()
        save_partner(partner, allow_overwrite=True)
        meet = generate_suggestion_variants_for_gui("partner_001", ["会う提案をする"], "自然", "")["variants"][0]["text"]
        partner = load_partner("partner_001")
        partner.pending_suggestions.clear()
        save_partner(partner, allow_overwrite=True)
        line = generate_suggestion_variants_for_gui("partner_001", ["LINE交換を提案する"], "自然", "")["variants"][0]["text"]
        partner = load_partner("partner_001")
        partner.pending_suggestions.clear()
        save_partner(partner, allow_overwrite=True)
        adult = generate_suggestion_variants_for_gui("partner_001", ["少し大人っぽい雰囲気にする"], "自然", "")["variants"][0]["text"]

        self.assertIn("10分くらい", phone)
        self.assertIn("無理なければ", phone)
        self.assertTrue(any(word in meet for word in ["お茶", "ランチ"]))
        self.assertIn("もちろんこのままアプリでも大丈夫", line)
        self.assertNotIn("LINE教えて", line)
        self.assertNotIn("ホテル", adult)
        self.assertNotIn("大人の関係", adult)

    def test_conversation_stage_summary_changes_by_turn_count_and_reply_wait(self):
        first = PartnerRecord(partner_id="partner_001", display_name="first", status="new_profile")
        one_round = PartnerRecord(
            partner_id="partner_002",
            display_name="one_round",
            status="chatting",
            conversation=[
                ConversationTurn("partner", "カフェも好きですか？", "2026-06-07T10:00:00+09:00"),
                ConversationTurn("user", "好きです", "2026-06-07T10:01:00+09:00"),
                ConversationTurn("partner", "休日によく行きます", "2026-06-07T10:02:00+09:00"),
            ],
            message_state=MessageState(awaiting_user_action=True),
        )
        waiting = PartnerRecord(
            partner_id="partner_003",
            display_name="waiting",
            status="chatting",
            conversation=[
                ConversationTurn("partner", "カフェ好きです", "2026-06-07T10:00:00+09:00"),
                ConversationTurn("user", "おすすめありますか？", "2026-06-07T10:01:00+09:00"),
            ],
            message_state=MessageState(awaiting_partner_reply=True),
        )

        self.assertEqual(build_conversation_stage_summary(first)["conversation_stage"], "初回前")
        self.assertEqual(build_conversation_stage_summary(one_round)["conversation_stage"], "1往復目")
        self.assertEqual(build_conversation_stage_summary(waiting)["conversation_stage"], "一旦保留")

    def test_temperature_reason_uses_partner_question(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="chatting",
            conversation=[ConversationTurn("partner", "映画も好きですか？", "2026-06-07T10:00:00+09:00")],
            message_state=MessageState(awaiting_user_action=True),
        )

        summary = build_conversation_stage_summary(partner)

        self.assertIn("相手から質問が返ってきている", summary["temperature_reasons"])
        self.assertEqual(summary["temperature"], "高め")

    def test_partner_note_can_block_phone_judgement(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="chatting",
            conversation=[
                ConversationTurn("partner", "カフェ好きですか？", "2026-06-07T10:00:00+09:00"),
                ConversationTurn("user", "好きです", "2026-06-07T10:01:00+09:00"),
                ConversationTurn("partner", "おすすめ知りたいです", "2026-06-07T10:02:00+09:00"),
            ],
            notes=[PartnerNote("電話はまだ早そう。旅行の話題は反応がよい。", "2026-06-07T10:03:00+09:00")],
            message_state=MessageState(awaiting_user_action=True),
        )

        preflight = build_generation_preflight(partner, ["電話に誘う"], "自然", "")
        warnings = "\n".join(preflight["warnings"])

        self.assertEqual(preflight["action_judgements"]["電話に誘う"]["status"], "非推奨")
        self.assertIn("相手別メモ上、電話はまだ早そう", warnings)

    def test_sent_outcome_improves_temperature_reason(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="chatting",
            conversation=[
                ConversationTurn("partner", "旅行も好きです", "2026-06-07T10:00:00+09:00"),
                ConversationTurn("user", "いいですね", "2026-06-07T10:01:00+09:00"),
                ConversationTurn("partner", "自然が多い場所が好きです", "2026-06-07T10:02:00+09:00"),
            ],
            sent_records=[
                SentRecord(
                    sent_id="sent_generated_suggestion_001",
                    source_type="generated_suggestion",
                    text="旅行の話題",
                    sent_at="2026-06-07T10:01:00+09:00",
                    source_suggestion_id="suggestion_001",
                    outcome_status="反応よかった",
                    outcome_memo="旅行の話題は反応よかった",
                )
            ],
            message_state=MessageState(awaiting_user_action=True),
        )

        summary = build_conversation_stage_summary(partner)
        preflight = build_generation_preflight(partner, ["質問を1つ入れる"], "自然", "")

        self.assertIn("送信結果メモで反応がよい記録がある", summary["temperature_reasons"])
        self.assertEqual(summary["temperature"], "高め")
        self.assertIn("sent_generated_suggestion_001: 反応よかった", preflight["recent_sent_outcomes"][0])

    def test_practical_rehearsal_notes_and_outcomes_surface_in_preflight(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="chatting",
            profile=PartnerProfile(profile_text="カフェ、旅行、映画、散歩が好きです。", hobbies=["カフェ", "旅行", "映画"]),
            conversation=[
                ConversationTurn("partner", "旅行は京都が好きです。カフェもよく行きます。", "2026-06-07T10:00:00+09:00"),
                ConversationTurn("user", "京都いいですね。", "2026-06-07T10:01:00+09:00"),
                ConversationTurn("partner", "落ち着いた雰囲気の場所が好きです。", "2026-06-07T10:02:00+09:00"),
            ],
            notes=[
                PartnerNote("返信は夜が多い。旅行の話題に反応がよい。電話はまだ早そう。大人っぽい話題は控えめがよさそう。", "2026-06-07T10:03:00+09:00")
            ],
            sent_records=[
                SentRecord(
                    sent_id="sent_generated_000001",
                    source_type="generated_suggestion",
                    text="質問多めの文",
                    sent_at="2026-06-07T10:01:00+09:00",
                    outcome_status="微妙だった",
                    outcome_memo="質問多めの文は微妙だった",
                ),
                SentRecord(
                    sent_id="sent_generated_000002",
                    source_type="generated_suggestion",
                    text="旅行の話題",
                    sent_at="2026-06-07T10:02:00+09:00",
                    outcome_status="反応よかった",
                    outcome_memo="旅行の話題で返信あり",
                ),
            ],
            message_state=MessageState(awaiting_user_action=True),
        )

        preflight = build_generation_preflight(partner, ["電話に誘う", "質問を1つ入れる"], "自然", "")
        cautions = "\n".join(preflight["caution_points"])
        warnings = "\n".join(preflight["warnings"])

        self.assertIn("旅行話題", cautions)
        self.assertIn("質問を1つに絞ってください", cautions)
        self.assertIn("電話はまだ早そう", warnings)
        self.assertEqual(preflight["action_judgements"]["電話に誘う"]["status"], "非推奨")

    def test_practical_first_and_reply_rehearsal_candidates_are_distinct_and_safe(self):
        first = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="new_profile",
            profile=PartnerProfile(
                profile_text="カフェ、旅行、映画、散歩、食べることが好きです。自然体で落ち着いた雰囲気。",
                hobbies=["カフェ", "旅行", "映画", "散歩", "食べること"],
            ),
        )
        reply = PartnerRecord(
            partner_id="partner_002",
            display_name="sample",
            status="chatting",
            profile=first.profile,
            conversation=[ConversationTurn("partner", "カフェ好きです。休日に行くこと多いです。", "2026-06-07T10:00:00+09:00")],
            message_state=MessageState(awaiting_user_action=True),
        )
        save_partner(first)
        save_partner(reply)

        first_result = generate_suggestion_variants_for_gui("partner_001", ["電話に誘う", "会う提案をする", "LINE交換を提案する"], "自然", "")
        reply_result = generate_suggestion_variants_for_gui("partner_002", ["電話に誘う", "会う提案をする", "LINE交換を提案する"], "自然", "")

        first_texts = "\n".join(item["text"] for item in first_result["variants"])
        self.assertNotIn("電話", first_texts)
        self.assertNotIn("LINE", first_texts)
        self.assertNotIn("お茶でも", first_texts)
        self.assertEqual([item["title"].split(":")[0] for item in first_result["variants"]], ["候補A", "候補B", "候補C"])
        self.assertEqual(len({item["aim"] for item in first_result["variants"]}), 3)
        self.assertTrue(all(item["quality_check"] for item in first_result["variants"]))
        self.assertTrue(any("まだ早い" in "\n".join(item["quality_check"]) for item in reply_result["variants"]))

    def test_mark_sent_requires_pending_suggestion_and_confirmation(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            pending_suggestions=[PendingSuggestion("suggestion_001", "reply", "送った候補", "2026-06-07T10:00:00+09:00")],
        )
        save_partner(partner)

        self.assertFalse(can_mark_suggestion_sent(partner, "suggestion_001", confirmed=False))
        self.assertTrue(can_mark_suggestion_sent(partner, "suggestion_001", confirmed=True))
        with self.assertRaises(ValueError):
            mark_suggestion_sent_from_gui("partner_001", "suggestion_001", confirmed=False)

    def test_mark_suggestion_sent_from_gui_updates_history_state_and_suggestion(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="first_message_suggested",
            pending_suggestions=[PendingSuggestion("suggestion_001", "first", "送った候補", "2026-06-07T10:00:00+09:00")],
        )
        save_partner(partner)

        preview = build_mark_sent_preview(partner, suggestion_id="suggestion_001")
        result = mark_suggestion_sent_from_gui("partner_001", "suggestion_001", confirmed=True)
        stored = load_partner("partner_001")

        self.assertEqual(preview["speaker"], "user")
        self.assertEqual(preview["source_type"], "generated_suggestion")
        self.assertEqual(result["status"], "sent")
        self.assertRegex(result["sent_id"], r"^sent_generated_\d{6}$")
        self.assertEqual(result["source_type"], "generated_suggestion")
        self.assertEqual(stored.pending_suggestions[0].status, "sent")
        self.assertEqual(stored.sent_records[0].sent_id, result["sent_id"])
        self.assertEqual(stored.sent_records[0].source_type, "generated_suggestion")
        self.assertEqual(stored.sent_records[0].source_suggestion_id, "suggestion_001")
        self.assertEqual(stored.conversation[-1].speaker, "user")
        self.assertEqual(stored.conversation[-1].text, "送った候補")
        self.assertTrue(stored.message_state.awaiting_partner_reply)
        self.assertFalse(stored.message_state.awaiting_user_action)
        self.assertEqual(stored.status, "first_message_sent")

    def test_mark_custom_text_sent_from_gui_records_text_and_leaves_pending_suggestion(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            pending_suggestions=[PendingSuggestion("suggestion_001", "reply", "元候補", "2026-06-07T10:00:00+09:00")],
        )
        save_partner(partner)

        preview = build_mark_sent_preview(partner, custom_text="実際に送った修正文")
        result = mark_custom_text_sent_from_gui("partner_001", "実際に送った修正文", confirmed=True)
        stored = load_partner("partner_001")

        self.assertEqual(preview["record_type"], "custom text")
        self.assertEqual(preview["source_type"], "custom_text")
        self.assertEqual(result["remaining_pending_suggestions"], 1)
        self.assertRegex(result["sent_id"], r"^sent_custom_\d{6}$")
        self.assertEqual(result["source_type"], "custom_text")
        self.assertEqual(stored.pending_suggestions[0].status, "pending")
        self.assertEqual(stored.sent_records[0].sent_id, result["sent_id"])
        self.assertEqual(stored.sent_records[0].source_type, "custom_text")
        self.assertEqual(stored.sent_records[0].source_suggestion_id, None)
        self.assertEqual(stored.conversation[-1].speaker, "user")
        self.assertEqual(stored.conversation[-1].text, "実際に送った修正文")
        self.assertTrue(stored.message_state.awaiting_partner_reply)

        update = update_sent_outcome_from_gui("partner_001", result["sent_id"], "返信あり", "修正文にも返信あり", confirmed=True)
        updated = load_partner("partner_001")
        outcomes = format_sent_suggestions_for_outcomes(updated)
        preflight = build_generation_preflight(updated, ["質問を1つ入れる"], "自然", "")

        self.assertEqual(update["sent_id"], result["sent_id"])
        self.assertEqual(outcomes[0]["source_type"], "custom_text")
        self.assertEqual(outcomes[0]["source_label"], "手入力")
        self.assertEqual(outcomes[0]["outcome_status"], "返信あり")
        self.assertIn(f"{result['sent_id']}: 返信あり", preflight["recent_sent_outcomes"][0])

    def test_mark_custom_text_requires_confirmation_and_text(self):
        save_partner(PartnerRecord(partner_id="partner_001", display_name="sample"))

        with self.assertRaises(ValueError):
            mark_custom_text_sent_from_gui("partner_001", "送った文", confirmed=False)
        with self.assertRaises(ValueError):
            mark_custom_text_sent_from_gui("partner_001", "", confirmed=True)

    def test_discard_suggestion_requires_pending_suggestion_and_confirmation(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            pending_suggestions=[PendingSuggestion("suggestion_001", "reply", "未使用候補", "2026-06-07T10:00:00+09:00")],
        )
        save_partner(partner)

        self.assertFalse(can_discard_suggestion(partner, "suggestion_001", confirmed=False))
        self.assertTrue(can_discard_suggestion(partner, "suggestion_001", confirmed=True))
        with self.assertRaises(ValueError):
            discard_suggestion_from_gui("partner_001", "suggestion_001", confirmed=False)
        with self.assertRaises(ValueError):
            build_discard_suggestion_preview(partner, "missing")

    def test_discard_suggestion_from_gui_marks_discarded_without_changing_history(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            conversation=[ConversationTurn("partner", "こんにちは", "2026-06-07T10:00:00+09:00")],
            pending_suggestions=[
                PendingSuggestion("suggestion_001", "reply", "未使用候補", "2026-06-07T10:01:00+09:00"),
                PendingSuggestion("suggestion_002", "reply", "残す候補", "2026-06-07T10:02:00+09:00"),
            ],
            message_state=MessageState(awaiting_user_action=True, next_action="返信候補を確認して送る"),
        )
        save_partner(partner)

        preview = build_discard_suggestion_preview(partner, "suggestion_001", reason="修正文を送ったため")
        result = discard_suggestion_from_gui("partner_001", "suggestion_001", confirmed=True, reason="修正文を送ったため")
        stored = load_partner("partner_001")

        self.assertEqual(preview["discard_target"], "suggestion_001")
        self.assertEqual(preview["remaining_pending_suggestions"], "suggestion_002")
        self.assertEqual(result["status"], "discarded")
        self.assertTrue(result["conversation_history_unchanged"])
        self.assertEqual(len(stored.conversation), 1)
        self.assertEqual(stored.conversation[0].text, "こんにちは")
        self.assertEqual([item["suggestion_id"] for item in format_pending_suggestions(stored)], ["suggestion_002"])
        self.assertTrue(any(event.event_type == "suggestion_discarded" for event in stored.activity_log))

    def test_discard_suggestion_blocks_archived_partner(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            status="archived",
            pending_suggestions=[PendingSuggestion("suggestion_001", "reply", "未使用候補", "2026-06-07T10:00:00+09:00")],
        )
        save_partner(partner)

        self.assertFalse(can_discard_suggestion(partner, "suggestion_001", confirmed=True))
        with self.assertRaises(ValueError):
            discard_suggestion_from_gui("partner_001", "suggestion_001", confirmed=True)


if __name__ == "__main__":
    unittest.main()
