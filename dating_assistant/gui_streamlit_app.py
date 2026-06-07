from __future__ import annotations

import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import streamlit as st

from gui_helpers import (
    build_partner_label,
    build_partner_summary,
    build_profile_save_preview,
    detect_profile_safety_warnings,
    format_conversation_history,
    format_pending_suggestions,
    format_timeline_items,
    load_partner_choices,
    load_partner_for_view,
    real_profile_exists,
    save_real_profile_from_form,
    validate_profile_form,
)


def main() -> None:
    st.set_page_config(page_title="dating_assistant", layout="wide")
    st.title("dating_assistant")
    st.caption("ローカルGUI")

    tab_viewer, tab_profile = st.tabs(["partnerビュー", "プロフィール登録"])

    with tab_viewer:
        render_partner_viewer()

    with tab_profile:
        render_profile_registration()


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

    with tab_timeline:
        timeline = format_timeline_items(partner)
        if not timeline:
            st.info("timeline は空です。")
        else:
            st.dataframe(timeline, width="stretch", hide_index=True)


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

    st.info("partner作成は次作業で追加します。")


if __name__ == "__main__":
    main()
