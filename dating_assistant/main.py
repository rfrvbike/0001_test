from __future__ import annotations

import argparse

from src.app_core import generate
from src.conversation_memory import add_turn, build_conversation_for_generation, get_recent_turns
from src.dashboard_builder import build_partner_dashboard
from src.formatter import format_result
from src.loaders import load_config, load_conversation, load_target_profile, load_user_profile
from src.models import GenerationRequest, PartnerRecord, TargetProfile
from src.output_writer import save_cli_output
from src.partner_manager import (
    VALID_PARTNER_STATUSES,
    add_partner_note,
    create_partner_from_target_profile,
    update_partner_analysis,
    update_partner_status,
)
from src.partner_store import list_partners, load_partner
from src.real_profile_manager import (
    build_create_success_message,
    create_real_profile,
    display_path,
    format_real_profile,
    format_real_profile_list,
    format_privacy_warning_message,
    list_real_profiles,
    load_real_profile,
    run_interactive_real_profile_create,
)
from src.rehearsal_runner import run_real_profile_rehearsal
from src.safety_reviewer import SafetyReviewer
from src.suggestion_manager import (
    add_suggestion,
    discard_suggestion,
    get_pending_suggestions,
    mark_suggestion_sent,
    mark_text_sent,
    pending_suggestion_count,
)
from src.timeline_builder import format_timeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Human-reviewed dating app conversation drafting assistant")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ["analyze", "generate-first", "generate-reply", "invite"]:
        cmd = sub.add_parser(name)
        cmd.add_argument("--target", required=True)
        cmd.add_argument("--history")
        cmd.add_argument("--stage", default="auto")
        cmd.add_argument("--flirt-level", type=int)
        cmd.add_argument("--save-output", action="store_true")

    review = sub.add_parser("review")
    review.add_argument("--message", required=True)
    review.add_argument("--save-output", action="store_true")

    create = sub.add_parser("partner-create")
    create.add_argument("--source", required=True)
    create.add_argument("--display-name", required=True)
    create.add_argument("--app-name", default="")

    sub.add_parser("partner-list")

    show = sub.add_parser("partner-show")
    show.add_argument("--partner-id", required=True)

    turn = sub.add_parser("partner-add-turn")
    turn.add_argument("--partner-id", required=True)
    turn.add_argument("--speaker", required=True, choices=["user", "partner"])
    turn.add_argument("--text", required=True)

    for name in ["partner-generate-first", "partner-generate-reply", "partner-generate-invite"]:
        command = sub.add_parser(name)
        command.add_argument("--partner-id", required=True)
        command.add_argument("--save-output", action="store_true")

    status = sub.add_parser("partner-update-status")
    status.add_argument("--partner-id", required=True)
    status.add_argument("--status", required=True, choices=sorted(VALID_PARTNER_STATUSES))

    note = sub.add_parser("partner-note")
    note.add_argument("--partner-id", required=True)
    note.add_argument("--text", required=True)

    mark_sent = sub.add_parser("partner-mark-sent")
    mark_sent.add_argument("--partner-id", required=True)
    sent_source = mark_sent.add_mutually_exclusive_group(required=True)
    sent_source.add_argument("--suggestion-id")
    sent_source.add_argument("--text")

    discard = sub.add_parser("partner-discard-suggestion")
    discard.add_argument("--partner-id", required=True)
    discard.add_argument("--suggestion-id", required=True)

    timeline = sub.add_parser("partner-timeline")
    timeline.add_argument("--partner-id", required=True)
    timeline.add_argument("--limit", default="30")
    timeline.add_argument("--verbose", action="store_true")
    timeline.add_argument("--save-output", action="store_true")

    dashboard = sub.add_parser("partner-dashboard")
    dashboard.add_argument("--active-only", action="store_true")
    dashboard.add_argument("--status", choices=sorted(VALID_PARTNER_STATUSES))
    dashboard.add_argument("--needs-action", action="store_true")
    dashboard.add_argument("--waiting", action="store_true")
    dashboard.add_argument("--sort", choices=["updated", "received", "sent"], default="updated")
    dashboard.add_argument("--save-output", action="store_true")

    real_create = sub.add_parser("real-profile-create")
    real_create.add_argument("--interactive", "-i", action="store_true")
    real_create.add_argument("--label")
    real_create.add_argument("--profile-text")
    real_create.add_argument("--age", type=int)
    real_create.add_argument("--hobby", action="append", default=[])
    real_create.add_argument("--photo-memo", action="append", default=[])
    real_create.add_argument("--location-hint")
    real_create.add_argument("--relationship-goal")
    real_create.add_argument("--free-notes")

    sub.add_parser("real-profile-list")

    real_show = sub.add_parser("real-profile-show")
    real_source = real_show.add_mutually_exclusive_group(required=True)
    real_source.add_argument("--label")
    real_source.add_argument("--path")

    rehearse = sub.add_parser("real-profile-rehearse")
    rehearse_source = rehearse.add_mutually_exclusive_group(required=True)
    rehearse_source.add_argument("--label")
    rehearse_source.add_argument("--path")
    rehearse.add_argument("--display-name", required=True)
    rehearse.add_argument("--app-name", default="")
    rehearse.add_argument("--save-output", action="store_true")
    rehearse.add_argument("--dry-run", action="store_true")
    return parser


