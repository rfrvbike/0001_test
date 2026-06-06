from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from x_auto_ops.reference_posts import (  # noqa: E402
    DEFAULT_LIMIT,
    collect_reference_posts,
    load_dotenv,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect reference X posts for structure analysis."
    )
    parser.add_argument("--source", default="data/source_accounts.csv")
    parser.add_argument("--output", default="data/reference_posts/raw_posts.csv")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        if not args.dry_run:
            env = load_dotenv()
            if not env.get("X_BEARER_TOKEN"):
                raise RuntimeError(
                    "X_BEARER_TOKEN is missing. Run --dry-run first; live "
                    "collection client wiring is a later phase."
                )
        result = collect_reference_posts(
            source_path=args.source,
            output_path=args.output,
            limit=args.limit,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    mode = "DRY-RUN" if result.dry_run else "LIVE"
    print(f"{mode}: wrote {result.collected_posts} posts to {result.output_path}")
    if result.dry_run:
        print("DRY-RUN: no X API call was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
