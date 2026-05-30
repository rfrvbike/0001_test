from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from x_auto_ops.mock_buzz_collector import (
    CSV_FIELDS,
    calculate_score,
    collect_mock_buzz_posts,
    filter_posts,
    generate_mock_posts,
    load_genre_config,
    write_posts_csv,
)


def write_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "defaults": {
                    "min_likes": 100,
                    "min_reposts": 10,
                    "min_replies": 1,
                    "min_quotes": 0,
                    "days_back": 7,
                    "score_weights": {
                        "likes": 1,
                        "reposts": 3,
                        "replies": 2,
                        "quotes": 2,
                    },
                },
                "genres": [
                    {
                        "id": "yokaze",
                        "keywords": ["night"],
                        "min_likes": 200,
                    },
                    {
                        "id": "ai_side_business",
                        "keywords": ["ai"],
                        "min_reposts": 20,
                    },
                    {
                        "id": "daily",
                        "keywords": ["daily"],
                        "days_back": 3,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


class MockBuzzCollectorTests(unittest.TestCase):
    def test_load_genre_config_merges_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            write_config(config)

            genres = load_genre_config(config)

        self.assertEqual([genre.id for genre in genres], ["yokaze", "ai_side_business", "daily"])
        self.assertEqual(genres[0].min_likes, 200)
        self.assertEqual(genres[0].min_reposts, 10)
        self.assertEqual(genres[2].days_back, 3)

    def test_calculate_score_uses_weights(self) -> None:
        post = {"likes": 10, "reposts": 3, "replies": 4, "quotes": 5}

        self.assertEqual(calculate_score(post), 37)
        self.assertEqual(
            calculate_score(post, {"likes": 1, "reposts": 10, "replies": 0, "quotes": 0}),
            40,
        )

    def test_filter_posts_applies_thresholds_and_days_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            write_config(config)
            genres = load_genre_config(config)
            now = datetime(2026, 5, 30, tzinfo=timezone.utc)
            posts = generate_mock_posts(genres, now=now)

            rows = filter_posts(posts, genres, now=now)

        self.assertEqual(len(rows), 6)
        self.assertTrue(all(int(row["score"]) > 0 for row in rows))
        self.assertNotIn("mock-yokaze-low", {row["post_id"] for row in rows})
        self.assertNotIn("mock-yokaze-old", {row["post_id"] for row in rows})

    def test_write_posts_csv_preserves_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "mock_buzz_posts.csv"
            write_posts_csv(
                output,
                [
                    {
                        "genre": "daily",
                        "post_id": "p1",
                        "author": "a",
                        "text": "t",
                        "likes": 1,
                        "reposts": 2,
                        "replies": 3,
                        "quotes": 4,
                        "score": 25,
                        "created_at": "2026-05-30T00:00:00+00:00",
                    }
                ],
            )

            with output.open(encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)

        self.assertEqual(reader.fieldnames, CSV_FIELDS)
        self.assertEqual(rows[0]["post_id"], "p1")

    def test_collect_mock_buzz_posts_writes_csv_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            output = Path(tmp) / "mock_buzz_posts.csv"
            report = Path(tmp) / "mock_buzz_report.md"
            write_config(config)

            result = collect_mock_buzz_posts(
                config_path=config,
                output_path=output,
                report_path=report,
                dry_run=True,
                now=datetime(2026, 5, 30, tzinfo=timezone.utc),
            )

            with output.open(encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            report_text = report.read_text(encoding="utf-8")

        self.assertEqual(result.generated_count, 12)
        self.assertEqual(result.filtered_count, 6)
        self.assertEqual(len(rows), 6)
        self.assertIn("Genre Summary", report_text)

    def test_live_mode_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            write_config(config)

            with self.assertRaises(RuntimeError):
                collect_mock_buzz_posts(config_path=config, dry_run=False)


if __name__ == "__main__":
    unittest.main()
