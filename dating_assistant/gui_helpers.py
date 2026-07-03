from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from io import BytesIO
import json
import re
import shutil
from pathlib import Path
from typing import Any

from src.activity_log import add_activity_event
from src.app_core import generate
from src.atomic_io import atomic_write_text
from src.conversation_planner import estimate_partner_temperature
from src.loaders import load_user_profile
from src.models import ConversationTurn, GenerationRequest, PartnerNote, PartnerRecord, SentRecord, TargetProfile
from src.partner_store import get_partner_dir, get_skipped_partner_files, list_partners, load_partner
from src.partner_manager import add_partner_note, archive_partner, create_partner_from_target_profile, save_updated_partner, unarchive_partner
from src.real_profile_manager import (
    create_real_profile,
    detect_privacy_warnings,
    get_real_profile_dir,
    list_real_profiles,
    load_real_profile,
    validate_real_profile_label,
)
from src.suggestion_manager import add_suggestion, discard_suggestion, get_pending_suggestions, mark_suggestion_sent, mark_text_sent
from src.timeline_builder import build_timeline_events

PROFILE_PASTE_FIELD_ALIASES = {
    "label": "label",
    "ラベル": "label",
    "保存名": "label",
    "display_name": "display_name",
    "name": "display_name",
    "表示名": "display_name",
    "名前": "display_name",
    "相手の表示名": "display_name",
    "app": "app_name",
    "app_name": "app_name",
    "アプリ": "app_name",
    "アプリ名": "app_name",
    "age": "age",
    "年齢": "age",
    "area": "area",
    "エリア": "area",
    "居住地": "area",
    "地域": "area",
    "profile": "profile_text",
    "profile_text": "profile_text",
    "プロフィール": "profile_text",
    "プロフィール文": "profile_text",
    "自己紹介": "profile_text",
    "interests": "interests",
    "hobbies": "interests",
    "趣味": "interests",
    "趣味・興味": "interests",
    "好きなこと": "interests",
    "photo": "photo_memo",
    "photo_memo": "photo_memo",
    "写真": "photo_memo",
    "写真メモ": "photo_memo",
    "写真から分かる印象メモ": "photo_memo",
    "印象": "photo_memo",
    "avoid_topics": "avoid_topics",
    "避けたい話題": "avoid_topics",
    "避けた方がよさそうな話題": "avoid_topics",
    "ng": "avoid_topics",
    "notes": "notes",
    "メモ": "notes",
    "その他": "notes",
    "conversation_hooks": "conversation_hooks",
    "会話に使えそうな情報": "conversation_hooks",
    "会話に使えそうな話題": "conversation_hooks",
    "first_message_hints": "first_message_hints",
    "初回候補ヒント": "first_message_hints",
    "初回メッセージのヒント": "first_message_hints",
    "safety_notes": "safety_notes",
    "privacy_notes": "safety_notes",
    "安全メモ": "safety_notes",
    "保存しない方がよい個人情報・注意": "safety_notes",
}

PROFILE_PASTE_FIELDS = [
    "label",
    "display_name",
    "app_name",
    "age",
    "area",
    "profile_text",
    "interests",
    "photo_memo",
    "avoid_topics",
    "conversation_hooks",
    "first_message_hints",
    "safety_notes",
    "notes",
]
PROFILE_LIST_FIELDS = {
    "interests",
    "photo_memo",
    "avoid_topics",
    "conversation_hooks",
    "first_message_hints",
    "safety_notes",
}
PROFILE_MULTILINE_FIELDS = PROFILE_LIST_FIELDS | {"profile_text", "notes"}
PROFILE_SCALAR_FIELDS = {"label", "display_name", "app_name", "age", "area"}
PROFILE_UNSET_VALUES = {"", "-", "未設定", "なし", "無し", "不明", "n/a", "none", "null"}
PROFILE_MINIMAL_TEXT = "プロフィール本文未設定。あとで補完できます。"
PROFILE_PHOTO_ONLY_TEXT = "プロフィール本文なし。写真メモのみ登録。"
PROFILE_DISPLAY_NAME_UNSET = "表示名未設定"
PROFILE_NORMALIZED_PLACEHOLDER_TEXTS = {PROFILE_MINIMAL_TEXT, PROFILE_PHOTO_ONLY_TEXT}
PARTNER_SOURCE_PROFILE_EVENT = "partner_created_from_profile"
PROFILE_PASTE_LABELS = {
    "label": "label",
    "display_name": "表示名",
    "app_name": "アプリ",
    "age": "年齢",
    "area": "エリア",
    "profile_text": "自己紹介",
    "interests": "趣味・興味",
    "photo_memo": "写真メモ",
    "avoid_topics": "避けた方がよい話題",
    "conversation_hooks": "会話に使えそうな話題",
    "first_message_hints": "初回メッセージのヒント",
    "safety_notes": "保存しない方がよい個人情報・注意",
    "notes": "メモ",
}

GENERATION_OBJECTIVE_OPTIONS = [
    "相手のプロフィールに触れる",
    "質問を1つ入れる",
    "共感のリアクション重視",
    "相手の趣味を広げる",
    "自分の紹介をする",
    "軽くユーモアを入れる",
    "恋愛観に軽く触れる",
    "少し大人っぽい雰囲気にする",
    "電話に誘う",
    "会う提案をする",
    "場所を指定して会う提案をする",
    "LINE交換を提案する",
]

GENERATION_TONE_OPTIONS = [
    "自然",
    "丁寧",
    "少し親しみやすい",
    "軽くユーモア",
    "落ち着いた感じ",
    "短め",
    "かなり無難",
    "少し大人っぽいが控えめ",
]

SENT_OUTCOME_STATUS_OPTIONS = [
    "未確認",
    "返信あり",
    "返信なし",
    "反応よかった",
    "話題が広がった",
    "微妙だった",
    "その他",
]

PROFILE_SAFETY_PATTERNS = {
    "メールアドレス": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "電話番号": re.compile(r"(?:\+?\d[\d -]{8,}\d)"),
}
PROFILE_SAFETY_WORDS = [
    "LINE",
    "ライン",
    "Instagram",
    "インスタ",
    "X ID",
    "Twitter",
    "住所",
    "勤務先",
    "会社名",
    "学校名",
    "大学名",
    "高校",
    "本名",
]
SPEAKER_ALIASES = {
    "自分": "user",
    "user": "user",
    "me": "user",
    "相手": "partner",
    "partner": "partner",
    "you": "partner",
}
SPEAKER_LINE_RE = re.compile(r"^\s*([^:：]+)\s*[:：]\s*(.*)$")


def load_partner_choices(include_archived: bool = False) -> list[PartnerRecord]:
    partners = list_partners()
    if not include_archived:
        partners = [partner for partner in partners if partner.status != "archived"]
    return sorted(partners, key=lambda partner: partner.partner_id)


def load_partner_for_view(partner_id: str) -> PartnerRecord:
    return load_partner(partner_id)


def build_partner_label(partner: PartnerRecord) -> str:
    name = partner.display_name or "(no display name)"
    return f"{partner.partner_id} / {name} / {partner.status}"


def build_partner_choice_label(partner: PartnerRecord) -> str:
    display_name = partner.display_name or PROFILE_DISPLAY_NAME_UNSET
    app_name = partner.app_name or "アプリ未設定"
    memo_tag = load_memo_tag(partner.partner_id)
    if memo_tag:
        label = f"{display_name}（{memo_tag}）/ {app_name}"
    else:
        action = build_partner_next_action_label(partner)
        label = f"{display_name} / {app_name} / {action}"
    if partner.status == "archived":
        label = f"{label}（アーカイブ）"
    return label


def build_partner_management_filter_options(include_archived: bool = False) -> dict[str, list[str]]:
    partners = load_partner_choices(include_archived=include_archived)
    app_names = sorted({partner.app_name.strip() for partner in partners if partner.app_name.strip()})
    statuses = sorted({partner.status.strip() for partner in partners if partner.status.strip()})
    return {
        "app_names": ["すべて"] + app_names,
        "statuses": ["すべて"] + statuses,
    }


def summarize_partner_management_rows(
    query: str = "",
    app_name: str = "すべて",
    status: str = "すべて",
    sparse_only: bool = False,
    include_archived: bool = False,
) -> list[dict[str, str]]:
    query = query.strip().lower()
    rows = []
    for partner in load_partner_choices(include_archived=include_archived):
        profile_card = build_partner_profile_card(partner)
        info_status = str(next((row["value"] for row in profile_card["summary"] if row["label"] == "情報量"), "未設定"))
        display_name = partner.display_name or PROFILE_DISPLAY_NAME_UNSET
        app_value = partner.app_name or "未設定"
        searchable = " ".join(
            [
                display_name,
                app_value,
                str(partner.profile.age or ""),
                partner.profile.location_hint or "",
                " ".join(partner.profile.hobbies),
                partner.status,
                build_partner_next_action_label(partner),
            ]
        ).lower()
        if query and query not in searchable:
            continue
        if app_name and app_name != "すべて" and app_value != app_name:
            continue
        if status and status != "すべて" and partner.status != status:
            continue
        if sparse_only and info_status not in {"情報少なめ", "一部不足"}:
            continue
        last_sent = max((record.sent_at for record in partner.sent_records if record.sent_at), default="-")
        rows.append(
            {
                "表示名": display_name,
                "アプリ": app_value,
                "年齢": str(partner.profile.age) if partner.profile.age is not None else "未設定",
                "エリア": partner.profile.location_hint or "未設定",
                "情報量": info_status,
                "会話状態": build_partner_next_action_label(partner),
                "ステータス": "非表示" if partner.status == "archived" else partner.status,
                "最終更新": partner.updated_at or partner.created_at or "-",
                "最後に送った日": last_sent,
                "メモ": "あり" if partner.notes else "なし",
            }
        )
    return rows


def update_partner_management_info_from_gui(
    partner_id: str,
    display_name: str,
    app_name: str,
    note: str = "",
    confirmed: bool = False,
) -> dict[str, Any]:
    if not confirmed:
        raise ValueError("更新前確認チェックを入れてください。")
    partner = load_partner(partner_id)
    changed = []
    normalized_display_name = display_name.strip() or PROFILE_DISPLAY_NAME_UNSET
    normalized_app_name = app_name.strip()
    if partner.display_name != normalized_display_name:
        partner.display_name = normalized_display_name
        changed.append("表示名")
    if partner.app_name != normalized_app_name:
        partner.app_name = normalized_app_name
        changed.append("アプリ名")
    if note.strip():
        partner.notes.append(PartnerNote(text=f"管理メモ: {note.strip()}", created_at=datetime.now().isoformat(timespec="seconds")))
        add_activity_event(partner, "note_added", f"管理メモ追加: {note.strip()}")
        changed.append("メモ")
    saved = save_updated_partner(partner)
    return {
        "partner": saved,
        "changed": changed,
        "message": "更新しました" if changed else "変更はありません",
    }


def archive_partner_from_gui(partner_id: str, reason: str = "", confirmed: bool = False) -> dict[str, Any]:
    if not confirmed:
        raise ValueError("非表示にする前の確認チェックを入れてください。")
    partner = load_partner(partner_id)
    archived = archive_partner(partner, reason.strip() or "管理画面から非表示")
    return {"partner": archived, "message": "この相手を非表示にしました。会話履歴や送信済み記録は削除していません。"}


def unarchive_partner_from_gui(partner_id: str, confirmed: bool = False) -> dict[str, Any]:
    if not confirmed:
        raise ValueError("再表示する前の確認チェックを入れてください。")
    partner = load_partner(partner_id)
    restored = unarchive_partner(partner, status="paused")
    return {"partner": restored, "message": "この相手を再表示しました。"}


def build_partner_next_action_label(partner: PartnerRecord) -> str:
    message_state = partner.message_state
    pending_count = len(get_pending_suggestions(partner))
    if message_state.awaiting_partner_reply:
        return "相手の返信待ち"
    if message_state.awaiting_user_action:
        return "返信を考える"
    if pending_count:
        return "候補を確認"
    if partner.conversation:
        return "次の返信候補を作る"
    if partner.status == "archived":
        return "アーカイブ済み"
    return "初回メッセージ候補を作る"


def build_partner_workspace_overview(partner: PartnerRecord) -> dict[str, Any]:
    stage = build_conversation_stage_summary(partner)
    pending_count = len(get_pending_suggestions(partner))
    return {
        "title": partner.display_name or PROFILE_DISPLAY_NAME_UNSET,
        "subtitle": f"{partner.app_name or 'アプリ未設定'} / {build_partner_next_action_label(partner)}",
        "next_action": build_partner_next_action_label(partner),
        "conversation_stage": stage["conversation_stage"] or "未設定",
        "temperature": stage["temperature"] or "不明",
        "pending_count": pending_count,
        "conversation_count": len(partner.conversation),
        "sent_count": len(partner.sent_records),
        "summary_rows": [
            {"label": "今やること", "value": build_partner_next_action_label(partner)},
            {"label": "会話ステージ", "value": stage["conversation_stage"] or "未設定"},
            {"label": "温度感", "value": stage["temperature"] or "不明"},
            {"label": "未確認候補", "value": f"{pending_count}件"},
        ],
        "detail": {
            "partner_id": partner.partner_id,
            "status": partner.status,
            "message_state": asdict(partner.message_state),
            "conversation_stage": stage,
        },
    }


