from __future__ import annotations

from .app_core import generate
from .models import GenerationRequest, PartnerAnalysis, PartnerProfile, PartnerRecord, TargetProfile
from .partner_manager import create_partner_from_target_profile, save_updated_partner, update_partner_analysis, update_partner_status
from .partner_store import generate_next_partner_id
from .real_profile_manager import display_path, load_real_profile
from .suggestion_manager import add_suggestion, generate_next_suggestion_id
from .loaders import load_user_profile


def run_real_profile_rehearsal(
    label: str | None,
    path: str | None,
    display_name: str,
    app_name: str = "",
    dry_run: bool = False,
) -> str:
    profile_path, target = load_real_profile(label=label, path=path)
    if dry_run:
        partner = _build_dry_run_partner(target, display_name, app_name)
    else:
        partner = create_partner_from_target_profile(target, display_name, app_name)

    result = generate(
        GenerationRequest(
            target_profile=_target_from_partner(partner),
            user_profile=load_user_profile(),
            purpose="first_message",
            current_stage="first_message",
        )
    )

    if dry_run:
        suggestion_id = generate_next_suggestion_id(partner)
        status = "dry_run_not_saved"
        next_action = "dry-runのため保存していません"
    else:
        update_partner_analysis(
            partner,
            partner_temperature=result.partner_temperature,
            safe_topics=result.safe_topics,
            light_only_topics=result.light_only_topics,
            avoid_topics=result.avoid_topics,
            next_strategy=result.recommended_strategy,
            last_suggested_message=result.best_message,
        )
        suggestion = add_suggestion(partner, "first", result.best_message, "real-profile-rehearse", "OK")
        update_partner_status(partner, "first_message_suggested")
        partner.message_state.next_action = "初回メッセージ候補を確認して送る"
        save_updated_partner(partner)
        suggestion_id = suggestion.suggestion_id
        status = partner.status
        next_action = partner.message_state.next_action

    return format_rehearsal_result(
        real_profile_path=display_path(profile_path),
        partner=partner,
        candidates=result.message_candidates,
        best_message=result.best_message,
        suggestion_id=suggestion_id,
        status=status,
        next_action=next_action,
        dry_run=dry_run,
    )


def format_rehearsal_result(
    real_profile_path: str,
    partner: PartnerRecord,
    candidates: list[str],
    best_message: str,
    suggestion_id: str,
    status: str,
    next_action: str,
    dry_run: bool = False,
) -> str:
    saved_line = (
        f"pending_suggestions に {suggestion_id} として保存しました。"
        if not dry_run
        else f"dry-runのため pending_suggestions には保存していません。保存予定ID: {suggestion_id}"
    )
    sections = [
        "【実運用リハーサル結果】",
        f"real profile:\n{real_profile_path}",
        (
            "partnerを作成しました:" if not dry_run else "partner作成予定:"
        )
        + f"\npartner_id: {partner.partner_id}\ndisplay_name: {partner.display_name}\napp_name: {partner.app_name or '-'}",
        f"【初回メッセージ候補】\n{_numbered(candidates)}",
        f"【一番おすすめ】\n{best_message}",
        f"【保存状態】\n{saved_line}\nstatus: {status}\nnext_action: {next_action}",
        (
            "【次に使うコマンド】\n"
            f"partner詳細:\npython main.py partner-show --partner-id {partner.partner_id}\n\n"
            f"送信済み登録:\npython main.py partner-mark-sent --partner-id {partner.partner_id} --suggestion-id {suggestion_id}\n\n"
            "ダッシュボード確認:\npython main.py partner-dashboard\n\n"
            f"タイムライン確認:\npython main.py partner-timeline --partner-id {partner.partner_id}"
        ),
    ]
    return "\n\n".join(sections)


def _build_dry_run_partner(target: TargetProfile, display_name: str, app_name: str) -> PartnerRecord:
    return PartnerRecord(
        partner_id=generate_next_partner_id(),
        display_name=display_name,
        app_name=app_name,
        status="dry_run",
        profile=PartnerProfile(
            age=target.age,
            profile_text=target.profile_text,
            hobbies=list(target.hobbies),
            photos_memo=list(target.photos_memo),
            location_hint=target.location_hint,
            relationship_goal=target.relationship_goal,
            free_notes=target.free_notes,
        ),
        analysis=PartnerAnalysis(),
    )


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


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, 1))
