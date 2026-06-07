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
    build_generation_preflight,
    build_mark_sent_preview,
    build_partner_note_preview,
    build_profile_form_from_paste,
    build_profile_paste_preview,
    build_profile_save_preview,
    build_real_profile_summary_for_gui,
    build_sent_outcome_preview,
    filter_real_profiles_for_gui,
    can_discard_suggestion,
    can_generate_suggestion,
    can_mark_suggestion_sent,
    detect_conversation_safety_warnings,
    detect_duplicate_turn_sequence,
    detect_profile_safety_warnings,
    format_conversation_history,
    format_partner_notes,
    format_pending_suggestions,
    format_sent_suggestions_for_outcomes,
    format_timeline_items,
    generate_suggestion_for_gui,
    generate_suggestion_variants_for_gui,
    find_existing_partners_for_profile,
    GENERATION_OBJECTIVE_OPTIONS,
    GENERATION_TONE_OPTIONS,
    get_generation_mode_for_partner,
    discard_suggestion_from_gui,
    load_partner_choices,
    load_partner_for_view,
    list_real_profiles_for_gui,
    merge_profile_form_with_paste,
    parse_conversation_paste,
    real_profile_exists,
    save_real_profile_from_form,
    save_partner_from_profile,
    SENT_OUTCOME_STATUS_OPTIONS,
    add_partner_note_from_gui,
    mark_custom_text_sent_from_gui,
    mark_suggestion_sent_from_gui,
    update_sent_outcome_from_gui,
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

    render_partner_notes(partner)
    render_generation_controls(partner)

    tab_history, tab_suggestions, tab_sent_outcomes, tab_timeline = st.tabs(["会話履歴", "未送信候補", "送信結果メモ", "timeline"])

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

    with tab_sent_outcomes:
        render_sent_outcome_controls(partner)

    with tab_timeline:
        timeline = format_timeline_items(partner)
        if not timeline:
            st.info("timeline は空です。")
        else:
            st.dataframe(timeline, width="stretch", hide_index=True)


def render_partner_notes(partner) -> None:
    st.subheader("相手別メモ")
    notes = format_partner_notes(partner)
    if not notes:
        st.info("まだメモはありません。返信傾向、反応がよい話題、避けたい誘い方などをlocalに残せます。")
    else:
        for note in notes:
            title = f"{note['index']}. {note['created_at'] or '時刻なし'}"
            with st.expander(title, expanded=False):
                st.write(note["text"])

    new_note = st.text_area(
        "相手別メモを追加",
        height=100,
        placeholder="例: 返信は夜が多い。旅行の話題に反応がよい。電話はまだ早そう。",
        key=f"partner_note_text_{partner.partner_id}",
    )
    if new_note.strip():
        with st.expander("相手別メモ保存プレビュー", expanded=False):
            preview = build_partner_note_preview(new_note)
            for warning in preview["warnings"]:
                st.warning(warning)
            st.json(preview)
    confirm = st.checkbox(
        "個人情報を含めず、相手別メモをlocal保存する",
        key=f"partner_note_confirm_{partner.partner_id}",
    )
    if st.button(
        "相手別メモを更新",
        disabled=not (new_note.strip() and confirm),
        key=f"partner_note_button_{partner.partner_id}",
    ):
        try:
            result = add_partner_note_from_gui(partner.partner_id, new_note, confirmed=confirm)
        except ValueError as error:
            st.error(str(error))
            return
        for warning in result["warnings"]:
            st.warning(warning)
        st.success("相手別メモをlocal保存しました。")
        st.rerun()