def run(args: argparse.Namespace) -> str:
    if args.command.startswith("real-profile-"):
        return _run_real_profile_command(args)
    if args.command.startswith("partner-"):
        return _run_partner_command(args)

    if args.command == "review":
        reviewer = SafetyReviewer(load_config("safety_policy.yaml"))
        result = reviewer.review(args.message)
        output = f"{result['status']}\n" + "\n".join(f"- {note}" for note in result["notes"])
        if args.save_output:
            output = _with_saved_path(output, save_cli_output(args.command, output))
        return output

    target = load_target_profile(args.target)
    request = GenerationRequest(
        target_profile=target,
        user_profile=load_user_profile(),
        conversation_history=load_conversation(getattr(args, "history", None)),
        purpose={"analyze": "first_message", "generate-first": "first_message", "generate-reply": "reply", "invite": "invite"}[
            args.command
        ],
        desired_flirt_level=args.flirt_level,
        current_stage="first_message" if args.command == "generate-first" and args.stage == "auto" else args.stage,
    )
    output = format_result(generate(request))
    if args.save_output:
        output = _with_saved_path(output, save_cli_output(args.command, output, target_path=args.target))
    return output


def _run_real_profile_command(args: argparse.Namespace) -> str:
    if args.command == "real-profile-create":
        if args.interactive:
            return run_interactive_real_profile_create(initial_label=args.label)
        if not args.label or not args.profile_text:
            raise ValueError("--label and --profile-text are required unless --interactive is used")
        path, warnings = create_real_profile(
            label=args.label,
            profile_text=args.profile_text,
            age=args.age,
            hobbies=args.hobby,
            photos_memo=args.photo_memo,
            location_hint=args.location_hint,
            relationship_goal=args.relationship_goal,
            free_notes=args.free_notes,
        )
        output = build_create_success_message(path)
        if warnings:
            output += f"\n\n{format_privacy_warning_message(warnings)}"
        return output
    if args.command == "real-profile-list":
        return format_real_profile_list(list_real_profiles())
    if args.command == "real-profile-rehearse":
        output = run_real_profile_rehearsal(
            label=args.label,
            path=args.path,
            display_name=args.display_name,
            app_name=args.app_name,
            dry_run=args.dry_run,
        )
        if args.save_output:
            output = _with_saved_path(output, save_cli_output(args.command, output, target_path=args.label or args.path))
        return output
    _, profile = load_real_profile(label=args.label, path=args.path)
    return format_real_profile(profile)


