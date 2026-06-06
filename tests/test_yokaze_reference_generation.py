from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from x_auto_ops.provider_routing import ProviderClients
from x_auto_ops.yokaze_reference_generation import (
    assess_similarity_risk,
    generate_yokaze_posts_from_reference,
    parse_target_ratio,
    select_analyses,
)


class FailingProvider:
    def clients(self) -> ProviderClients:
        return ProviderClients(
            call_openai_text=self.fail,
            call_gemini_text=self.fail,
        )

    def fail(self, prompt: str, model: str, account_id: str) -> str:
        raise AssertionError("external LLM should not be called in dry-run/mock")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False))
            fh.write("\n")


def sample_rows() -> list[dict[str, object]]:
    return [
        {
            "source_handle": "source",
            "post_id": "love",
            "score": "100",
            "theme": "恋愛",
            "target": "返信を待ってしまう女性",
            "pain": "待つ時間に自分の価値を疑ってしまう傷",
            "hidden_feeling": "少しだけ安心させてほしかった",
        },
        {
            "source_handle": "source",
            "post_id": "work",
            "score": "90",
            "theme": "仕事・人間関係・孤独",
            "target": "職場では笑って家で崩れる女性",
            "pain": "平気な顔を続けすぎて、限界を誰にも気づかれない疲れ",
            "hidden_feeling": "本当は、ちゃんとしなくていい場所がほしかった",
        },
    ]


class YokazeReferenceGenerationTests(unittest.TestCase):
    def test_select_analyses_supports_theme_and_top_n(self) -> None:
        rows = [
            {"theme": "恋愛", "score": "10", "post_id": "a"},
            {"theme": "仕事・人間関係・孤独", "score": "30", "post_id": "b"},
            {"theme": "恋愛", "score": "20", "post_id": "c"},
        ]

        selected = select_analyses(rows, top_n=1, theme="恋愛")

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["post_id"], "c")

    def test_parse_target_ratio(self) -> None:
        self.assertEqual(
            parse_target_ratio("romance:0.7,other:0.3"),
            {"romance": 0.7, "other": 0.3},
        )
        with self.assertRaises(ValueError):
            parse_target_ratio("love:0.7,other:0.3")

    def test_mock_llm_dry_run_outputs_style_and_quality_without_provider_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "analyzed.jsonl"
            output_path = Path(tmp) / "generated.jsonl"
            report_path = Path(tmp) / "report.md"
            write_jsonl(input_path, sample_rows())

            result = generate_yokaze_posts_from_reference(
                input_path=input_path,
                output_path=output_path,
                report_path=report_path,
                top_n=None,
                theme=None,
                dry_run=True,
                mock_llm=True,
                style_pattern="auto",
                target_ratio={"romance": 0.7, "other": 0.3},
                max_same_pattern=2,
                settings={
                    "TEXT_LLM_PROVIDER": "openai",
                    "OPENAI_MODEL": "gpt-test",
                    "GEMINI_MODEL": "gemini-test",
                },
                clients=FailingProvider().clients(),
            )
            generated = [
                json.loads(line)
                for line in output_path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(result.generated_count, 2)
        self.assertIn(generated[0]["style_pattern"], {"daiben", "joukei", "hitei_kaijo", "kioku", "short_yoin"})
        self.assertIn("quality_check", generated[0])
        self.assertIn(generated[0]["image_recommendation"], {"none", "ambient_only", "avoid"})
        self.assertIn(generated[0]["similarity_risk"], {"low", "medium", "high"})
        self.assertGreaterEqual(generated[0]["quality_check"]["final_score"], 0)
        self.assertLessEqual(generated[0]["quality_check"]["final_score"], 100)

    def test_provider_generation_is_blocked_without_explicit_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "analyzed.jsonl"
            output_path = Path(tmp) / "generated.jsonl"
            report_path = Path(tmp) / "report.md"
            write_jsonl(input_path, sample_rows())

            with self.assertRaisesRegex(RuntimeError, "Provider generation is disabled"):
                generate_yokaze_posts_from_reference(
                    input_path=input_path,
                    output_path=output_path,
                    report_path=report_path,
                    top_n=1,
                    theme=None,
                    dry_run=False,
                    mock_llm=False,
                    settings={
                        "TEXT_LLM_PROVIDER": "openai",
                        "OPENAI_MODEL": "gpt-test",
                    },
                    clients=FailingProvider().clients(),
                )

    def test_style_pattern_argument_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "analyzed.jsonl"
            output_path = Path(tmp) / "generated.jsonl"
            report_path = Path(tmp) / "report.md"
            write_jsonl(input_path, sample_rows())

            generate_yokaze_posts_from_reference(
                input_path=input_path,
                output_path=output_path,
                report_path=report_path,
                top_n=2,
                theme=None,
                dry_run=True,
                mock_llm=True,
                style_pattern="short_yoin",
                target_ratio={"romance": 0.7, "other": 0.3},
                max_same_pattern=3,
            )
            generated = [
                json.loads(line)
                for line in output_path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual({row["style_pattern"] for row in generated}, {"short_yoin"})

    def test_other_theme_shortage_warning_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "analyzed.jsonl"
            output_path = Path(tmp) / "generated.jsonl"
            report_path = Path(tmp) / "report.md"
            write_jsonl(input_path, [sample_rows()[0]])

            generate_yokaze_posts_from_reference(
                input_path=input_path,
                output_path=output_path,
                report_path=report_path,
                top_n=None,
                theme=None,
                dry_run=True,
                mock_llm=True,
                style_pattern="auto",
                target_ratio={"romance": 0.7, "other": 0.3},
                max_same_pattern=2,
            )
            report = report_path.read_text(encoding="utf-8")

        self.assertIn("Other-theme analyses are missing", report)

    def test_similarity_risk_detects_high_overlap(self) -> None:
        generated = "通知が鳴っていないのに\n画面を伏せたまま気にしてしまう夜がある。"
        risk = assess_similarity_risk(
            generated_post=generated,
            analysis={"source_text": generated},
        )

        self.assertEqual(risk, "high")

    def test_report_generation_contains_new_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "analyzed.jsonl"
            output_path = Path(tmp) / "generated.jsonl"
            report_path = Path(tmp) / "report.md"
            write_jsonl(input_path, sample_rows())

            generate_yokaze_posts_from_reference(
                input_path=input_path,
                output_path=output_path,
                report_path=report_path,
                top_n=2,
                theme=None,
                dry_run=True,
                mock_llm=True,
                style_pattern="auto",
                target_ratio={"romance": 0.7, "other": 0.3},
                max_same_pattern=2,
            )
            report = report_path.read_text(encoding="utf-8")

        self.assertIn("Style Pattern Counts", report)
        self.assertIn("Average quality score", report)
        self.assertIn("generic_advice_risk high", report)
        self.assertIn("self_help_tone_risk high", report)
        self.assertIn("Human Review Candidates", report)


if __name__ == "__main__":
    unittest.main()