def build_partner_profile_card(partner: PartnerRecord) -> dict[str, Any]:
    profile = partner.profile
    content_count = _partner_profile_content_count(partner)
    if content_count <= 1:
        info_status = "情報少なめ"
    elif content_count <= 3:
        info_status = "一部不足"
    else:
        info_status = "ある程度あり"
    return {
        "title": partner.display_name or PROFILE_DISPLAY_NAME_UNSET,
        "summary": [
            {"label": "表示名", "value": partner.display_name or PROFILE_DISPLAY_NAME_UNSET},
            {"label": "年齢", "value": profile.age if profile.age is not None else "未設定"},
            {"label": "エリア", "value": profile.location_hint or "未設定"},
            {"label": "アプリ", "value": partner.app_name or "未設定"},
            {"label": "情報量", "value": info_status},
        ],
        "profile_text": profile.profile_text.strip() or "プロフィール本文未設定",
        "sections": [
            {"title": "趣味・興味", "items": format_list_or_empty(profile.hobbies)},
            {"title": "写真から分かる印象メモ", "items": format_list_or_empty(profile.photos_memo)},
            {"title": "会話に使えそうな話題", "items": format_list_or_empty(_free_note_list(profile.free_notes or "", "conversation_hooks"))},
            {"title": "初回メッセージのヒント", "items": format_list_or_empty(_free_note_list(profile.free_notes or "", "first_message_hints"))},
            {"title": "避けた方がよさそうな話題", "items": format_list_or_empty(_free_note_list(profile.free_notes or "", "avoid_topics"))},
        ],
        "notes": _free_note_body(profile.free_notes or ""),
        "detail": {
            "partner_id": partner.partner_id,
            "status": partner.status,
        },
    }


def build_partner_summary(partner: PartnerRecord) -> dict[str, Any]:
    pending = get_pending_suggestions(partner)
    return {
        "partner_id": partner.partner_id,
        "display_name": partner.display_name or "-",
        "status": partner.status,
        "next_action": partner.message_state.next_action or "-",
        "partner_temperature": partner.analysis.partner_temperature,
        "pending_suggestions_count": len(pending),
        "message_state": asdict(partner.message_state),
    }


def build_partner_operational_display(partner: PartnerRecord) -> dict[str, Any]:
    summary = build_partner_summary(partner)
    stage = build_conversation_stage_summary(partner)
    pending_count = summary["pending_suggestions_count"]
    message_state = partner.message_state
    return {
        "basic": [
            {"label": "partner_id", "value": summary["partner_id"]},
            {"label": "表示名", "value": summary["display_name"]},
            {"label": "状態", "value": summary["status"] or "未設定"},
            {"label": "温度感", "value": stage["temperature"] or "未設定"},
        ],
        "conversation": [
            {"label": "最終送信", "value": "あり" if message_state.last_user_message or message_state.last_sent_at else "なし"},
            {"label": "最終返信", "value": "あり" if message_state.last_partner_message or message_state.last_received_at else "なし"},
            {"label": "返信待ち", "value": "はい" if message_state.awaiting_partner_reply else "いいえ"},
            {"label": "こちらの対応待ち", "value": "はい" if message_state.awaiting_user_action else "いいえ"},
            {"label": "未送信候補", "value": "あり" if pending_count else "なし"},
            {"label": "会話ステージ", "value": stage["conversation_stage"] or "未設定"},
            {"label": "次の一手", "value": message_state.next_action or stage["next_recommendation"] or "未設定"},
        ],
        "detail": {
            "message_state": asdict(message_state),
            "conversation_stage": stage,
        },
    }


def format_conversation_history(partner: PartnerRecord) -> list[dict[str, Any]]:
    rows = []
    for index, turn in enumerate(partner.conversation, start=1):
        rows.append(
            {
                "index": index,
                "speaker": turn.speaker,
                "speaker_label": "自分" if turn.speaker == "user" else "相手",
                "timestamp": turn.timestamp or "",
                "text": turn.text,
            }
        )
    return rows


def format_pending_suggestions(partner: PartnerRecord) -> list[dict[str, Any]]:
    return [
        {
            "suggestion_id": suggestion.suggestion_id,
            "purpose": suggestion.purpose,
            "created_at": suggestion.created_at,
            "status": suggestion.status,
            "text": suggestion.text,
        }
        for suggestion in get_pending_suggestions(partner)
    ]


def format_partner_notes(partner: PartnerRecord) -> list[dict[str, str]]:
    return [
        {
            "index": str(index),
            "created_at": note.created_at or "",
            "text": note.text,
        }
        for index, note in enumerate(partner.notes, start=1)
        if note.text.strip()
    ]


def build_partner_note_preview(text: str) -> dict[str, Any]:
    text = text.strip()
    warnings = detect_privacy_warnings([text]) if text else []
    return {
        "保存先": "partner.notes",
        "メモ": text or "-",
        "warnings": warnings,
        "local_save_only": True,
        "auto_send": False,
    }


def add_partner_note_from_gui(partner_id: str, text: str, confirmed: bool) -> dict[str, Any]:
    text = text.strip()
    if not confirmed:
        raise ValueError("確認チェックを入れてください。")
    if not text:
        raise ValueError("相手別メモを入力してください。")
    partner = load_partner(partner_id)
    if partner.status == "archived":
        raise ValueError("archivedのpartnerにはメモを追加できません。")
    warnings = detect_privacy_warnings([text])
    add_partner_note(partner, text)
    updated = load_partner(partner_id)
    return {
        "partner_id": partner_id,
        "notes_count": len(updated.notes),
        "warnings": warnings,
    }


def format_sent_suggestions_for_outcomes(partner: PartnerRecord) -> list[dict[str, Any]]:
    records = [
        _sent_record_to_display(record)
        for record in partner.sent_records
    ]
    recorded_suggestion_ids = {record.source_suggestion_id for record in partner.sent_records if record.source_suggestion_id}
    for suggestion in partner.pending_suggestions:
        if suggestion.status == "sent" and suggestion.suggestion_id not in recorded_suggestion_ids:
            records.append(_legacy_sent_suggestion_to_display(suggestion))
    return sorted(records, key=lambda item: item["sent_at"] or "")


def build_sent_outcome_preview(partner: PartnerRecord, sent_id: str, outcome_status: str, outcome_memo: str = "") -> dict[str, Any]:
    record = _find_sent_record_or_legacy(partner, sent_id)
    outcome_status = outcome_status if outcome_status in SENT_OUTCOME_STATUS_OPTIONS else "未確認"
    outcome_memo = outcome_memo.strip()
    warnings = detect_privacy_warnings([outcome_memo])
    return {
        "partner_id": partner.partner_id,
        "sent_id": record["sent_id"],
        "source_type": record["source_type"],
        "source_suggestion_id": record["source_suggestion_id"] or "-",
        "sent_at": record["sent_at"] or "-",
        "送信文": record["text"],
        "結果ステータス": outcome_status,
        "結果メモ": outcome_memo or "-",
        "warnings": warnings,
        "local_save_only": True,
        "auto_send": False,
    }


def update_sent_outcome_from_gui(
    partner_id: str,
    sent_id: str,
    outcome_status: str,
    outcome_memo: str = "",
    confirmed: bool = False,
) -> dict[str, Any]:
    if not confirmed:
        raise ValueError("確認チェックを入れてください。")
    if outcome_status not in SENT_OUTCOME_STATUS_OPTIONS:
        raise ValueError(f"Invalid outcome status: {outcome_status}")
    partner = load_partner(partner_id)
    if partner.status == "archived":
        raise ValueError("archivedのpartnerには送信結果メモを追加できません。")
    record = _find_sent_record(partner, sent_id)
    outcome_memo = outcome_memo.strip()
    warnings = detect_privacy_warnings([outcome_memo])
    record.outcome_status = outcome_status
    record.outcome_memo = outcome_memo
    record.outcome_updated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    if record.source_suggestion_id:
        suggestion = _find_sent_suggestion(partner, record.source_suggestion_id)
        suggestion.outcome_status = outcome_status
        suggestion.outcome_memo = outcome_memo
        suggestion.outcome_updated_at = record.outcome_updated_at
    add_activity_event(partner, "sent_outcome_updated", f"{sent_id} 結果: {outcome_status}", sent_id, record.outcome_updated_at)
    save_updated_partner(partner)
    return {
        "partner_id": partner_id,
        "sent_id": sent_id,
        "source_type": record.source_type,
        "source_suggestion_id": record.source_suggestion_id or "",
        "outcome_status": outcome_status,
        "outcome_memo": outcome_memo,
        "warnings": warnings,
    }


def format_timeline_items(partner: PartnerRecord, limit: int = 50) -> list[dict[str, Any]]:
    events = build_timeline_events(partner)
    if limit > 0:
        events = events[-limit:]
    return [
        {
            "created_at": event.created_at or "",
            "actor": event.actor,
            "event_type": event.event_type,
            "summary": event.summary,
            "text": event.text or "",
            "related_id": event.related_id or "",
        }
        for event in events
    ]


def get_generation_mode_for_partner(partner: PartnerRecord) -> str:
    if partner.status == "archived":
        return "blocked"
    if get_pending_suggestions(partner):
        return "blocked"
    if partner.message_state.awaiting_partner_reply:
        return "blocked"
    if not partner.conversation:
        if partner.profile.profile_text.strip() or partner.profile.hobbies or partner.profile.photos_memo:
            return "first"
        return "blocked"
    latest_partner = next((turn for turn in reversed(partner.conversation) if turn.speaker == "partner"), None)
    if latest_partner and partner.message_state.awaiting_user_action:
        return "reply"
    return "blocked"


def build_generation_status_message(partner: PartnerRecord) -> str:
    pending_count = len(get_pending_suggestions(partner))
    if partner.status == "archived":
        return "archivedのため候補生成できません。"
    if pending_count:
        return "既存のpending_suggestionsがあります。確認または破棄してから生成してください。"
    if partner.message_state.awaiting_partner_reply:
        return "現在は相手の返信待ちです。新しい候補は生成しません。"
    mode = get_generation_mode_for_partner(partner)
    if mode == "first":
        return "初回メッセージ候補を生成できます。自動送信ではありません。"
    if mode == "reply":
        return "返信候補を生成できます。自動送信ではありません。"
    return "候補生成に必要なプロフィール情報または相手発話が不足しています。"


def can_generate_suggestion(partner: PartnerRecord) -> bool:
    return get_generation_mode_for_partner(partner) in {"first", "reply"}


def generate_suggestion_for_gui(partner_id: str) -> dict[str, Any]:
    partner = load_partner(partner_id)
    mode = get_generation_mode_for_partner(partner)
    if mode not in {"first", "reply"}:
        raise ValueError(build_generation_status_message(partner))
    purpose = "first_message" if mode == "first" else "reply"
    request = GenerationRequest(
        target_profile=_target_from_partner(partner),
        user_profile=load_user_profile(),
        conversation_history=list(partner.conversation),
        purpose=purpose,
        current_stage="first_message" if mode == "first" else "auto",
    )
    result = generate(request)
    text = result.best_message
    partner.analysis.partner_temperature = result.partner_temperature
    partner.analysis.safe_topics = list(result.safe_topics)
    partner.analysis.light_only_topics = list(result.light_only_topics)
    partner.analysis.avoid_topics = list(result.avoid_topics)
    partner.analysis.next_strategy = result.recommended_strategy
    partner.analysis.last_suggested_message = text
    suggestion = add_suggestion(
        partner,
        purpose="first" if mode == "first" else "reply",
        text=text,
        source="gui-generate-first" if mode == "first" else "gui-generate-reply",
        safety_result="OK",
    )
    if mode == "first":
        partner.status = "first_message_suggested"
        save_updated_partner(partner)
    elif partner.status in {"new_profile", "first_message_sent", "first_message_suggested"}:
        partner.status = "chatting"
        save_updated_partner(partner)
    return {
        "mode": mode,
        "suggestion_id": suggestion.suggestion_id,
        "text": suggestion.text,
        "status": suggestion.status,
    }


def build_conversation_stage_summary(partner: PartnerRecord) -> dict[str, Any]:
    partner_turns = [turn for turn in partner.conversation if turn.speaker == "partner"]
    user_turns = [turn for turn in partner.conversation if turn.speaker == "user"]
    round_count = min(len(partner_turns), len(user_turns))
    latest_partner = partner_turns[-1].text if partner_turns else ""
    raw_temperature = estimate_partner_temperature(partner.conversation) if partner.conversation else "unknown"
    partner_notes = _partner_notes_text(partner)
    outcome_summaries = _recent_outcome_summaries(partner)
    temperature, temperature_reasons = _build_temperature_summary(partner, raw_temperature, partner_notes, outcome_summaries)
    if not partner.conversation:
        stage = "初回前"
        next_step = "プロフィールに触れた初回候補を作る"
    elif partner.message_state.awaiting_partner_reply:
        stage = "初回送信済み・返信待ち" if round_count == 0 else "一旦保留"
        next_step = "今は追撃せず、返信待ちがよさそうです"
    elif round_count <= 1:
        stage = "1往復目"
        next_step = "今回は「共感・リアクション重視」＋「質問を1つ」がよさそうです"
    elif round_count == 2:
        stage = "2往復目"
        next_step = "今回は「相手の趣味を広げる」が自然です"
    elif temperature == "高め" and round_count >= 3:
        stage = "電話提案を検討してよさそう"
        next_step = "相手の反応が良いので、控えめな電話提案を検討してもよさそうです"
    elif temperature in {"高め", "普通"} and round_count >= 4:
        stage = "会う提案を検討してよさそう"
        next_step = "会う提案より先に、短めの電話提案や軽い確認が自然です"
    elif temperature == "低め":
        stage = "相手の反応が薄い"
        next_step = "まだ電話や会う提案は避け、短く返しやすい雑談が安全です"
    elif round_count >= 3:
        stage = "雑談継続がよさそう"
        next_step = "急いで誘わず、もう1往復雑談を続けるのが安全です"
    else:
        stage = "判定不能"
        next_step = "相手の返信内容をもう少し見てから判断します"
    action_judgements = _build_action_judgements(round_count, temperature, partner_notes, outcome_summaries, partner)
    cautions = _build_guidance_cautions(action_judgements, partner_notes, outcome_summaries)
    return {
        "stage": stage,
        "conversation_stage": stage,
        "round_count": round_count,
        "partner_temperature": raw_temperature,
        "temperature": temperature,
        "temperature_reasons": temperature_reasons,
        "latest_partner_message": latest_partner or "-",
        "next_recommendation": next_step,
        "caution_points": cautions,
        "action_judgements": action_judgements,
        "phone_suggestion": action_judgements["電話に誘う"]["status"],
        "meet_suggestion": action_judgements["会う提案をする"]["status"],
        "line_exchange": action_judgements["LINE交換を提案する"],
        "adult_topic": action_judgements["少し大人っぽい雰囲気にする"],
    }


