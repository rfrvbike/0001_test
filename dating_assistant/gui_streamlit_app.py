from __future__ import annotations

import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import streamlit as st

from gui_helpers import (
    append_conversation_turns_to_partner,
    build_partner_label,
    build_partner_summary,
    build_conversation_import_preview,
    build_partner_creation_preview,
    build_generation_status_message,
    build_discard_suggestion_preview,
    build_mark_sent_preview,
    build_profile_save_preview,
    can_discard_suggestion,
    can_generate_suggestion,
    can_mark_suggestion_sent,
    detect_conversation_safety_warnings,
    detect_duplicate_turn_sequence,
    detect_profile_safety_warnings,
    format_conversation_history,
    format_pending_suggestions,
    format_timeline_items,
    generate_suggestion_for_gui,
    get_generation_mode_for_partner,
    discard_suggestion_from_gui,
    load_partner_choices,
    load_partner_for_view,
    list_real_profiles_for_gui,
    parse_conversation_paste,
    real_profile_exists,
    save_real_profile_from_form,
    save_partner_from_profile,
    mark_custom_text_sent_from_gui,
    mark_suggestion_sent_from_gui,
    validate_imported_turns,
    validate_profile_form,
)


def main() -> None:
    st.set_page_config(page_title="dating_assistant", layout="wide")
    st.title("dating_assistant")
    st.caption("ローカルGUI")

    tab_viewer, tab_profile, tab_partner_create, tab_import = st.tabs(
        ["partnerビュー", "プロフィール登録", "プロフィールからpartner作成", "会話履歴インポート"]
    )

    with tab_viewer:
        render_partner_viewer()

    with tab_profile:
        render_profile_registration()

    with tab_partner_create:
        render_partner_creation()

    with tab_import:
        render_conversation_import()


def render_partner_viewer() -> None:
    st.subheader("partnerビュー")

    include_archived = st.sidebar.checkbox("archivedを含める", value=False)
    if st.sidebar.button("更新"):
        st.rerun()

    partners = load_partner_choices(include_archived=include_archived)
    if not partners:
        st.info("表示できるpartnerがありません。")
        return

    labels = {build_partner_label(partner): partner.partner_id for partner in partners}
    selected_label = st.sidebar.selectbox("partner選択", options=list(labels.keys()))
    partner = load_partner_for_view(labels[selected_label])

    summary = build_partner_summary(partner)
    st.subheader("状態")
    cols = st.columns(4)
    cols[0].metric("partner_id", summary["partner_id"])
    cols[1].metric("status", summary["status"])
    cols[2].metric("temperature", summary["partner_temperature"])
    cols[3].metric("pending", summary["pending_suggestions_count"])

    st.write(f"**display_name:** {summary['display_name']}")
    st.write(f"**next_action:** {summary['next_action']}")
    with st.expander("message_state", expanded=True):
        st.json(summary["message_state"])

    render_generation_controls(partner)

    tab_history, tab_suggestions, tab_timeline = st.tabs(["会話履歴", "未送信候補", "timeline"])

    with tab_history:
        rows = format_conversation_history(partner)
        if not rows:
            st.info("conversation_history は空です。")
        for row in rows:
            title = f"{row['index']}. {row['speaker_label']}"
            if row["timestamp"]:
                title += f" / {row['timestamp']}"
            with st.expander(title, expanded=True):
                st.text_area("本文", row["text"], height=120, disabled=True, key=f"turn_{row['index']}")

    with tab_suggestions:
        suggestions = format_pending_suggestions(partner)
        if not suggestions:
            st.info("pending_suggestions はありません。")
        for suggestion in suggestions:
            title = f"{suggestion['suggestion_id']} / {suggestion['purpose']} / {suggestion['created_at']}"
            with st.expander(title, expanded=True):
                st.write(f"**status:** {suggestion['status']}")
                st.text_area(
                    "候補本文",
                    suggestion["text"],
                    height=150,
                    disabled=True,
                    key=f"suggestion_{suggestion['suggestion_id']}",
                )
                render_sent_recording_controls(partner, suggestion)
                render_discard_controls(partner, suggestion)

    with tab_timeline:
        timeline = format_timeline_items(partner)
        if not timeline:
            st.info("timeline は空です。")
        else:
            st.dataframe(timeline, width="stretch", hide_index=True)


