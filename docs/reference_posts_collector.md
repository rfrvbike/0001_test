# Reference Posts Collector

This feature collects and analyzes popular X posts for structure only. It must
not copy, rewrite, preserve, or closely follow source wording, metaphors, line
breaks, or sentence order.

## Files

- `data/source_accounts.csv.example`: sample source-account list.
- `data/source_accounts.csv`: local source-account list, ignored by git.
- `data/reference_posts/raw_posts.csv`: collected posts, ignored by git.
- `data/reference_posts/scored_posts.csv`: filtered and scored posts, ignored by git.
- `data/reference_posts/analyzed_posts.jsonl`: structure analysis, ignored by git.
- `reports/reference_posts_report.md`: generated summary report.

## Dry-Run Flow

Run these commands for the current local/mock workflow:

```powershell
python tools/x_collect_reference_posts.py --dry-run
python tools/x_score_reference_posts.py
python tools/x_analyze_reference_posts.py --mock-llm --dry-run
python -m unittest tests.test_reference_posts -v
```

`--dry-run` collection uses sample posts and never calls X. `--mock-llm`
analysis uses local deterministic analysis and never calls an external LLM.

## Live API Status

Live X collection is not implemented in the normal flow. The collector does not
create an X client, does not call X, and does not read live credentials during
local/mock operation. Non-dry-run collection is blocked unless future code
explicitly opts in and injects a reviewed client.

Any production credential design is a future review item. Do not commit local
raw CSVs, generated JSONL analysis files, or credential files.

## Yokaze Analysis Rules

For `yokaze_daily`, analysis should extract:

- who the post is for
- the specific wound
- the hidden feeling
- theme
- structure
- opening pattern
- emotional flow
- ending type
- phrases to avoid
- a rewrite direction for original yokaze posts

The output should help generate original yokaze drafts with love themes around
70% and work/relationships/loneliness/fatigue around 30%.
