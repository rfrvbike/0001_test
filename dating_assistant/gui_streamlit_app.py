from __future__ import annotations

import base64
import io
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
_USER_PROFILE_PATH = APP_DIR / "data" / "local" / "user_profile.json"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import streamlit as st

from src.claude_generator import (
    generate_like_message,
    generate_reply_candidates_for_gui,
    is_api_key_configured,
)

from gui_helpers import (
    append_conversation_turns_to_partner,
    delete_conversation_turn_from_gui,
    get_partner_photo_path,
    save_partner_photo_from_gui,
    delete_partner_photo_from_gui,
    load_memo_tag,
    save_memo_tag_from_gui,
    delete_partner_completely_from_gui,
    build_partner_summary,
    build_partner_creation_preview,
    build_partner_choice_label,
    build_partner_management_filter_options,
    build_partner_profile_card,
    build_partner_workspace_overview,
    build_profile_form_from_paste,
    build_profile_ocr_failure_guidance,
    build_profile_ocr_privacy_notes,
    build_profile_ocr_text_preview,
    build_profile_paste_preview,
    build_profile_save_debug_info,
    build_profile_save_payload,
    build_profile_save_preview,
    build_profile_display_sections,
    build_real_profile_summary_for_gui,
    filter_real_profiles_for_gui,
    detect_duplicate_turn_sequence,
    detect_profile_safety_warnings,
    format_conversation_history,
    build_profile_label_candidate,

    get_profile_ocr_environment_status,
    get_clipboard_image_for_ocr,
    extract_profile_text_from_image,
    ensure_conversation_partner_for_profile,
    format_partner_preview_for_display,
    GENERATION_OBJECTIVE_OPTIONS,
    GENERATION_TONE_OPTIONS,
    get_skipped_partner_files,
    archive_partner_from_gui,
    load_partner_choices,
    load_partner_for_view,
    list_real_profiles_for_gui,
    load_uploaded_image_for_ocr,
    real_profile_exists,
    save_real_profile_from_form,
    summarize_existing_partner_candidates,
    summarize_partner_management_rows,
    unarchive_partner_from_gui,
    update_partner_management_info_from_gui,
)


_CUSTOM_CSS = """
<style>
/* ===== 全体: フォント・背景・テキスト色 ===== */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #FAFAFA;
    color: #2D2D2D;
    font-family: "Hiragino Kaku Gothic ProN", "Hiragino Sans", "Yu Gothic UI", "Meiryo", sans-serif;
}
[data-testid="stAppViewContainer"] .block-container {
    max-width: 1100px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}
p, li, label, [data-testid="stMarkdownContainer"] p {
    font-size: 16px;
    line-height: 1.7;
}
h1 {
    color: #E85D8A;
    font-weight: 800;
    letter-spacing: 0.02em;
}
h2, h3 {
    color: #2D2D2D;
    font-weight: 700;
}

/* ===== タブ ===== */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    border-bottom: 2px solid #F8A5C2;
}
.stTabs [data-baseweb="tab"] {
    font-size: 16px;
    font-weight: 700;
    padding: 10px 22px;
    border-radius: 12px 12px 0 0;
    background-color: #FFFFFF;
    color: #2D2D2D;
}
.stTabs [aria-selected="true"] {
    background-color: #E85D8A !important;
    color: #FFFFFF !important;
}

/* ===== ボタン共通: ホバーエフェクト ===== */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
    border-radius: 10px;
    font-weight: 700;
    font-size: 15px;
    border: 1.5px solid #F8A5C2;
    color: #E85D8A;
    background-color: #FFFFFF;
    transition: all 0.15s ease-in-out;
}
.stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover {
    border-color: #E85D8A;
    background-color: #FDEFF4;
    box-shadow: 0 3px 10px rgba(232, 93, 138, 0.25);
    transform: translateY(-1px);
}

/* ===== メインアクション（primary）: 大きくメインカラー ===== */
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"] {
    background: linear-gradient(135deg, #E85D8A 0%, #FF6B9D 100%);
    color: #FFFFFF;
    border: none;
    padding: 0.65rem 1.6rem;
    font-size: 16px;
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primaryFormSubmit"]:hover {
    background: linear-gradient(135deg, #FF6B9D 0%, #E85D8A 100%);
    color: #FFFFFF;
    box-shadow: 0 4px 14px rgba(232, 93, 138, 0.45);
}

/* ===== カード（border付きコンテナ）: シャドウ ===== */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px;
    background-color: #FFFFFF;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

/* ===== expander ===== */
[data-testid="stExpander"] details {
    border-radius: 10px;
    border: 1px solid #F0E4E9;
    background-color: #FFFFFF;
}
[data-testid="stExpander"] summary {
    font-weight: 600;
}

/* ===== 会話履歴の✕削除ボタン: 普段は薄く・ホバーで濃く ===== */
div[class*="st-key-delwrap_"] button {
    border: none;
    background: transparent;
    color: #BBBBBB;
    font-size: 13px;
    padding: 2px 8px;
    min-height: 28px;
    opacity: 0.45;
    box-shadow: none;
}
div[class*="st-key-delwrap_"] button:hover {
    opacity: 1;
    color: #E85D8A;
    background-color: #FDEFF4;
    transform: none;
    box-shadow: none;
}

/* ===== 返信候補カード: A/B/Cの背景色 ===== */
div[class*="st-key-cand_card_0"] {
    background-color: #FDF0F5;
}
div[class*="st-key-cand_card_1"] {
    background-color: #EFF5FD;
}
div[class*="st-key-cand_card_2"] {
    background-color: #EFFAF2;
}
</style>
"""


def main() -> None:
    st.set_page_config(page_title="dating_assistant", page_icon="💬", layout="wide")
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)
    st.title("dating_assistant")
    st.caption("ローカルGUI")
    st.info(
        "このツールは、マッチングアプリ上で送るメッセージ候補を作るための補助画面です。"
        "まず「👤 相手を管理する」タブのプロフィール登録で相手情報を登録し、保存後に「💬 会話する」で候補を作ります。"
        "自動送信は行いません。実際の送信はマッチングアプリ上でユーザー本人が手動で行います。"
    )

    tab_talk, tab_manage, tab_settings = st.tabs(
        ["💬 会話する", "👤 相手を管理する", "⚙️ 設定"]
    )

    with tab_talk:
        render_partner_viewer()

    with tab_manage:
        sub_tab_profile, sub_tab_partners, sub_tab_import = st.tabs(
            ["📝 プロフィール登録", "👥 登録済みの相手", "💬 会話履歴追加"]
        )
        with sub_tab_profile:
            render_profile_registration()
        with sub_tab_partners:
            render_partner_creation()
        with sub_tab_import:
            render_conversation_import()

    with tab_settings:
        render_help()