def _run_partner_command(args: argparse.Namespace) -> str:
    if args.command == "partner-create":
        partner = create_partner_from_target_profile(load_target_profile(args.source), args.display_name, args.app_name)
        return f"作成しました: {partner.partner_id} ({partner.display_name})"
    if args.command == "partner-list":
        return _format_partner_list(list_partners())
    if args.command == "partner-dashboard":
        output = build_partner_dashboard(
            list_partners(),
            active_only=args.active_only,
            status=args.status,
            needs_action=args.needs_action,
            waiting=args.waiting,
            sort_key=args.sort,
        )
        if args.save_output:
            output = _with_saved_path(output, save_cli_output(args.command, output))
        return output

    partner = load_partner(args.partner_id)
    if args.command == "partner-show":
        return _format_partner_show(partner)
    if args.command == "partner-timeline":
        limit = _parse_timeline_limit(args.limit)
        output = format_timeline(partner, limit=limit, verbose=args.verbose)
        if args.save_output:
            output = _with_saved_path(output, save_cli_output(args.command, output, target_path=partner.partner_id))
        return output
    if args.command == "partner-add-turn":
        add_turn(partner, args.speaker, args.text)
        return f"会話を追加しました: {partner.partner_id} / {args.speaker}"
    if args.command == "partner-update-status":
        update_partner_status(partner, args.status)
        return f"ステータスを更新しました: {partner.partner_id} / {args.status}"
    if args.command == "partner-note":
        add_partner_note(partner, args.text)
        return f"メモを追加しました: {partner.partner_id}"
    if args.command == "partner-mark-sent":
        if args.suggestion_id:
            suggestion = mark_suggestion_sent(partner, args.suggestion_id)
            text = suggestion.text
            detail = f"suggestion_id: {suggestion.suggestion_id}"
        else:
            mark_text_sent(partner, args.text)
            text = args.text
            detail = "直接指定した文"
        return (
            f"送信済みにしました:\npartner_id: {partner.partner_id}\n{detail}\n\n"
            f"会話履歴に追加しました:\nspeaker: user\ntext: {text}"
        )
    if args.command == "partner-discard-suggestion":
        suggestion = discard_suggestion(partner, args.suggestion_id)
        return f"候補を破棄しました:\npartner_id: {partner.partner_id}\nsuggestion_id: {suggestion.suggestion_id}"
    return _generate_for_partner(args, partner)


def _generate_for_partner(args: argparse.Namespace, partner: PartnerRecord) -> str:
    command_settings = {
        "partner-generate-first": ("first_message", "first_message"),
        "partner-generate-reply": ("reply", "auto"),
        "partner-generate-invite": ("invite", "auto"),
    }
    purpose, stage = command_settings[args.command]
    request = GenerationRequest(
        target_profile=_target_from_partner(partner),
        user_profile=load_user_profile(),
        conversation_history=build_conversation_for_generation(partner),
        purpose=purpose,
        current_stage=stage,
    )
    result = generate(request)
    update_partner_analysis(
        partner,
        partner_temperature=result.partner_temperature,
        safe_topics=result.safe_topics,
        light_only_topics=result.light_only_topics,
        avoid_topics=result.avoid_topics,
        next_strategy=result.recommended_strategy,
        last_suggested_message=result.invite_suggestion or result.best_message,
    )
    suggestion_text = result.invite_suggestion if args.command == "partner-generate-invite" else result.best_message
    if suggestion_text:
        add_suggestion(
            partner,
            purpose={"partner-generate-first": "first", "partner-generate-reply": "reply", "partner-generate-invite": "invite"}[
                args.command
            ],
            text=suggestion_text,
            source=args.command,
            safety_result="OK",
        )
    if args.command == "partner-generate-first":
        update_partner_status(partner, "first_message_suggested")
    elif args.command == "partner-generate-reply" and partner.status in {"new_profile", "first_message_sent", "first_message_suggested"}:
        update_partner_status(partner, "chatting")
    elif args.command == "partner-generate-invite" and result.invite_suggestion:
        update_partner_status(partner, "invite_ready")

    output = format_result(result)
    if args.command == "partner-generate-invite" and not result.invite_suggestion:
        output += "\n\n【招待判断】\nまだ誘う段階ではありません。会話を続けて温度感を確認してください。"
    if args.save_output:
        output = _with_saved_path(output, save_cli_output(args.command, output, target_path=partner.partner_id))
    return output


