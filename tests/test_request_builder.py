from __future__ import annotations

import csv
import io
import tempfile
import unittest
from pathlib import Path

from x_auto_ops.credential_loader import (
    FAKE_API_KEY,
    FAKE_API_SECRET,
    FAKE_BEARER_TOKEN,
    FakeCredentialLoader,
)
from x_auto_ops.dry_run_recent_search_pipeline import (
    load_mock_transport_fixture,
    run_dry_run_recent_search_pipeline,
)
from x_auto_ops.mock_transport import contains_sensitive_marker
from x_auto_ops.query_builder import build_recent_search_query
from x_auto_ops.request_builder import (
    DEFAULT_RECENT_SEARCH_ENDPOINT,
    RequestBuildError,
    build_recent_search_request,
)


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _render_csv(text: str) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["debug"])
    writer.writeheader()
    writer.writerow({"debug": text})
    return output.getvalue()


class RequestBuilderTests(unittest.TestCase):
    def test_builds_recent_search_http_request(self) -> None:
        query = build_recent_search_query(
            {
                "source_genre": "ai_side_business",
                "search_queries": ["AI workflow"],
            }
        )
        credentials = FakeCredentialLoader().load()

        result = build_recent_search_request(
            query=query,
            credential_bundle=credentials,
            config={"timeout_seconds": 7},
        )

        self.assertEqual(result.endpoint_name, "recent_search")
        self.assertEqual(result.request.method, "GET")
        self.assertEqual(result.request.url, DEFAULT_RECENT_SEARCH_ENDPOINT)
        self.assertEqual(result.request.query_params["query"], query.query)
        self.assertEqual(result.request.headers["Authorization"], f"Bearer {FAKE_BEARER_TOKEN}")
        self.assertEqual(result.request.headers["User-Agent"], "x-auto-ops-runtime/0.1 dry-run-prelive")
        self.assertEqual(result.request.headers["Accept"], "application/json")
        self.assertEqual(result.header_names, ("Authorization", "User-Agent", "Accept"))
        self.assertEqual(result.timeout_seconds, 7.0)

    def test_query_builder_to_credential_loader_to_request_builder(self) -> None:
        query = build_recent_search_query(
            {
                "source_genre": "daily",
                "search_queries": ["coffee"],
                "target_accounts": ["daily_author"],
            }
        )
        credentials = FakeCredentialLoader().load()

        result = build_recent_search_request(query=query, credential_bundle=credentials)

        self.assertIn("coffee", result.query)
        self.assertIn("from:daily_author", result.query)
        self.assertEqual(result.request.query_params["tweet.fields"], "created_at,public_metrics,author_id")
        self.assertEqual(result.request.query_params["expansions"], "author_id")
        self.assertEqual(result.request.query_params["user.fields"], "username")

    def test_request_builder_rejects_empty_query_endpoint_and_bad_timeout(self) -> None:
        credentials = FakeCredentialLoader().load()

        with self.assertRaises(RequestBuildError):
            build_recent_search_request(query="", credential_bundle=credentials)
        with self.assertRaises(RequestBuildError):
            build_recent_search_request(query="AI", credential_bundle=credentials, config={"endpoint": ""})
        with self.assertRaises(RequestBuildError):
            build_recent_search_request(query="AI", credential_bundle=credentials, config={"timeout_seconds": 0})
        with self.assertRaises(RequestBuildError):
            build_recent_search_request(query="AI", credential_bundle=credentials, config={"timeout_seconds": "bad"})

    def test_safe_debug_summary_does_not_expose_header_values_or_sensitive_markers(self) -> None:
        credentials = FakeCredentialLoader().load()
        result = build_recent_search_request(query="AI lang:ja", credential_bundle=credentials)

        debug = result.safe_debug_summary()

        self.assertNotIn(FAKE_BEARER_TOKEN, debug)
        self.assertNotIn("Bearer", debug)
        self.assertNotIn("Authorization", debug)
        self.assertFalse(contains_sensitive_marker(debug), debug)

    def test_authorization_value_does_not_leak_to_report_csv_debug_or_exception(self) -> None:
        credentials = FakeCredentialLoader().load()
        result = build_recent_search_request(query="AI lang:ja", credential_bundle=credentials)
        debug = result.safe_debug_summary()
        csv_text = _render_csv(debug)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pipeline.csv"
            report = Path(tmp) / "pipeline.md"
            pipeline = run_dry_run_recent_search_pipeline(
                output_path=output,
                report_path=report,
                transport=load_mock_transport_fixture(FIXTURE_DIR / "pipeline_success.json"),
                source_genre="ai_side_business",
                dry_run=True,
            )
            report_text = report.read_text(encoding="utf-8")
            pipeline_csv = output.read_text(encoding="utf-8")
        try:
            build_recent_search_request(
                query="AI",
                credential_bundle=credentials,
                config={"timeout_seconds": "bad"},
            )
        except RequestBuildError as exc:
            exception_text = str(exc)
        else:  # pragma: no cover
            self.fail("expected RequestBuildError")

        combined = "\n".join([debug, csv_text, report_text, pipeline_csv, pipeline.debug_log, exception_text])
        self.assertNotIn(FAKE_BEARER_TOKEN, combined)
        self.assertNotIn(FAKE_API_KEY, combined)
        self.assertNotIn(FAKE_API_SECRET, combined)
        self.assertNotIn("Bearer", combined)
        self.assertNotIn("Authorization", combined)
        self.assertFalse(contains_sensitive_marker(combined), combined)


if __name__ == "__main__":
    unittest.main()