def render_generation_controls(partner) -> None:
    st.subheader("候補生成")
    mode = get_generation_mode_for_partner(partner)
    mode_label = {"first": "初回メッセージ候補", "reply": "返信候補", "blocked": "生成不可"}[mode]
    button_label = f"{mode_label}を3つ生成する" if mode in {"first", "reply"} else "候補生成不可"
    st.write(f"**現在:** {build_generation_status_message(partner)}")
    st.write(f"**生成タイプ:** {mode_label}")
    objectives = st.multiselect(
        "今回の目的（上の方ほど日常会話向け）",
        options=GENERATION_OBJECTIVE_OPTIONS,
        default=["相手のプロフィールに触れる", "質問を1つ入れる"],
        help="電話、会う提案、LINE交換、大人っぽい雰囲気は下の方に置いています。会話の温度感が十分ある場合だけ選んでください。",
        key=f"generation_objectives_{partner.partner_id}",
    )
    st.caption("電話・会う提案・LINE交換・大人っぽい雰囲気は、相手の反応が良い場合だけ使います。")
    tone = st.selectbox(
        "文章の雰囲気",
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
    preflight = build_generation_preflight(partner, objectives, tone, place_hint)
    with st.expander("生成前チェック", expanded=True):
        st.markdown(f"**会話ステージ:** {preflight['conversation_stage']}")
        st.markdown(f"**温度感:** {preflight['temperature']['label']}")
        for reason in preflight["temperature"]["reasons"]:
            st.markdown(f"- {reason}")
        st.markdown(f"**次の一手おすすめ:** {preflight['next_recommendation']}")
        st.markdown("**注意すべき点**")
        for caution in preflight["caution_points"]:
            st.markdown(f"- {caution}")
        st.markdown("**誘い系アクションの可否**")
        action_rows = [
            {"action": action, "status": judgement["status"], "reason": judgement["reason"]}
            for action, judgement in preflight["action_judgements"].items()
            if action in {"電話に誘う", "会う提案をする", "場所を指定して会う提案をする", "LINE交換を提案する", "少し大人っぽい雰囲気にする", "恋愛観に軽く触れる"}
        ]
        st.dataframe(action_rows, width="stretch", hide_index=True)
        for warning in preflight["warnings"]:
            st.warning(warning)
        with st.expander("詳細データ", expanded=False):
            st.json(preflight)
    st.caption("候補生成はlocalのpending_suggestionsへ保存するだけです。自動送信ではありません。")
    confirm = st.checkbox("自動送信ではないことを確認し、候補をlocal保存する", key=f"generate_confirm_{partner.partner_id}")
    if st.button(button_label, disabled=not (can_generate_suggestion(partner) and confirm), key=f"generate_button_{partner.partner_id}"):
        try:
            generated = generate_suggestion_variants_for_gui(
                partner.partner_id,
                objectives=objectives,
                tone=tone,
                place_hint=place_hint,
            )
        except ValueError as error:
            st.error(str(error))
            return
        st.success("3候補をpending_suggestionsへ保存しました。")
        for variant in generated["variants"]:
            with st.expander(f"{variant['title']} / {variant['suggestion_id']}", expanded=True):
                st.write(f"**使いどころ:** {variant['use_case']}")
                st.write(f"**狙い:** {variant['aim']}")
                st.write(f"**会話ステージとの相性:** {variant['compatibility']}")
                st.text_area(
                    "候補本文",
                    variant["text"],
                    height=120,
                    disabled=True,
                    key=f"generated_{variant['suggestion_id']}",
                )
                st.write("**品質チェック:**")
                for check in variant["quality_check"]:
                    st.write(f"- {check}")
                st.write("注意: " + " / ".join(variant["safety_notes"]))
        st.info("実際に手動送信した後、pending_suggestions欄から送信済みとしてlocal記録できます。")


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
            st.info("元候補はpendingに残っています。下の候補破棄から未使用候補として整理できます。")
        st.rerun()


def render_sent_outcome_controls(partner) -> None:
    st.subheader("送信結果メモ")
    sent_suggestions = format_sent_suggestions_for_outcomes(partner)
    if not sent_suggestions:
        st.info("送信済みlocal記録はまだありません。実際に手動送信した文だけ、結果メモを残せます。")
        return

    for suggestion in sent_suggestions:
        title = f"{suggestion['sent_id']} / {suggestion['source_label']} / {suggestion['outcome_status']} / {suggestion['sent_at'] or 'sent_atなし'}"
        with st.expander(title, expanded=True):
            st.markdown(f"**sent_id:** {suggestion['sent_id']}")
            st.markdown(f"**種別:** {suggestion['source_label']}")
            if suggestion["source_suggestion_id"]:
                st.markdown(f"**source_suggestion_id:** {suggestion['source_suggestion_id']}")
            st.markdown(f"**sent_at:** {suggestion['sent_at'] or '-'}")
            st.markdown(f"**outcome_updated_at:** {suggestion['outcome_updated_at'] or '-'}")
            st.text_area(
                "送信文",
                suggestion["text"],
                height=100,
                disabled=True,
                key=f"sent_text_{partner.partner_id}_{suggestion['sent_id']}",
            )
            current_index = SENT_OUTCOME_STATUS_OPTIONS.index(suggestion["outcome_status"]) if suggestion["outcome_status"] in SENT_OUTCOME_STATUS_OPTIONS else 0
            outcome_status = st.selectbox(
                "結果ステータス",
                options=SENT_OUTCOME_STATUS_OPTIONS,
                index=current_index,
                key=f"outcome_status_{partner.partner_id}_{suggestion['sent_id']}",
            )
            outcome_memo = st.text_area(
                "送信結果メモ",
                value=suggestion["outcome_memo"],
                height=90,
                placeholder="例: 旅行の話題は反応よかった。次も広げてよさそう。",
                key=f"outcome_memo_{partner.partner_id}_{suggestion['sent_id']}",
            )
            if outcome_memo.strip():
                with st.expander("送信結果メモ保存プレビュー", expanded=False):
                    preview = build_sent_outcome_preview(partner, suggestion["sent_id"], outcome_status, outcome_memo)
                    for warning in preview["warnings"]:
                        st.warning(warning)
                    st.json(preview)
            confirm = st.checkbox(
                "個人情報を含めず、送信結果メモをlocal保存する",
                key=f"outcome_confirm_{partner.partner_id}_{suggestion['sent_id']}",
            )
            if st.button(
                "送信結果メモを更新",
                disabled=not confirm,
                key=f"outcome_button_{partner.partner_id}_{suggestion['sent_id']}",
            ):
                try:
                    result = update_sent_outcome_from_gui(
                        partner.partner_id,
                        suggestion["sent_id"],
                        outcome_status,
                        outcome_memo,
                        confirmed=confirm,
                    )
                except ValueError as error:
                    st.error(str(error))
                    return
                for warning in result["warnings"]:
                    st.warning(warning)
                st.success("送信結果メモをlocal保存しました。")
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
        st.info("まずここにプロフィール文、趣味、写真の印象メモをまとめて貼り付けます。下の入力欄は不足分や修正だけに使います。")
        profile_paste = st.text_area(
            "プロフィール情報まとめ貼り付け欄",
            height=280,
            help="マッチングアプリ上のプロフィール文、自己紹介、趣味、エリア、年齢、写真の印象メモなどをまとめて貼り付けます。画像そのものは保存しません。",
        )
        st.caption("スクリーンショット画像や顔写真そのものは保存しません。読み取ったテキストとメモだけを貼り付けてください。")
        st.markdown("**不足分・修正欄**")
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
    pasted_form, paste_warnings = build_profile_form_from_paste(profile_paste)
    form = merge_profile_form_with_paste(form, pasted_form)

    errors = validate_profile_form(form)
    warnings = detect_profile_safety_warnings(form)
    if paste_warnings:
        warnings.extend(paste_warnings)
    if profile_paste.strip():
        st.markdown("**貼り付け内容の抽出プレビュー**")
        st.json(build_profile_paste_preview(profile_paste))
        st.info("抽出できなかった項目や違う項目は、不足分・修正欄で直してから保存してください。")
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

    search_query = st.text_input("保存済みプロフィール検索", placeholder="label / 趣味 / 年齢などで絞り込み")
    profiles = filter_real_profiles_for_gui(search_query)
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
    st.markdown("**選択中プロフィール**")
    st.json(build_real_profile_summary_for_gui(label))
    existing_partners = find_existing_partners_for_profile(label)
    if existing_partners:
        st.warning("このreal_profileから作成済みと思われるpartnerがあります。必要ならpartnerビューで開いてください。")
        st.dataframe(existing_partners, width="stretch", hide_index=True)
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
