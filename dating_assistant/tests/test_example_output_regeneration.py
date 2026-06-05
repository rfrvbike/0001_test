import unittest

from tools.regenerate_example_outputs import FIRST_SAMPLES, REPLY_SAMPLES, ROOT


class ExampleOutputRegenerationTest(unittest.TestCase):
    def test_expected_example_outputs_are_declared(self):
        expected = {
            "generate_first_travel_active.md",
            "generate_first_cafe_movie.md",
            "generate_first_fashion_beauty.md",
            "generate_first_drink_night.md",
            "generate_reply_movie.md",
            "generate_reply_cafe.md",
            "generate_reply_drink.md",
            "generate_reply_short.md",
            "generate_reply_multi_topic.md",
        }

        self.assertEqual(expected, set(FIRST_SAMPLES) | set(REPLY_SAMPLES))

    def test_declared_outputs_use_examples_directory_not_local(self):
        output_dir = ROOT / "outputs" / "examples"

        self.assertEqual(output_dir.name, "examples")
        self.assertNotEqual(output_dir.name, "local")

    def test_regeneration_result_shape_includes_diff_summary_fields(self):
        from tools.regenerate_example_outputs import _write
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            first = _write(path, "before")
            second = _write(path, "after")

            self.assertEqual((path, 0, 6, True), first)
            self.assertEqual((path, 6, 5, True), second)

    def test_dry_run_does_not_write_file_but_reports_change(self):
        from tools.regenerate_example_outputs import _write
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            result = _write(path, "planned", dry_run=True)

            self.assertEqual((path, 0, 7, True), result)
            self.assertFalse(path.exists())

    def test_summary_counts_match_results(self):
        results = [
            ("a", 1, 2, True),
            ("b", 2, 2, False),
            ("c", 3, 4, True),
        ]

        self.assertEqual(3, len(results))
        self.assertEqual(2, sum(1 for *_, changed in results if changed))


if __name__ == "__main__":
    unittest.main()
