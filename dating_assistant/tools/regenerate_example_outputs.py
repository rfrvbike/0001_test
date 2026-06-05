from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.app_core import generate
from src.formatter import format_result
from src.loaders import load_conversation, load_target_profile, load_user_profile
from src.models import GenerationRequest


FIRST_SAMPLES = {
    "generate_first_travel_active.md": "sample_target_travel_active.yaml",
    "generate_first_cafe_movie.md": "sample_target_cafe_movie.yaml",
    "generate_first_fashion_beauty.md": "sample_target_fashion_beauty.yaml",
    "generate_first_drink_night.md": "sample_target_drink_night.yaml",
}

REPLY_SAMPLES = {
    "generate_reply_movie.md": ("sample_target_cafe_movie.yaml", "sample_conversation_movie_reply.yaml"),
    "generate_reply_cafe.md": ("sample_target_cafe_movie.yaml", "sample_conversation_cafe_reply.yaml"),
    "generate_reply_drink.md": ("sample_target_drink_night.yaml", "sample_conversation_drink_reply.yaml"),
    "generate_reply_short.md": ("sample_target_cafe_movie.yaml", "sample_conversation_short_reply.yaml"),
    "generate_reply_multi_topic.md": ("sample_target_cafe_movie.yaml", "sample_conversation_multi_topic_reply.yaml"),
}


def regenerate(dry_run: bool = False) -> list[tuple[Path, int, int, bool]]:
    examples = ROOT / "data" / "examples"
    output_dir = ROOT / "outputs" / "examples"
    output_dir.mkdir(parents=True, exist_ok=True)
    user = load_user_profile()
    written: list[tuple[Path, int, int, bool]] = []

    for output_name, target_name in FIRST_SAMPLES.items():
        request = GenerationRequest(
            target_profile=load_target_profile(examples / target_name),
            user_profile=user,
            current_stage="first_message",
        )
        written.append(_write(output_dir / output_name, format_result(generate(request)), dry_run))

    for output_name, (target_name, history_name) in REPLY_SAMPLES.items():
        request = GenerationRequest(
            target_profile=load_target_profile(examples / target_name),
            user_profile=user,
            conversation_history=load_conversation(examples / history_name),
            purpose="reply",
            current_stage="auto",
        )
        written.append(_write(output_dir / output_name, format_result(generate(request)), dry_run))

    return written


def _write(path: Path, content: str, dry_run: bool = False) -> tuple[Path, int, int, bool]:
    before = path.read_text(encoding="utf-8") if path.exists() else ""
    if not dry_run:
        path.write_text(content, encoding="utf-8")
    return path, len(before), len(content), before != content


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regenerate checked example outputs.")
    parser.add_argument("--dry-run", action="store_true", help="Show diff summary without writing files.")
    args = parser.parse_args()
    results = regenerate(dry_run=args.dry_run)
    if args.dry_run:
        print("dry-run: 更新は行いません")
        print()
        print("確認しました:")
    else:
        print("更新しました:")
    for path, before_len, after_len, changed in results:
        print(path.relative_to(ROOT).as_posix())
        print(f"  文字数: {before_len} -> {after_len}")
        print(f"  変更あり: {'yes' if changed else 'no'}")
    changed_count = sum(1 for _, _, _, changed in results if changed)
    print()
    print("集計:")
    print(f"対象ファイル数: {len(results)}")
    print(f"変更あり: {changed_count}")
    print(f"変更なし: {len(results) - changed_count}")
    print(f"dry-run: {'yes' if args.dry_run else 'no'}")
