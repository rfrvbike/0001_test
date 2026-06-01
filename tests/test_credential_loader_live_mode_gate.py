from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path

from x_auto_ops.credential_loader import (
    FAKE_API_KEY,
    FAKE_API_SECRET,
    FAKE_BEARER_TOKEN,
    CredentialBundle,
    FakeCredentialLoader,
)
from x_auto_ops.dry_run_recent_search_pipeline import (
    load_mock_transport_fixture,
    run_dry_run_recent_search_pipeline,
)
from x_auto_ops.live_mode_gate import assert_live_mode_allowed
from x_auto_ops.mock_transport import contains_sensitive_marker


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


if __name__ == "__main__":
    unittest.main()
