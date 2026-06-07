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
    format_conversation_history,
    format_pending_suggestions,
    format_timeline_items,
    load_partner_choices,
    load_partner_for_view,
)


def main() -> None:
    st.set_page_config(page_title="dating_assistant", layout="wide")
    st.title("dating_assistant")
    st.caption("読み取り専用ビューア")

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
            st.dataframe(timeline, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