def build_generation_preflight(partner: PartnerRecord, objectives: list[str] | None = None, tone: str = "", place_hint: str = "") -> dict[str, Any]:
    stage = build_conversation_stage_summary(partner)
    objectives = [item for item in (objectives or []) if item]
    warnings = []
    partner_notes = _partner_notes_text(partner)
    recent_outcomes = _recent_outcome_summaries(partner)
    action_judgements = stage["action_judgements"]
    if any("電話" in item for item in objectives) and stage["round_count"] < 2:
        warnings.append("電話提案はまだ早い可能性があります。2から3往復後で、相手の反応が良い場合だけ検討してください。")
    if any("会う" in item for item in objectives) and stage["round_count"] < 3:
        warnings.append("会う提案はまだ早い可能性があります。電話後、または十分に自然な会話が続いた後まで待つ方が安全です。")
    if any("LINE" in item for item in objectives) and stage["round_count"] < 2:
        warnings.append("LINE交換提案は唐突になりやすいため注意してください。LINE IDそのものは保存しないでください。")
    if (any("大人っぽい" in item for item in objectives) or "大人っぽい" in tone) and stage["round_count"] < 2:
        warnings.append("大人っぽい雰囲気は距離が近すぎる印象になりやすいため、初回や1往復目では控えめにしてください。")
    if partner_notes:
        note_text = partner_notes.lower()
        if any("電話" in item for item in objectives) and "電話" in partner_notes and any(word in partner_notes for word in ["早", "まだ", "控え"]):
            warnings.append("相手別メモ上、電話はまだ早そうです。電話提案を送る前に温度感を確認してください。")
        if any("LINE" in item for item in objectives) and "LINE" in partner_notes and any(word in partner_notes for word in ["早", "まだ", "控え"]):
            warnings.append("相手別メモ上、LINE交換はまだ早そうです。IDそのものは保存しないでください。")
        if "旅行" in partner_notes and not any("電話" in item or "会う" in item or "LINE" in item for item in objectives):
            warnings.append("相手別メモに旅行の反応が良い記録があります。自然な範囲で旅行話題を広げる候補が合いそうです。")
        if "night" in note_text or "夜" in partner_notes:
            warnings.append("相手別メモに夜の返信傾向があります。送る時間帯はユーザーが手動で判断してください。")
    for objective in objectives:
        judgement = _judgement_for_objective(objective, action_judgements)
        if not judgement:
            continue
        status = judgement["status"]
        reason = judgement["reason"]
        if status in {"まだ早い", "非推奨"}:
            warnings.append(f"{objective}: {status}。{reason}")
        elif status == "控えめなら可":
            warnings.append(f"{objective}: {status}。送る場合は相手が断りやすい短い文にしてください。")
    return {
        "partner_id": partner.partner_id,
        "generation_mode": get_generation_mode_for_partner(partner),
        "objectives": objectives or ["指定なし"],
        "tone": tone or "自然",
        "place_hint": place_hint.strip() or "-",
        "stage": stage,
        "conversation_stage": stage["conversation_stage"],
        "temperature": {
            "label": stage["temperature"],
            "reasons": stage["temperature_reasons"],
        },
        "next_recommendation": stage["next_recommendation"],
        "caution_points": stage["caution_points"],
        "action_judgements": action_judgements,
        "line_exchange": stage["line_exchange"],
        "adult_topic": stage["adult_topic"],
        "partner_notes": {
            "has_notes": bool(partner_notes),
            "count": len([note for note in partner.notes if note.text.strip()]),
            "summary": _truncate_for_display(partner_notes, 240) or "-",
        },
        "recent_sent_outcomes": recent_outcomes or ["-"],
        "warnings": warnings,
        "local_save_only": True,
        "auto_send": False,
    }


def generate_suggestion_variants_for_gui(
    partner_id: str,
    objectives: list[str] | None = None,
    tone: str = "自然",
    place_hint: str = "",
) -> dict[str, Any]:
    partner = load_partner(partner_id)
    mode = get_generation_mode_for_partner(partner)
    if mode not in {"first", "reply"}:
        raise ValueError(build_generation_status_message(partner))
    purpose = "first_message" if mode == "first" else "reply"
    request = GenerationRequest(
        target_profile=_target_from_partner(partner),
        user_profile=load_user_profile(),
        conversation_history=list(partner.conversation),
        purpose=purpose,
        current_stage="first_message" if mode == "first" else "auto",
    )
    result = generate(request)
    base_candidates = _unique_candidates([result.best_message, *result.message_candidates])
    variants = []
    selected_objectives = [item for item in (objectives or []) if item]
    preflight = build_generation_preflight(partner, selected_objectives, tone, place_hint)
    stage = preflight["stage"]
    for index in range(3):
        base = base_candidates[index % len(base_candidates)]
        objective = selected_objectives[index % len(selected_objectives)] if selected_objectives else "質問を1つ入れる"
        text = _shape_candidate_for_objective(base, objective, tone, place_hint, mode, index, partner, stage)
        quality_check = _candidate_quality_check(text, objective, partner, stage)
        metadata = _variant_metadata(index, objective, stage, quality_check)
        suggestion = add_suggestion(
            partner,
            purpose="first" if mode == "first" else "reply",
            text=text,
            source="gui-generate-variants",
            safety_result="OK",
        )
        variants.append(
            {
                "suggestion_id": suggestion.suggestion_id,
                "text": suggestion.text,
                "purpose": suggestion.purpose,
                "objective": objective,
                "tone": tone or "自然",
                "title": metadata["title"],
                "use_case": metadata["use_case"],
                "aim": metadata["aim"],
                "conversation_stage": stage["conversation_stage"],
                "temperature": stage["temperature"],
                "compatibility": metadata["compatibility"],
                "next_recommendation": stage["next_recommendation"],
                "partner_notes": _truncate_for_display(_partner_notes_text(partner), 240) or "-",
                "recent_sent_outcomes": _recent_outcome_summaries(partner),
                "safety_notes": _candidate_safety_notes(text, objective, partner),
                "quality_check": quality_check,
            }
        )
    partner.analysis.partner_temperature = result.partner_temperature
    partner.analysis.safe_topics = list(result.safe_topics)
    partner.analysis.light_only_topics = list(result.light_only_topics)
    partner.analysis.avoid_topics = list(result.avoid_topics)
    partner.analysis.next_strategy = result.recommended_strategy
    partner.analysis.last_suggested_message = variants[0]["text"]
    if mode == "first":
        partner.status = "first_message_suggested"
    elif partner.status in {"new_profile", "first_message_sent", "first_message_suggested"}:
        partner.status = "chatting"
    save_updated_partner(partner)
    saved_stage = build_conversation_stage_summary(partner)
    return {
        "mode": mode,
        "variants": variants,
        "stage": saved_stage,
        "preflight": build_generation_preflight(partner, selected_objectives, tone, place_hint),
        "conversation_stage": saved_stage["conversation_stage"],
        "temperature": saved_stage["temperature"],
        "next_recommendation": saved_stage["next_recommendation"],
        "partner_notes": _truncate_for_display(_partner_notes_text(partner), 240) or "-",
        "recent_sent_outcomes": _recent_outcome_summaries(partner),
    }


def can_mark_suggestion_sent(partner: PartnerRecord, suggestion_id: str, confirmed: bool = False) -> bool:
    if partner.status == "archived" or not confirmed:
        return False
    return any(suggestion.suggestion_id == suggestion_id and suggestion.status == "pending" for suggestion in partner.pending_suggestions)


def build_mark_sent_preview(partner: PartnerRecord, suggestion_id: str | None = None, custom_text: str = "") -> dict[str, Any]:
    custom_text = custom_text.strip()
    if suggestion_id:
        suggestion = next(
            (item for item in partner.pending_suggestions if item.suggestion_id == suggestion_id and item.status == "pending"),
            None,
        )
        if suggestion is None:
            raise ValueError(f"pending suggestion not found: {suggestion_id}")
        text = suggestion.text
        source = f"suggestion_id: {suggestion_id}"
        remaining_note = "-"
    else:
        if not custom_text:
            raise ValueError("実際に送信した文を入力してください。")
        text = custom_text
        source = "custom text"
        remaining = [item.suggestion_id for item in get_pending_suggestions(partner)]
        remaining_note = " / ".join(remaining) if remaining else "-"
    return {
        "partner_id": partner.partner_id,
        "record_type": source,
        "source_type": "generated_suggestion" if suggestion_id else "custom_text",
        "sent_id": "保存時に自動採番",
        "speaker": "user",
        "text": text,
        "warnings": detect_privacy_warnings([text]),
        "conversation_history": "user発話を1件追加",
        "message_state": "相手の返信待ちへ更新",
        "remaining_pending_suggestions": remaining_note,
        "local_record_only": True,
    }


def mark_suggestion_sent_from_gui(partner_id: str, suggestion_id: str, confirmed: bool) -> dict[str, Any]:
    partner = load_partner(partner_id)
    if not can_mark_suggestion_sent(partner, suggestion_id, confirmed=confirmed):
        raise ValueError("確認チェックがないか、送信済み記録できるpending suggestionではありません。")
    suggestion = mark_suggestion_sent(partner, suggestion_id)
    stored = load_partner(partner_id)
    sent_record = next((record for record in stored.sent_records if record.source_suggestion_id == suggestion_id), None)
    return {
        "partner_id": partner.partner_id,
        "suggestion_id": suggestion.suggestion_id,
        "sent_id": sent_record.sent_id if sent_record else f"legacy_generated_{suggestion.suggestion_id}",
        "source_type": "generated_suggestion",
        "text": suggestion.text,
        "status": suggestion.status,
        "remaining_pending_suggestions": len(get_pending_suggestions(stored)),
    }


def mark_custom_text_sent_from_gui(partner_id: str, text: str, confirmed: bool) -> dict[str, Any]:
    text = text.strip()
    if not confirmed:
        raise ValueError("確認チェックを入れてください。")
    if not text:
        raise ValueError("実際に送信した文を入力してください。")
    partner = load_partner(partner_id)
    if partner.status == "archived":
        raise ValueError("archivedのpartnerには送信済み記録できません。")
    pending_before = len(get_pending_suggestions(partner))
    sent_record = mark_text_sent(partner, text)
    stored = load_partner(partner_id)
    return {
        "partner_id": stored.partner_id,
        "sent_id": sent_record.sent_id,
        "source_type": sent_record.source_type,
        "text": text,
        "remaining_pending_suggestions": pending_before,
        "note": "custom textで記録したため、元候補がpendingに残る場合があります。",
    }


def can_discard_suggestion(partner: PartnerRecord, suggestion_id: str, confirmed: bool = False) -> bool:
    if partner.status == "archived" or not confirmed:
        return False
    return any(suggestion.suggestion_id == suggestion_id and suggestion.status == "pending" for suggestion in partner.pending_suggestions)


def build_discard_suggestion_preview(partner: PartnerRecord, suggestion_id: str, reason: str = "") -> dict[str, Any]:
    suggestion = next(
        (item for item in partner.pending_suggestions if item.suggestion_id == suggestion_id and item.status == "pending"),
        None,
    )
    if suggestion is None:
        raise ValueError(f"pending suggestion not found: {suggestion_id}")
    remaining = [item.suggestion_id for item in get_pending_suggestions(partner) if item.suggestion_id != suggestion_id]
    return {
        "partner_id": partner.partner_id,
        "discard_target": suggestion_id,
        "purpose": suggestion.purpose,
        "reason": reason.strip() or "GUIから未使用候補として破棄",
        "conversation_history": "変更しない",
        "message_state": "既存discard処理に従ってnext_actionを再計算",
        "remaining_pending_suggestions": " / ".join(remaining) if remaining else "-",
        "local_record_only": True,
    }


def discard_suggestion_from_gui(partner_id: str, suggestion_id: str, confirmed: bool, reason: str = "") -> dict[str, Any]:
    partner = load_partner(partner_id)
    if not can_discard_suggestion(partner, suggestion_id, confirmed=confirmed):
        raise ValueError("確認チェックがないか、破棄できるpending suggestionではありません。")
    conversation_count_before = len(partner.conversation)
    suggestion = discard_suggestion(partner, suggestion_id)
    stored = load_partner(partner_id)
    return {
        "partner_id": stored.partner_id,
        "suggestion_id": suggestion.suggestion_id,
        "status": suggestion.status,
        "discard_reason": reason.strip() or "GUIから未使用候補として破棄",
        "conversation_history_unchanged": len(stored.conversation) == conversation_count_before,
        "remaining_pending_suggestions": len(get_pending_suggestions(stored)),
        "next_action": stored.message_state.next_action,
    }


def split_form_list(value: str) -> list[str]:
    if not value:
        return []
    normalized = value.replace(",", "\n").replace("、", "\n")
    return [item.strip() for item in normalized.splitlines() if item.strip() and not _is_profile_unset_value(item)]


