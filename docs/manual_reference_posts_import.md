# Manual Reference Posts Import

Use this when you want to feed manually collected X posts into the reference
analysis flow before enabling any live X API collection.

This importer never calls X, LLMs, or any external API. It only reads a local
CSV and writes `data/reference_posts/raw_posts.csv` in the same shape as the
collector output.

## Input

Local file:

```text
data/reference_posts/manual_reference_posts.csv
```

Columns:

```text
source_handle,post_url,text,created_at,like_count,repost_count,reply_count,quote_count,impression_count,category,note
```

Required:

- `post_url`
- `text`
- `category`

Optional:

- `source_handle`
- `created_at`
- `like_count`
- `repost_count`
- `reply_count`
- `quote_count`
- `impression_count`
- `note`

## Output

```text
data/reference_posts/raw_posts.csv
```

The importer:

- extracts `post_id` from `/status/<id>` URLs when possible
- generates `manual_0001` style ids when no post id is available
- infers `source_handle` from the URL when the column is empty
- fills missing count fields with `0`
- requires `category`
- warns on short text
- skips duplicate `post_url`

## Commands

```powershell
python tools/x_import_reference_posts_manual.py --dry-run
python tools/x_import_reference_posts_manual.py
python -m unittest tests.test_manual_reference_posts_import -v
```

After import, continue with:

```powershell
python tools/x_score_reference_posts.py
python tools/x_analyze_reference_posts.py --mock-llm --dry-run
python tools/x_generate_yokaze_from_reference.py --mock-llm --dry-run --style-pattern auto --target-ratio romance:0.7,other:0.3
```
