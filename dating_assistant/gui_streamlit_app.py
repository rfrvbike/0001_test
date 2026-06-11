from __future__ import annotations

import io
import sys
import zipfile
from datetime import datetime
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import streamlit as st

from src.claude_generator import generate_reply_candidates_for_gui, is_api_key_configured

from gui_helpers import (
    append_conversation_turns_to_partner,
    build_partner_summary,
    build_conversation_import_preview,
    build_conversation_import_failure_guidance,
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
    detect_conversation_safety_warnings,
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
    parse_conversation_paste,
    load_uploaded_image_for_ocr,
    real_profile_exists,
    save_real_profile_from_form,
    summarize_existing_partner_candidates,
    summarize_partner_management_rows,
    unarchive_partner_from_gui,
    update_partner_management_info_from_gui,
    validate_imported_turns,
)


def main() -> None:
    st.set_page_config(page_title="dating_assistant", layout="wide")
    st.title("dating_assistant")
    st.caption("ローカルGUI")
    st.info(
        "このツールは、マッチングアプリ上で送るメッセージ候補を作るための補助画面です。"
        "まず「プロフィール登録」で相手情報を登録し、保存後に「相手と会話する」で候補を作ります。"
        "自動送信は行いません。実際の送信はマッチングアプリ上でユーザー本人が手動で行います。"
    )

    tab_viewer, tab_profile, tab_partner_create, tab_import, tab_help = st.tabs(
        ["相手と会話する", "プロフィール登録", "登録済み相手の管理", "会話履歴追加", "設定・ヘルプ"]
    )

    with tab_viewer:
        render_partner_viewer()

    with tab_profile:
        render_profile_registration()

    with tab_partner_create:
        render_partner_creation()

    with tab_import:
        render_conversation_import()

    with tab_help:
        render_help()


def render_partner_viewer() -> None:
    st.subheader("相手と会話する")
    st.caption("相手を選び、プロフィールと会話履歴を見ながら、次に送る文を作る画面です。実際の送信はマッチングアプリ上で手動で行います。")

    include_archived = st.checkbox("アーカイブ済みの相手も表示", value=False)
    partners = load_partner_choices(include_archived=include_archived)
    _render_skipped_partner_warning()
    if not partners:
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
    selected_partner_id = str(st.session_state.get("selected_partner_id", "") or "")
    label_values = list(labels.values())
    selected_index = label_values.index(selected_partner_id) if selected_partner_id in label_values else 0
    selected_label = st.selectbox("相手を選ぶ", options=list(labels.keys()), index=selected_index)
    partner = load_partner_for_view(labels[selected_label])
    st.session_state["selected_partner_id"] = partner.partner_id
    workspace = build_partner_workspace_overview(partner)

    st.markdown(f"### {workspace['title']}")
    st.caption(workspace["subtitle"])
    cols = st.columns(4)
    cols[0].metric("今やること", workspace["next_action"])
    cols[1].metric("会話ステージ", workspace["conversation_stage"])
    cols[2].metric("温度感", workspace["temperature"])
    cols[3].metric("未確認候補", workspace["pending_count"])

    left, right = st.columns([1, 1.25])
    with left:
        st.markdown("### 相手のプロフィール")
        _render_profile_display_card(build_partner_profile_card(partner))

    with right:
        st.markdown("### 会話履歴")
        render_conversation_history_section(partner)
        render_inline_conversation_import(partner)

    st.divider()
    render_generation_controls(partner)


