from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from x_auto_ops.reference_posts import (  # noqa: E402
    analyze_reference_posts,
    generate_reference_report,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze top reference posts for yokaze structure."
    )
    parser.add_argument("--input", default="data/reference_posts/scored_posts.csv")
    parser.add_argument("--output", default="data/reference_posts/analyzed_posts.jsonl")
    parser.add_argument("--raw", default="data/reference_posts/raw_posts.csv")
    parser.add_argument("--report", default="reports/reference_posts_report.md")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mock-llm", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        result = analyze_reference_posts(
            input_path=args.input,
            output_path=args.output,
            top_n=args.top_n,
            dry_run=args.dry_run,
            mock_llm=args.mock_llm,
        )
        report_path = generate_reference_report(
            raw_path=args.raw,
            scored_path=args.input,
            analyzed_path=args.output,
            output_path=args.report,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    mode = "DRY-RUN" if result.dry_run else "LIVE"
    llm_mode = "mock-llm" if result.mock_llm else "provider"
    print(f"{mode} {llm_mode}: analyzed {result.analyzed_count} posts")
    print(f"Wrote: {result.output_path}")
    print(f"Report: {report_path}")
    if result.dry_run or result.mock_llm:
        print("DRY-RUN/MOCK: no external LLM call was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
