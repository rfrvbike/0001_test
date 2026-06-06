from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.excel_daily_poster.excel_queue import (  # noqa: E402
    ContentRowError,
    QueueError,
    iter_post_candidates,
    mark_content_error,
    mark_posted,
    open_queue,
    queue_lock,
    validate_candidate_for_post,
)
from tools.excel_daily_poster.x_client import (  # noqa: E402
    BlockedXPoster,
    XPoster,
    validate_post_text,
)


LEGACY_MANUAL_ACCOUNT_ID = "legacy_manual_account"


@dataclass(frozen=True)
class DailyPostResult:
    selected_row: int | None
    post_text: str | None
    mode: str
    changed_queue: bool
    content_error_rows: tuple[int, ...] = ()


def build_logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger("excel_daily_poster")


def run_once(
    queue_path: str | Path,
    *,
    dry_run: bool,
    poster: XPoster | None = None,
    today: date | None = None,
    logger: logging.Logger | None = None,
) -> DailyPostResult:
    log = logger or logging.getLogger("excel_daily_poster")
    queue = open_queue(queue_path)
    rows, fieldnames = queue.read()

    if dry_run:
        return _process_rows(
            rows,
            fieldnames,
            queue,
            dry_run=True,
            poster=poster,
            today=today,
            log=log,
        )

    active_poster = poster or BlockedXPoster()
    with queue_lock(queue.path):
        rows, fieldnames = queue.read()
        queue.assert_writable()
        return _process_rows(
            rows,
            fieldnames,
            queue,
            dry_run=False,
            poster=active_poster,
            today=today,
            log=log,
        )


def _process_rows(
    rows: list[dict[str, str]],
    fieldnames: list[str],
    queue,
    *,
    dry_run: bool,
    poster: XPoster | None,
    today: date | None,
    log: logging.Logger,
) -> DailyPostResult:
    mode = "dry-run" if dry_run else "live"
    content_error_rows: list[int] = []
    changed_rows = False

    for candidate in iter_post_candidates(rows, today=today):
        try:
            validate_candidate_for_post(candidate, today=today)
            validate_post_text(candidate.post_text)
        except (ContentRowError, ValueError) as exc:
            content_error_rows.append(candidate.csv_line_number)
            print(
                f"{mode.upper()} content_error row: "
                f"{candidate.csv_line_number} reason: {exc}"
            )
            if not dry_run:
                mark_content_error(rows, candidate.index, error=str(exc))
                changed_rows = True
            continue

        log.info(
            "excel_daily_poster_selected",
            extra={
                "account_id": LEGACY_MANUAL_ACCOUNT_ID,
                "mode": mode,
                "queue_path": str(queue.path),
                "row_number": candidate.csv_line_number,
            },
        )

        if dry_run:
            print(f"DRY-RUN selected row: {candidate.csv_line_number}")
            print(f"DRY-RUN post_text: {candidate.post_text}")
            print("DRY-RUN: no X API call and no queue update were performed.")
            return DailyPostResult(
                candidate.csv_line_number,
                candidate.post_text,
                mode,
                False,
                tuple(content_error_rows),
            )

        if poster is None:
            raise RuntimeError("Live mode requires an XPoster")
        result = poster.post(candidate.post_text)
        posted_at = datetime.now()
        mark_posted(rows, candidate.index, tweet_id=result.tweet_id, posted_at=posted_at)
        try:
            queue.write(rows, fieldnames)
        except Exception as exc:
            posted_at_text = posted_at.isoformat(timespec="seconds")
            log.critical(
                "excel_daily_poster_csv_update_failed_after_post "
                "row_number=%s posted_at=%s tweet_id=%s recovery_required=true",
                candidate.csv_line_number,
                posted_at_text,
                result.tweet_id,
            )
            raise QueueError(
                "X post appears to have succeeded, but CSV update failed. "
                "Manual recovery is required. Close Excel and pause OneDrive sync. "
                f"Set row {candidate.csv_line_number} to status=posted, "
                f"posted_at={posted_at_text}, tweet_id={result.tweet_id}, error=. "
                f"Original error type: {exc.__class__.__name__}"
            ) from exc
        return DailyPostResult(
            candidate.csv_line_number,
            candidate.post_text,
            mode,
            True,
            tuple(content_error_rows),
        )

    if changed_rows:
        queue.write(rows, fieldnames)

    log.info(
        "excel_daily_poster_noop",
        extra={
            "account_id": LEGACY_MANUAL_ACCOUNT_ID,
            "mode": mode,
            "queue_path": str(queue.path),
        },
    )
    return DailyPostResult(None, None, mode, changed_rows, tuple(content_error_rows))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run-first daily poster for one legacy X account."
    )
    parser.add_argument(
        "--queue",
        default="data/manual_account_posts.csv",
        help="Path to the CSV or XLSX post queue.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Do not post or write.")
    mode.add_argument("--live", action="store_true", help="Run the live write path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logger = build_logger()
    dry_run = not args.live

    try:
        result = run_once(args.queue, dry_run=dry_run, logger=logger)
    except Exception as exc:
        logger.error(
            "excel_daily_poster_failed",
            extra={
                "account_id": LEGACY_MANUAL_ACCOUNT_ID,
                "mode": "dry-run" if dry_run else "live",
                "queue_path": args.queue,
            },
        )
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if result.selected_row is None:
        print("No eligible post row found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