def render_conversation_history_section(partner) -> None:
    rows = format_conversation_history(partner)
    if not rows:
        st.info("まだ会話履歴はありません。会話履歴が少なくても候補は作れます。")
        return
    chat_parts = []
    for row in rows[-20:]:
        is_user = row["speaker"] == "user"
        align = "flex-end" if is_user else "flex-start"
        bg = "#DCF8C6" if is_user else "#FFFFFF"
        name = "自分" if is_user else "相手"
        text = row["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        chat_parts.append(
            f'<div style="display:flex;justify-content:{align};margin-bottom:8px;">'
            f'<div style="max-width:75%;background:{bg};border-radius:12px;padding:8px 12px;box-shadow:0 1px 2px rgba(0,0,0,0.15);">'
            f'<div style="font-size:11px;color:#888;margin-bottom:2px;">{name}</div>'
            f'<div style="font-size:14px;line-height:1.5;">{text}</div>'
            f"</div></div>"
        )
    st.markdown(
        '<div style="height:400px;overflow-y:auto;border:1px solid #e0e0e0;border-radius:8px;padding:12px;background:#ECE5DD;">'
        + "".join(chat_parts)
        + "</div>",
        unsafe_allow_html=True,
    )


def render_inline_conversation_import(partner) -> None:
    with st.expander("相手から返信が来たら会話履歴に追加", expanded=False):
        st.caption("「自分:」「相手:」形式で貼り付けると、この相手のlocal会話履歴に追加できます。自動送信ではありません。")
        pasted = st.text_area(
            "会話履歴を貼り付け",
            height=160,
            placeholder="自分: はじめまして。\n相手: よろしくお願いします。",
            key=f"inline_conversation_paste_{partner.partner_id}",
        )
        if pasted.strip():
            turns, parse_warnings = parse_conversation_paste(pasted)
            duplicate_warning = detect_duplicate_turn_sequence(partner, turns)
            errors = validate_imported_turns(turns, parse_warnings)
            warnings = list(parse_warnings)
            warnings.extend(detect_conversation_safety_warnings(pasted))
            preview = build_conversation_import_preview(partner, turns, warnings)
            if parse_warnings:
                guidance = build_conversation_import_failure_guidance()
                st.warning("読み取れない行があります。自分: / 相手: の形に直すと追加しやすくなります。")
                with st.expander("直し方のヒント（詳細）", expanded=False):
                    st.json(guidance)
            if errors:
                for error in errors:
                    st.error(error)
            if duplicate_warning:
                st.warning("同じ会話履歴がすでに登録されています。")
            if warnings:
                st.warning("保存前に確認してください: " + " / ".join(warnings))
            with st.expander("追加前プレビュー（開発者向け詳細）", expanded=False):
                st.json(preview)
            confirm = st.checkbox(
                "この会話履歴をlocalに追加する",
                key=f"inline_conversation_confirm_{partner.partner_id}",
            )
            if st.button(
                "会話履歴を追加",
                disabled=bool(errors) or duplicate_warning or not confirm,
                key=f"inline_conversation_button_{partner.partner_id}",
            ):
                try:
                    result = append_conversation_turns_to_partner(partner.partner_id, turns)
                except ValueError as error:
                    st.error(str(error))
                    return
                st.success(f"{len(turns)}件の会話履歴をlocalに追加しました。")
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
    if st.button("返信候補を生成する", key=f"generate_button_{partner.partner_id}"):
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
        st.success("返信候補を3つ作りました。気に入った文をコピーして、マッチングアプリで手動送信してください。")
        for variant in generated["variants"]:
            with st.container(border=True):
                st.markdown(f"**{variant['title']}**")
                st.text_area(
                    "候補本文",
                    variant["text"],
                    height=150,
                    key=f"generated_{partner.partner_id}_{variant['suggestion_id']}",
                )


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
    with st.container(border=True):
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
        management_labels = {build_partner_choice_label(partner): partner.partner_id for partner in management_partners}
        selected_management_label = st.selectbox("整理する相手を選ぶ", options=list(management_labels.keys()))
        selected_management_partner = load_partner_for_view(management_labels[selected_management_label])
        _render_profile_display_card(build_partner_profile_card(selected_management_partner))

        if st.button("この相手と会話する", key=f"manage_open_{selected_management_partner.partner_id}"):
            st.session_state["selected_partner_id"] = selected_management_partner.partner_id
            st.info("上の「相手と会話する」タブを開いてください。相手の選択は切り替わっています。")

        with st.expander("表示名・アプリ名・管理メモを修正", expanded=False):
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