def build_profile_form_from_paste(text: str) -> tuple[dict[str, Any], list[str]]:
    extracted = {field: "" for field in PROFILE_PASTE_FIELDS}
    warnings = []
    current_field: str | None = None
    unknown_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        field, value = _split_profile_paste_line(line)
        if field:
            current_field = field
            cleaned_value = _clean_profile_paste_value(value)
            if cleaned_value:
                extracted[field] = _append_profile_field_value(extracted[field], cleaned_value)
            continue
        if current_field in PROFILE_MULTILINE_FIELDS:
            cleaned = _clean_profile_paste_value(_strip_profile_list_marker(line))
            if cleaned:
                extracted[current_field] = _append_profile_field_value(extracted[current_field], cleaned)
        elif current_field in PROFILE_SCALAR_FIELDS and not extracted.get(current_field):
            cleaned = _clean_profile_paste_value(_strip_profile_list_marker(line))
            if cleaned:
                extracted[current_field] = cleaned
        else:
            unknown_lines.append(line)
    if unknown_lines and not extracted["profile_text"]:
        extracted["profile_text"] = "\n".join(unknown_lines)
    elif unknown_lines:
        extracted["notes"] = _append_profile_field_value(extracted["notes"], "\n".join(unknown_lines))
    safety_warnings = detect_profile_safety_warnings(extracted)
    if safety_warnings:
        warnings.append("保存前に見直してください: " + " / ".join(safety_warnings))
    return extracted, warnings


def build_profile_label_candidate(
    display_name: str = "",
    now: datetime | None = None,
    existing_labels: set[str] | None = None,
) -> dict[str, Any]:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    display_name = str(display_name or "").strip()
    base = _safe_profile_label_base(display_name)
    reason = "display_nameを安全なASCIIの補助情報として使い、内部保存IDを自動生成しました" if base != "profile" else "labelはユーザー入力せず、内部保存IDを自動生成しました"
    label = f"profile_{base}_{timestamp}" if base != "profile" else f"profile_{timestamp}"
    label = _deduplicate_profile_label(label, existing_labels=existing_labels)
    return {
        "label": label,
        "label_source": "自動生成",
        "label_reason": reason,
        "editable": False,
    }


def merge_profile_form_with_paste(form: dict[str, Any], pasted_form: dict[str, Any]) -> dict[str, Any]:
    merged = dict(form)
    for key, value in pasted_form.items():
        if key not in merged or not str(merged.get(key, "")).strip():
            merged[key] = value
    return merged


def build_profile_save_payload(
    form_values: dict[str, Any],
    pasted_form: dict[str, Any],
    label_candidate: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str], list[str]]:
    merged = merge_profile_form_with_paste(form_values, pasted_form)
    merged, label_meta = apply_profile_label_candidate(merged, label_candidate)
    merged = normalize_profile_save_form(merged)
    return merged, label_meta, validate_profile_form(merged), build_profile_save_warnings(merged)


