import unittest
from argparse import Namespace
from datetime import datetime

from main import run
from src.output_writer import ROOT, build_output_filename, save_cli_output


class OutputSavingTest(unittest.TestCase):
    def test_save_output_writes_markdown_to_outputs_local(self):
        content = "【一番おすすめ】\nテスト文\n\n【安全チェック結果】\n- OK"

        path = save_cli_output("generate-first", content, target_path="data/examples/sample_target_cafe_movie.yaml")

        self.assertEqual(path.parent, ROOT / "outputs" / "local")
        self.assertTrue(path.name.startswith("generate_first_sample_target_cafe_movie_"))
        self.assertEqual(path.suffix, ".md")
        saved = path.read_text(encoding="utf-8")
        self.assertIn("【一番おすすめ】", saved)
        self.assertIn("【安全チェック結果】", saved)
        path.unlink()

    def test_reports_latest_report_is_not_changed_by_save_output(self):
        report = ROOT / "reports" / "latest_report.md"
        before = report.read_text(encoding="utf-8") if report.exists() else ""

        path = save_cli_output("review", "OK\n- テスト")

        after = report.read_text(encoding="utf-8") if report.exists() else ""
        self.assertEqual(before, after)
        path.unlink()

    def test_build_output_filename_includes_command_target_and_timestamp(self):
        name = build_output_filename("generate-reply", "data/examples/sample_target_cafe_movie.yaml")

        self.assertTrue(name.startswith("generate_reply_sample_target_cafe_movie_"))
        self.assertTrue(name.endswith(".md"))

    def test_same_second_saves_do_not_overwrite_existing_file(self):
        now = datetime(2026, 6, 5, 23, 15, 0)
        first = save_cli_output("generate-first", "first", "data/examples/sample_target_cafe_movie.yaml", now=now)
        second = save_cli_output("generate-first", "second", "data/examples/sample_target_cafe_movie.yaml", now=now)

        self.assertNotEqual(first, second)
        self.assertTrue(first.exists())
        self.assertTrue(second.exists())
        self.assertEqual("first", first.read_text(encoding="utf-8"))
        self.assertEqual("second", second.read_text(encoding="utf-8"))
        self.assertTrue(second.stem.endswith("_2"))
        first.unlink()
        second.unlink()

    def test_cli_save_output_returns_visible_saved_path(self):
        args = Namespace(
            command="generate-first",
            target="data/examples/sample_target_cafe_movie.yaml",
            history=None,
            stage="auto",
            flirt_level=None,
            save_output=True,
        )

        output = run(args)

        self.assertIn("保存しました:", output)
        self.assertIn("outputs/local/generate_first_sample_target_cafe_movie_", output)
        saved_relative = output.split("保存しました:\n", 1)[1].strip()
        saved_path = ROOT / saved_relative
        self.assertTrue(saved_path.exists())
        saved_path.unlink()

    def test_cli_without_save_output_does_not_show_saved_path(self):
        args = Namespace(
            command="generate-first",
            target="data/examples/sample_target_cafe_movie.yaml",
            history=None,
            stage="auto",
            flirt_level=None,
            save_output=False,
        )

        output = run(args)

        self.assertNotIn("保存しました:", output)


if __name__ == "__main__":
    unittest.main()

