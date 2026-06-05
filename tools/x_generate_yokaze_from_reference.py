from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from x_auto_ops.yokaze_reference_generation import (  # noqa: E402
    generate_yokaze_posts_from_reference,
    parse_target_ratio,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate yokaze_daily draft previews from analyzed references."
    )
    parser.add_argument("--input", default="data/reference_posts/analyzed_posts.jsonl")
    parser.add_argument(
        "--output",
        default="data/reference_posts/yokaze_generated_posts.jsonl",
    )
    parser.add_argument(
        "--report",
        default="reports/yokaze_reference_generation_report.md",
    )
    parser.add_argument("--top-n", type=int, default=None)
    parser.add_argument("--theme", default=None)
    parser.add_argument(
        "--style-pattern",
        default="auto",
        choices=[
            "daiben",
            "joukei",
            "hitei_kaijo",
            "kioku",
            "short_yoin",
            "auto",
        ],
    )
    parser.add_argument("--target-ratio", default="romance:0.7,other:0.3")
    parser.add_argument("--max-same-pattern", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mock-llm", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        result = generate_yokaze_posts_from_reference(
            input_path=args.input,
            output_path=args.output,
            report_path=args.report,
            top_n=args.top_n,
            theme=args.theme,
            dry_run=args.dry_run,
            mock_llm=args.mock_llm,
            style_pattern=args.style_pattern,
            target_ratio=parse_target_ratio(args.target_ratio),
            max_same_pattern=args.max_same_pattern,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    mode = "DRY-RUN" if result.dry_run else "LIVE"
    llm_mode = "mock-llm" if result.mock_llm else "provider"
    print(f"{mode} {llm_mode}: generated {result.generated_count} yokaze drafts")
    print(f"Wrote: {result.output_path}")
    print(f"Report: {result.report_path}")
    if result.dry_run or result.mock_llm:
        print("DRY-RUN/MOCK: no external LLM call was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
