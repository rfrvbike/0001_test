from __future__ import annotations

import inspect
import re
import tempfile
import unittest
from pathlib import Path

from x_auto_ops.credential_loader import (
    FAKE_API_KEY,
    FAKE_API_SECRET,
    FAKE_BEARER_TOKEN,
    CredentialBundle,
    FakeCredentialLoader,
    select_credential_loader,
)
from x_auto_ops.dry_run_recent_search_pipeline import (
    load_mock_transport_fixture,
    run_dry_run_recent_search_pipeline,
)
from x_auto_ops.live_mode_gate import assert_live_mode_allowed
from x_auto_ops.mock_transport import contains_sensitive_marker
from x_auto_ops.real_credential_loader import (
    RealCredentialLoader,
    RealCredentialLoaderDisabledError,
)


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


class CredentialLoaderAndLiveModeGateTests(unittest.TestCase):
    def test_fake_credential_loader_returns_fake_bundle(self) -> None:
        bundle = FakeCredentialLoader().load()

        self.assertIsInstance(bundle, CredentialBundle)
        self.assertEqual(bundle.bearer_token, FAKE_BEARER_TOKEN)
        self.assertEqual(bundle.api_key, FAKE_API_KEY)
        self.assertEqual(bundle.api_secret, FAKE_API_SECRET)
        self.assertEqual(bundle.source, "FAKE")

    def test_fake_credential_loader_does_not_read_files_env_or_environment(self) -> None:
        source = inspect.getsource(FakeCredentialLoader)

        self.assertNotIn("open(", source)
        self.assertNotIn("Path(", source)
        self.assertNotIn(".env", source)
        self.assertNotIn("os.environ", source)
        self.assertNotIn("getenv", source)

    def test_real_credential_loader_is_disabled_and_does_not_read_credentials(self) -> None:
        source = inspect.getsource(RealCredentialLoader)

        self.assertNotIn("open(", source)
        self.assertNotIn("Path(", source)
        self.assertNotIn(".env", source)
        self.assertNotIn("os.environ", source)
        self.assertNotIn("getenv", source)
        with self.assertRaises(RealCredentialLoaderDisabledError) as ctx:
            RealCredentialLoader().load()

        self.assertEqual(str(ctx.exception), "Real credential loader disabled")
        self.assertFalse(contains_sensitive_marker(str(ctx.exception)))

    def test_select_credential_loader_routes_fake_and_real(self) -> None:
        self.assertIsInstance(select_credential_loader({"credential_loader": "fake"}), FakeCredentialLoader)
        self.assertIsInstance(select_credential_loader({"credential_loader": "real"}), RealCredentialLoader)

    def test_select_credential_loader_rejects_unknown_loader(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            select_credential_loader({"credential_loader": "env"})

        self.assertIn("unknown credential loader", str(ctx.exception))
        self.assertFalse(contains_sensitive_marker(str(ctx.exception)))

    def test_live_mode_gate_allows_dry_run(self) -> None:
        assert_live_mode_allowed({"dry_run": True, "live_mode": False})

    def test_live_mode_gate_rejects_live_mode(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            assert_live_mode_allowed({"dry_run": False, "live_mode": True})

        self.assertEqual(str(ctx.exception), "live mode disabled")

    def test_live_mode_gate_rejects_even_with_fake_credentials(self) -> None:
        bundle = FakeCredentialLoader().load()

        with self.assertRaises(RuntimeError) as ctx:
            assert_live_mode_allowed(
                {
                    "dry_run": False,
                    "live_mode": True,
                    "credentials": bundle,
                }
            )

        self.assertEqual(str(ctx.exception), "live mode disabled")
        self.assertNotIn(FAKE_API_KEY, str(ctx.exception))
        self.assertNotIn(FAKE_API_SECRET, str(ctx.exception))
        self.assertNotIn(FAKE_BEARER_TOKEN, str(ctx.exception))

    def test_pipeline_uses_fake_loader_without_leaking_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pipeline.csv"
            report = Path(tmp) / "pipeline.md"
            result = run_dry_run_recent_search_pipeline(
                output_path=output,
                report_path=report,
                transport=load_mock_transport_fixture(FIXTURE_DIR / "pipeline_success.json"),
                source_genre="ai_side_business",
                dry_run=True,
                credential_loader=FakeCredentialLoader(),
            )
            report_text = report.read_text(encoding="utf-8")
            csv_text = output.read_text(encoding="utf-8")

        self.assertEqual(result.credential_source, "FAKE")
        combined = "\n".join([result.debug_log, report_text, csv_text])
        self.assertNotIn(FAKE_API_KEY, combined)
        self.assertNotIn(FAKE_API_SECRET, combined)
        self.assertNotIn(FAKE_BEARER_TOKEN, combined)
        self.assertFalse(contains_sensitive_marker(combined), combined)

    def test_pipeline_with_real_loader_fails_closed_without_leaking_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pipeline.csv"
            report = Path(tmp) / "pipeline.md"
            with self.assertRaises(RealCredentialLoaderDisabledError) as ctx:
                run_dry_run_recent_search_pipeline(
                    output_path=output,
                    report_path=report,
                    transport=load_mock_transport_fixture(FIXTURE_DIR / "pipeline_success.json"),
                    source_genre="ai_side_business",
                    dry_run=True,
                    credential_loader=select_credential_loader({"credential_loader": "real"}),
                )

            self.assertFalse(output.exists())
            self.assertFalse(report.exists())

        self.assertEqual(str(ctx.exception), "Real credential loader disabled")
        self.assertFalse(contains_sensitive_marker(str(ctx.exception)))

    def test_frontend_has_no_x_credential_loader_fields(self) -> None:
        root = Path(__file__).resolve().parents[1]
        frontend_files = list((root / "src").rglob("*.js"))
        frontend_files.extend([root / "index.html", root / "stock-analyzer.html"])
        combined = "\n".join(path.read_text(encoding="utf-8") for path in frontend_files)

        for marker in ("bearer_token", "api_key", "api_secret", "authorization"):
            self.assertIsNone(
                re.search(rf"(?<![a-z0-9_]){re.escape(marker)}(?![a-z0-9_])", combined.lower()),
                marker,
            )

        x_api_key_paths = [
            path.relative_to(root).as_posix()
            for path in frontend_files
            if "x-api-key" in path.read_text(encoding="utf-8").lower()
        ]
        self.assertEqual(
            sorted(x_api_key_paths),
            sorted(
                [
                    "src/logic/aiSummaryMockBuilder.js",
                    "src/logic/preTradeCheckBuilder.js",
                    "src/logic/structuredSummaryBuilder.js",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
