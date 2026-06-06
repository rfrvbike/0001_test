from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from x_auto_ops.manual_reference_import import (
    extract_handle_from_url,
    extract_post_id_from_url,
    import_manual_reference_posts,
    normalize_count,
)
from x_auto_ops.reference_posts import RAW_POST_FIELDS


FIELDS = [
    "source_handle",
    "post_url",
    "text",
    "created_at",
    "like_count",
    "repost_count",
    "reply_count",
    "quote_count",
    "impression_count",
    "category",
    "note",
]


def write_manual_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


class ManualReferencePostsImportTests(unittest.TestCase):
    def test_extract_post_id_and_handle_from_url(self) -> None:
        url = "https://x.com/yokaze_ref/status/1234567890123456789"

        self.assertEqual(extract_post_id_from_url(url), "1234567890123456789")
        self.assertEqual(extract_handle_from_url(url), "yokaze_ref")

    def test_missing_count_fields_are_zero_filled(self) -> None:
        self.assertEqual(normalize_count(""), "0")
        self.assertEqual(normalize_count(None), "0")
        self.assertEqual(normalize_count("1,234"), "1234")
        self.assertEqual(normalize_count("bad"), "0")

    def test_import_converts_to_raw_posts_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "manual.csv"
            output_path = Path(tmp) / "raw_posts.csv"
            write_manual_csv(
                input_path,
                [
                    {
                        "source_handle": "",
                        "post_url": "https://x.com/work_ref/status/987654321",
                        "text": "職場では笑っていたのに、家に帰った瞬間に何もできなくなる夜がある。",
                        "created_at": "2026-05-21T22:30:00+09:00",
                        "like_count": "830",
                        "repost_count": "",
                        "reply_count": "21",
                        "quote_count": "",
                        "impression_count": "",
                        "category": "仕事・人間関係・孤独",
                        "note": "sample",
                    }
                ],
            )

            result = import_manual_reference_posts(
                input_path=input_path,
                output_path=output_path,
                dry_run=False,
                now=datetime(2026, 5, 28, tzinfo=timezone.utc),
            )
            with output_path.open(encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))

        self.assertEqual(result.imported_count, 1)
        self.assertEqual(rows[0].keys(), set(RAW_POST_FIELDS))
        self.assertEqual(rows[0]["source_handle"], "work_ref")
        self.assertEqual(rows[0]["post_id"], "987654321")
        self.assertEqual(rows[0]["repost_count"], "0")
        self.assertEqual(rows[0]["quote_count"], "0")
        self.assertEqual(rows[0]["impression_count"], "0")

    def test_category_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "manual.csv"
            output_path = Path(tmp) / "raw_posts.csv"
            write_manual_csv(
                input_path,
                [
                    {
                        "post_url": "https://x.com/a/status/1",
                        "text": "返信を待つ夜に何度もスマホを見てしまう。平気なふりをしているだけで苦しい。",
                        "category": "",
                    }
                ],
            )

            with self.assertRaises(ValueError):
                import_manual_reference_posts(
                    input_path=input_path,
                    output_path=output_path,
                    dry_run=True,
                )

    def test_duplicate_url_is_warned_and_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "manual.csv"
            output_path = Path(tmp) / "raw_posts.csv"
            row = {
                "post_url": "https://x.com/a/status/1",
                "text": "返信を待つ夜に何度もスマホを見てしまう。平気なふりをしているだけで苦しい。",
                "category": "恋愛",
            }
            write_manual_csv(input_path, [row, row])

            result = import_manual_reference_posts(
                input_path=input_path,
                output_path=output_path,
                dry_run=True,
            )

        self.assertEqual(result.input_count, 2)
        self.assertEqual(result.imported_count, 1)
        self.assertEqual(result.duplicate_count, 1)
        self.assertTrue(any("duplicate post_url" in warning for warning in result.warnings))

    def test_missing_post_id_generates_manual_id_and_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "manual.csv"
            output_path = Path(tmp) / "raw_posts.csv"
            write_manual_csv(
                input_path,
                [
                    {
                        "post_url": "https://example.com/reference",
                        "text": "相談できず一人で抱えてしまう夜ほど、誰かに気づいてほしい気持ちが残る。",
                        "category": "仕事・人間関係・孤独",
                    }
                ],
            )

            result = import_manual_reference_posts(
                input_path=input_path,
                output_path=output_path,
                dry_run=True,
            )

        self.assertEqual(result.rows[0]["post_id"], "manual_0001")
        self.assertEqual(result.rows[0]["source_handle"], "manual")
        self.assertTrue(any("post_id not found" in warning for warning in result.warnings))

    def test_short_text_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "manual.csv"
            output_path = Path(tmp) / "raw_posts.csv"
            write_manual_csv(
                input_path,
                [
                    {
                        "post_url": "https://x.com/a/status/1",
                        "text": "短い投稿",
                        "category": "恋愛",
                    }
                ],
            )

            result = import_manual_reference_posts(
                input_path=input_path,
                output_path=output_path,
                dry_run=True,
            )

        self.assertTrue(any("text is short" in warning for warning in result.warnings))

    def test_dry_run_does_not_write_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "manual.csv"
            output_path = Path(tmp) / "raw_posts.csv"
            output_path.write_text("keep me", encoding="utf-8")
            write_manual_csv(
                input_path,
                [
                    {
                        "post_url": "https://x.com/a/status/1",
                        "text": "返信を待つ夜に何度もスマホを見てしまう。平気なふりをしているだけで苦しい。",
                        "category": "恋愛",
                    }
                ],
            )

            import_manual_reference_posts(
                input_path=input_path,
                output_path=output_path,
                dry_run=True,
            )

            self.assertEqual(output_path.read_text(encoding="utf-8"), "keep me")


if __name__ == "__main__":
    unittest.main()
