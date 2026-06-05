from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from x_auto_ops.reference_posts import score_reference_posts  # noqa: E402


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score collected reference posts.")
    parser.add_argument("--input", default="data/reference_posts/raw_posts.csv")
    parser.add_argument("--output", default="data/reference_posts/scored_posts.csv")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        result = score_reference_posts(input_path=args.input, output_path=args.output)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Read posts: {result.input_count}")
    print(f"Excluded posts: {result.excluded_count}")
    print(f"Scored posts: {result.scored_count}")
    print(f"Wrote: {result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