def normalize_profile_save_form(form: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(form)
    if not _is_safe_profile_label(str(normalized.get("label", "")).strip()):
        normalized["label"] = build_profile_label_candidate(str(normalized.get("display_name", "")))["label"]
    if _is_profile_unset_value(normalized.get("display_name", "")):
        normalized["display_name"] = PROFILE_DISPLAY_NAME_UNSET
    normalized.setdefault("photo_memo", "")
    normalized.setdefault("interests", "")
    normalized.setdefault("profile_text", "")
    return normalized


def apply_profile_label_candidate(form: dict[str, Any], candidate: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    merged = dict(form)
    explicit_label = str(merged.get("label", "")).strip()
    candidate = candidate or build_profile_label_candidate(str(merged.get("display_name", "")))
    merged["label"] = candidate["label"]
    if explicit_label and explicit_label != candidate["label"]:
        candidate = {
            **candidate,
            "ignored_input_label": explicit_label,
            "label_reason": "貼り付け内容や補助入力欄のlabelは使わず、内部保存IDを自動生成しました",
        }
    return merged, candidate


def build_profile_paste_preview(text: str, label_candidate: dict[str, Any] | None = None) -> dict[str, Any]:
    extracted, warnings = build_profile_form_from_paste(text)
    pasted_label = str(extracted.get("label", "")).strip()
    label_meta = label_candidate or build_profile_label_candidate(str(extracted.get("display_name", "")))
    if pasted_label:
        label_meta = {
            **label_meta,
            "ignored_input_label": pasted_label,
            "label_reason": "貼り付け内容のlabelは使わず、保存時に内部IDを自動生成します",
        }
    extracted["label"] = label_meta["label"]
    extracted_fields = {key: extracted.get(key) or "未設定" for key in PROFILE_PASTE_FIELDS}
    missing_fields = [key for key, value in extracted.items() if not value]
    recommended_missing_fields = _profile_missing_fields(extracted)
    return {
        "extracted_fields": extracted_fields,
        "summary": [
            {"label": "保存ID", "value": "自動生成予定"},
            {"label": "保存IDの扱い", "value": "ユーザー入力不要"},
            {"label": "表示名", "value": extracted_fields["display_name"]},
            {"label": "アプリ", "value": extracted_fields["app_name"]},
            {"label": "年齢", "value": extracted_fields["age"]},
            {"label": "エリア", "value": extracted_fields["area"]},
        ],
        "profile_text": extracted_fields["profile_text"],
        "sections": [
            {"title": PROFILE_PASTE_LABELS["interests"], "items": format_list_or_empty(split_form_list(str(extracted.get("interests", ""))))},
            {"title": PROFILE_PASTE_LABELS["photo_memo"], "items": format_list_or_empty(split_form_list(str(extracted.get("photo_memo", ""))))},
            {"title": PROFILE_PASTE_LABELS["conversation_hooks"], "items": format_list_or_empty(split_form_list(str(extracted.get("conversation_hooks", ""))))},
            {"title": PROFILE_PASTE_LABELS["first_message_hints"], "items": format_list_or_empty(split_form_list(str(extracted.get("first_message_hints", ""))))},
            {"title": PROFILE_PASTE_LABELS["avoid_topics"], "items": format_list_or_empty(split_form_list(str(extracted.get("avoid_topics", ""))))},
            {"title": PROFILE_PASTE_LABELS["safety_notes"], "items": format_list_or_empty(split_form_list(str(extracted.get("safety_notes", ""))))},
        ],
        "notes": extracted_fields["notes"],
        "missing_labels": [PROFILE_PASTE_LABELS.get(key, key) for key in recommended_missing_fields],
        "required_missing_fields": [],
        "recommended_missing_fields": recommended_missing_fields,
        "missing_fields": missing_fields,
        "warnings": warnings,
        "review_notes": [
            "抽出できなかった項目や違う項目は、保存前に下の入力欄で修正できます。",
            "labelは内部保存IDとして自動生成します。ChatGPTプロジェクト出力やユーザー入力には不要です。",
            "スクリーンショット画像や顔写真そのものではなく、読み取ったテキストと印象メモだけを保存します。",
            "本名、勤務先、学校名、LINE ID、SNS ID、住所、電話番号、メールアドレスは保存しないでください。",
        ],
        "manual_review_required": True,
        "saves_images": False,
        "auto_send": False,
        "label_meta": label_meta,
        "detail": extracted_fields,
    }


def build_profile_ocr_privacy_notes() -> list[str]:
    return [
        "画像そのものは保存しません",
        "顔写真そのものは保存しません",
        "スクリーンショット画像そのものは保存しません",
        "OCRで読み取った文字だけを確認用に表示します",
        "保存する前に必ず内容を確認してください",
        "本名、勤務先、学校名、LINE ID、SNS ID、住所、電話番号、メールアドレスは保存しないでください",
    ]


def build_profile_ocr_failure_guidance() -> dict[str, list[str]]:
    return {
        "考えられる理由": [
            "クリップボードに画像が入っていない",
            "画像ではなくテキストをコピーしている",
            "OCR環境が未設定",
            "文字が小さすぎる",
            "画像がぼやけている",
            "日本語OCRの設定が不足している",
        ],
        "対処": [
            "Windowsキー + Shift + S で範囲選択し直してください",
            "画像を大きめに切り取ってください",
            "文字が見える部分だけを切り取ってください",
            "うまくいかない場合は、画像ではなくテキストを手入力またはメモ帳経由で貼り付けてください",
            "画像ファイルアップロード方式も試してください",
        ],
    }


def get_profile_ocr_environment_status() -> dict[str, Any]:
    messages: list[str] = []
    languages: list[str] = []
    pillow_available = False
    imagegrab_available = False
    pytesseract_available = False
    tesseract_available = False
    tesseract_version = ""
    tesseract_path = shutil.which("tesseract") or ""

    try:
        import PIL  # noqa: F401

        pillow_available = True
    except Exception:
        messages.append("Pillowが未設定のため、画像ファイル読み取りが使えません。")

    try:
        from PIL import ImageGrab  # noqa: F401

        imagegrab_available = True
    except Exception:
        messages.append("Pillow ImageGrabが未設定のため、クリップボード画像読み取りが使えません。")

    try:
        import pytesseract

        pytesseract_available = True
        try:
            tesseract_version = str(pytesseract.get_tesseract_version())
            languages = list(pytesseract.get_languages(config=""))
            tesseract_available = True
        except Exception as exc:
            messages.append(f"Tesseract OCR本体を確認できません: {exc}")
    except Exception:
        messages.append("pytesseractが未設定です。OCRを使う場合はPython環境へ追加してください。")

    if not tesseract_path and not tesseract_available:
        messages.append("tesseract.exe がPATHから見つかりません。")
    if tesseract_available and "jpn" not in languages:
        messages.append("日本語OCRデータ jpn が見つかりません。日本語プロフィールは正しく読めない可能性があります。")
    if tesseract_available and "eng" not in languages:
        messages.append("英語OCRデータ eng が見つかりません。")

    return {
        "summary": "設定済み" if pytesseract_available and tesseract_available else "未設定",
        "pillow": pillow_available,
        "imagegrab": imagegrab_available,
        "pytesseract": pytesseract_available,
        "tesseract": tesseract_available,
        "tesseract_path": tesseract_path or "未検出",
        "tesseract_version": tesseract_version or "未検出",
        "languages": languages,
        "japanese": "jpn" in languages,
        "english": "eng" in languages,
        "messages": messages,
        "alternatives": ["テキスト貼り付け", "画像ファイル選択", "メモ帳経由で貼り付け"],
    }


def build_profile_ocr_text_preview(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    return {
        "text": cleaned,
        "text_length": len(cleaned),
        "warnings": detect_profile_safety_warnings({"ocr_text": cleaned}) if cleaned else [],
        "auto_save": False,
        "image_saved": False,
    }


def get_clipboard_image_for_ocr() -> tuple[Any | None, list[str]]:
    try:
        from PIL import ImageGrab
    except Exception:
        return None, ["PillowのImageGrabが利用できないため、クリップボード画像を取得できません。"]

    try:
        clipboard = ImageGrab.grabclipboard()
    except Exception as exc:
        return None, [f"クリップボード画像を取得できませんでした: {exc}"]
    if clipboard is None:
        return None, ["クリップボードに画像がありません。"]
    if isinstance(clipboard, list):
        return None, ["クリップボードにはファイル参照が入っています。画像ファイルアップロード方式を使ってください。"]
    if not hasattr(clipboard, "convert"):
        return None, ["クリップボードの内容は画像として扱えません。"]
    return clipboard, []


def load_uploaded_image_for_ocr(data: bytes) -> tuple[Any | None, list[str]]:
    try:
        from PIL import Image
    except Exception:
        return None, ["Pillowが利用できないため、画像ファイルを読み取れません。"]
    try:
        image = Image.open(BytesIO(data))
        image.load()
        return image, []
    except Exception as exc:
        return None, [f"画像ファイルを読み取れませんでした: {exc}"]


def extract_profile_text_from_image(image: Any, languages: str = "jpn+eng") -> dict[str, Any]:
    try:
        import pytesseract
    except Exception:
        return {
            "ok": False,
            "text": "",
            "engine": "pytesseract",
            "errors": ["OCR環境が未設定です。pytesseract と Tesseract OCR本体を設定してください。"],
            "warnings": [],
        }

    try:
        if hasattr(image, "convert"):
            image = image.convert("RGB")
        text = pytesseract.image_to_string(image, lang=languages).strip()
    except Exception as exc:
        return {
            "ok": False,
            "text": "",
            "engine": "pytesseract",
            "errors": [f"OCRに失敗しました: {exc}"],
            "warnings": [],
        }
    preview = build_profile_ocr_text_preview(text)
    errors = [] if text else ["画像から文字を読み取れませんでした。"]
    return {
        "ok": bool(text),
        "text": text,
        "engine": "pytesseract",
        "errors": errors,
        "warnings": preview["warnings"],
    }


def validate_profile_form(form: dict[str, Any]) -> list[str]:
    errors = []
    label = str(form.get("label", "")).strip()
    if not label:
        errors.append("保存IDを自動生成できませんでした。もう一度試すか、アプリを再起動してください。")
    else:
        try:
            validate_real_profile_label(label)
        except ValueError:
            errors.append("保存IDの形式が正しくありません。もう一度試すか、アプリを再起動してください。")
    return errors


def build_profile_save_warnings(form: dict[str, Any]) -> list[str]:
    missing = _profile_missing_fields(form)
    if not missing:
        return []
    return ["情報が少ないプロフィールとして保存できます。不足項目はあとで補完できます。", *[f"不足項目: {field}" for field in missing]]


def build_profile_save_debug_info(
    form: dict[str, Any],
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    has_profile_input: bool = True,
) -> dict[str, Any]:
    photo_items = split_form_list(str(form.get("photo_memo", "")))
    interest_items = split_form_list(str(form.get("interests", "")))
    missing = _profile_missing_fields(form)
    validation_errors = list(errors or validate_profile_form(form))
    return {
        "save_payload.label": str(form.get("label", "")).strip(),
        "save_payload.display_name": str(form.get("display_name", "")).strip(),
        "save_payload.has_profile_text": bool(_profile_text_value(form, "profile_text")),
        "save_payload.photo_memo_count": len(photo_items),
        "save_payload.interests_count": len(interest_items),
        "missing_fields": missing,
        "profile_status": build_profile_completion_status(form),
        "validation_result": "ok" if not validation_errors else "error",
        "validation_errors": validation_errors,
        "warnings": list(warnings or []),
        "has_profile_input": has_profile_input,
        "can_save": has_profile_input and not validation_errors,
    }


def build_profile_completion_status(form: dict[str, Any]) -> str:
    missing = _profile_missing_fields(form)
    has_profile_content = bool(_profile_text_value(form, "profile_text") or split_form_list(str(form.get("photo_memo", ""))))
    content_signal_count = _profile_content_signal_count(form)
    if content_signal_count <= 1 or not has_profile_content:
        return "minimal"
    if missing:
        return "incomplete"
    return "complete"


def detect_profile_safety_warnings(form: dict[str, Any]) -> list[str]:
    texts = [str(value) for value in form.values() if value is not None]
    warnings = set(detect_privacy_warnings(texts))
    joined = "\n".join(texts)
    joined_lower = joined.lower()
    for word in PROFILE_SAFETY_WORDS:
        if word.lower() in joined_lower:
            warnings.add(word)
    for label, pattern in PROFILE_SAFETY_PATTERNS.items():
        if pattern.search(joined):
            warnings.add(label)
    return sorted(warnings)


def build_real_profile_from_form(form: dict[str, Any]) -> dict[str, Any]:
    photo_items = split_form_list(str(form.get("photo_memo", "")))
    profile_text = _profile_text_value(form, "profile_text")
    if not profile_text and photo_items:
        profile_text = PROFILE_PHOTO_ONLY_TEXT
    elif not profile_text:
        profile_text = PROFILE_MINIMAL_TEXT
    free_notes = _build_free_notes(form)
    return {
        "label": str(form.get("label", "")).strip(),
        "profile_text": profile_text,
        "age": _parse_optional_int(form.get("age")),
        "hobbies": split_form_list(str(form.get("interests", ""))),
        "photos_memo": photo_items,
        "location_hint": _empty_to_none(str(form.get("area", "")).strip()),
        "relationship_goal": None,
        "free_notes": free_notes,
    }


def build_profile_save_preview(form: dict[str, Any]) -> dict[str, Any]:
    data = build_real_profile_from_form(form)
    return {
        "保存先label": data["label"],
        "display_name": str(form.get("display_name", "")).strip() or "-",
        "app_name": str(form.get("app_name", "")).strip() or "-",
        "age": data["age"] if data["age"] is not None else "-",
        "area": data["location_hint"] or "-",
        "profile_text": data["profile_text"],
        "photo_memo": data["photos_memo"],
        "interests": data["hobbies"],
        "avoid_topics": split_form_list(str(form.get("avoid_topics", ""))),
        "conversation_hooks": split_form_list(str(form.get("conversation_hooks", ""))),
        "first_message_hints": split_form_list(str(form.get("first_message_hints", ""))),
        "safety_notes": split_form_list(str(form.get("safety_notes", ""))),
        "notes": str(form.get("notes", "")).strip() or "-",
        "profile_status": build_profile_completion_status(form),
        "warnings": build_profile_save_warnings(form),
        "保存先": str(get_real_profile_path(data["label"])),
    }


def get_real_profile_path(label: str) -> Path:
    validate_real_profile_label(label)
    return get_real_profile_dir() / f"{label}.yaml"


def real_profile_exists(label: str) -> bool:
    return get_real_profile_path(label).exists()


def save_real_profile_from_form(form: dict[str, Any]) -> tuple[Path, list[str]]:
    form = normalize_profile_save_form(form)
    errors = validate_profile_form(form)
    if errors:
        raise ValueError("\n".join(errors))
    data = build_real_profile_from_form(form)
    path, warnings = create_real_profile(**data)
    return path, sorted(set(warnings + build_profile_save_warnings(form)))


def list_real_profiles_for_gui() -> list[dict[str, Any]]:
    profiles = []
    for path, profile in list_real_profiles():
        label = path.stem
        display_name = _first_free_note_value(profile.free_notes or "", "display_name") or profile.name_or_label or PROFILE_DISPLAY_NAME_UNSET
        profiles.append(
            {
                "label": label,
                "path": path,
                "display_label": f"{display_name} / age:{profile.age or '-'} / hobbies:{', '.join(profile.hobbies[:3]) if profile.hobbies else '-'}",
            }
        )
    return profiles


def filter_real_profiles_for_gui(query: str = "") -> list[dict[str, Any]]:
    query = query.strip().lower()
    profiles = list_real_profiles_for_gui()
    if not query:
        return profiles
    return [profile for profile in profiles if query in profile["display_label"].lower() or query in profile["label"].lower()]


def load_real_profile_for_gui(label: str) -> tuple[Path, TargetProfile]:
    return load_real_profile(label=label)


def build_real_profile_summary_for_gui(label: str) -> dict[str, Any]:
    path, profile = load_real_profile_for_gui(label)
    return {
        "label": label,
        "path": str(path),
        "age": profile.age or "-",
        "area": profile.location_hint or "-",
        "profile_text": profile.profile_text,
        "interests": profile.hobbies,
        "photo_memo": profile.photos_memo,
        "free_notes": profile.free_notes or "-",
    }


def format_list_or_empty(values: Any, empty: str = "未設定") -> list[str]:
    if values is None:
        return [empty]
    if isinstance(values, str):
        items = split_form_list(values)
    elif isinstance(values, (list, tuple, set)):
        items = [str(item).strip() for item in values if str(item).strip()]
    else:
        item = str(values).strip()
        items = [item] if item else []
    return items or [empty]


def build_profile_display_sections(label: str) -> dict[str, Any]:
    _path, profile = load_real_profile_for_gui(label)
    free_sections = _parse_free_note_sections(profile.free_notes or "")
    return {
        "title": "選択中のプロフィール",
        "summary": [
            {"label": "表示名", "value": profile.name_or_label or label},
            {"label": "年齢", "value": profile.age if profile.age is not None else "未設定"},
            {"label": "エリア", "value": profile.location_hint or "未設定"},
            {"label": "アプリ", "value": _first_free_note_value(profile.free_notes or "", "app_name") or "未設定"},
        ],
        "profile_text": profile.profile_text.strip() or "未設定",
        "sections": [
            {"title": "趣味", "items": format_list_or_empty(profile.hobbies)},
            {"title": "写真メモ", "items": format_list_or_empty(profile.photos_memo, empty="なし")},
            {
                "title": "会話に使えそうな話題",
                "items": format_list_or_empty(free_sections.get("conversation_hooks")),
            },
            {
                "title": "初回メッセージのヒント",
                "items": format_list_or_empty(free_sections.get("first_message_hints")),
            },
            {"title": "避けた方がよい話題", "items": format_list_or_empty(free_sections.get("avoid_topics"))},
            {"title": "安全メモ", "items": format_list_or_empty(free_sections.get("safety_notes"))},
        ],
        "notes": _free_note_body(profile.free_notes or ""),
    }


def _partner_source_profile_labels(partner: PartnerRecord) -> set[str]:
    return {
        event.related_id
        for event in partner.activity_log
        if event.event_type == PARTNER_SOURCE_PROFILE_EVENT and event.related_id
    }


def find_existing_partners_for_profile(label: str) -> list[dict[str, str]]:
    _path, profile = load_real_profile_for_gui(label)
    # 本文が共通の補完文に正規化された情報少なめプロフィール同士は、
    # 内容一致では同一人物と判定しない（label紐付けのみで同定する）。
    allow_content_match = (
        profile.profile_text.strip() != ""
        and profile.profile_text not in PROFILE_NORMALIZED_PLACEHOLDER_TEXTS
    )
    matches = []
    for partner in list_partners():
        linked_by_label = label in _partner_source_profile_labels(partner)
        content_match = (
            allow_content_match
            and partner.profile.profile_text == profile.profile_text
            and partner.profile.hobbies == profile.hobbies
        )
        if linked_by_label or content_match:
            matches.append(
                {
                    "partner_id": partner.partner_id,
                    "display_name": partner.display_name,
                    "status": partner.status,
                    "updated_at": partner.updated_at or "-",
                    "source_real_profile": label,
                }
            )
    return matches


def summarize_existing_partner_candidates(label: str) -> list[dict[str, str]]:
    candidates = find_existing_partners_for_profile(label)
    return [
        {
            "partner_id": item["partner_id"],
            "表示名": item["display_name"] or "-",
            "現在の状態": item["status"] or "-",
            "最終更新": item.get("updated_at") or "-",
            "元プロフィール": item.get("source_real_profile") or label,
            "操作のヒント": "重複作成前にpartnerビューで確認",
        }
        for item in candidates
    ]


def build_partner_creation_preview(label: str, display_name: str, app_name: str = "", source_memo: str = "") -> dict[str, Any]:
    path, profile = load_real_profile_for_gui(label)
    return {
        "source_real_profile": label,
        "source_path": str(path),
        "display_name": display_name.strip() or profile.name_or_label or label,
        "app_name": app_name.strip() or "-",
        "source_memo": source_memo.strip() or "-",
        "status": "new_profile",
        "next_action": "初回候補生成待ち",
        "conversation_history": "空",
        "pending_suggestions": "空",
        "profile_summary": {
            "age": profile.age,
            "hobbies": profile.hobbies,
            "location_hint": profile.location_hint,
            "profile_text_chars": len(profile.profile_text),
        },
        "保存先": "data/local/partners/<next partner_id>.yaml",
    }


def format_partner_preview_for_display(label: str, display_name: str, app_name: str = "", source_memo: str = "") -> dict[str, Any]:
    _path, profile = load_real_profile_for_gui(label)
    return {
        "title": "作成されるpartner",
        "summary": [
            {"label": "partner_id", "value": "<next partner_id>"},
            {"label": "表示名", "value": display_name.strip() or profile.name_or_label or label},
            {"label": "元プロフィール", "value": label},
            {"label": "アプリ", "value": app_name.strip() or "未設定"},
            {"label": "状態", "value": "未開始"},
            {"label": "初期ステージ", "value": "プロフィール確認済み"},
        ],
        "included": [
            "プロフィール情報",
            "会話履歴: 空",
            "未送信候補: 空",
            "相手別メモ: 空" if not source_memo.strip() else "相手別メモ: source memoを保存",
            "送信結果メモ: 空",
        ],
        "cautions": [
            "実際の送信は行われません",
            "マッチングアプリには接続しません",
            "local保存のみです",
        ],
    }


def save_partner_from_profile(label: str, display_name: str, app_name: str = "", source_memo: str = "") -> PartnerRecord:
    _path, profile = load_real_profile_for_gui(label)
    chosen_display_name = display_name.strip() or profile.name_or_label or label
    partner = create_partner_from_target_profile(profile, display_name=chosen_display_name, app_name=app_name.strip())
    partner.message_state.next_action = "初回候補生成待ち"
    add_activity_event(partner, PARTNER_SOURCE_PROFILE_EVENT, f"元プロフィール {label} から作成", label)
    if source_memo.strip():
        partner.notes.append(
            PartnerNote(text=f"source memo: {source_memo.strip()}", created_at=partner.created_at)
        )
    save_updated_partner(partner)
    return partner


def ensure_conversation_partner_for_profile(
    label: str,
    display_name: str = "",
    app_name: str = "",
    source_memo: str = "",
) -> dict[str, Any]:
    existing = find_existing_partners_for_profile(label)
    if existing:
        partner = load_partner(existing[0]["partner_id"])
        return {
            "created": False,
            "partner": partner,
            "partner_id": partner.partner_id,
            "display_name": partner.display_name,
            "duplicate_prevented": True,
            "existing_count": len(existing),
            "message": "existing_partner_selected",
        }

    partner = save_partner_from_profile(
        label,
        display_name=display_name,
        app_name=app_name,
        source_memo=source_memo,
    )
    return {
        "created": True,
        "partner": partner,
        "partner_id": partner.partner_id,
        "display_name": partner.display_name,
        "duplicate_prevented": False,
        "existing_count": 0,
        "message": "partner_created",
    }


def parse_conversation_paste(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    turns: list[dict[str, Any]] = []
    warnings: list[str] = []
    current: dict[str, Any] | None = None
    unknown_lines: list[str] = []

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        match = SPEAKER_LINE_RE.match(line)
        if match:
            label = match.group(1).strip()
            content = match.group(2).strip()
            speaker = SPEAKER_ALIASES.get(label.lower()) or SPEAKER_ALIASES.get(label)
            if speaker:
                if current:
                    _append_parsed_turn(turns, current)
                current = {"speaker": speaker, "text": content, "line_no": line_no, "source_label": label}
            else:
                unknown_lines.append(f"{line_no}: {raw_line}")
                if current:
                    current["text"] = f"{current['text']}\n{raw_line}".strip()
            continue

        if current:
            current["text"] = f"{current['text']}\n{raw_line}".strip()
        else:
            unknown_lines.append(f"{line_no}: {raw_line}")

    if current:
        _append_parsed_turn(turns, current)
    if unknown_lines:
        warnings.append("発話者を判定できない行があります: " + " / ".join(unknown_lines[:5]))
    return turns, warnings


def validate_imported_turns(turns: list[dict[str, Any]], warnings: list[str] | None = None) -> list[str]:
    errors = list(warnings or [])
    if not turns:
        errors.append("会話履歴を解析できませんでした。")
    for index, turn in enumerate(turns, start=1):
        if turn.get("speaker") not in {"user", "partner"}:
            errors.append(f"{index}件目のspeakerが不正です。")
        if not str(turn.get("text", "")).strip():
            errors.append(f"{index}件目の本文が空です。")
    return errors


def detect_conversation_safety_warnings(text: str) -> list[str]:
    return detect_profile_safety_warnings({"conversation": text})


def build_conversation_import_failure_guidance() -> dict[str, list[str]]:
    return {
        "考えられる理由": [
            "自分/相手のラベルが一致していない",
            "発言が1件も検出できない",
            "空行や記号だけになっている",
            "スクリーンショット画像のままで、テキスト化されていない",
        ],
        "対処": [
            "「自分:」「相手:」の形式で貼り付けてください",
            "ラベル欄に入力した名前と、貼り付け本文のラベルを合わせてください",
            "解析できない場合は、1発言ずつ手動追加してください",
        ],
    }


def build_conversation_import_preview(partner: PartnerRecord, turns: list[dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
    return {
        "対象partner_id": partner.partner_id,
        "display_name": partner.display_name,
        "追加予定turn数": len(turns),
        "speakerごとの発話数": {
            "user": sum(1 for turn in turns if turn.get("speaker") == "user"),
            "partner": sum(1 for turn in turns if turn.get("speaker") == "partner"),
        },
        "turns": [
            {"index": index, "speaker": turn["speaker"], "text": turn["text"]}
            for index, turn in enumerate(turns, start=1)
        ],
        "警告一覧": warnings,
        "保存先": f"data/local/partners/{partner.partner_id}.yaml",
    }


def detect_duplicate_turn_sequence(partner: PartnerRecord, turns: list[dict[str, Any]]) -> bool:
    if not turns or len(partner.conversation) < len(turns):
        return False
    recent = partner.conversation[-len(turns) :]
    return all(
        existing.speaker == turn.get("speaker") and existing.text == str(turn.get("text", ""))
        for existing, turn in zip(recent, turns)
    )


def append_conversation_turns_to_partner(partner_id: str, turns: list[dict[str, Any]]) -> PartnerRecord:
    errors = validate_imported_turns(turns)
    if errors:
        raise ValueError("\n".join(errors))
    partner = load_partner(partner_id)
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    for turn in turns:
        speaker = str(turn["speaker"])
        text = str(turn["text"]).strip()
        partner.conversation.append(ConversationTurn(speaker=speaker, text=text, timestamp=timestamp))
        add_activity_event(partner, "turn_added", f"{speaker}発言をインポート", created_at=timestamp)
        _update_message_state_from_turn(partner, speaker, text, timestamp)
    partner.analysis.partner_temperature = estimate_partner_temperature(partner.conversation)
    return save_updated_partner(partner)


def delete_conversation_turn_from_gui(partner_id: str, turn_index: int) -> PartnerRecord:
    """turn_index は format_conversation_history の index フィールド（1始まり）に対応する。"""
    partner = load_partner(partner_id)
    idx = turn_index - 1
    if not (0 <= idx < len(partner.conversation)):
        raise ValueError(f"会話履歴のインデックスが範囲外です: {turn_index}")
    partner.conversation.pop(idx)
    add_activity_event(partner, "turn_deleted", f"会話履歴 {turn_index} 件目を削除")
    partner.analysis.partner_temperature = estimate_partner_temperature(partner.conversation)
    return save_updated_partner(partner)


_PARTNER_PHOTO_DIR = Path(__file__).resolve().parent / "data" / "local" / "partner_photos"


def get_partner_photo_path(partner_id: str) -> Path | None:
    path = _PARTNER_PHOTO_DIR / f"{partner_id}.jpg"
    return path if path.exists() else None


def save_partner_photo_from_gui(partner_id: str, image_bytes: bytes) -> Path:
    from PIL import Image, ImageOps

    try:
        image = Image.open(BytesIO(image_bytes))
    except Exception:
        raise ValueError("画像ファイルを読み込めませんでした。jpg / jpeg / png 形式の画像を選択してください。")
    image = ImageOps.exif_transpose(image).convert("RGB")
    image = ImageOps.fit(image, (400, 400))
    _PARTNER_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    path = _PARTNER_PHOTO_DIR / f"{partner_id}.jpg"
    image.save(path, format="JPEG", quality=90)
    return path


def delete_partner_photo_from_gui(partner_id: str) -> bool:
    path = _PARTNER_PHOTO_DIR / f"{partner_id}.jpg"
    if path.exists():
        path.unlink()
        return True
    return False


_MEMO_TAG_PATH = Path(__file__).resolve().parent / "data" / "local" / "partner_memo_tags.json"


def load_all_memo_tags() -> dict[str, str]:
    if not _MEMO_TAG_PATH.exists():
        return {}
    try:
        data = json.loads(_MEMO_TAG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if str(value).strip()}


def load_memo_tag(partner_id: str) -> str:
    return load_all_memo_tags().get(partner_id, "")


def _write_memo_tags(tags: dict[str, str]) -> None:
    atomic_write_text(_MEMO_TAG_PATH, json.dumps(tags, ensure_ascii=False, indent=2) + "\n")


def save_memo_tag_from_gui(partner_id: str, memo_tag: str) -> dict[str, Any]:
    # 不正なpartner_idや存在しない相手は弾く（load_partnerがValueError/FileNotFoundを投げる）
    load_partner(partner_id)
    tags = load_all_memo_tags()
    memo_tag = memo_tag.strip()
    if memo_tag:
        tags[partner_id] = memo_tag
    else:
        tags.pop(partner_id, None)
    _write_memo_tags(tags)
    return {"partner_id": partner_id, "memo_tag": memo_tag}


def delete_partner_completely_from_gui(partner_id: str, confirmed: bool = False) -> dict[str, Any]:
    if not confirmed:
        raise ValueError("「削除することを理解しました」にチェックを入れてください。")
    # load_partnerでpartner_idの形式と存在を検証する（不正なら例外）
    partner = load_partner(partner_id)
    linked_labels = _partner_source_profile_labels(partner)
    deleted: dict[str, Any] = {
        "partner_file": False,
        "real_profiles": [],
        "photo": False,
        "memo_tag": False,
    }

    partner_file = get_partner_dir() / f"{partner_id}.yaml"
    if partner_file.exists():
        partner_file.unlink()
        deleted["partner_file"] = True

    # 削除後に残っている相手がまだ参照しているreal_profileは消さない
    still_referenced: set[str] = set()
    for other in list_partners():
        still_referenced |= _partner_source_profile_labels(other)
    real_dir = get_real_profile_dir()
    for label in linked_labels:
        if not label or label in still_referenced:
            continue
        real_path = real_dir / f"{label}.yaml"
        if real_path.exists():
            real_path.unlink()
            deleted["real_profiles"].append(label)

    if delete_partner_photo_from_gui(partner_id):
        deleted["photo"] = True

    tags = load_all_memo_tags()
    if partner_id in tags:
        tags.pop(partner_id, None)
        _write_memo_tags(tags)
        deleted["memo_tag"] = True

    return {"partner_id": partner_id, "deleted": deleted, "message": "削除しました"}


def _parse_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if _is_profile_unset_value(text):
        return None
    if not text:
        return None
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else None


def _safe_profile_label_base(display_name: str) -> str:
    text = str(display_name or "").strip()
    if not text or detect_privacy_warnings([text]):
        return "profile"
    ascii_text = text.encode("ascii", errors="ignore").decode("ascii").lower()
    ascii_text = re.sub(r"[^a-z0-9_-]+", "_", ascii_text)
    ascii_text = re.sub(r"_+", "_", ascii_text).strip("_-")
    if not ascii_text or not re.search(r"[a-z]", ascii_text):
        return "profile"
    return ascii_text[:32].strip("_-") or "profile"


def _is_safe_profile_label(label: str) -> bool:
    if not label:
        return False
    if not label.startswith("profile_"):
        return False
    try:
        validate_real_profile_label(label)
    except ValueError:
        return False
    return True


def _deduplicate_profile_label(label: str, existing_labels: set[str] | None = None) -> str:
    existing = set(existing_labels) if existing_labels is not None else {path.stem for path, _profile in list_real_profiles()}
    if label not in existing:
        return label
    for index in range(1, 1000):
        candidate = f"{label}_{index:03d}"
        if candidate not in existing:
            return candidate
    raise ValueError("利用可能なlabel候補を作成できませんでした。")


def _empty_to_none(value: str) -> str | None:
    return value if value else None


def _profile_missing_fields(form: dict[str, Any]) -> list[str]:
    missing = []
    display_name = str(form.get("display_name", "")).strip()
    if _is_profile_unset_value(display_name) or display_name == PROFILE_DISPLAY_NAME_UNSET:
        missing.append("display_name")
    if not _profile_text_value(form, "profile_text") and not split_form_list(str(form.get("photo_memo", ""))):
        missing.append("profile_text_or_photo_memo")
    if not split_form_list(str(form.get("interests", ""))):
        missing.append("interests")
    return missing


def _profile_content_signal_count(form: dict[str, Any]) -> int:
    signals = [
        _profile_text_value(form, "display_name")
        and _profile_text_value(form, "display_name") != PROFILE_DISPLAY_NAME_UNSET,
        _profile_text_value(form, "profile_text"),
        split_form_list(str(form.get("photo_memo", ""))),
        split_form_list(str(form.get("interests", ""))),
        _profile_text_value(form, "age"),
        _profile_text_value(form, "area"),
        _profile_text_value(form, "app_name"),
        split_form_list(str(form.get("conversation_hooks", ""))),
        split_form_list(str(form.get("first_message_hints", ""))),
        split_form_list(str(form.get("avoid_topics", ""))),
        split_form_list(str(form.get("safety_notes", ""))),
        _profile_text_value(form, "notes"),
    ]
    return sum(1 for signal in signals if bool(signal))


def _profile_text_value(form: dict[str, Any], key: str) -> str:
    value = str(form.get(key, "")).strip()
    return "" if _is_profile_unset_value(value) else value


def _build_free_notes(form: dict[str, Any]) -> str | None:
    display_name = str(form.get("display_name", "")).strip()
    app_name = str(form.get("app_name", "")).strip()
    avoid_topics = split_form_list(str(form.get("avoid_topics", "")))
    conversation_hooks = split_form_list(str(form.get("conversation_hooks", "")))
    first_message_hints = split_form_list(str(form.get("first_message_hints", "")))
    safety_notes = split_form_list(str(form.get("safety_notes", "")))
    notes = str(form.get("notes", "")).strip()
    status = build_profile_completion_status(form)
    missing = _profile_missing_fields(form)
    lines = [f"profile_status: {status}"]
    if missing:
        lines.append("profile_missing_fields:")
        lines.extend(f"- {item}" for item in missing)
    if display_name:
        lines.append(f"display_name: {display_name}")
    if app_name:
        lines.append(f"app_name: {app_name}")
    if avoid_topics:
        lines.append("avoid_topics:")
        lines.extend(f"- {item}" for item in avoid_topics)
    if conversation_hooks:
        lines.append("conversation_hooks:")
        lines.extend(f"- {item}" for item in conversation_hooks)
    if first_message_hints:
        lines.append("first_message_hints:")
        lines.extend(f"- {item}" for item in first_message_hints)
    if safety_notes:
        lines.append("safety_notes:")
        lines.extend(f"- {item}" for item in safety_notes)
    if notes:
        lines.append("notes:")
        lines.append(notes)
    return "\n".join(lines) if lines else None


def _parse_free_note_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.endswith(":") and not line.startswith("- "):
            current_key = line[:-1].strip()
            sections.setdefault(current_key, [])
            continue
        if current_key and line.startswith("- "):
            item = line[2:].strip()
            if item:
                sections.setdefault(current_key, []).append(item)
    return sections


def _first_free_note_value(text: str, key: str) -> str:
    prefix = f"{key}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def _free_note_list(text: str, key: str) -> list[str]:
    sections = _parse_free_note_sections(text)
    return sections.get(key, [])


def _partner_profile_content_count(partner: PartnerRecord) -> int:
    profile = partner.profile
    count = 0
    if partner.display_name.strip():
        count += 1
    if profile.profile_text.strip():
        count += 1
    if profile.hobbies:
        count += 1
    if profile.photos_memo:
        count += 1
    if profile.location_hint:
        count += 1
    if profile.free_notes:
        count += 1
    return count


def _free_note_body(text: str) -> str:
    sections = _parse_free_note_sections(text)
    notes = sections.get("notes")
    if notes:
        return "\n".join(notes)
    capture = False
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "notes:":
            capture = True
            continue
        if capture:
            if line.endswith(":") and not line.startswith("- "):
                break
            if line:
                lines.append(line)
    return "\n".join(lines)


def _append_parsed_turn(turns: list[dict[str, Any]], current: dict[str, Any]) -> None:
    text = str(current.get("text", "")).strip()
    if text:
        turns.append(
            {
                "speaker": current["speaker"],
                "text": text,
                "line_no": current["line_no"],
                "source_label": current["source_label"],
            }
        )


def _update_message_state_from_turn(partner: PartnerRecord, speaker: str, text: str, timestamp: str) -> None:
    if speaker == "partner":
        partner.message_state.last_partner_message = text
        partner.message_state.last_received_at = timestamp
        partner.message_state.awaiting_user_action = True
        partner.message_state.awaiting_partner_reply = False
        partner.message_state.next_action = "返信候補を生成する"
        if partner.status == "first_message_sent":
            previous = partner.status
            partner.status = "chatting"
            add_activity_event(partner, "status_updated", f"status: {previous} -> chatting", created_at=timestamp)
    else:
        partner.message_state.last_user_message = text
        partner.message_state.last_sent_at = timestamp
        partner.message_state.awaiting_user_action = False
        partner.message_state.awaiting_partner_reply = True
        partner.message_state.next_action = "相手の返信待ち"


def _target_from_partner(partner: PartnerRecord) -> TargetProfile:
    profile = partner.profile
    return TargetProfile(
        name_or_label=partner.display_name,
        age=profile.age,
        profile_text=profile.profile_text,
        hobbies=list(profile.hobbies),
        photos_memo=list(profile.photos_memo),
        location_hint=profile.location_hint,
        relationship_goal=profile.relationship_goal,
        free_notes=profile.free_notes,
    )


def _split_profile_paste_line(line: str) -> tuple[str | None, str]:
    match = re.match(r"^\s*([^:：]+)\s*[:：]\s*(.*)$", line)
    if not match:
        return None, ""
    raw_key = match.group(1).strip().lower()
    field = PROFILE_PASTE_FIELD_ALIASES.get(raw_key) or PROFILE_PASTE_FIELD_ALIASES.get(match.group(1).strip())
    return field, match.group(2).strip() if field else ""


def _is_profile_unset_value(value: Any) -> bool:
    return str(value or "").strip().lower() in PROFILE_UNSET_VALUES


def _clean_profile_paste_value(value: str) -> str:
    cleaned = value.strip()
    return "" if _is_profile_unset_value(cleaned) else cleaned


def _strip_profile_list_marker(line: str) -> str:
    return re.sub(r"^\s*(?:[-*・]|[0-9]+[.)])\s*", "", line).strip()


def _append_profile_field_value(current: Any, value: str) -> str:
    value = value.strip()
    if not value:
        return str(current or "")
    current_text = str(current or "").strip()
    return f"{current_text}\n{value}" if current_text else value


def _unique_candidates(candidates: list[str]) -> list[str]:
    unique = []
    for candidate in candidates:
        text = candidate.strip()
        if text and text not in unique:
            unique.append(text)
    return unique or ["はじめまして。プロフィールを見て、話してみたいなと思いました。休日はどんな過ごし方が多いですか？"]


def _shape_candidate_for_objective(
    base: str,
    objective: str,
    tone: str,
    place_hint: str,
    mode: str,
    index: int,
    partner: PartnerRecord | None = None,
    stage: dict[str, Any] | None = None,
) -> str:
    place = place_hint.strip()
    stage = stage or (build_conversation_stage_summary(partner) if partner else {})
    if mode == "first":
        return _first_message_variant(partner, base, objective, tone, index)
    judgement = _judgement_for_objective(objective, stage.get("action_judgements", {})) if stage else None
    if judgement and judgement["status"] in {"まだ早い", "非推奨"}:
        return _safe_reply_variant(partner, base, objective, tone, index)
    if "電話" in objective:
        return _phone_candidate_variant(index)
    if "LINE" in objective:
        return _line_exchange_candidate_variant(index)
    if "場所" in objective and place:
        return _meet_candidate_variant(index, place)
    if "会う" in objective:
        return _meet_candidate_variant(index, place)
    if "大人" in objective or "大人" in tone:
        return _adult_candidate_variant(index)
    if "自分の紹介" in objective:
        return _safe_reply_variant(partner, base, objective, tone, index, include_self=True)
    if "ユーモア" in objective or "ユーモア" in tone:
        return _trim_for_gui(f"{_safe_reply_variant(partner, base, objective, tone, index)} ちょっと気になって聞いてみたくなりました。")
    if "短め" in tone:
        return _trim_for_gui(base, 90)
    if index == 1:
        return _safe_reply_variant(partner, base, objective, tone, index, include_self=True)
    if index == 2:
        return _safe_reply_variant(partner, base, objective, tone, index, bridge=True)
    return _safe_reply_variant(partner, base, objective, tone, index)


def _phone_candidate_variant(index: int) -> str:
    options = [
        "もしタイミング合えば、今度10分くらいだけ軽く話してみませんか？無理なければで全然大丈夫です。",
        "メッセージだと少し伝わりにくいところもあるので、都合が合う時に10分くらい話せたら嬉しいです。もちろん無理なければで大丈夫です。",
        "話していてもう少し声でも雰囲気を知れたら嬉しいなと思いました。急ぎではないので、負担なければ短く話せたら嬉しいです。",
    ]
    return _trim_for_gui(options[index % len(options)], 135)


def _meet_candidate_variant(index: int, place: str = "") -> str:
    place_phrase = f"{place}あたりで" if place else ""
    options = [
        f"もし予定が合えば、今度{place_phrase}短めにお茶かランチでもどうですか？もちろん無理なければ大丈夫です。",
        "話していて雰囲気が合いそうだなと思いました。無理なければ、タイミング合う時に軽くカフェで話せたら嬉しいです。",
        f"{place_phrase}行きやすければ、今度少しだけお茶でもできたら嬉しいです。難しければ全然大丈夫です。",
    ]
    return _trim_for_gui(options[index % len(options)], 135)


def _line_exchange_candidate_variant(index: int) -> str:
    options = [
        "もしアプリだと見落としやすければ、話しやすい方に移しても大丈夫です。もちろんこのままアプリでも大丈夫です。",
        "やり取りしやすい方があれば合わせます。無理に移さなくて大丈夫なので、アプリのままでも全然大丈夫です。",
        "もう少し話しやすくするなら別の連絡先でも大丈夫ですが、安心できる方で大丈夫です。",
    ]
    return _trim_for_gui(options[index % len(options)], 135)


def _adult_candidate_variant(index: int) -> str:
    options = [
        "やり取りしていて、落ち着いて話せそうな感じがしてちょっと気になっています。無理なく話せるペースで続けられたら嬉しいです。",
        "話していると落ち着くので、もう少しゆっくり知れたら嬉しいです。無理のないペースで大丈夫です。",
        "少しだけ距離が近づいた感じがして嬉しいです。急がず、自然に話せたらいいなと思っています。",
    ]
    return _trim_for_gui(options[index % len(options)], 130)


def _first_message_variant(partner: PartnerRecord | None, base: str, objective: str, tone: str, index: int) -> str:
    hook = _profile_hook_for_candidate(partner)
    if index == 0:
        return _trim_for_gui(f"はじめまして。{hook}が印象に残りました。休日はそのあたりで過ごすことが多いですか？", 120)
    if index == 1:
        natural_hook = hook if hook.endswith("雰囲気") else f"{hook}の雰囲気"
        return _trim_for_gui(f"はじめまして。{natural_hook}が自然で、話してみたいなと思いました。最近もよく楽しんでいますか？", 120)
    topic_hook = "プロフィール" if hook.endswith("雰囲気") else hook
    return _trim_for_gui(f"はじめまして。{topic_hook}の話、少し気になりました。気軽に話せたら嬉しいです。", 100)


def _safe_reply_variant(
    partner: PartnerRecord | None,
    base: str,
    objective: str,
    tone: str,
    index: int,
    include_self: bool = False,
    bridge: bool = False,
) -> str:
    latest = _latest_partner_text(partner)
    hook = _conversation_hook_for_candidate(partner) or _profile_hook_for_candidate(partner)
    reaction = _reaction_for_latest(latest)
    if include_self:
        return _trim_for_gui(f"{reaction} {_self_disclosure_for_hook(hook)} 最近だとどんな感じが多いですか？", 135)
    if bridge:
        return _trim_for_gui(f"{reaction} {hook}の話、もう少し聞いてみたいです。無理なく話しやすいところからで大丈夫です。", 120)
    if index == 0:
        return _trim_for_gui(f"{reaction} {hook}の感じ、自然でいいですね。最近もそういう時間は作れていますか？", 120)
    if index == 1:
        return _trim_for_gui(f"{reaction} 自分も少し近いところがあるので、聞いていて話しやすいです。休日はそのあたりが多いですか？", 130)
    return _trim_for_gui(f"{reaction} その話、もう少し聞いてみたいです。特に印象に残っていることはありますか？", 115)


def _profile_hook_for_candidate(partner: PartnerRecord | None) -> str:
    if not partner:
        return "プロフィールの雰囲気"
    profile = partner.profile
    candidates = list(profile.hobbies)
    text = " ".join([profile.profile_text or "", profile.free_notes or "", " ".join(profile.photos_memo or [])])
    for keyword in ["カフェ", "映画", "旅行", "ご飯", "食べ物", "自然", "散歩", "音楽", "料理", "写真"]:
        if keyword in text and keyword not in candidates:
            candidates.append(keyword)
    return candidates[0] if candidates else "プロフィールの雰囲気"


def _conversation_hook_for_candidate(partner: PartnerRecord | None) -> str:
    text = _latest_partner_text(partner)
    for phrase in ["静かなカフェ", "落ち着いたカフェ", "落ち着いた雰囲気"]:
        if phrase in text:
            return phrase
    for keyword in ["カフェ", "映画", "旅行", "ご飯", "食べ物", "自然", "散歩", "仕事", "休日", "音楽", "料理"]:
        if keyword in text:
            return keyword
    return ""


def _self_disclosure_for_hook(hook: str) -> str:
    if hook in {"カフェ", "静かなカフェ", "落ち着いたカフェ", "落ち着いた雰囲気", "自然", "散歩"}:
        return f"自分も{hook}みたいな雰囲気は好きなので、ゆるく聞いてみたくなりました。"
    return f"自分も{hook}の話は好きなので、ゆるく聞いてみたくなりました。"


def _latest_partner_text(partner: PartnerRecord | None) -> str:
    if not partner:
        return ""
    partner_turns = [turn.text.strip() for turn in partner.conversation if turn.speaker == "partner" and turn.text.strip()]
    return partner_turns[-1] if partner_turns else ""


def _reaction_for_latest(text: str) -> str:
    if not text:
        return "ありがとうございます。"
    if "仕事" in text:
        return "それはお疲れさまです。"
    if any(word in text for word in ["好き", "楽しい", "よく", "行きます"]):
        return "いいですね。"
    if len(text) <= 8:
        return "返信ありがとうございます。"
    return "そうなんですね。"


def _trim_for_gui(text: str, max_len: int = 160) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _variant_use_case(index: int, stage: dict[str, Any] | None = None) -> str:
    if not stage:
        return ["候補A: 一番無難。迷ったらこれ。", "候補B: 少し距離を縮める用。", "候補C: 相手の反応が良いとき用。"][index % 3]
    stage_label = stage.get("conversation_stage") or stage.get("stage") or "現在の会話"
    temperature = stage.get("temperature") or "不明"
    return [
        f"候補A: 一番無難。{stage_label}向け。",
        f"候補B: 少し距離を縮める用。温度感: {temperature}。",
        f"候補C: 次につなげる用。{stage.get('next_recommendation', '送信前に確認してください')}",
    ][index % 3]


def _variant_metadata(index: int, objective: str, stage: dict[str, Any], quality_check: list[str]) -> dict[str, str]:
    stage_label = stage.get("conversation_stage") or "現在の会話"
    temperature = stage.get("temperature") or "不明"
    if index % 3 == 0:
        title = "一番無難"
        use_case = "迷ったらこれ"
        aim = "相手の話題に軽く触れて、返信しやすい1問に絞る"
    elif index % 3 == 1:
        title = "少し親しみやすい"
        use_case = "相手が明るい雰囲気なら"
        aim = "自分の話を少しだけ混ぜて、会話を広げる"
    else:
        title = "少し距離を縮める"
        use_case = "温度感が普通以上のとき"
        aim = "次につながる一言を入れる。早い段階では誘いすぎない"
    risky_note = " / 注意あり" if any("注意" in item or "まだ早い" in item for item in quality_check) else ""
    return {
        "title": f"候補{chr(ord('A') + index % 3)}: {title}",
        "use_case": f"{use_case}{risky_note}",
        "aim": aim,
        "compatibility": f"会話ステージ: {stage_label} / 温度感: {temperature}",
    }


def _candidate_quality_check(text: str, objective: str, partner: PartnerRecord | None, stage: dict[str, Any] | None = None) -> list[str]:
    checks: list[str] = []
    question_count = text.count("？") + text.count("?")
    if len(text) <= 130:
        checks.append("長さ: OK")
    else:
        checks.append("長さ: 注意。少し長めです")
    if question_count <= 1:
        checks.append("質問数: OK")
    else:
        checks.append("質問数: 注意。質問は1つまでが自然です")
    praise_count = sum(text.count(word) for word in ["素敵", "かわいい", "綺麗", "美人", "すごい", "嬉しい"])
    if praise_count <= 1:
        checks.append("褒め方: OK")
    else:
        checks.append("褒め方: 注意。褒めすぎに見える可能性があります")
    if any(template in text for template in ["プロフィール見ました", "共通点があります", "共通点があって嬉しい"]):
        checks.append("テンプレ感: 注意。少しAIっぽく見える可能性があります")
    else:
        checks.append("テンプレ感: OK")
    if any(word in text for word in ["電話番号", "ID送って", "LINE教えて", "住所", "メール"]):
        checks.append("個人情報: 注意。個人情報を聞かないでください")
    else:
        checks.append("個人情報: OK")
    if any(word in text for word in ["ホテル", "自宅", "家来る", "泊まり", "体", "身体", "エロ", "大人の関係"]):
        checks.append("大人っぽさ: 注意。露骨な表現は避けてください")
    else:
        checks.append("大人っぽさ: OK")
    if stage:
        judgement = _judgement_for_objective(objective, stage.get("action_judgements", {}))
        if judgement and judgement["status"] in {"まだ早い", "非推奨"}:
            checks.append(f"会話ステージ: 注意。{objective}は{judgement['status']}です")
        elif judgement and judgement["status"] == "控えめなら可":
            checks.append(f"会話ステージ: 控えめなら可。{judgement['reason']}")
        else:
            checks.append("会話ステージ: OK")
    return checks


def _candidate_safety_notes(text: str, objective: str, partner: PartnerRecord | None = None) -> list[str]:
    notes = ["自動送信ではありません。送信前に人間が確認してください。"]
    if "電話" in objective or "会う" in objective or "LINE" in objective:
        notes.append("会話の温度感が低い場合は送らないでください。")
    if "LINE" in objective:
        notes.append("LINE IDそのものは保存しないでください。")
    if "大人っぽい" in objective:
        notes.append("下ネタや身体的表現に寄せず、控えめにしてください。")
    if partner:
        stage = build_conversation_stage_summary(partner)
        judgement = _judgement_for_objective(objective, stage["action_judgements"])
        if judgement and judgement["status"] in {"まだ早い", "非推奨", "控えめなら可"}:
            notes.append(f"{objective}: {judgement['status']}。{judgement['reason']}")
        partner_notes = _partner_notes_text(partner)
        if "旅行" in partner_notes:
            notes.append("相手別メモに旅行話題の反応記録があります。無理なく広げられるか確認してください。")
        if "電話" in objective and "電話" in partner_notes and any(word in partner_notes for word in ["早", "まだ", "控え"]):
            notes.append("相手別メモ上、電話はまだ早そうです。")
    if text.count("？") + text.count("?") > 1:
        notes.append("質問が複数あります。1つに減らすと自然です。")
    return notes


def _build_temperature_summary(
    partner: PartnerRecord,
    raw_temperature: str,
    partner_notes: str,
    outcome_summaries: list[str],
) -> tuple[str, list[str]]:
    partner_turns = [turn for turn in partner.conversation if turn.speaker == "partner"]
    reasons: list[str] = []
    if not partner.conversation:
        return "不明", ["会話履歴がまだありません"]
    if partner.message_state.awaiting_partner_reply:
        reasons.append("直近で返信待ち")
    if any(_has_question(turn.text) for turn in partner_turns):
        reasons.append("相手から質問が返ってきている")
    if any(len(turn.text.strip()) >= 18 for turn in partner_turns[-3:]):
        reasons.append("相手の返信が一定量ある")
    if sum(1 for turn in partner_turns[-3:] if len(turn.text.strip()) <= 8) >= 2:
        reasons.append("短文が続いている")
    outcome_text = "\n".join(outcome_summaries)
    if any(word in outcome_text for word in ["反応よかった", "話題が広がった", "返信あり"]):
        reasons.append("送信結果メモで反応がよい記録がある")
    if "電話" in partner_notes and any(word in partner_notes for word in ["早", "まだ", "控え"]):
        reasons.append("相手別メモに電話はまだ早そうとある")

    if "送信結果メモで反応がよい記録がある" in reasons:
        label = "高め"
    elif "相手から質問が返ってきている" in reasons and raw_temperature in {"good", "very_good", "normal"}:
        label = "高め"
    elif "短文が続いている" in reasons or raw_temperature == "low":
        label = "低め"
    elif raw_temperature in {"good", "very_good", "normal"}:
        label = "普通"
    else:
        label = "不明"
    return label, reasons or ["明確な判断材料はまだ少ない"]


def _judgement_for_objective(objective: str, action_judgements: dict[str, dict[str, str]]) -> dict[str, str] | None:
    if "電話" in objective:
        return action_judgements.get("電話に誘う")
    if "場所" in objective:
        return action_judgements.get("場所を指定して会う提案をする")
    if "会う" in objective:
        return action_judgements.get("会う提案をする")
    if "LINE" in objective:
        return action_judgements.get("LINE交換を提案する")
    if "大人" in objective:
        return action_judgements.get("少し大人っぽい雰囲気にする")
    if "恋愛" in objective:
        return action_judgements.get("恋愛観に軽く触れる")
    return None


def _build_action_judgements(
    round_count: int,
    temperature: str,
    partner_notes: str,
    outcome_summaries: list[str],
    partner: PartnerRecord,
) -> dict[str, dict[str, str]]:
    judgement = {
        "電話に誘う": _judge_phone(round_count, temperature, partner_notes),
        "会う提案をする": _judge_meet(round_count, temperature, partner_notes),
        "場所を指定して会う提案をする": _judge_specific_place(round_count, temperature, partner_notes),
        "LINE交換を提案する": _judge_line(round_count, temperature, partner_notes),
        "少し大人っぽい雰囲気にする": _judge_adult_topic(round_count, temperature, partner_notes),
        "恋愛観に軽く触れる": _judge_romance_topic(round_count, temperature),
    }
    outcome_text = "\n".join(outcome_summaries)
    if any(word in outcome_text for word in ["反応よかった", "話題が広がった"]):
        judgement["次に広げる話題"] = {
            "status": "OK",
            "reason": "送信結果メモで反応が良い記録があるため、同じ話題を自然に広げるのがよさそうです。",
        }
    if partner.message_state.awaiting_partner_reply:
        for value in judgement.values():
            value["status"] = "非推奨"
            value["reason"] = "直近で返信待ちのため、今は追撃せず待つ方が安全です。"
    return judgement


def _judge_phone(round_count: int, temperature: str, partner_notes: str) -> dict[str, str]:
    if "電話" in partner_notes and any(word in partner_notes for word in ["早", "まだ", "控え"]):
        return {"status": "非推奨", "reason": "相手別メモに電話はまだ早そうとあります。"}
    if round_count < 2:
        return {"status": "まだ早い", "reason": "まだ1往復目以下なので、電話提案は早い可能性があります。"}
    if temperature == "高め":
        return {"status": "控えめなら可", "reason": "相手から質問や良い反応があり、短く断りやすい形なら検討できます。"}
    return {"status": "まだ早い", "reason": "温度感が十分に高いとは言えないため、もう1往復雑談が安全です。"}


def _judge_meet(round_count: int, temperature: str, partner_notes: str) -> dict[str, str]:
    if round_count < 3:
        return {"status": "まだ早い", "reason": "まだ3往復未満なので、会う提案は早い可能性があります。"}
    if "会う" in partner_notes and any(word in partner_notes for word in ["早", "まだ", "控え"]):
        return {"status": "非推奨", "reason": "相手別メモに会う提案はまだ早そうとあります。"}
    if temperature == "高め":
        return {"status": "控えめなら可", "reason": "会話が続いているため、軽く断りやすい提案なら検討できます。"}
    return {"status": "まだ早い", "reason": "会う提案より先に、趣味や日常の話題をもう少し続けるのが安全です。"}


def _judge_specific_place(round_count: int, temperature: str, partner_notes: str) -> dict[str, str]:
    base = _judge_meet(round_count, temperature, partner_notes)
    if base["status"] in {"まだ早い", "非推奨"}:
        return base
    return {"status": "控えめなら可", "reason": "場所指定は圧が出やすいため、相手が断りやすい軽い候補に留めてください。"}


def _judge_line(round_count: int, temperature: str, partner_notes: str) -> dict[str, str]:
    if "LINE" in partner_notes and any(word in partner_notes for word in ["早", "まだ", "控え"]):
        return {"status": "非推奨", "reason": "相手別メモにLINE交換はまだ早そうとあります。"}
    if round_count < 4:
        return {"status": "まだ早い", "reason": "LINE交換は個人情報に近いため、十分に会話が続いてからにしてください。"}
    if temperature == "高め":
        return {"status": "控えめなら可", "reason": "会話が続いている場合のみ、相手が断りやすい聞き方で検討できます。"}
    return {"status": "まだ早い", "reason": "温度感が高いとは言えないため、LINE交換は急がない方が安全です。"}


def _judge_adult_topic(round_count: int, temperature: str, partner_notes: str) -> dict[str, str]:
    if round_count < 2:
        return {"status": "まだ早い", "reason": "初回や1往復目では距離が近すぎる印象になりやすいです。"}
    if "大人" in partner_notes and any(word in partner_notes for word in ["控え", "早", "まだ"]):
        return {"status": "控えめなら可", "reason": "相手別メモ上、控えめな恋愛感に留めるのが安全です。"}
    if temperature == "高め":
        return {"status": "控えめなら可", "reason": "下ネタや身体的表現を避け、軽い恋愛観に留めるなら検討できます。"}
    return {"status": "まだ早い", "reason": "露骨な性的表現、身体の部位、ホテルや自宅の誘いは避けてください。"}


def _judge_romance_topic(round_count: int, temperature: str) -> dict[str, str]:
    if round_count < 2:
        return {"status": "まだ早い", "reason": "初回や1往復目では重く見えやすいため、日常話題を優先してください。"}
    if temperature in {"高め", "普通"}:
        return {"status": "控えめなら可", "reason": "軽い恋愛観に触れる程度なら、質問は1つに絞ってください。"}
    return {"status": "まだ早い", "reason": "温度感が低めなので、恋愛観より返しやすい雑談が安全です。"}


def _build_guidance_cautions(action_judgements: dict[str, dict[str, str]], partner_notes: str, outcome_summaries: list[str]) -> list[str]:
    cautions = []
    for action, judgement in action_judgements.items():
        if judgement["status"] in {"まだ早い", "非推奨"} and action in {"電話に誘う", "会う提案をする", "LINE交換を提案する"}:
            cautions.append(f"{action}: {judgement['status']}。{judgement['reason']}")
    if "旅行" in partner_notes:
        cautions.append("相手別メモに旅行話題の反応記録があります。無理なく広げられるか確認してください。")
    if any("微妙" in item for item in outcome_summaries):
        cautions.append("最近の送信結果に微妙だった記録があります。短く返しやすい文を優先してください。")
    if any("質問多め" in item or "質問が多" in item for item in outcome_summaries):
        cautions.append("質問が多い文の反応が弱い記録があります。今回は質問を1つに絞ってください。")
    return cautions or ["強い誘いは避け、相手が返しやすい文にしてください。"]


def _has_question(text: str) -> bool:
    return "?" in text or "？" in text or any(word in text for word in ["ですか", "ますか", "どう", "何", "どこ"])


def _find_sent_suggestion(partner: PartnerRecord, suggestion_id: str):
    for suggestion in partner.pending_suggestions:
        if suggestion.suggestion_id == suggestion_id and suggestion.status == "sent":
            return suggestion
    raise ValueError(f"sent suggestion not found: {suggestion_id}")


def _find_sent_record(partner: PartnerRecord, sent_id: str) -> SentRecord:
    for record in partner.sent_records:
        if record.sent_id == sent_id:
            return record
    if sent_id.startswith("legacy_generated_"):
        suggestion_id = sent_id.removeprefix("legacy_generated_")
        suggestion = _find_sent_suggestion(partner, suggestion_id)
        record = SentRecord(
            sent_id=sent_id,
            source_type="generated_suggestion",
            source_suggestion_id=suggestion.suggestion_id,
            text=suggestion.text,
            sent_at=suggestion.sent_at or suggestion.created_at,
            outcome_status=suggestion.outcome_status or "未確認",
            outcome_memo=suggestion.outcome_memo or "",
            outcome_updated_at=suggestion.outcome_updated_at,
        )
        partner.sent_records.append(record)
        return record
    raise ValueError(f"sent record not found: {sent_id}")


def _find_sent_record_or_legacy(partner: PartnerRecord, sent_id: str) -> dict[str, Any]:
    try:
        return _sent_record_to_display(_find_sent_record(partner, sent_id))
    except ValueError:
        if sent_id.startswith("legacy_generated_"):
            suggestion_id = sent_id.removeprefix("legacy_generated_")
            return _legacy_sent_suggestion_to_display(_find_sent_suggestion(partner, suggestion_id))
        raise


def _sent_record_to_display(record: SentRecord) -> dict[str, Any]:
    return {
        "sent_id": record.sent_id,
        "suggestion_id": record.source_suggestion_id or "",
        "source_type": record.source_type,
        "source_label": "AI候補" if record.source_type == "generated_suggestion" else "手入力",
        "source_suggestion_id": record.source_suggestion_id or "",
        "purpose": "custom_text" if record.source_type == "custom_text" else "generated_suggestion",
        "sent_at": record.sent_at or "",
        "text": record.text,
        "outcome_status": record.outcome_status or "未確認",
        "outcome_memo": record.outcome_memo or "",
        "outcome_updated_at": record.outcome_updated_at or "",
    }


def _legacy_sent_suggestion_to_display(suggestion) -> dict[str, Any]:
    return {
        "sent_id": f"legacy_generated_{suggestion.suggestion_id}",
        "suggestion_id": suggestion.suggestion_id,
        "source_type": "generated_suggestion",
        "source_label": "AI候補",
        "source_suggestion_id": suggestion.suggestion_id,
        "purpose": suggestion.purpose,
        "sent_at": suggestion.sent_at or suggestion.created_at,
        "text": suggestion.text,
        "outcome_status": suggestion.outcome_status or "未確認",
        "outcome_memo": suggestion.outcome_memo or "",
        "outcome_updated_at": suggestion.outcome_updated_at or "",
    }


def _partner_notes_text(partner: PartnerRecord) -> str:
    return "\n".join(note.text.strip() for note in partner.notes if note.text.strip())


def _recent_outcome_summaries(partner: PartnerRecord, limit: int = 3) -> list[str]:
    summaries = []
    for record in format_sent_suggestions_for_outcomes(partner)[-limit:]:
        status = record["outcome_status"] or "未確認"
        memo = record["outcome_memo"].strip()
        detail = f"{record['sent_id']}: {status}"
        if memo:
            detail += f" / {_truncate_for_display(memo, 80)}"
        summaries.append(detail)
    return summaries


def _truncate_for_display(text: str, max_length: int) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= max_length else compact[: max_length - 3] + "..."