def render_generation_controls(partner) -> None:
    st.subheader("候補生成")
    mode = get_generation_mode_for_partner(partner)
    mode_label = {"first": "初回メッセージ候補", "reply": "返信候補", "blocked": "生成不可"}[mode]
    st.write(f"**現在:** {build_generation_status_message(partner)}")
    st.write(f"**生成タイプ:** {mode_label}")
    st.caption("候補生成はlocalのpending_suggestionsへ保存するだけです。自動送信ではありません。")
    confirm = st.checkbox("自動送信ではないことを確認し、候補をlocal保存する", key=f"generate_confirm_{partner.partner_id}")
    if st.button(f"{mode_label}を生成する", disabled=not (can_generate_suggestion(partner) and confirm), key=f"generate_button_{partner.partner_id}"):
        try:
            generated = generate_suggestion_for_gui(partner.partner_id)
        except ValueError as error:
            st.error(str(error))
            return
        st.success(f"{generated['suggestion_id']} をpending_suggestionsへ保存しました。")
        st.text_area("生成された候補", generated["text"], height=140, disabled=True, key=f"generated_{generated['suggestion_id']}")
        st.info("実際に手動送信した後、pending_suggestions欄から送信済みとしてlocal記録できます。")
        st.rerun()


def render_sent_recording_controls(partner, suggestion: dict) -> None:
    suggestion_id = suggestion["suggestion_id"]
    st.warning(
        "この操作はlocal記録のみです。マッチングアプリへの送信は行いません。"
        "実際に送っていない文を送信済みにしないでください。"
    )
    confirm = st.checkbox(
        "私はこの文をマッチングアプリ上で手動送信しました",
        key=f"mark_sent_confirm_{partner.partner_id}_{suggestion_id}",
    )
    with st.expander("送信済み記録プレビュー", expanded=False):
        st.json(build_mark_sent_preview(partner, suggestion_id=suggestion_id))

    if st.button(
        "この候補を送信済みとして記録",
        disabled=not can_mark_suggestion_sent(partner, suggestion_id, confirmed=confirm),
        key=f"mark_sent_button_{partner.partner_id}_{suggestion_id}",
    ):
        try:
            result = mark_suggestion_sent_from_gui(partner.partner_id, suggestion_id, confirmed=confirm)
        except ValueError as error:
            st.error(str(error))
            return
        st.success(f"{result['suggestion_id']} を送信済みとしてlocal記録しました。")
        st.rerun()

    custom_text = st.text_area(
        "実際に送った文（修正した場合のみ入力）",
        height=100,
        key=f"mark_sent_custom_text_{partner.partner_id}_{suggestion_id}",
    )
    if custom_text.strip():
        with st.expander("修正文の送信済み記録プレビュー", expanded=False):
            st.json(build_mark_sent_preview(partner, custom_text=custom_text))
        st.info("実際に送信した文を別入力で記録するため、元候補が未使用候補として残る場合があります。")
    if st.button(
        "入力文を送信済みとして記録",
        disabled=not (confirm and custom_text.strip()),
        key=f"mark_custom_sent_button_{partner.partner_id}_{suggestion_id}",
    ):
        try:
            result = mark_custom_text_sent_from_gui(partner.partner_id, custom_text, confirmed=confirm)
        except ValueError as error:
            st.error(str(error))
            return
        st.success("入力文を送信済みとしてlocal記録しました。")
        if result["remaining_pending_suggestions"]:
            st.info("元候補はpendingに残っています。候補破棄機能は次作業で追加します。")
        st.rerun()


