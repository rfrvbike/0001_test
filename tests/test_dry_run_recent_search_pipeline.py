from __future__ import annotations

import csv
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.mock_recent_search_pipeline import main as pipeline_cli_main
from x_auto_ops.buzz_read_client import BuzzFetchResult, XApiBuzzReadClient
from x_auto_ops.dry_run_recent_search_pipeline import (
    SUPPORTED_MOCK_ERROR_TYPES,
    load_mock_transport_fixture,
    run_dry_run_recent_search_pipeline,
)
from x_auto_ops.mock_transport import (
    MockRecentSearchTransport,
    contains_sensitive_marker,
)
from x_auto_ops.redaction import redact_sensitive_text
from x_auto_ops.redacted_live_summary import RedactedLiveSummary


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
ROOT = Path(__file__).resolve().parents[1]
TEST_REFERENCE_NOW = datetime(2026, 6, 3, 0, 30, tzinfo=timezone.utc)


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class DryRunRecentSearchPipelineTests(unittest.TestCase):
    def test_x_api_read_client_uses_injected_mock_transport(self) -> None:
        client = XApiBuzzReadClient(
            transport=MockRecentSearchTransport(load_fixture("pipeline_success.json")),
            dry_run=True,
        )

        result = client.fetch_posts(
            {
                "source_genre": "ai_side_business",
                "search_queries": ["AI workflow"],
                "exclude_keywords": ["giveaway"],
            }
        )

        self.assertIsInstance(result, BuzzFetchResult)
        self.assertEqual(len(result.posts), 2)
        self.assertEqual(result.posts[0]["source_genre"], "ai_side_business")
        self.assertFalse(result.rate_limited)

    def test_success_pipeline_writes_csv_and_report_with_ranking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pipeline.csv"
            report = Path(tmp) / "pipeline.md"

            result = run_dry_run_recent_search_pipeline(
                output_path=output,
                report_path=report,
                transport=load_mock_transport_fixture(FIXTURE_DIR / "pipeline_success.json"),
                source_genre="ai_side_business",
                dry_run=True,
                reference_now=TEST_REFERENCE_NOW,
            )

            with output.open(encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            csv_text = output.read_text(encoding="utf-8")
            report_text = report.read_text(encoding="utf-8")
            output_exists = output.exists()
            report_exists = report.exists()

        self.assertEqual(len(result.fetch_result.posts), 2)
        self.assertEqual(len(result.ranked_rows), 2)
        self.assertTrue(output_exists)
        self.assertTrue(report_exists)
        self.assertEqual(rows[0]["detected_genre"], "ai_side_business")
        self.assertEqual(rows[0]["rank_in_genre"], "1")
        self.assertIn("Mock Recent Search Pipeline Report", report_text)
        self.assertIn("Top Posts", report_text)
        self.assertIsInstance(result.redacted_live_summary, RedactedLiveSummary)
        self.assertEqual(result.redacted_live_summary.status, "success")
        self.assertEqual(result.redacted_live_summary.status_code, 200)
        self.assertIn("Redacted Live Summary", report_text)
        self.assertIn(result.redacted_live_summary.safe_debug_summary(), report_text)
        self.assertNotIn("diagnostics_version", rows[0])
        self.assertNotIn("RedactedLiveSummary", csv_text)
        self.assertNotIn("pipeline_ai_top", report_text)
        self.assertNotIn("4001", report_text)
        self.assertNotIn("Non-engineer AI workflow", report_text)

    def test_partial_pipeline_preserves_next_token_and_metrics_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_dry_run_recent_search_pipeline(
                output_path=Path(tmp) / "pipeline.csv",
                report_path=Path(tmp) / "pipeline.md",
                transport=load_mock_transport_fixture(FIXTURE_DIR / "pipeline_partial.json"),
                source_genre="daily",
                dry_run=True,
                reference_now=TEST_REFERENCE_NOW,
            )

        self.assertTrue(result.fetch_result.partial_result)
        self.assertEqual(result.fetch_result.next_token, "pipeline-next-token")
        self.assertIn("missing_impression_count", result.ranked_rows[0]["metrics_missing"])
        self.assertEqual(result.ranked_rows[0]["detected_genre"], "daily")
        self.assertEqual(result.redacted_live_summary.status, "partial")
        self.assertTrue(result.redacted_live_summary.partial_result)
        self.assertTrue(result.redacted_live_summary.next_token_present)
        self.assertGreater(result.redacted_live_summary.metrics_missing_count, 0)

    def test_rate_limited_pipeline_preserves_retry_after(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "pipeline.md"
            result = run_dry_run_recent_search_pipeline(
                output_path=Path(tmp) / "pipeline.csv",
                report_path=report,
                transport=load_mock_transport_fixture(FIXTURE_DIR / "pipeline_rate_limited.json"),
                source_genre="ai_side_business",
                dry_run=True,
            )
            report_text = report.read_text(encoding="utf-8")

        self.assertTrue(result.fetch_result.rate_limited)
        self.assertEqual(result.fetch_result.retry_after_seconds, 240)
        self.assertTrue(result.fetch_result.partial_result)
        self.assertEqual(result.ranked_rows, [])
        self.assertEqual(result.retry_queue.size(), 1)
        self.assertIn("retry_queue_size: 1", report_text)
        self.assertIn("rate_limited_count: 1", report_text)
        self.assertIn("Retry Tasks", report_text)
        self.assertIn("redaction_status: ok", report_text)
        self.assertEqual(result.redacted_live_summary.status, "rate_limited")
        self.assertEqual(result.redacted_live_summary.status_code, 429)
        self.assertTrue(result.redacted_live_summary.rate_limited)
        self.assertTrue(result.redacted_live_summary.retryable)
        self.assertEqual(result.redacted_live_summary.retry_after_seconds, 240)
        self.assertIn(result.redacted_live_summary.safe_debug_summary(), report_text)

    def test_synthetic_error_pipeline_builds_safe_summary_without_csv(self) -> None:
        retryable_by_type = {
            "timeout",
            "network_error",
            "rate_limited",
            "server_error",
        }
        partial_by_type = retryable_by_type

        for error_type in sorted(SUPPORTED_MOCK_ERROR_TYPES):
            with self.subTest(error_type=error_type):
                with tempfile.TemporaryDirectory() as tmp:
                    output = Path(tmp) / "pipeline.csv"
                    report = Path(tmp) / "pipeline.md"
                    transport = load_mock_transport_fixture(FIXTURE_DIR / "pipeline_success.json")

                    result = run_dry_run_recent_search_pipeline(
                        output_path=output,
                        report_path=report,
                        transport=transport,
                        source_genre="ai_side_business",
                        dry_run=True,
                        reference_now=TEST_REFERENCE_NOW,
                        mock_error_type=error_type,
                    )
                    report_text = report.read_text(encoding="utf-8")
                    output_exists = output.exists()

                summary = result.redacted_live_summary
                self.assertEqual(result.fetch_result.posts, [])
                self.assertEqual(result.ranked_rows, [])
                self.assertFalse(output_exists)
                self.assertEqual(getattr(transport, "sent_queries", []), [])
                self.assertEqual(summary.status, "error")
                self.assertEqual(summary.stop_reason, error_type)
                self.assertEqual(summary.result_count, 0)
                self.assertEqual(summary.normalized_post_count, 0)
                self.assertEqual(summary.fetched_count, 0)
                self.assertEqual(summary.retryable, error_type in retryable_by_type)
                self.assertEqual(summary.partial_result, error_type in partial_by_type)
                if error_type == "rate_limited":
                    self.assertTrue(summary.rate_limited)
                    self.assertEqual(summary.retry_after_seconds, 120)
                    self.assertEqual(summary.status_code, 429)
                else:
                    self.assertFalse(summary.rate_limited)
                self.assertIn("Redacted Live Summary", report_text)
                self.assertIn(summary.safe_debug_summary(), report_text)
                self.assertIn("No posts ranked.", report_text)
                self.assertFalse(contains_sensitive_marker(report_text), report_text)
                self.assertFalse(contains_sensitive_marker(result.debug_log), result.debug_log)
                self.assertNotIn("mock timeout", report_text)
                self.assertNotIn("mock network error", report_text)
                self.assertNotIn("mock auth error", report_text)
                self.assertNotIn("Non-engineer AI workflow", report_text)
                self.assertNotIn("pipeline_ai_top", report_text)
                self.assertNotIn("4001", report_text)

    def test_credential_leak_regression_for_debug_report_csv_and_exception(self) -> None:
        secret_config = {
            "source_genre": "ai_side_business",
            "search_queries": ["AI workflow"],
            "api_key": "API_KEY_SHOULD_NOT_APPEAR",
            "token": "TOKEN_SHOULD_NOT_APPEAR",
            "bearer": "BEARER_SHOULD_NOT_APPEAR",
            "secret": "SECRET_SHOULD_NOT_APPEAR",
            "cookie": "COOKIE_SHOULD_NOT_APPEAR",
            "authorization": "AUTHORIZATION_SHOULD_NOT_APPEAR",
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pipeline.csv"
            report = Path(tmp) / "pipeline.md"
            transport = MockRecentSearchTransport(load_fixture("pipeline_success.json"))

            result = run_dry_run_recent_search_pipeline(
                output_path=output,
                report_path=report,
                transport=transport,
                source_genre="ai_side_business",
                dry_run=True,
            )
            csv_text = output.read_text(encoding="utf-8")
            report_text = report.read_text(encoding="utf-8")

        safe_summary = result.redacted_live_summary.safe_debug_summary()
        self.assertFalse(contains_sensitive_marker(result.debug_log), result.debug_log)
        self.assertFalse(contains_sensitive_marker(safe_summary), safe_summary)
        self.assertFalse(contains_sensitive_marker(report_text), report_text)
        self.assertFalse(contains_sensitive_marker(csv_text), csv_text)
        self.assertFalse(contains_sensitive_marker(redact_sensitive_text("AUTHORIZATION=Bearer TOKEN_SHOULD_NOT_APPEAR")))

        with self.assertRaises(RuntimeError) as ctx:
            XApiBuzzReadClient(dry_run=False).fetch_posts(secret_config)
        self.assertFalse(contains_sensitive_marker(str(ctx.exception)), str(ctx.exception))

        with self.assertRaises(RuntimeError) as ctx:
            run_dry_run_recent_search_pipeline(
                transport=MockRecentSearchTransport(load_fixture("pipeline_success.json")),
                dry_run=False,
            )
        self.assertFalse(contains_sensitive_marker(str(ctx.exception)), str(ctx.exception))

    def test_cli_dry_run_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pipeline.csv"
            report = Path(tmp) / "pipeline.md"

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = pipeline_cli_main(
                    [
                        "--dry-run",
                        "--fixture",
                        str(FIXTURE_DIR / "pipeline_success.json"),
                        "--output",
                        str(output),
                        "--report",
                        str(report),
                        "--genre",
                        "ai_side_business",
                        "--reference-now",
                        TEST_REFERENCE_NOW.isoformat(),
                    ]
                )

        self.assertEqual(exit_code, 0)
        cli_text = stdout.getvalue()
        self.assertIn("RedactedLiveSummary:", cli_text)
        self.assertFalse(contains_sensitive_marker(cli_text), cli_text)
        self.assertNotIn("Non-engineer AI workflow", cli_text)
        self.assertNotIn("pipeline_ai_top", cli_text)
        self.assertNotIn("4001", cli_text)

    def test_cli_synthetic_error_modes(self) -> None:
        for error_type in ("rate_limited", "timeout", "auth_error"):
            with self.subTest(error_type=error_type):
                with tempfile.TemporaryDirectory() as tmp:
                    output = Path(tmp) / "pipeline.csv"
                    report = Path(tmp) / "pipeline.md"

                    stdout = io.StringIO()
                    with contextlib.redirect_stdout(stdout):
                        exit_code = pipeline_cli_main(
                            [
                                "--dry-run",
                                "--fixture",
                                str(FIXTURE_DIR / "pipeline_success.json"),
                                "--output",
                                str(output),
                                "--report",
                                str(report),
                                "--genre",
                                "ai_side_business",
                                "--reference-now",
                                TEST_REFERENCE_NOW.isoformat(),
                                "--mock-error-type",
                                error_type,
                            ]
                        )
                    report_text = report.read_text(encoding="utf-8")
                    output_exists = output.exists()

                cli_text = stdout.getvalue()
                self.assertEqual(exit_code, 0)
                self.assertFalse(output_exists)
                self.assertIn("DRY-RUN recent search pipeline complete.", cli_text)
                self.assertIn("RedactedLiveSummary:", cli_text)
                self.assertIn('"status":"error"', cli_text)
                self.assertIn(f'"stop_reason":"{error_type}"', cli_text)
                self.assertIn("CSV: not written", cli_text)
                self.assertIn("No X API call, credential lookup, .env edit, or posting was performed.", cli_text)
                self.assertFalse(contains_sensitive_marker(cli_text), cli_text)
                self.assertFalse(contains_sensitive_marker(report_text), report_text)
                self.assertNotIn("Non-engineer AI workflow", cli_text)
                self.assertNotIn("pipeline_ai_top", cli_text)
                self.assertNotIn("4001", cli_text)
                self.assertNotIn("mock timeout", report_text)
                self.assertNotIn("mock auth error", report_text)

    def test_pipeline_generated_csv_is_gitignored(self) -> None:
        ignored = subprocess.run(
            [
                "git",
                "check-ignore",
                "data/mock_recent_search_pipeline_posts.csv",
                "data/mock_recent_search_pipeline_posts_20260531.csv",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(ignored.returncode, 0, ignored.stderr)


if __name__ == "__main__":
    unittest.main()