def _escape_card_html(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_partner_card_body(partner) -> None:
    photo_path = get_partner_photo_path(partner.partner_id)
    if photo_path:
        encoded_photo = base64.b64encode(photo_path.read_bytes()).decode("ascii")
        avatar_html = (
            f'<img src="data:image/jpeg;base64,{encoded_photo}" '
            'style="width:60px;height:60px;border-radius:50%;object-fit:cover;'
            'border:2px solid #F8A5C2;flex-shrink:0;">'
        )
    else:
        avatar_html = (
            '<div style="width:60px;height:60px;border-radius:50%;background:#FDEFF4;'
            'border:2px solid #F8A5C2;display:flex;align-items:center;justify-content:center;'
            'font-size:28px;flex-shrink:0;">😊</div>'
        )
    name = _escape_card_html(partner.display_name or "表示名未設定")
    memo_tag = _escape_card_html(load_memo_tag(partner.partner_id))
    memo_html = (
        f'<div style="font-size:12px;color:#999;">{memo_tag}</div>' if memo_tag else ""
    )
    timestamps = [turn.timestamp for turn in partner.conversation if turn.timestamp]
    last_conv = max(timestamps)[:16].replace("T", " ") if timestamps else "会話なし"
    stage = _escape_card_html(build_partner_workspace_overview(partner)["conversation_stage"])
    unreplied = (
        '<span style="font-size:12px;margin-left:6px;">🔴</span>'
        if partner.message_state.awaiting_user_action
        else ""
    )
    st.markdown(
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
        f"{avatar_html}"
        "<div>"
        f'<div style="font-size:16px;font-weight:800;color:#2D2D2D;">{name}{unreplied}</div>'
        f"{memo_html}"
        f'<div style="font-size:11px;color:#AAA;">最終会話: {last_conv}</div>'
        "</div></div>"
        '<span style="display:inline-block;background:#FDEFF4;color:#E85D8A;'
        'border-radius:999px;padding:3px 12px;font-size:12px;font-weight:600;">'
        f"{stage}</span>",
        unsafe_allow_html=True,
    )


def _select_partner_cb(select_key, label, partner_id) -> None:
    # コールバック内ならselectboxのwidget keyを安全に更新できる（再実行前に走るため）
    st.session_state[select_key] = label
    st.session_state["selected_partner_id"] = partner_id


def _last_conversation_ts(partner) -> str:
    timestamps = [turn.timestamp for turn in partner.conversation if turn.timestamp]
    return max(timestamps) if timestamps else ""


def _filter_and_sort_partners(partners, search_text, filter_mode, sort_mode):
    search = (search_text or "").strip().lower()
    result = []
    for partner in partners:
        if search:
            name = (partner.display_name or "").lower()
            memo = load_memo_tag(partner.partner_id).lower()
            if search not in name and search not in memo:
                continue
        if filter_mode == "未返信" and not partner.message_state.awaiting_user_action:
            continue
        if filter_mode == "返信待ち" and not partner.message_state.awaiting_partner_reply:
            continue
        result.append(partner)
    if sort_mode == "名前順":
        result.sort(key=lambda partner: (partner.display_name or ""))
    elif sort_mode == "登録日が新しい順":
        result.sort(key=lambda partner: (partner.created_at or ""), reverse=True)
    else:  # 最終会話日が新しい順（デフォルト）
        result.sort(key=_last_conversation_ts, reverse=True)
    return result


def _render_partner_selection_cards(partners, selected_partner_id, label_by_id, select_key) -> None:
    # 選択中カードをピンク系ボーダーで強調（コンテナのkeyクラスを利用）
    st.markdown(
        f"<style>.st-key-pcard_{selected_partner_id}"
        "{border:2px solid #E85D8A !important;border-radius:14px;"
        "box-shadow:0 2px 10px rgba(232,93,138,0.25);}</style>",
        unsafe_allow_html=True,
    )
    for row_start in range(0, len(partners), 3):
        row_partners = partners[row_start:row_start + 3]
        columns = st.columns(3)
        for column, partner_choice in zip(columns, row_partners):
            partner_id = partner_choice.partner_id
            with column:
                with st.container(border=True, key=f"pcard_{partner_id}"):
                    body_col, trash_col = st.columns([5, 1])
                    with body_col:
                        _render_partner_card_body(partner_choice)
                    with trash_col:
                        if st.button("🗑️", key=f"card_trash_{partner_id}", help="この相手を削除する"):
                            st.session_state[f"confirm_card_delete_{partner_id}"] = True
                            st.rerun()
                    is_selected = partner_id == selected_partner_id
                    st.button(
                        "✓ 選択中" if is_selected else "この相手を選ぶ",
                        key=f"pcard_btn_{partner_id}",
                        type="primary" if is_selected else "secondary",
                        use_container_width=True,
                        on_click=_select_partner_cb,
                        args=(select_key, label_by_id[partner_id], partner_id),
                    )
                    if st.session_state.get(f"confirm_card_delete_{partner_id}"):
                        st.warning("本当に削除しますか？この操作は取り消せません。")
                        del_yes, del_no = st.columns(2)
                        if del_yes.button("削除する", key=f"card_del_yes_{partner_id}", type="primary", use_container_width=True):
                            delete_partner_completely_from_gui(partner_id, confirmed=True)
                            st.session_state.pop(f"confirm_card_delete_{partner_id}", None)
                            st.session_state["selected_partner_id"] = ""
                            st.rerun()
                        if del_no.button("キャンセル", key=f"card_del_no_{partner_id}", use_container_width=True):
                            st.session_state.pop(f"confirm_card_delete_{partner_id}", None)
                            st.rerun()


def render_partner_viewer() -> None:
    st.subheader("相手と会話する")
    st.caption("相手を選び、プロフィールと会話履歴を見ながら、次に送る文を作る画面です。実際の送信はマッチングアプリ上で手動で行います。")

    include_archived = st.checkbox("アーカイブ済みの相手も表示", value=False)
    partners = load_partner_choices(include_archived=include_archived)
    _render_skipped_partner_warning()
    if not partners:
        st.markdown(
            '<div style="background:linear-gradient(135deg,#FDEFF4 0%,#FFF5F9 100%);'
            'border:1.5px solid #F8A5C2;border-radius:16px;padding:28px 24px;'
            'text-align:center;margin:12px 0;">'
            '<div style="font-size:22px;font-weight:800;color:#E85D8A;margin-bottom:8px;">まずは相手を登録しましょう！</div>'
            '<div style="font-size:16px;color:#2D2D2D;">「👤 相手を管理する」タブから相手のプロフィールを登録してください。</div>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.info(
            "まだ会話対象が登録されていません。"
            "まず「プロフィール登録」で相手のプロフィール情報を貼り付けて保存してください。"
            "保存後、この画面に自動で表示され、初回メッセージ候補を作れます。"
        )
        return

    labels: dict[str, str] = {}
    for partner_choice in partners:
        label = build_partner_choice_label(partner_choice)
        if label in labels:
            base = label
            counter = 2
            while f"{base} ({counter})" in labels:
                counter += 1
            label = f"{base} ({counter})"
        labels[label] = partner_choice.partner_id
    label_by_id = {partner_id: label for label, partner_id in labels.items()}
    partner_ids = list(label_by_id.keys())

    # 選択状態はカードとプルダウンで共有する。
    # プルダウンはテスト互換のため最初のselectboxとして残し、検索・並び替えより前に置く。
    select_key = "talk_partner_select"
    if st.session_state.get(select_key) not in labels:
        fallback_id = str(st.session_state.get("selected_partner_id", "") or "")
        if fallback_id not in partner_ids:
            fallback_id = partner_ids[0]
        st.session_state[select_key] = label_by_id[fallback_id]

    with st.expander("プルダウンでも選べます", expanded=False):
        selected_label = st.selectbox("相手を選ぶ", options=list(labels.keys()), key=select_key)
    selected_partner_id = labels[selected_label]
    st.session_state["selected_partner_id"] = selected_partner_id

    # 主UI: カード一覧（横3列・モバイルは1列）。上に検索・絞り込み・並び替えを置く。
    st.markdown("#### 相手を選ぶ")
    search_text = st.text_input(
        "検索",
        placeholder="名前・識別メモで検索",
        key="card_search_text",
        label_visibility="collapsed",
    )
    filter_mode = st.session_state.get("card_filter_mode", "すべて")
    filter_cols = st.columns(3)
    if filter_cols[0].button(
        "すべて", key="card_filter_all",
        type="primary" if filter_mode == "すべて" else "secondary",
        use_container_width=True,
    ):
        st.session_state["card_filter_mode"] = "すべて"
        st.rerun()
    if filter_cols[1].button(
        "🔴 未返信", key="card_filter_unreplied",
        type="primary" if filter_mode == "未返信" else "secondary",
        use_container_width=True,
    ):
        st.session_state["card_filter_mode"] = "未返信"
        st.rerun()
    if filter_cols[2].button(
        "💬 返信待ち", key="card_filter_waiting",
        type="primary" if filter_mode == "返信待ち" else "secondary",
        use_container_width=True,
    ):
        st.session_state["card_filter_mode"] = "返信待ち"
        st.rerun()
    sort_mode = st.selectbox(
        "並び替え",
        options=["最終会話日が新しい順", "名前順", "登録日が新しい順"],
        key="card_sort_mode",
    )

    display_partners = _filter_and_sort_partners(
        partners,
        search_text,
        st.session_state.get("card_filter_mode", "すべて"),
        sort_mode,
    )
    if display_partners:
        _render_partner_selection_cards(display_partners, selected_partner_id, label_by_id, select_key)
    else:
        st.info("条件に一致する相手がいません。検索条件や絞り込みを変えてください。")

    partner = load_partner_for_view(selected_partner_id)
    workspace = build_partner_workspace_overview(partner)

    chips = "".join(
        f'<span style="display:inline-block;background:#FDEFF4;color:#E85D8A;'
        f'border-radius:999px;padding:4px 14px;margin:4px 6px 0 0;font-size:13px;font-weight:600;">{label}: {value}</span>'
        for label, value in [
            ("今やること", workspace["next_action"]),
            ("会話ステージ", workspace["conversation_stage"]),
            ("温度感", workspace["temperature"]),
            ("未確認候補", workspace["pending_count"]),
        ]
    )
    photo_path = get_partner_photo_path(partner.partner_id)
    if photo_path:
        encoded_photo = base64.b64encode(photo_path.read_bytes()).decode("ascii")
        avatar_html = (
            f'<img src="data:image/jpeg;base64,{encoded_photo}" '
            f'style="width:80px;height:80px;border-radius:50%;object-fit:cover;'
            f'border:2px solid #F8A5C2;flex-shrink:0;">'
        )
    else:
        avatar_html = (
            '<div style="width:80px;height:80px;border-radius:50%;background:#FDEFF4;'
            'border:2px solid #F8A5C2;display:flex;align-items:center;justify-content:center;'
            'font-size:36px;flex-shrink:0;">😊</div>'
        )
    st.markdown(
        f'<div style="background:#FFFFFF;border:1px solid #F0E4E9;border-radius:14px;'
        f'padding:16px 20px;margin:8px 0 16px 0;box-shadow:0 2px 8px rgba(0,0,0,0.06);'
        f'display:flex;align-items:center;gap:16px;">'
        f"{avatar_html}"
        f"<div>"
        f'<div style="font-size:24px;font-weight:800;color:#2D2D2D;">{workspace["title"]}</div>'
        f'<div style="font-size:13px;color:#888;margin:2px 0 6px 0;">{workspace["subtitle"]}</div>'
        f"<div>{chips}</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([4, 6])
    with left:
        st.markdown("### 📋 相手のプロフィール")
        with st.expander("プロフィール詳細を見る", expanded=False):
            _render_profile_display_card(build_partner_profile_card(partner))

    with right:
        st.markdown("### 💬 会話履歴")
        render_conversation_history_section(partner)

    st.divider()
    render_inline_conversation_import(partner)

    if not partner.conversation:
        st.divider()
        render_like_message_controls(partner)

    st.divider()
    render_generation_controls(partner)


def render_like_message_controls(partner) -> None:
    st.subheader("💝 いいね文言を生成する")
    st.caption(
        "まだ会話していない相手へのいいね文言を生成します。"
        "相手のプロフィールをもとに、自然で返信率の高い文言を3パターン作ります。"
    )
    tone = st.radio(
        "文言のトーン",
        options=["自然・普通", "少し明るく・ユーモアあり", "丁寧・真面目"],
        index=0,
        key=f"like_message_tone_{partner.partner_id}",
    )
    if st.button("いいね文言を生成する", type="primary", key=f"like_message_button_{partner.partner_id}"):
        if not is_api_key_configured():
            st.error(
                "APIキーが設定されていません。"
                "設定・ヘルプタブでAPIキーの設定方法を確認してください。"
            )
            return
        try:
            with st.spinner("文言を考えています..."):
                messages = generate_like_message(partner.partner_id, tone=tone)
        except ValueError as error:
            st.error(f"生成中にエラーが発生しました。{error}")
            return
        st.session_state[f"last_like_messages_{partner.partner_id}"] = messages
        st.success("いいね文言を3パターン作りました。気に入った文をコピーして使ってください。")

    messages = st.session_state.get(f"last_like_messages_{partner.partner_id}", [])
    if messages:
        chip_colors = ["#E85D8A", "#4A90D9", "#3CA86B"]
        columns = st.columns(len(messages))
        for index, (column, message_text) in enumerate(zip(columns, messages)):
            text_key = f"like_message_{partner.partner_id}_{index}"
            chip_color = chip_colors[index % len(chip_colors)]
            with column:
                with st.container(border=True, key=f"like_card_{index}_{partner.partner_id}"):
                    st.markdown(
                        f'<span style="display:inline-block;background:{chip_color};color:#FFFFFF;'
                        f'border-radius:999px;padding:3px 14px;font-size:13px;font-weight:700;">'
                        f"パターン{index + 1}</span>",
                        unsafe_allow_html=True,
                    )
                    edited_text = st.text_area(
                        "いいね文言",
                        message_text,
                        height=100,
                        key=text_key,
                    )
                    char_count = len(edited_text)
                    over_limit = char_count > 140
                    color = "#E85D8A" if over_limit else "#888888"
                    st.markdown(
                        f'<div style="font-size:12px;color:{color};text-align:right;">'
                        f"{char_count}文字（140文字以内推奨）</div>",
                        unsafe_allow_html=True,
                    )


def render_conversation_history_section(partner) -> None:
    rows = format_conversation_history(partner)
    if not rows:
        st.info("まだ会話履歴はありません。会話履歴が少なくても候補は作れます。")
        return
    for row in rows[-20:]:
        is_user = row["speaker"] == "user"
        name = "自分" if is_user else "相手"
        align = "right" if is_user else "left"
        bubble_style = (
            "background:#FCE0EC;border:1px solid #F8A5C2;border-radius:16px 16px 4px 16px;"
            if is_user
            else "background:#FFFFFF;border:1px solid #DDDDDD;border-radius:16px 16px 16px 4px;"
        )
        text = row["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        timestamp = str(row["timestamp"] or "")[:16].replace("T", " ")
        timestamp_html = (
            f'<div style="font-size:10px;color:#AAAAAA;margin-top:3px;text-align:{align};">{timestamp}</div>'
            if timestamp else ""
        )
        msg_col, del_col = st.columns([9, 1])
        with msg_col:
            st.markdown(
                f'<div style="display:flex;justify-content:{"flex-end" if is_user else "flex-start"};margin-bottom:6px;">'
                f'<div style="max-width:85%;{bubble_style}padding:10px 14px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">'
                f'<div style="font-size:11px;color:#999;text-align:{align};margin-bottom:2px;">{name}</div>'
                f'<div style="font-size:15px;line-height:1.6;color:#2D2D2D;text-align:{align};">{text}</div>'
                f"{timestamp_html}"
                f"</div></div>",
                unsafe_allow_html=True,
            )
        with del_col:
            with st.container(key=f"delwrap_{partner.partner_id}_{row['index']}"):
                if st.button("✕", key=f"del_turn_{partner.partner_id}_{row['index']}", help="このメッセージを削除"):
                    try:
                        delete_conversation_turn_from_gui(partner.partner_id, row["index"])
                        st.success("削除しました")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))


def render_inline_conversation_import(partner) -> None:
    with st.expander("新しいメッセージを追加する", expanded=False):
        speaker_option = st.radio(
            "発言者",
            options=["相手から届いたメッセージ", "自分が送ったメッセージ"],
            key=f"inline_conv_speaker_{partner.partner_id}",
            horizontal=True,
        )
        message_text = st.text_area(
            "メッセージ",
            placeholder="メッセージを貼り付けてください",
            height=100,
            key=f"inline_conv_text_{partner.partner_id}",
        )
        if st.button("追加する", type="primary", key=f"inline_conv_add_{partner.partner_id}"):
            if not message_text.strip():
                st.error("メッセージを入力してください")
                return
            speaker = "partner" if speaker_option == "相手から届いたメッセージ" else "user"
            new_turn = {"speaker": speaker, "text": message_text.strip()}
            reload_partner = load_partner_for_view(partner.partner_id)
            if detect_duplicate_turn_sequence(reload_partner, [new_turn]):
                st.warning("同じ内容がすでに登録されています")
                return
            append_conversation_turns_to_partner(partner.partner_id, [new_turn])
            st.success("追加しました")
            st.rerun()



def render_generation_controls(partner) -> None:
    st.subheader("次に送る文を作る")
    objectives = st.multiselect(
        "どんな会話にしたいか",
        options=GENERATION_OBJECTIVE_OPTIONS,
        default=["相手のプロフィールに触れる", "質問を1つ入れる"],
        help="電話、会う提案、LINE交換、大人っぽい雰囲気は下の方に置いています。会話の温度感が十分ある場合だけ選んでください。",
        key=f"generation_objectives_{partner.partner_id}",
    )
    st.caption("電話・会う提案・LINE交換・大人っぽい雰囲気は、相手の反応が良い場合だけ慎重に使います。")
    tone = st.selectbox(
        "文の雰囲気",
        options=GENERATION_TONE_OPTIONS,
        index=0,
        key=f"generation_tone_{partner.partner_id}",
    )
    place_hint = ""
    if any("場所" in objective for objective in objectives):
        place_hint = st.text_input(
            "場所の指定",
            placeholder="例: 新宿あたり / 近場のカフェ / 仕事帰りに寄りやすい場所",
            key=f"generation_place_{partner.partner_id}",
        )
    st.caption("候補はlocalに保存されるだけです。実際に送る文は、ユーザー本人がマッチングアプリ上で手動送信してください。")
    if st.button("返信候補を生成する", type="primary", key=f"generate_button_{partner.partner_id}"):
        if not is_api_key_configured():
            st.error(
                "APIキーが設定されていません。"
                "設定・ヘルプタブでAPIキーの設定方法を確認してください。"
            )
            return
        try:
            with st.spinner("Claude AIが返信を考えています..."):
                generated = generate_reply_candidates_for_gui(
                    partner.partner_id,
                    objectives=objectives,
                    tone=tone,
                    place_hint=place_hint,
                )
        except ValueError as error:
            st.error(f"生成中にエラーが発生しました。{error}")
            return
        st.session_state[f"last_generated_{partner.partner_id}"] = generated["variants"]
        st.success("返信候補を3つ作りました。気に入った文をコピーして、マッチングアプリで手動送信してください。")

    variants = st.session_state.get(f"last_generated_{partner.partner_id}", [])
    if variants:
        chip_colors = ["#E85D8A", "#4A90D9", "#3CA86B"]
        columns = st.columns(len(variants))
        for index, (column, variant) in enumerate(zip(columns, variants)):
            text_key = f"generated_{partner.partner_id}_{variant['suggestion_id']}"
            chip_color = chip_colors[index % len(chip_colors)]
            with column:
                with st.container(border=True, key=f"cand_card_{index}_{partner.partner_id}"):
                    st.markdown(
                        f'<span style="display:inline-block;background:{chip_color};color:#FFFFFF;'
                        f'border-radius:999px;padding:3px 14px;font-size:13px;font-weight:700;">'
                        f"{variant['title']}</span>",
                        unsafe_allow_html=True,
                    )
                    st.text_area(
                        "候補本文",
                        variant["text"],
                        height=200,
                        key=text_key,
                    )
                    if st.button("✓ この文章を送った", key=f"sent_{partner.partner_id}_{variant['suggestion_id']}"):
                        sent_text = st.session_state.get(text_key, variant["text"])
                        new_turn = {"speaker": "user", "text": sent_text.strip()}
                        reload_partner = load_partner_for_view(partner.partner_id)
                        if detect_duplicate_turn_sequence(reload_partner, [new_turn]):
                            st.warning("同じ内容がすでに登録されています")
                        else:
                            append_conversation_turns_to_partner(partner.partner_id, [new_turn])
                            st.success("送信済みとして登録しました")
                            st.rerun()


def render_profile_registration() -> None:
    st.subheader("プロフィール登録")

    if "profile_paste_text" not in st.session_state:
        st.session_state["profile_paste_text"] = ""
    _render_profile_ocr_intake()
    pasted_seed_form, _seed_warnings = build_profile_form_from_paste(str(st.session_state.get("profile_paste_text", "")))
    label_seed_candidate = None
    if st.session_state.get("profile_paste_text"):
        label_seed_candidate = build_profile_label_candidate(str(pasted_seed_form.get("display_name", "")))

    with st.form("profile_registration_form"):
        st.markdown("### まずここにプロフィールを貼り付け")
        st.info(
            "ChatGPTプロジェクトで整理したプロフィール文や、アプリ上で読める自己紹介・趣味・写真の印象メモをここに貼り付けます。"
            "情報が少なくても保存できます。保存IDは自動生成するため、入力する必要はありません。"
            "下の入力欄は、自動抽出できなかった項目だけ補助的に使います。"
        )
        profile_paste = st.text_area(
            "プロフィール情報まとめ貼り付け欄",
            height=320,
            key="profile_paste_text",
            help="マッチングアプリ上のプロフィール文、自己紹介、趣味、エリア、年齢、写真の印象メモなどをまとめて貼り付けます。画像そのものは保存しません。",
        )
        st.caption("スクリーンショット画像や顔写真そのものは保存しません。読み取ったテキストとメモだけを貼り付けてください。")
        st.caption("テキストを貼り付けて「保存」を押すと、内容のプレビューが表示されます。")
        with st.expander("貼り付け形式の例", expanded=False):
            st.caption("ChatGPTプロジェクトから出力する場合は、この形式がおすすめです。")
            st.code(_profile_paste_format_example(), language="text")
        with st.expander("不足分・修正欄", expanded=False):
            st.caption("自動抽出できなかった項目だけ、必要に応じて修正してください。")
            if label_seed_candidate:
                st.info("保存IDは保存時に自動生成します。入力・修正する必要はありません。")
            display_name = st.text_input("display_name", value=str(pasted_seed_form.get("display_name", "")))
            app_name = st.text_input("app_name", value=str(pasted_seed_form.get("app_name", "")))
            age = st.number_input("age", min_value=18, max_value=120, value=None, step=1)
            area = st.text_input("area", value=str(pasted_seed_form.get("area", "")))
            profile_text = st.text_area("profile_text", value=str(pasted_seed_form.get("profile_text", "")), height=160)
            photo_memo = st.text_area("photo_memo", value=str(pasted_seed_form.get("photo_memo", "")), height=100)
            interests = st.text_area("interests", value=str(pasted_seed_form.get("interests", "")), height=80, help="改行、カンマ、読点で区切れます")
            avoid_topics = st.text_area("avoid_topics", value=str(pasted_seed_form.get("avoid_topics", "")), height=80, help="改行、カンマ、読点で区切れます")
            notes = st.text_area("notes", value=str(pasted_seed_form.get("notes", "")), height=100)
        confirm_local_save = st.checkbox("保存内容を確認し、このプロフィールをlocal保存する")
        submitted = st.form_submit_button("保存")

    form = {
        "label": "",
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
    pasted_form, paste_warnings = build_profile_form_from_paste(profile_paste)
    has_profile_input = bool(profile_paste.strip()) or any(
        str(value).strip() for key, value in form.items() if key != "label"
    )
    form, label_meta, errors, save_readiness_warnings = build_profile_save_payload(form, pasted_form, label_seed_candidate)

    warnings = detect_profile_safety_warnings(form)
    warnings.extend(save_readiness_warnings)
    if paste_warnings:
        warnings.extend(paste_warnings)
    if profile_paste.strip():
        _render_profile_paste_preview_card(build_profile_paste_preview(profile_paste, label_meta))
        st.info("抽出できなかった項目や違う項目は、不足分・修正欄で直してから保存してください。")
    elif not submitted:
        st.info("プロフィールを貼り付けると、保存に必要な項目を確認できます。")
    preview = None
    if has_profile_input and not errors:
        preview = build_profile_save_preview(form)
        st.markdown("**保存前の確認**")
        display_preview = dict(preview)
        display_preview.pop("保存先label", None)
        display_preview["保存ID"] = "自動生成済み"
        st.write(f"表示名: {form.get('display_name') or '表示名未設定'}")
        st.write(f"自己紹介: {form.get('profile_text') or 'プロフィール本文未設定'}")
        st.write(f"状態: {form.get('profile_status') or '情報確認中'}")
        st.caption("保存IDは自動生成します。情報が少ない場合も、あとから補完できます。")
        with st.expander("保存前データの詳細を表示（開発者向け）", expanded=False):
            st.json(display_preview)
        if real_profile_exists(preview["保存先label"]):
            errors.append("同じ保存IDのプロフィールが既に存在します。上書きはできません。")

    if submitted and errors:
        for error in errors:
            st.error(error)
        st.error("保存IDを自動生成できませんでした。もう一度試すか、アプリを再起動してください。")
    if submitted and warnings:
        st.warning("保存前に見直してください: " + " / ".join(warnings))

    if submitted:
        debug_info = build_profile_save_debug_info(form, errors, warnings, has_profile_input=has_profile_input)
        if not has_profile_input:
            st.error("保存対象のプロフィール情報が空です。貼り付け欄または補助入力欄に1文字以上入力してください。")
            with st.expander("保存前データ確認（開発者向け詳細）", expanded=True):
                st.json(debug_info)
            return
        if errors:
            st.error("保存できません。入力内容を確認してください。")
            with st.expander("保存前データ確認（開発者向け詳細）", expanded=True):
                st.json(debug_info)
            return
        if not confirm_local_save:
            st.error("保存前確認チェックを入れてください。")
            with st.expander("保存前データ確認（開発者向け詳細）", expanded=False):
                st.json(debug_info)
            return
        try:
            path, save_warnings = save_real_profile_from_form(form)
        except FileExistsError:
            st.error("同じ保存IDのプロフィールが既に存在します。")
            return
        except ValueError as error:
            st.error(str(error))
            with st.expander("保存前データ確認（開発者向け詳細）", expanded=True):
                st.json(debug_info)
            return
        except Exception as error:
            st.error("保存用データの形式に問題があります。プロフィール文内の記号や改行を安全に保存できるよう処理します。")
            with st.expander("開発者向け詳細"):
                st.code(f"{type(error).__name__}: {error}")
            return
        st.success("プロフィールを保存しました。")
        with st.expander("保存先の詳細を表示", expanded=False):
            st.code(str(path))
        if save_warnings:
            st.warning("保存内容に注意語が含まれます: " + " / ".join(save_warnings))
        try:
            partner_result = ensure_conversation_partner_for_profile(
                form["label"],
                display_name=str(form.get("display_name", "")),
                app_name=str(form.get("app_name", "")),
                source_memo="プロフィール登録画面から自動で会話対象にしました。",
            )
        except Exception as error:
            st.warning(
                "プロフィール保存は完了しましたが、会話対象の自動登録に失敗しました。"
                "登録済み相手の管理から手動で確認してください。"
            )
            with st.expander("会話対象登録エラーの詳細", expanded=False):
                st.code(f"{type(error).__name__}: {error}")
            return
        partner = partner_result["partner"]
        st.session_state["selected_partner_id"] = partner.partner_id
        if partner_result["created"]:
            st.success(f"会話対象として登録しました: {partner.display_name or partner.partner_id}")
        else:
            st.info(
                "このプロフィールはすでに会話対象として登録されています。"
                "既存の相手画面を開けます。"
            )
        st.info(
            "次は「相手と会話する」画面で、この相手向けの初回メッセージ候補を作れます。"
            "候補はlocalに記録されるだけで、自動送信はしません。"
            "実際の送信はユーザー本人がマッチングアプリ上で手動で行います。"
        )
        if st.button("この相手と会話する", key=f"open_saved_partner_{partner.partner_id}"):
            st.session_state["selected_partner_id"] = partner.partner_id
            st.info("上の「相手と会話する」タブを開いてください。相手の選択は切り替わっています。")

    st.info("プロフィールを保存すると、自動で会話対象としてlocal登録します。保存後は「相手と会話する」画面で候補生成へ進めます。")


def _profile_paste_format_example() -> str:
    return """display_name:
サンプル

app_name:
未設定

age:
未設定

area:
未設定

profile_text:
はじめまして。
プロフィールを見ていただき、ありがとうございます。

interests:
* 自然が好き
* 食事が好き

photo_memo:
* 落ち着いた雰囲気

conversation_hooks:
* 自然の話

first_message_hints:
* 返信しやすい質問を1つ入れる

avoid_topics:
* 未設定

notes:
未設定

privacy_notes:
* 個人情報は保存しない"""


def _render_profile_paste_preview_card(preview: dict[str, object]) -> None:
    st.markdown("**貼り付け内容の抽出プレビュー**")
    with st.container(border=True):
        st.markdown("**基本情報**")
        _render_summary_rows(preview["summary"])
        st.markdown("**自己紹介**")
        st.write(preview["profile_text"])
        for section in preview["sections"]:
            _render_bullet_items(section["title"], section["items"])
        st.markdown("**メモ**")
        st.write(preview["notes"])
        if preview["missing_labels"]:
            st.warning(
                "不足している項目: "
                + " / ".join(preview["missing_labels"])
                + "。貼り付け形式が標準フォーマットと違う可能性があります。"
            )
        if preview["warnings"]:
            st.warning("保存前に見直してください: " + " / ".join(preview["warnings"]))
        _render_bullet_items("確認メモ", preview["review_notes"])
    with st.expander("詳しい抽出内容を表示（開発者向け）", expanded=False):
        st.json(preview["detail"])


def _render_summary_rows(rows: list[dict[str, object]]) -> None:
    columns = st.columns(2)
    for index, row in enumerate(rows):
        with columns[index % 2]:
            st.caption(str(row["label"]))
            st.write(str(row["value"]))


def _render_bullet_items(title: str, items: list[str]) -> None:
    st.markdown(f"**{title}**")
    for item in items:
        st.markdown(f"- {item}")


def _render_profile_display_card(profile_display: dict[str, object]) -> None:
    with st.container(border=True):
        st.markdown(f"**{profile_display['title']}**")
        _render_summary_rows(profile_display["summary"])
        st.markdown("**自己紹介**")
        st.write(profile_display["profile_text"])
        for section in profile_display["sections"]:
            _render_bullet_items(section["title"], section["items"])
        notes = str(profile_display.get("notes") or "").strip()
        if notes:
            st.markdown("**補足メモ**")
            st.write(notes)


def _render_partner_preview_card(preview_display: dict[str, object]) -> None:
    with st.container(border=True):
        st.markdown(f"**{preview_display['title']}**")
        _render_summary_rows(preview_display["summary"])
        _render_bullet_items("作成時に含まれる内容", preview_display["included"])
        _render_bullet_items("注意", preview_display["cautions"])


def _render_profile_ocr_intake() -> None:
    st.markdown("### 画像からプロフィールを読み取る")
    st.info(
        "Windowsキー + Shift + S でプロフィール画面を範囲選択したあと、"
        "「クリップボード画像を読み取る」を押してください。画像そのものは保存しません。"
    )
    _render_bullet_items("安全メモ", build_profile_ocr_privacy_notes())
    ocr_status = get_profile_ocr_environment_status()
    with st.expander("🔧 OCR環境の設定（上級者向け）", expanded=False):
        st.markdown("**OCR環境**")
        _render_summary_rows(
            [
                {"label": "OCR環境", "value": ocr_status["summary"]},
                {"label": "日本語OCR", "value": "使用可" if ocr_status["japanese"] else "未設定"},
                {"label": "英語OCR", "value": "使用可" if ocr_status["english"] else "未設定"},
                {"label": "Tesseract", "value": ocr_status["tesseract_version"]},
            ]
        )
        if ocr_status["messages"]:
            for message in ocr_status["messages"]:
                st.caption(str(message))
        _render_bullet_items("代替手段", ocr_status["alternatives"])

    col_clipboard, col_upload = st.columns(2)
    with col_clipboard:
        if st.button("クリップボード画像を読み取る"):
            image, image_errors = get_clipboard_image_for_ocr()
            if image_errors:
                st.session_state["profile_ocr_errors"] = image_errors
                st.session_state["profile_ocr_text"] = ""
            else:
                result = extract_profile_text_from_image(image)
                st.session_state["profile_ocr_errors"] = result["errors"]
                st.session_state["profile_ocr_warnings"] = result["warnings"]
                st.session_state["profile_ocr_text"] = result["text"]
    with col_upload:
        uploaded_image = st.file_uploader(
            "画像ファイルを選択",
            type=["png", "jpg", "jpeg", "webp"],
            help="クリップボードから読めない場合の代替です。画像そのものは保存しません。",
        )
        if st.button("選択画像を読み取る"):
            if uploaded_image is None:
                st.session_state["profile_ocr_errors"] = ["画像ファイルを選択してください。"]
                st.session_state["profile_ocr_text"] = ""
            else:
                image, image_errors = load_uploaded_image_for_ocr(uploaded_image.getvalue())
                if image_errors:
                    st.session_state["profile_ocr_errors"] = image_errors
                    st.session_state["profile_ocr_text"] = ""
                else:
                    result = extract_profile_text_from_image(image)
                    st.session_state["profile_ocr_errors"] = result["errors"]
                    st.session_state["profile_ocr_warnings"] = result["warnings"]
                    st.session_state["profile_ocr_text"] = result["text"]

    ocr_text = str(st.session_state.get("profile_ocr_text", "") or "")
    ocr_errors = list(st.session_state.get("profile_ocr_errors", []) or [])
    ocr_warnings = list(st.session_state.get("profile_ocr_warnings", []) or [])

    if ocr_errors:
        st.warning("画像から文字を読み取れませんでした。")
        guidance = build_profile_ocr_failure_guidance()
        with st.container(border=True):
            _render_bullet_items("考えられる理由", guidance["考えられる理由"])
            _render_bullet_items("対処", guidance["対処"])
        for error in ocr_errors:
            st.caption(error)

    if ocr_text:
        st.markdown("**読み取ったテキスト**")
        edited_text = st.text_area("OCR結果確認・修正欄", value=ocr_text, height=180, key="profile_ocr_edit_text")
        preview = build_profile_ocr_text_preview(edited_text)
        if preview["warnings"] or ocr_warnings:
            st.warning("OCR結果に注意語が含まれます。保存前に削除・修正してください: " + " / ".join(sorted(set(preview["warnings"] + ocr_warnings))))
        if st.button("このテキストをプロフィール欄へ反映"):
            st.session_state["profile_paste_text"] = edited_text
            st.success("プロフィール情報まとめ貼り付け欄へ反映しました。保存前に内容を確認してください。")


def render_partner_creation() -> None:
    st.subheader("登録済み相手の管理")
    st.info(
        "この画面では、登録済みの相手プロフィールと会話対象を確認・整理できます。"
        "通常の候補作成は「相手と会話する」画面で行います。"
        "プロフィール登録後は自動で会話対象として登録されるため、ここは管理用の補助画面です。"
    )

    st.markdown("### 登録済みの相手一覧")
    st.caption("複数人を登録したときに、誰が登録されているか、次に何をする相手かを確認できます。内部IDは通常表示では主役にしません。")
    include_archived_management = st.checkbox("非表示中の相手も一覧に含める", value=False, key="management_include_archived")
    filter_options = build_partner_management_filter_options(include_archived=include_archived_management)
    cols = st.columns(4)
    partner_query = cols[0].text_input("相手を検索", placeholder="表示名 / 趣味 / エリア")
    app_filter = cols[1].selectbox("アプリで絞り込み", options=filter_options["app_names"])
    status_filter = cols[2].selectbox("状態で絞り込み", options=filter_options["statuses"])
    sparse_only = cols[3].checkbox("情報少なめだけ")
    partner_rows = summarize_partner_management_rows(
        query=partner_query,
        app_name=app_filter,
        status=status_filter,
        sparse_only=sparse_only,
        include_archived=include_archived_management,
    )
    if partner_rows:
        st.dataframe(partner_rows, width="stretch", hide_index=True)
    else:
        st.info(
            "登録済みの会話対象がありません。"
            "まずは「プロフィール登録」から相手情報を登録してください。"
            "登録すると、自動で「相手と会話する」画面に表示されます。"
        )

    management_partners = load_partner_choices(include_archived=include_archived_management)
    _render_skipped_partner_warning()
    if management_partners:
        st.markdown("### 登録済み相手の整理")
        # 同名の相手でもプルダウンに全員表示されるよう、partner_idを含めたユニークなラベルにする
        management_labels: dict[str, str] = {}
        for partner in management_partners:
            label = f"{build_partner_choice_label(partner)} ［{partner.partner_id}］"
            management_labels[label] = partner.partner_id
        selected_management_label = st.selectbox("整理する相手を選ぶ", options=list(management_labels.keys()))
        selected_management_partner = load_partner_for_view(management_labels[selected_management_label])

        photo_saved_flag = f"photo_saved_{selected_management_partner.partner_id}"
        if st.session_state.pop(photo_saved_flag, False):
            st.success("写真を登録しました")
        current_photo = get_partner_photo_path(selected_management_partner.partner_id)
        if current_photo:
            encoded_photo = base64.b64encode(current_photo.read_bytes()).decode("ascii")
            st.markdown(
                f'<img src="data:image/jpeg;base64,{encoded_photo}" '
                f'style="width:100px;height:100px;border-radius:50%;object-fit:cover;'
                f'border:2px solid #F8A5C2;">',
                unsafe_allow_html=True,
            )
            st.caption("現在の写真")
        else:
            st.markdown(
                '<div style="width:100px;height:100px;border-radius:50%;background:#FDEFF4;'
                'border:2px solid #F8A5C2;display:flex;align-items:center;justify-content:center;'
                'font-size:48px;">😊</div>',
                unsafe_allow_html=True,
            )
        uploaded_photo = st.file_uploader(
            "📷 写真を登録・変更する",
            type=["jpg", "jpeg", "png"],
            help="ドラッグ&ドロップまたはクリックしてファイルを選択できます",
            key=f"photo_{selected_management_partner.partner_id}",
        )
        if st.button("登録する", type="primary", key=f"photo_save_{selected_management_partner.partner_id}"):
            if uploaded_photo is None:
                st.warning("写真を選択してください")
            else:
                try:
                    save_partner_photo_from_gui(selected_management_partner.partner_id, uploaded_photo.getvalue())
                except ValueError:
                    st.error("写真の登録に失敗しました")
                else:
                    st.session_state[photo_saved_flag] = True
                    st.rerun()
        if current_photo:
            delete_cols = st.columns([1, 4])
            if delete_cols[0].button("削除する", key=f"photo_delete_{selected_management_partner.partner_id}"):
                delete_partner_photo_from_gui(selected_management_partner.partner_id)
                st.rerun()

        if st.button("この相手と会話する", key=f"manage_open_{selected_management_partner.partner_id}"):
            st.session_state["selected_partner_id"] = selected_management_partner.partner_id
            st.info("上の「相手と会話する」タブを開いてください。相手の選択は切り替わっています。")

        with st.expander("プロフィール詳細", expanded=False):
            _render_profile_display_card(build_partner_profile_card(selected_management_partner))

        with st.expander("表示名・アプリ名・管理メモを修正", expanded=True):
            st.caption("表示名やメモだけを更新します。内部保存IDや会話履歴、送信済み記録は変更しません。")
            new_display_name = st.text_input(
                "表示名",
                value=selected_management_partner.display_name or "表示名未設定",
                key=f"manage_display_{selected_management_partner.partner_id}",
            )
            new_app_name = st.text_input(
                "アプリ名",
                value=selected_management_partner.app_name or "",
                key=f"manage_app_{selected_management_partner.partner_id}",
            )
            management_note = st.text_area(
                "追加メモ",
                height=80,
                placeholder="例: 情報少なめ。あとで写真メモを補完する。",
                key=f"manage_note_{selected_management_partner.partner_id}",
            )
            confirm_update = st.checkbox("更新内容を確認しました", key=f"manage_update_confirm_{selected_management_partner.partner_id}")
            if st.button("表示名・メモを更新", key=f"manage_update_{selected_management_partner.partner_id}"):
                try:
                    result = update_partner_management_info_from_gui(
                        selected_management_partner.partner_id,
                        new_display_name,
                        new_app_name,
                        note=management_note,
                        confirmed=confirm_update,
                    )
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.success(result["message"])
                    st.rerun()

        memo_tag_saved_flag = f"memo_tag_saved_{selected_management_partner.partner_id}"
        if st.session_state.pop(memo_tag_saved_flag, False):
            st.success("識別メモを保存しました")
        with st.expander("識別メモ（同名の相手を区別するメモ）", expanded=False):
            st.caption("同じ名前の相手が複数いるとき、プルダウンで見分けるための短いメモです。")
            new_memo_tag = st.text_input(
                "識別メモ（同名の相手を区別するメモ）",
                value=load_memo_tag(selected_management_partner.partner_id),
                placeholder="例: 旅行好き・東京、看護師・背高い など",
                key=f"memo_tag_input_{selected_management_partner.partner_id}",
            )
            if st.button("メモを保存する", key=f"memo_tag_save_{selected_management_partner.partner_id}"):
                save_memo_tag_from_gui(selected_management_partner.partner_id, new_memo_tag)
                st.session_state[memo_tag_saved_flag] = True
                st.rerun()

        with st.expander("⚠️ この相手を完全に削除する", expanded=False):
            st.warning(
                "削除すると、プロフィール・会話履歴・写真がすべて消えます。この操作は取り消せません。"
            )
            confirm_delete = st.checkbox(
                "削除することを理解しました",
                key=f"manage_delete_confirm_{selected_management_partner.partner_id}",
            )
            if st.button(
                "完全に削除する",
                type="primary",
                disabled=not confirm_delete,
                key=f"manage_delete_{selected_management_partner.partner_id}",
            ):
                try:
                    delete_partner_completely_from_gui(
                        selected_management_partner.partner_id,
                        confirmed=confirm_delete,
                    )
                except ValueError as error:
                    st.error(str(error))
                else:
                    if st.session_state.get("selected_partner_id") == selected_management_partner.partner_id:
                        st.session_state["selected_partner_id"] = ""
                    st.success("削除しました")
                    st.rerun()

        with st.expander("この相手を非表示・再表示", expanded=False):
            st.caption("完全削除ではありません。会話履歴や送信済み記録は残し、通常一覧から非表示にします。")
            if selected_management_partner.status == "archived":
                confirm_unarchive = st.checkbox("この相手を再表示することを確認しました", key=f"manage_unarchive_confirm_{selected_management_partner.partner_id}")
                if st.button("この相手を再表示する", key=f"manage_unarchive_{selected_management_partner.partner_id}"):
                    try:
                        result = unarchive_partner_from_gui(selected_management_partner.partner_id, confirmed=confirm_unarchive)
                    except ValueError as error:
                        st.error(str(error))
                    else:
                        st.success(result["message"])
                        st.rerun()
            else:
                archive_reason = st.text_input("非表示にする理由", placeholder="例: 会話が終わったため", key=f"manage_archive_reason_{selected_management_partner.partner_id}")
                confirm_archive = st.checkbox("この相手を非表示にしても、会話履歴は削除されないことを確認しました", key=f"manage_archive_confirm_{selected_management_partner.partner_id}")
                if st.button("この相手を非表示にする", key=f"manage_archive_{selected_management_partner.partner_id}"):
                    try:
                        result = archive_partner_from_gui(selected_management_partner.partner_id, reason=archive_reason, confirmed=confirm_archive)
                    except ValueError as error:
                        st.error(str(error))
                    else:
                        st.success(result["message"])
                        st.rerun()

    st.markdown("### 保存済みプロフィール")
    # 選択中の相手があれば、表示名をその場で素早く編集できるショートカット
    if management_partners:
        current_display = selected_management_partner.display_name or ""
        st.markdown("**📝 表示名を編集**")
        col_name, col_btn = st.columns([3, 1])
        with col_name:
            new_name_quick = st.text_input(
                "表示名",
                value=current_display,
                placeholder="会話で教えてもらった名前など",
                key="quick_display_name_edit",
            )
        with col_btn:
            st.write("")  # ラベル分の余白
            if st.button("保存", key="quick_display_name_save"):
                if new_name_quick.strip() and new_name_quick != current_display:
                    try:
                        update_partner_management_info_from_gui(
                            selected_management_partner.partner_id,
                            new_name_quick,
                            selected_management_partner.app_name or "",
                            note="",
                            confirmed=True,
                        )
                    except ValueError as error:
                        st.error(str(error))
                    else:
                        st.success("表示名を更新しました")
                        st.rerun()
                else:
                    st.info("表示名が変更されていません")
        st.divider()

    search_query = st.text_input("保存済みプロフィール検索", placeholder="表示名 / 趣味 / 年齢などで絞り込み")
    profiles = filter_real_profiles_for_gui(search_query)
    if not profiles:
        st.info(
            "まだ登録済みプロフィールはありません。"
            "まずは「プロフィール登録」から相手情報を登録してください。"
            "登録すると、自動で「相手と会話する」画面に表示されます。"
        )
        return

    profile_options = {profile["display_label"]: profile["label"] for profile in profiles}
    selected_profile = st.selectbox("保存済みプロフィール選択", options=list(profile_options.keys()))
    label = profile_options[selected_profile]
    _render_profile_display_card(build_profile_display_sections(label))
    with st.expander("詳しいプロフィール情報を表示（開発者向け）", expanded=False):
        st.json(build_real_profile_summary_for_gui(label))

    existing_partners = summarize_existing_partner_candidates(label)
    if existing_partners:
        st.warning(
            "このプロフィールから作成済みと思われる会話対象があります。"
            "重複作成しないよう、既存の相手を開くか、新しく作成するか確認してください。"
        )
        st.dataframe(existing_partners, width="stretch", hide_index=True)

    st.markdown("**会話対象の手動登録**")
    st.caption("通常は使わなくて大丈夫です。既存データの確認や補助管理が必要な場合だけ使います。")
    display_name = st.text_input("会話対象の表示名", help="空欄の場合は保存済みプロフィールの表示名を使います。")
    app_name = st.text_input("アプリ名", help="Pairs、withなど。未設定でも保存できます。")
    source_memo = st.text_area("作成時メモ", height=80, help="相手別メモとしてlocal保存したい補足だけを書きます。個人情報は入れないでください。")

    preview = build_partner_creation_preview(label, display_name=display_name, app_name=app_name, source_memo=source_memo)
    _render_partner_preview_card(format_partner_preview_for_display(label, display_name=display_name, app_name=app_name, source_memo=source_memo))
    with st.expander("保存前の詳しい内容を表示（開発者向け）", expanded=False):
        st.json(preview)

    confirm_create = st.checkbox("保存内容を確認し、会話対象としてlocal保存する")
    submitted = st.button("会話対象として登録")
    if submitted:
        if not confirm_create:
            st.error("保存前確認チェックを入れてください。")
            return
        result = ensure_conversation_partner_for_profile(
            label,
            display_name=display_name,
            app_name=app_name,
            source_memo=source_memo,
        )
        partner = result["partner"]
        st.session_state["selected_partner_id"] = partner.partner_id
        if result["created"]:
            st.success(f"会話対象として登録しました: {partner.display_name or partner.partner_id}")
        else:
            st.info("このプロフィールはすでに会話対象として登録されています。既存の相手を選択しました。")
        st.info("次は「相手と会話する」画面で、会話履歴、相手別メモ、生成前チェック、3候補生成へ進めます。")


def render_conversation_import() -> None:
    st.subheader("会話履歴追加")
    st.caption(
        "相手から返信が来たときや、過去のやり取りを残したいときに使います。"
        "自動送信ではなく、localの会話履歴に追加するだけです。"
    )

    partners = load_partner_choices(include_archived=False)
    _render_skipped_partner_warning()
    if not partners:
        st.info("会話履歴を追加する相手がまだありません。まずは「プロフィール登録」から相手情報を登録してください。")
        return

    labels = {build_partner_choice_label(partner): partner.partner_id for partner in partners}
    selected_label = st.selectbox("会話を追加する相手", options=list(labels.keys()), key="conv_import_partner")
    partner = load_partner_for_view(labels[selected_label])

    st.write("マッチングアプリで会話した内容を1件ずつ登録してください。")

    speaker_label = st.selectbox("発言者", options=["自分", "相手"], key="conv_import_speaker")
    message_text = st.text_area(
        "メッセージ内容",
        placeholder="ここにメッセージを貼り付けてください",
        height=100,
        key="conv_import_text",
    )

    if st.button("この1件を追加する", type="primary", key="conv_import_add"):
        if not message_text.strip():
            st.error("メッセージを入力してください")
            return
        speaker = "user" if speaker_label == "自分" else "partner"
        new_turn = {"speaker": speaker, "text": message_text.strip()}
        reload_partner = load_partner_for_view(partner.partner_id)
        if detect_duplicate_turn_sequence(reload_partner, [new_turn]):
            st.warning("同じ内容がすでに登録されています")
            return
        append_conversation_turns_to_partner(partner.partner_id, [new_turn])
        st.success("追加しました")
        st.rerun()


def _render_skipped_partner_warning() -> None:
    skipped = get_skipped_partner_files()
    if skipped:
        st.warning("一部のデータが読み込めませんでした。該当ファイル: " + ", ".join(skipped))


def _load_user_profile_data() -> dict:
    if not _USER_PROFILE_PATH.exists():
        return {}
    try:
        return json.loads(_USER_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_user_profile_data(data: dict) -> None:
    _USER_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _USER_PROFILE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _create_local_backup_zip() -> bytes:
    buf = io.BytesIO()
    local_dir = APP_DIR / "data" / "local"
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(local_dir.rglob("*")):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(APP_DIR))
    buf.seek(0)
    return buf.read()


def _has_existing_local_data() -> bool:
    local_dir = APP_DIR / "data" / "local"
    return any(local_dir.rglob("*.yaml"))


def _extract_backup_zip(zip_bytes: bytes) -> tuple[bool, str]:
    buf = io.BytesIO(zip_bytes)
    try:
        with zipfile.ZipFile(buf, "r") as zf:
            valid = [n for n in zf.namelist() if n.startswith("data/local/") and not n.endswith("/")]
            if not valid:
                return False, "このzipファイルにはdating_assistantのデータが含まれていません。"
            for name in valid:
                target = APP_DIR / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))
    except zipfile.BadZipFile:
        return False, "zipファイルが壊れているか、形式が正しくありません。"
    except Exception as e:
        return False, f"展開中にエラーが発生しました: {e}"
    return True, f"{len(valid)}件のファイルを復元しました。"