def render_discard_controls(partner, suggestion: dict) -> None:
    suggestion_id = suggestion["suggestion_id"]
    st.divider()
    st.markdown("**候補破棄**")
    st.warning(
        "この操作は未使用候補をlocal上で破棄するだけです。conversation_historyは削除されません。"
        "マッチングアプリには何も送信・削除しません。"
    )
    reason = st.text_area(
        "破棄理由",
        value="GUIから未使用候補として破棄",
        height=80,
        key=f"discard_reason_{partner.partner_id}_{suggestion_id}",
    )
    confirm = st.checkbox(
        "この候補を未使用候補として破棄します",
        key=f"discard_confirm_{partner.partner_id}_{suggestion_id}",
    )
    with st.expander("候補破棄プレビュー", expanded=False):
        st.json(build_discard_suggestion_preview(partner, suggestion_id, reason=reason))
    if partner.status == "archived":
        st.warning("archivedのpartnerでは候補破棄できません。")
    if st.button(
        "候補を破棄",
        disabled=not can_discard_suggestion(partner, suggestion_id, confirmed=confirm),
        key=f"discard_button_{partner.partner_id}_{suggestion_id}",
    ):
        try:
            result = discard_suggestion_from_gui(partner.partner_id, suggestion_id, confirmed=confirm, reason=reason)
        except ValueError as error:
            st.error(str(error))
            return
        if result["conversation_history_unchanged"]:
            st.success(f"{result['suggestion_id']} をlocal上で破棄しました。conversation_historyは変更していません。")
        else:
            st.error("conversation_historyが変化しました。状態を確認してください。")
        st.rerun()


def render_profile_registration() -> None:
    st.subheader("プロフィール登録")

    with st.form("profile_registration_form"):
        label = st.text_input("label", help="英数字・ハイフン・アンダースコアのみ")
        display_name = st.text_input("display_name")
        app_name = st.text_input("app_name")
        age = st.number_input("age", min_value=18, max_value=120, value=None, step=1)
        area = st.text_input("area")
        profile_text = st.text_area("profile_text", height=160)
        photo_memo = st.text_area("photo_memo", height=100)
        interests = st.text_area("interests", height=80, help="改行、カンマ、読点で区切れます")
        avoid_topics = st.text_area("avoid_topics", height=80, help="改行、カンマ、読点で区切れます")
        notes = st.text_area("notes", height=100)
        confirm_local_save = st.checkbox("保存内容を確認し、local YAMLとして保存する")
        submitted = st.form_submit_button("保存")

    form = {
        "label": label,
        "display_name": display_name,
        "app_name": app_name,
        "age": "" if age is None else str(age),
        "area": area,
        "profile_text": profile_text,
        "photo_memo": photo_memo,
        "interests": interests,
        "avoid_topics": avoid_topics,
        "notes": notes,
    }

    errors = validate_profile_form(form)
    warnings = detect_profile_safety_warnings(form)
    preview = None
    if not errors:
        preview = build_profile_save_preview(form)
        st.markdown("**保存プレビュー**")
        st.json(preview)
        if real_profile_exists(preview["保存先label"]):
            errors.append("同じlabelのreal profileが既に存在します。上書きはできません。")

    if errors:
        for error in errors:
            st.error(error)
    if warnings:
        st.warning("保存前に見直してください: " + " / ".join(warnings))

    if submitted:
        if errors:
            st.error("保存できません。入力内容を確認してください。")
            return
        if not confirm_local_save:
            st.error("保存前確認チェックを入れてください。")
            return
        try:
            path, save_warnings = save_real_profile_from_form(form)
        except FileExistsError:
            st.error("同じlabelのreal profileが既に存在します。")
            return
        except ValueError as error:
            st.error(str(error))
            return
        st.success(f"保存しました: {path}")
        if save_warnings:
            st.warning("保存内容に注意語が含まれます: " + " / ".join(save_warnings))

    st.info("保存後は「プロフィールからpartner作成」タブでpartner化できます。")


