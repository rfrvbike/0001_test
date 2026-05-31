from __future__ import annotations

import csv
import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.mock_buzz_collector import main as mock_buzz_cli_main
from x_auto_ops.buzz_read_client import MockBuzzReadClient, XApiBuzzReadClient
from x_auto_ops.mock_buzz_collector import (
    CSV_FIELDS,
    calculate_score,
    collect_mock_buzz_posts,
    detect_genre,
    filter_posts,
    generate_mock_posts,
    load_genre_config,
    rank_posts_by_genre,
    write_posts_csv,
)


def write_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "min_genre_score": 1,
                "tie_break_priority": ["yokaze", "ai_side_business", "daily"],
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
                        "detection_keywords": ["night", "hurt", "relationship", "lonely"],
                        "min_likes": 200,
                    },
                    {
                        "id": "ai_side_business",
                        "keywords": ["ai"],
                        "detection_keywords": ["ai", "side business", "automation", "paper"],
                        "min_reposts": 20,
                    },
                    {
                        "id": "daily",
                        "keywords": ["daily"],
                        "detection_keywords": ["daily", "coffee", "sunday night", "room"],
                        "days_back": 3,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


class MockBuzzCollectorTests(unittest.TestCase):
    def test_generated_outputs_and_local_config_are_gitignored(self) -> None:
        ignored = subprocess.run(
            [
                "git",
                "check-ignore",
                "data/mock_buzz_posts.csv",
                "data/mock_buzz_posts_yokaze.csv",
                "data/x_buzz_genres.json",
            ],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(ignored.returncode, 0, ignored.stderr)
        self.assertIn("data/mock_buzz_posts.csv", ignored.stdout)
        self.assertIn("data/mock_buzz_posts_yokaze.csv", ignored.stdout)
        self.assertIn("data/x_buzz_genres.json", ignored.stdout)

        example = subprocess.run(
            ["git", "check-ignore", "data/x_buzz_genres.json.example"],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(example.returncode, 0)

    def test_load_genre_config_merges_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            write_config(config)

            genres = load_genre_config(config)

        self.assertEqual([genre.id for genre in genres], ["yokaze", "ai_side_business", "daily"])
        self.assertEqual(genres[0].min_likes, 200)
        self.assertEqual(genres[0].min_reposts, 10)
        self.assertEqual(genres[2].days_back, 3)
        self.assertIn("relationship", genres[0].detection_keywords)
        self.assertEqual(genres[0].min_genre_score, 1)
        self.assertEqual(genres[0].tie_break_priority[0], "yokaze")

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

        self.assertEqual(len(rows), 9)
        self.assertTrue(all(int(row["buzz_score"]) > 0 for row in rows))
        self.assertNotIn("mock-yokaze-low", {row["post_id"] for row in rows})
        self.assertNotIn("mock-yokaze-old", {row["post_id"] for row in rows})
        self.assertIn("mock-unknown-general", {row["post_id"] for row in rows})

    def test_detect_genre_classifies_yokaze_post(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            write_config(config)
            genres = load_genre_config(config)

            result = detect_genre(
                "A hurt person feels lonely at night after a relationship.",
                genres,
            )

        self.assertEqual(result.genre, "yokaze")
        self.assertGreater(result.score, 0)

    def test_detect_genre_classifies_ai_side_business_post(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            write_config(config)
            genres = load_genre_config(config)

            result = detect_genre(
                "AI automation turns a paper into a side business workflow.",
                genres,
            )

        self.assertEqual(result.genre, "ai_side_business")

    def test_detect_genre_classifies_daily_post(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            write_config(config)
            genres = load_genre_config(config)

            result = detect_genre(
                "Sunday night coffee in a small room before work.",
                genres,
            )

        self.assertEqual(result.genre, "daily")

    def test_detect_genre_returns_unknown_without_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            write_config(config)
            genres = load_genre_config(config)

            result = detect_genre("Plain unrelated update with no signal.", genres)

        self.assertEqual(result.genre, "unknown")
        self.assertIn("below min_genre_score", result.reason)

    def test_detect_genre_returns_unknown_below_min_genre_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            write_config(config)
            data = json.loads(config.read_text(encoding="utf-8"))
            data["min_genre_score"] = 2
            config.write_text(json.dumps(data), encoding="utf-8")
            genres = load_genre_config(config)

            result = detect_genre("Only night appears once.", genres)

        self.assertEqual(result.genre, "unknown")
        self.assertEqual(result.score, 1)

    def test_detect_genre_uses_highest_score_for_mixed_post(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            write_config(config)
            genres = load_genre_config(config)

            result = detect_genre(
                "Coffee before work, then AI automation summarizes a paper for a side business.",
                genres,
            )

        self.assertEqual(result.genre, "ai_side_business")

    def test_detect_genre_tie_uses_tie_break_priority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            write_config(config)
            data = json.loads(config.read_text(encoding="utf-8"))
            data["tie_break_priority"] = ["daily", "ai_side_business", "yokaze"]
            config.write_text(json.dumps(data), encoding="utf-8")
            genres = load_genre_config(config)

            result = detect_genre("night coffee", genres)

        self.assertEqual(result.genre, "daily")
        self.assertIn("tie among", result.reason)

    def test_detect_genre_tie_without_priority_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            write_config(config)
            data = json.loads(config.read_text(encoding="utf-8"))
            data["tie_break_priority"] = ["missing_genre"]
            config.write_text(json.dumps(data), encoding="utf-8")
            genres = load_genre_config(config)

            first = detect_genre("night coffee", genres)
            second = detect_genre("night coffee", genres)

        self.assertEqual(first.genre, "yokaze")
        self.assertEqual(second.genre, "yokaze")

    def test_rank_posts_by_genre_adds_rank_by_buzz_score(self) -> None:
        rows = rank_posts_by_genre(
            [
                {"detected_genre": "daily", "post_id": "low", "buzz_score": 10},
                {"detected_genre": "daily", "post_id": "high", "buzz_score": 30},
                {"detected_genre": "yokaze", "post_id": "other", "buzz_score": 20},
            ]
        )

        daily_rows = [row for row in rows if row["detected_genre"] == "daily"]
        self.assertEqual([row["post_id"] for row in daily_rows], ["high", "low"])
        self.assertEqual([row["rank_in_genre"] for row in daily_rows], [1, 2])

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
                        "detected_genre": "daily",
                        "genre_score": 1,
                        "genre_reason": "matched: daily",
                        "buzz_score": 25,
                        "rank_in_genre": 1,
                        "created_at": "2026-05-30T00:00:00+00:00",
                    }
                ],
            )

            with output.open(encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)

        self.assertEqual(reader.fieldnames, CSV_FIELDS)
        self.assertEqual(rows[0]["post_id"], "p1")
        self.assertEqual(rows[0]["detected_genre"], "daily")

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

        self.assertEqual(result.generated_count, 15)
        self.assertEqual(result.filtered_count, 9)
        self.assertEqual(len(rows), 9)
        self.assertIn("Genre Summary", report_text)
        self.assertIn("Genre Rankings", report_text)
        self.assertIn("Buzz Score Top Posts", report_text)

    def test_collect_mock_buzz_posts_supports_genre_filter(self) -> None:
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
                genre_filter="yokaze",
                now=datetime(2026, 5, 30, tzinfo=timezone.utc),
            )

            with output.open(encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))

        self.assertEqual(result.filtered_count, 3)
        self.assertEqual({row["detected_genre"] for row in rows}, {"yokaze"})

    def test_mock_buzz_read_client_fetches_posts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            write_config(config)
            genres = load_genre_config(config)
            client = MockBuzzReadClient(
                post_factory=generate_mock_posts,
                now=datetime(2026, 5, 30, tzinfo=timezone.utc),
            )

            posts = client.fetch_posts(genres)

        self.assertEqual(len(posts), 15)
        self.assertIn("post_id", posts[0])

    def test_x_api_buzz_read_client_placeholder_errors_without_api_call(self) -> None:
        with self.assertRaises(NotImplementedError):
            XApiBuzzReadClient().fetch_posts([])

    def test_cli_dry_run_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            output = Path(tmp) / "out.csv"
            report = Path(tmp) / "report.md"
            write_config(config)

            exit_code = mock_buzz_cli_main(
                [
                    "--dry-run",
                    "--config",
                    str(config),
                    "--output",
                    str(output),
                    "--report",
                    str(report),
                ]
            )

        self.assertEqual(exit_code, 0)

    def test_live_mode_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "genres.json"
            write_config(config)

            with self.assertRaises(RuntimeError):
                collect_mock_buzz_posts(config_path=config, dry_run=False)


if __name__ == "__main__":
    unittest.main()
