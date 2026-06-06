from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from x_auto_ops.manual_reference_import import import_manual_reference_posts  # noqa: E402


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import manually collected X reference posts into raw_posts.csv."
    )
    parser.add_argument(
        "--input",
        default="data/reference_posts/manual_reference_posts.csv",
    )
    parser.add_argument(
        "--output",
        default="data/reference_posts/raw_posts.csv",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        result = import_manual_reference_posts(
            input_path=args.input,
            output_path=args.output,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    mode = "DRY-RUN" if result.dry_run else "IMPORT"
    print(f"{mode}: read {result.input_count} manual rows")
    print(f"{mode}: imported {result.imported_count} rows")
    print(f"{mode}: duplicate URLs skipped {result.duplicate_count}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    if result.dry_run:
        print("DRY-RUN preview:")
        for row in result.rows[:5]:
            print(
                f"- {row['source_handle']} / {row['post_id']} / "
                f"{row['category']} / {row['text'][:40]}"
            )
        print("DRY-RUN: raw_posts.csv was not written.")
    else:
        print(f"Wrote: {result.output_path}")
    print("No external API call was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
