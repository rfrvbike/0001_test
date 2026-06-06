from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from x_auto_ops.reference_posts import (
    MAX_LIMIT,
    analyze_reference_posts,
    calculate_score,
    clamp_limit,
    collect_reference_posts,
    exclusion_reason,
    generate_reference_report,
    read_source_accounts,
    score_reference_posts,
)


class FailingXClient:
    def get_user_id(self, handle: str) -> str:
        raise AssertionError(f"external API should not be called for {handle}")

    def get_recent_posts(self, user_id: str, limit: int) -> list[dict[str, str]]:
        raise AssertionError(f"external API should not be called for {user_id}")


class ReferencePostsTests(unittest.TestCase):
    def test_read_source_accounts_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source_accounts.csv"
            path.write_text(
                "handle,category,priority,note\n"
                "@kiwamiamaama,恋愛,high,女性向けの刺さる言葉\n",
                encoding="utf-8",
            )

            accounts = read_source_accounts(path)

        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].handle, "kiwamiamaama")
        self.assertEqual(accounts[0].category, "恋愛")

    def test_calculate_score(self) -> None:
        row = {
            "like_count": "10",
            "repost_count": "3",
            "reply_count": "4",
            "quote_count": "5",
        }

        self.assertEqual(calculate_score(row), 37)

    def test_exclusion_logic(self) -> None:
        self.assertEqual(exclusion_reason({"text": "https://example.com"}), "link_only")
        self.assertEqual(exclusion_reason({"text": "RT @someone 長い本文です" * 3}), "repost")
        self.assertEqual(exclusion_reason({"text": "@someone 返信として十分長い本文です"}), "reply")
        self.assertEqual(exclusion_reason({"text": "登録すると無料で限定セミナーに参加できます"}), "promotional")
        self.assertIsNone(
            exclusion_reason(
                {
                    "text": (
                        "返信が来ない夜に何度もスマホを見てしまう。"
                        "平気なふりをしているだけで本当は苦しかった。"
                    )
                }
            )
        )

    def test_collect_dry_run_never_calls_external_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "raw_posts.csv"
            result = collect_reference_posts(
                source_path=Path(tmp) / "missing_source.csv",
                output_path=output,
                limit=2,
                dry_run=True,
                client=FailingXClient(),
            )

            with output.open(encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))

        self.assertEqual(result.collected_posts, 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["source_handle"], "kiwamiamaama")

    def test_collect_non_dry_run_is_blocked_without_explicit_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "raw_posts.csv"
            with self.assertRaisesRegex(RuntimeError, "Live X collection is not implemented"):
                collect_reference_posts(
                    source_path=Path(tmp) / "missing_source.csv",
                    output_path=output,
                    limit=2,
                    dry_run=False,
                    client=FailingXClient(),
                )

    def test_limit_cap_is_enforced(self) -> None:
        self.assertEqual(clamp_limit(MAX_LIMIT), MAX_LIMIT)
        with self.assertRaises(ValueError):
            clamp_limit(MAX_LIMIT + 1)

    def test_score_posts_filters_and_writes_scored_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.csv"
            scored = Path(tmp) / "scored.csv"
            with raw.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(
                    fh,
                    fieldnames=[
                        "source_handle",
                        "post_id",
                        "post_url",
                        "text",
                        "created_at",
                        "like_count",
                        "repost_count",
                        "reply_count",
                        "quote_count",
                        "impression_count",
                        "category",
                        "collected_at",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "source_handle": "a",
                        "post_id": "1",
                        "text": "返信を待つ夜に何度もスマホを見てしまう。平気なふりをしているだけで本当は苦しい。",
                        "like_count": "10",
                        "repost_count": "3",
                        "reply_count": "4",
                        "quote_count": "5",
                        "impression_count": "1000",
                        "category": "恋愛",
                    }
                )
                writer.writerow({"source_handle": "a", "post_id": "2", "text": "短い"})

            result = score_reference_posts(input_path=raw, output_path=scored)
            with scored.open(encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))

        self.assertEqual(result.input_count, 2)
        self.assertEqual(result.scored_count, 1)
        self.assertEqual(result.excluded_count, 1)
        self.assertEqual(rows[0]["score"], "37")
        self.assertEqual(rows[0]["engagement_rate"], "0.022000")

    def test_mock_llm_dry_run_and_report_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.csv"
            scored = Path(tmp) / "scored.csv"
            analyzed = Path(tmp) / "analyzed.jsonl"
            report = Path(tmp) / "report.md"
            collect_reference_posts(
                source_path=Path(tmp) / "missing.csv",
                output_path=raw,
                limit=3,
                dry_run=True,
                client=FailingXClient(),
            )
            score_reference_posts(input_path=raw, output_path=scored)

            result = analyze_reference_posts(
                input_path=scored,
                output_path=analyzed,
                top_n=2,
                dry_run=True,
                mock_llm=True,
            )
            generate_reference_report(
                raw_path=raw,
                scored_path=scored,
                analyzed_path=analyzed,
                output_path=report,
            )
            analyses = [
                json.loads(line)
                for line in analyzed.read_text(encoding="utf-8").splitlines()
            ]
            report_text = report.read_text(encoding="utf-8")

        self.assertEqual(result.analyzed_count, 2)
        self.assertEqual(len(analyses), 2)
        self.assertIn("target", analyses[0])
        self.assertIn("Collected accounts: 1", report_text)
        self.assertIn("Similarity Risk", report_text)

    def test_provider_analysis_is_blocked_without_explicit_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scored = Path(tmp) / "scored.csv"
            analyzed = Path(tmp) / "analyzed.jsonl"
            with scored.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(
                    fh,
                    fieldnames=[
                        "source_handle",
                        "post_id",
                        "text",
                        "score",
                        "category",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "source_handle": "a",
                        "post_id": "1",
                        "text": "sample structure text for provider guard",
                        "score": "10",
                        "category": "romance",
                    }
                )

            with self.assertRaisesRegex(RuntimeError, "Provider analysis is disabled"):
                analyze_reference_posts(
                    input_path=scored,
                    output_path=analyzed,
                    top_n=1,
                    dry_run=False,
                    mock_llm=False,
                    settings={"TEXT_LLM_PROVIDER": "openai"},
                    clients=None,
                )


if __name__ == "__main__":
    unittest.main()
