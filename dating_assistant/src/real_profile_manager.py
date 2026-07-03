from __future__ import annotations

import os
import re
from pathlib import Path

from .atomic_io import atomic_write_text
from .loaders import dump_yaml, load_target_profile
from .models import TargetProfile

ROOT = Path(__file__).resolve().parents[1]
LABEL_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
PRIVACY_WARNING_WORDS = [
    "本名",
    "勤務先",
    "会社名",
    "学校名",
    "大学名",
    "高校",
    "LINE",
    "ライン",
    "Instagram",
    "インスタ",
    "X ID",
    "Twitter",
    "最寄り駅",
    "住所",
    "電話番号",
    "メールアドレス",
]


def get_real_profile_dir() -> Path:
    override = os.environ.get("DATING_ASSISTANT_REAL_PROFILE_DIR")
    path = Path(override) if override else ROOT / "data" / "local" / "real_profiles"
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_real_profile_label(label: str) -> None:
    if not LABEL_PATTERN.fullmatch(label):
        raise ValueError("label must contain only ASCII letters, numbers, hyphens, and underscores")


def create_real_profile(
    label: str,
    profile_text: str,
    age: int | None = None,
    hobbies: list[str] | None = None,
    photos_memo: list[str] | None = None,
    location_hint: str | None = None,
    relationship_goal: str | None = None,
    free_notes: str | None = None,
) -> tuple[Path, list[str]]:
    validate_real_profile_label(label)
    profile_text = profile_text.strip() or "プロフィール本文未設定。あとで補完できます。"
    path = get_real_profile_dir() / f"{label}.yaml"
    if path.exists():
        raise FileExistsError(f"Real profile already exists: {label}")
    profile = TargetProfile(
        name_or_label=label,
        age=age,
        profile_text=profile_text,
        hobbies=list(hobbies or []),
        photos_memo=list(photos_memo or []),
        location_hint=location_hint,
        relationship_goal=relationship_goal,
        free_notes=free_notes,
    )
    atomic_write_text(path, _format_yaml(profile))
    warnings = detect_privacy_warnings(
        [profile_text, *(hobbies or []), *(photos_memo or []), location_hint or "", relationship_goal or "", free_notes or ""]
    )
    return path, warnings


def build_create_success_message(path: Path) -> str:
    shown_path = display_path(path)
    return (
        f"実プロフィールYAMLを作成しました:\n{shown_path}\n\n"
        "次のコマンドでpartner化できます:\n"
        f'python main.py partner-create --source {shown_path} --display-name "表示名を入力" --app-name pairs'
    )


def format_privacy_warning_message(warnings: list[str]) -> str:
    if not warnings:
        return ""
    details = "\n".join(f'- 入力内容に「{word}」が含まれています。' for word in warnings)
    return f"注意:\n{details}\nSNS IDや連絡先は保存しないことを推奨します。\n\n内容を見直してから保存してください。"


def list_real_profiles() -> list[tuple[Path, TargetProfile]]:
    profiles = []
    for path in sorted(get_real_profile_dir().glob("*.yaml")):
        profiles.append((path, load_target_profile(path)))
    return profiles


def load_real_profile(label: str | None = None, path: str | Path | None = None) -> tuple[Path, TargetProfile]:
    if bool(label) == bool(path):
        raise ValueError("Specify exactly one of label or path")
    if label:
        validate_real_profile_label(label)
        resolved = get_real_profile_dir() / f"{label}.yaml"
    else:
        resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Real profile not found: {resolved}")
    return resolved, load_target_profile(resolved)


def detect_privacy_warnings(texts: list[str]) -> list[str]:
    joined = "\n".join(texts).lower()
    return [word for word in PRIVACY_WARNING_WORDS if word.lower() in joined]


def prompt_multiline(prompt: str, input_func=input, output_func=print) -> str:
    output_func(prompt)
    output_func("複数行入力できます。空行のみで終了します。")
    lines = []
    while True:
        line = input_func("> ")
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines)


def prompt_list(prompt: str, input_func=input, output_func=print) -> list[str]:
    output_func(prompt)
    output_func("1つずつ入力してください。空行のみで終了します。")
    items = []
    while True:
        item = input_func("> ")
        if item == "":
            break
        items.append(item)
    return items


def build_real_profile_preview(
    label: str,
    age: int | None,
    profile_text: str,
    hobbies: list[str],
    photos_memo: list[str],
    location_hint: str | None,
    relationship_goal: str | None,
    free_notes: str | None,
) -> str:
    return "\n\n".join(
        [
            "作成内容を確認してください。",
            f"【label】\n{label}",
            f"【年齢】\n{age if age is not None else '-'}",
            f"【プロフィール文】\n{profile_text or '-'}",
            f"【趣味】\n{_bullets(hobbies)}",
            f"【写真メモ】\n{_bullets(photos_memo)}",
            f"【大まかな地域】\n{location_hint or '-'}",
            f"【関係性希望】\n{relationship_goal or '-'}",
            f"【補足メモ】\n{free_notes or '-'}",
        ]
    )


