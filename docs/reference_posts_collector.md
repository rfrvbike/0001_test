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

Run these commands before any live API work:

```powershell
python tools/x_collect_reference_posts.py --dry-run
python tools/x_score_reference_posts.py
python tools/x_analyze_reference_posts.py --mock-llm --dry-run
python -m unittest tests.test_reference_posts -v
```

`--dry-run` collection uses sample posts and never calls X. `--mock-llm`
analysis uses local deterministic analysis and never calls an external LLM.

## Live API Notes

Live X collection is intentionally not wired by default. A future phase should
inject an `XReferenceClient` that resolves user ids, fetches recent posts, and
honors `Retry-After` on 429 responses. Keep `--limit` capped at 200 unless the
cost/rate-limit policy is reviewed.

Use `.env` for `X_BEARER_TOKEN`; never commit `.env`, tokens, local raw CSVs,
or generated JSONL analysis files.

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