def render_partner_creation() -> None:
    st.subheader("プロフィールからpartner作成")

    profiles = list_real_profiles_for_gui()
    if not profiles:
        st.info("保存済みreal_profileがありません。先にプロフィール登録を行ってください。")
        return

    profile_options = {profile["display_label"]: profile["label"] for profile in profiles}
    with st.form("partner_creation_form"):
        selected_profile = st.selectbox("real_profile選択", options=list(profile_options.keys()))
        display_name = st.text_input("partner display_name")
        app_name = st.text_input("partner app_name")
        source_memo = st.text_area("source memo", height=80)
        confirm_create = st.checkbox("保存内容を確認し、partner YAMLとして保存する")
        submitted = st.form_submit_button("partnerを作成")

    label = profile_options[selected_profile]
    preview = build_partner_creation_preview(label, display_name=display_name, app_name=app_name, source_memo=source_memo)
    st.markdown("**保存プレビュー**")
    st.json(preview)

    if submitted:
        if not confirm_create:
            st.error("保存前確認チェックを入れてください。")
            return
        partner = save_partner_from_profile(label, display_name=display_name, app_name=app_name, source_memo=source_memo)
        st.success(f"保存しました: {partner.partner_id}")
        st.info("返信候補生成とmark-sentは次作業以降で追加します。")


def render_conversation_import() -> None:
    st.subheader("会話履歴インポート")

    partners = load_partner_choices(include_archived=False)
    if not partners:
        st.info("インポート対象のpartnerがありません。")
        return

    labels = {build_partner_label(partner): partner.partner_id for partner in partners}
    with st.form("conversation_import_form"):
        selected_label = st.selectbox("対象partner選択", options=list(labels.keys()))
        user_label = st.text_input("自分の発話者ラベル", value="自分")
        partner_label = st.text_input("相手の発話者ラベル", value="相手")
        pasted = st.text_area("会話履歴貼り付け欄", height=220)
        confirm_import = st.checkbox("保存内容を確認し、conversation_historyへ追加する")
        submitted = st.form_submit_button("会話履歴を保存")

    normalized = _normalize_conversation_labels(pasted, user_label, partner_label)
    turns, parse_warnings = parse_conversation_paste(normalized)
    safety_warnings = detect_conversation_safety_warnings(pasted)
    partner = load_partner_for_view(labels[selected_label])
    errors = validate_imported_turns(turns, parse_warnings)
    duplicate_warning = detect_duplicate_turn_sequence(partner, turns)
    warnings = list(parse_warnings)
    if safety_warnings:
        warnings.append("安全チェック: " + " / ".join(safety_warnings))
    if duplicate_warning:
        warnings.append("既存conversation_history末尾と完全一致する連続turnです。")

    if turns:
        st.markdown("**保存プレビュー**")
        st.json(build_conversation_import_preview(partner, turns, warnings))
    if errors:
        for error in errors:
            st.error(error)
    if safety_warnings:
        st.warning("保存前に見直してください: " + " / ".join(safety_warnings))
    if duplicate_warning:
        st.warning("既存conversation_history末尾と完全一致する連続turnです。")

    if submitted:
        if errors:
            st.error("保存できません。貼り付け内容を確認してください。")
            return
        if not confirm_import:
            st.error("保存前確認チェックを入れてください。")
            return
        updated = append_conversation_turns_to_partner(partner.partner_id, turns)
        st.success(f"保存しました: {updated.partner_id} に {len(turns)} turn 追加")
        st.info("返信候補生成とmark-sentは次作業以降で追加します。")


def _normalize_conversation_labels(text: str, user_label: str, partner_label: str) -> str:
    replacements = {}
    if user_label.strip() and user_label.strip() not in {"自分", "user", "me"}:
        replacements[user_label.strip()] = "自分"
    if partner_label.strip() and partner_label.strip() not in {"相手", "partner", "you"}:
        replacements[partner_label.strip()] = "相手"
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        replaced = line
        for source, target in replacements.items():
            if stripped.startswith(f"{source}:") or stripped.startswith(f"{source}："):
                prefix_len = len(source)
                replaced = f"{target}{stripped[prefix_len:]}"
                break
        lines.append(replaced)
    return "\n".join(lines)


if __name__ == "__main__":
    main()
