from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from x_auto_ops.dry_run_recent_search_pipeline import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    DEFAULT_PIPELINE_FIXTURE_PATH,
    DEFAULT_PIPELINE_OUTPUT_PATH,
    DEFAULT_PIPELINE_REPORT_PATH,
    load_mock_transport_fixture,
    run_dry_run_recent_search_pipeline,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the mock-only recent-search integration pipeline."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--fixture", default=str(DEFAULT_PIPELINE_FIXTURE_PATH))
    parser.add_argument("--output", default=str(DEFAULT_PIPELINE_OUTPUT_PATH))
    parser.add_argument("--report", default=str(DEFAULT_PIPELINE_REPORT_PATH))
    parser.add_argument("--genre", default="ai_side_business")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.dry_run:
        print("ERROR: --dry-run is required; live X API access is blocked.", file=sys.stderr)
        return 1
    try:
        result = run_dry_run_recent_search_pipeline(
            config_path=args.config,
            output_path=args.output,
            report_path=args.report,
            transport=load_mock_transport_fixture(args.fixture),
            source_genre=args.genre,
            dry_run=True,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("DRY-RUN recent search pipeline complete.")
    print(f"Fetched posts: {len(result.fetch_result.posts)}")
    print(f"Ranked posts: {len(result.ranked_rows)}")
    print(f"Rate limited: {result.fetch_result.rate_limited}")
    print(f"Retry after seconds: {result.fetch_result.retry_after_seconds}")
    print(f"Partial result: {result.fetch_result.partial_result}")
    print(f"CSV: {result.output_path}")
    print(f"Report: {result.report_path}")
    print("No X API call, credential lookup, .env edit, or posting was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