def _format_partner_list(partners: list[PartnerRecord]) -> str:
    if not partners:
        return "保存済みpartner一覧:\n\n登録なし"
    blocks = ["保存済みpartner一覧:"]
    for partner in partners:
        state = partner.message_state
        blocks.append(
            f"{partner.partner_id}  {partner.display_name}  {partner.app_name}\n"
            f"  status: {partner.status}\n"
            f"  温度感: {partner.analysis.partner_temperature}\n"
            f"  最終受信: {state.last_received_at or '-'}\n"
            f"  最終送信: {state.last_sent_at or '-'}\n"
            f"  自分の対応待ち: {_yes_no(state.awaiting_user_action)}\n"
            f"  相手の返信待ち: {_yes_no(state.awaiting_partner_reply)}\n"
            f"  未送信候補: {pending_suggestion_count(partner)}件\n"
            f"  次の行動: {state.next_action or '-'}"
        )
    return "\n\n".join(blocks)


def _format_partner_show(partner: PartnerRecord) -> str:
    profile = partner.profile
    state = partner.message_state
    recent = get_recent_turns(partner, 10)
    pending = get_pending_suggestions(partner)
    sections = [
        (
            "基本情報",
            f"partner_id: {partner.partner_id}\ndisplay_name: {partner.display_name}\napp_name: {partner.app_name or '-'}\n"
            f"status: {partner.status}\npartner_temperature: {partner.analysis.partner_temperature}",
        ),
        (
            "現在の状態",
            f"最終送信: {state.last_sent_at or '-'}\n最終受信: {state.last_received_at or '-'}\n"
            f"未送信候補: {len(pending)}件\n次の行動: {state.next_action or '-'}\n"
            f"返信待ち: {_yes_no(state.awaiting_partner_reply)}\n自分の対応待ち: {_yes_no(state.awaiting_user_action)}",
        ),
        (
            "プロフィール",
            f"年齢: {profile.age or '-'}\nプロフィール文: {profile.profile_text or '-'}\n"
            f"趣味: {_inline(profile.hobbies)}\n写真メモ: {_inline(profile.photos_memo)}\n"
            f"関係性希望: {profile.relationship_goal or '-'}\n補足: {profile.free_notes or '-'}",
        ),
        ("話しやすい話題", _lines(partner.analysis.safe_topics)),
        ("避ける話題", _lines(partner.analysis.avoid_topics)),
        ("最近の会話", "\n".join(f"{turn.speaker}: {turn.text}" for turn in recent) or "- なし"),
        (
            "未送信候補",
            "\n\n".join(f"{item.suggestion_id} ({item.purpose}):\n{item.text}" for item in pending) or "- なし",
        ),
        ("最後に生成した候補", state.last_suggested_message or partner.analysis.last_suggested_message or "- なし"),
        ("メモ", _lines([note.text for note in partner.notes])),
    ]
    return "\n\n".join(f"【{title}】\n{body}" for title, body in sections)


def _lines(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- なし"


def _inline(items: list[str]) -> str:
    return ", ".join(items) if items else "-"


def _yes_no(value: bool) -> str:
    return "はい" if value else "いいえ"


def _parse_timeline_limit(value: str) -> int | None:
    if value.lower() == "all":
        return None
    limit = int(value)
    if limit < 1:
        raise ValueError("--limit must be a positive integer or all")
    return limit


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


def _with_saved_path(output: str, saved_path) -> str:
    relative = saved_path.relative_to(saved_path.parents[2]).as_posix()
    return f"{output}\n\n保存しました:\n{relative}"


def main() -> None:
    print(run(build_parser().parse_args()))


if __name__ == "__main__":
    main()
