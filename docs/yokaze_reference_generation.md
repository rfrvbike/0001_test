# Yokaze Reference Generation

This preview generator uses `analyzed_posts.jsonl` as structure-only input for
new `yokaze_daily` draft candidates. It must not copy, rewrite, or preserve
source wording, metaphors, line breaks, or sentence order.

## Dry-Run Flow

```powershell
python tools/x_generate_yokaze_from_reference.py --mock-llm --dry-run
python tools/x_generate_yokaze_from_reference.py --mock-llm --dry-run --style-pattern auto --target-ratio romance:0.7,other:0.3
python -m unittest tests.test_yokaze_reference_generation -v
python -m unittest tests.test_reference_posts tests.test_yokaze_reference_generation tests.test_account_policy -v
```

If `python` is not on PATH, use the bundled Codex Python path shown in
`reports/latest_report.md`.

## Provider Status

The current workflow is local/mock generation only. External LLM providers are
not called by default, and provider-backed generation is blocked unless future
code explicitly opts in with reviewed settings and injected clients.

## Inputs

- `data/reference_posts/analyzed_posts.jsonl`
- Optional `--top-n`
- Optional `--theme`
- Optional `--dry-run`
- Optional `--mock-llm`
- Optional `--style-pattern`: `daiben`, `joukei`, `hitei_kaijo`, `kioku`,
  `short_yoin`, or `auto`.
- Optional `--target-ratio`: for example `romance:0.7,other:0.3`.
- Optional `--max-same-pattern`: maximum same style streak before warnings.

## Outputs

- `data/reference_posts/yokaze_generated_posts.jsonl`
- `reports/yokaze_reference_generation_report.md`

## Output Fields

- `source_analysis_id`
- `theme`
- `target`
- `pain`
- `hidden_feeling`
- `style_pattern`
- `generated_post`
- `image_recommendation`
- `similarity_risk`
- `quality_check`
- `quality_notes`

## Style Patterns

- `daiben`: centers the hidden feeling she could not say.
- `joukei`: opens from a concrete scene such as a room, phone, entrance, or night.
- `hitei_kaijo`: loosens self-blame such as "重いんじゃない".
- `kioku`: uses remembered kindness, words, or moments that remain.
- `short_yoin`: shorter, quieter, with more white space and less explanation.

## Quality Check

Each generated item includes:

- `target_specificity`
- `emotional_specificity`
- `generic_advice_risk`
- `self_help_tone_risk`
- `style_repetition_risk`
- `final_score`

## Review Rules

Human review should confirm:

- The opening names a specific situation, not a broad audience.
- The hidden feeling is spoken before any relief.
- The ending is quiet and not self-help.
- `image_recommendation` is `none`, `ambient_only`, or `avoid`.
- `similarity_risk` is not `high`.
