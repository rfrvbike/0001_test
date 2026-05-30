from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from x_auto_ops.mock_buzz_collector import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_REPORT_PATH,
    collect_mock_buzz_posts,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the mock-only genre buzz collector."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        result = collect_mock_buzz_posts(
            config_path=args.config,
            output_path=args.output,
            report_path=args.report,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("DRY-RUN mock buzz collection complete.")
    print(f"Generated mock posts: {result.generated_count}")
    print(f"Filtered posts: {result.filtered_count}")
    print(f"CSV: {result.output_path}")
    print(f"Report: {result.report_path}")
    print("No X API call, token access, .env edit, or posting was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