def render_help() -> None:
    st.subheader("設定・ヘルプ")
    st.caption("このツールの使い方、安全な利用方法、local保存の考え方を確認できます。")

    st.markdown("### あなたのプロフィール設定")
    st.write("あなたの名前を設定すると、返信候補にあなたの名前が反映されます。")
    user_profile = _load_user_profile_data()
    saved_name = str(user_profile.get("name", "") or "")
    saved_age = user_profile.get("age") or None
    saved_intro = str(user_profile.get("self_intro", "") or "")
    with st.container(border=True):
        current_name = st.text_input(
            "あなたの名前（ニックネームでOK）",
            value=saved_name,
            placeholder="例: 太郎、たろう など",
            key="user_profile_name",
        )
        current_age = st.number_input(
            "年齢（任意）",
            min_value=18,
            max_value=120,
            value=int(saved_age) if saved_age is not None else None,
            step=1,
            key="user_profile_age",
        )
        current_intro = st.text_area(
            "自己紹介（任意）",
            value=saved_intro,
            placeholder="趣味や仕事など、簡単に",
            height=80,
            key="user_profile_intro",
        )
        if st.button("プロフィールを保存する", key="user_profile_save"):
            _save_user_profile_data({
                "name": current_name.strip(),
                "age": int(current_age) if current_age else None,
                "self_intro": current_intro.strip(),
            })
            st.success("プロフィールを保存しました")
            st.rerun()
        if saved_name:
            age_str = f"（{int(saved_age)}歳）" if saved_age is not None else ""
            st.info(f"現在の設定: {saved_name}さん{age_str}")
        else:
            st.warning("名前が設定されていません。設定すると返信候補に名前が反映されます。")

    st.divider()
    st.info(
        "まずは「プロフィール登録」で相手情報を保存し、普段は「相手と会話する」で候補作成と記録を行います。"
        "実際の送信は必ずユーザー本人がマッチングアプリ上で手動で行います。"
    )
    st.markdown("### このツールでできること")
    _render_bullet_items(
        "できること",
        [
            "相手プロフィールを文字情報として登録する",
            "登録済みの相手を選んで、次に送る候補A/B/Cを作る",
            "実際に送った文だけを送信済みとしてlocal記録する",
            "相手から返信が来たら会話履歴へ追加する",
            "会話が終わった相手を非表示にして整理する",
        ],
    )
    st.markdown("### このツールでできないこと")
    _render_bullet_items(
        "できないこと",
        [
            "マッチングアプリへの自動送信",
            "マッチングアプリへの直接接続や自動操作",
            "外部API通信や実LLM API呼び出し",
            "プロフィール画像、顔写真、スクリーンショット画像そのものの保存",
            "課金、ユーザー認証、販売ページ作成",
        ],
    )
    st.markdown("### 基本の使い方")
    _render_bullet_items(
        "手順",
        [
            "初めて使うときは「プロフィール登録」から始める",
            "ChatGPTで整理したプロフィール文や、アプリ上で読める文字情報を貼り付ける",
            "保存すると自動で会話対象になる",
            "普段は「相手と会話する」で相手を選び、候補を作る",
            "実際の送信はマッチングアプリ上で手動で行う",
            "送った後だけ、このGUIで送信済みlocal記録を行う",
        ],
    )
    st.markdown("### 安全な使い方")
    _render_bullet_items(
        "注意事項",
        [
            "本名、勤務先、学校名、LINE ID、SNS ID、住所、電話番号、メールアドレスは保存しない",
            "情報が少ないプロフィールでも保存でき、あとからメモで補完できる",
            "候補文は必ず人間が確認し、相手との温度感に合わない場合は送らない",
            "電話、会う提案、LINE交換、大人っぽい雰囲気は慎重に扱う",
            "データはlocal保存です。実データをGitに入れないでください",
            "データファイル（data/local/内）は直接編集しないでください。編集が必要な場合はアプリ内の機能を使ってください",
        ],
    )
    st.markdown("### よくある困りごと")
    with st.expander("Q. 起動できないときはどうすればよいですか？"):
        st.markdown(
            "- `start_dating_assistant_gui.bat` をダブルクリックして起動し直してください。\n"
            "- 起動後はブラウザで `http://localhost:8501` を開きます。\n"
            "- 古い画面が残っている場合は、ブラウザを再読み込みしてください。"
        )
    with st.expander("Q. このツールからマッチングアプリへ自動送信されますか？"):
        st.markdown(
            "いいえ。候補文を作るだけです。実際の送信は、ユーザー本人がマッチングアプリ上で手動で行います。"
        )
    with st.expander("Q. 入力したプロフィールや会話履歴はどこに保存されますか？"):
        st.markdown(
            "入力したプロフィール、会話履歴、送信済み記録、メモは、基本的にお使いのPC内にlocal保存されます。"
            "外部サービスへ自動送信したり、マッチングアプリへ直接送ったりしません。"
        )
    with st.expander("Q. どのファイルを触ればよいですか？"):
        st.markdown(
            "`start_dating_assistant_gui.bat` を起動し、ブラウザでGUIを操作してください。"
            "通常利用では、Pythonファイル、YAMLファイル、data/local、outputs/local、Git関連ファイルを開いたり編集したりする必要はありません。"
        )
    with st.expander("Q. 画像やスクリーンショットは保存されますか？"):
        st.markdown(
            "保存しません。画像から読み取った文字や、ユーザーが確認して入力したメモだけを保存対象にします。"
        )
    with st.expander("Q. プロフィール情報が少ない場合でも使えますか？"):
        st.markdown(
            "使えます。表示名や自己紹介が少なくてもプロフィールとして保存できます。"
            "不足している内容は警告として表示され、あとから補完できます。"
        )

    st.divider()
    st.markdown("### データのバックアップ・復元")

    with st.container(border=True):
        st.markdown("**データをエクスポートする**")
        st.write(
            "すべての相手データ・会話履歴をzipファイルにまとめてダウンロードできます。"
            "PC買い替えや移行時にご利用ください。"
        )
        zip_filename = f"dating_assistant_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_bytes = _create_local_backup_zip()
        st.download_button(
            label="データをバックアップする",
            data=zip_bytes,
            file_name=zip_filename,
            mime="application/zip",
        )

    st.write("")

    with st.container(border=True):
        st.markdown("**バックアップからデータを復元する**")
        st.write("バックアップしたzipファイルを選択してください。既存のデータは上書きされます。")
        uploaded = st.file_uploader(
            "バックアップzipファイル",
            type=["zip"],
            key="backup_restore_uploader",
        )
        if uploaded is not None:
            if _has_existing_local_data():
                st.warning("既存のデータが上書きされます。続ける場合は「復元を実行」を押してください。")
            if st.button("復元を実行", key="backup_restore_execute"):
                ok, msg = _extract_backup_zip(uploaded.read())
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    st.divider()
    st.markdown("### APIキー設定状態")
    with st.container(border=True):
        if is_api_key_configured():
            st.success("APIキーが設定されています。")
        else:
            st.warning(
                "APIキーが設定されていません。"
                "返信生成を使うには .env ファイルに ANTHROPIC_API_KEY を設定してください。"
            )

    st.divider()
    st.markdown("### バージョン情報")
    with st.container(border=True):
        st.write("**バージョン:** v1.0.0-beta")
        st.write("**リリース日:** 2026-06-11")
        st.write("**問い合わせ先:** -")
    st.caption("このツールはlocalで動作します。返信生成にはClaude APIを使用します。")


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