def run_interactive_real_profile_create(initial_label: str | None = None, input_func=input, output_func=print) -> str:
    output_func("実プロフィールYAMLを対話式で作成します。")
    output_func("")
    output_func(
        "注意:\n"
        "スクリーンショット画像そのもの、顔写真、本名、勤務先、学校名、SNS ID、LINE ID、"
        "最寄り駅、住所、電話番号、メールアドレスは入力しないでください。"
    )
    label = _prompt_label(initial_label, input_func, output_func)
    age = _prompt_age(input_func, output_func)
    profile_text = prompt_multiline("プロフィール文を入力してください。", input_func, output_func)
    if not profile_text.strip():
        return "プロフィール文が空のため保存しませんでした。"
    hobbies = prompt_list("趣味を入力してください。", input_func, output_func)
    photos_memo = prompt_list("写真メモを入力してください。", input_func, output_func)
    location_hint = _empty_to_none(_prompt_one_line("大まかな地域を入力してください（不明ならEnter）:", input_func, output_func))
    relationship_goal = _empty_to_none(_prompt_one_line("関係性希望を入力してください（不明ならEnter）:", input_func, output_func))
    free_notes = _empty_to_none(prompt_multiline("補足メモを入力してください。", input_func, output_func))

    warnings = detect_privacy_warnings(
        [profile_text, *hobbies, *photos_memo, location_hint or "", relationship_goal or "", free_notes or ""]
    )
    output_func("")
    output_func(build_real_profile_preview(label, age, profile_text, hobbies, photos_memo, location_hint, relationship_goal, free_notes))
    if warnings:
        output_func("")
        output_func(format_privacy_warning_message(warnings))
    answer = _prompt_one_line("この内容で保存しますか？ [y/N]:", input_func, output_func)
    if answer.lower() != "y":
        return "保存をキャンセルしました。"
    try:
        path, _ = create_real_profile(
            label=label,
            profile_text=profile_text,
            age=age,
            hobbies=hobbies,
            photos_memo=photos_memo,
            location_hint=location_hint,
            relationship_goal=relationship_goal,
            free_notes=free_notes,
        )
    except FileExistsError:
        return f"エラー:\n{display_path(get_real_profile_dir() / f'{label}.yaml')} は既に存在します。\n別のlabelを指定してください。"
    return build_create_success_message(path)


def format_real_profile(profile: TargetProfile) -> str:
    return "\n\n".join(
        [
            f"【実プロフィールYAML】\nlabel: {profile.name_or_label}\nage: {profile.age or '-'}",
            f"【プロフィール文】\n{profile.profile_text}",
            f"【趣味】\n{_bullets(profile.hobbies)}",
            f"【写真メモ】\n{_bullets(profile.photos_memo)}",
            (
                "【補足】\n"
                f"location_hint: {profile.location_hint or '-'}\n"
                f"relationship_goal: {profile.relationship_goal or '-'}\n"
                f"free_notes: {profile.free_notes or '-'}"
            ),
        ]
    )


def format_real_profile_list(profiles: list[tuple[Path, TargetProfile]]) -> str:
    if not profiles:
        return "保存済みreal profile:\n\n- なし"
    blocks = ["保存済みreal profile:"]
    for path, profile in profiles:
        blocks.append(
            f"{profile.name_or_label}\n"
            f"  path: {_display_path(path)}\n"
            f"  age: {profile.age or '-'}\n"
            f"  hobbies: {', '.join(profile.hobbies) if profile.hobbies else '-'}"
        )
    return "\n\n".join(blocks)


def display_path(path: Path) -> str:
    return _display_path(path)


def _format_yaml(profile: TargetProfile) -> str:
    return dump_yaml(
        {
            "name_or_label": profile.name_or_label,
            "age": profile.age,
            "profile_text": profile.profile_text,
            "hobbies": profile.hobbies,
            "photos_memo": profile.photos_memo,
            "location_hint": profile.location_hint,
            "relationship_goal": profile.relationship_goal,
            "free_notes": profile.free_notes,
        }
    )


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- なし"


def _prompt_label(initial_label: str | None, input_func, output_func) -> str:
    if initial_label:
        try:
            validate_real_profile_label(initial_label)
            return initial_label
        except ValueError:
            output_func("指定されたlabelが不正です。再入力してください。")
    while True:
        label = _prompt_one_line("labelを入力してください（英数字・ハイフン・アンダースコアのみ）:", input_func, output_func)
        try:
            validate_real_profile_label(label)
            return label
        except ValueError as error:
            output_func(f"エラー: {error}")


def _prompt_age(input_func, output_func) -> int | None:
    while True:
        value = _prompt_one_line("年齢を入力してください（不明ならEnter）:", input_func, output_func)
        if value == "":
            return None
        try:
            return int(value)
        except ValueError:
            output_func("年齢は数字で入力してください。")


def _prompt_one_line(prompt: str, input_func, output_func) -> str:
    output_func(prompt)
    return input_func("> ")


def _empty_to_none(value: str) -> str | None:
    return value if value else None
