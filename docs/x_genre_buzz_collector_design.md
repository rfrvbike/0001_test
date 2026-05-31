# X Genre Buzz Collector Design

Design only. No live X API call, token access, `.env` edit, or posting was
performed for this memo.

## Goal

Collect growing X posts for three configurable genres, save them to CSV, and
make the output usable for later post analysis.

Each genre should be able to define its own:

- search keywords and query operators
- target accounts
- collection period
- minimum like, repost, reply, and quote counts
- scoring weights
- maximum result count

## Existing Repository Findings

X-related code already exists.

- `x_auto_ops/reference_posts.py` contains dry-run/mock-first collection,
  scoring, CSV writing, and analysis helpers.
- `tools/x_collect_reference_posts.py` is a CLI for reference-post collection.
  Live collection is blocked unless a future injected client is added.
- `tools/x_score_reference_posts.py` scores existing CSV rows.
- `tools/x_analyze_reference_posts.py` analyzes top scored rows with mock LLM or
  injected provider clients.
- `tools/excel_daily_poster/x_client.py` contains future posting clients and a
  default blocked poster. It is posting-oriented and should not be reused for
  read collection except for its error-classification patterns.

CSV and analysis flow already exists.

- `data/reference_posts/raw_posts.csv` is the current raw collection target.
- `data/reference_posts/scored_posts.csv` is the scored output.
- `data/reference_posts/analyzed_posts.jsonl` is the later analysis output.
- `data/reference_posts/manual_reference_posts.csv.example` supports local
  manual import without external APIs.
- `tests/test_reference_posts.py` already checks dry-run collection, scoring,
  CSV output, exclusion rules, and report generation.

## X API Notes

Sources checked on 2026-05-30:

- X Metrics docs:
  https://docs.x.com/x-api/fundamentals/metrics
- X Recent Search quickstart:
  https://docs.x.com/x-api/posts/search/quickstart/recent-search
- X Rate Limits docs:
  https://docs.x.com/x-api/fundamentals/rate-limits
- X Search introduction:
  https://docs.x.com/x-api/posts/search/introduction

Likely available with `tweet.fields=public_metrics`:

- `public_metrics.like_count`
- `public_metrics.retweet_count`
- `public_metrics.reply_count`
- `public_metrics.quote_count`
- `public_metrics.impression_count`
- `public_metrics.bookmark_count`

Useful non-metric fields:

- `id`
- `text`
- `author_id`
- `created_at`
- `conversation_id`
- `lang`
- `possibly_sensitive`
- `referenced_tweets`
- `attachments`

Potentially unavailable, plan-dependent, or not appropriate for competitor
collection:

- URL clicks, profile clicks, and total engagements are non-public metrics and
  generally require user-context access to owned posts.
- Organic and promoted metrics are user-context metrics and are for owned or
  promoted posts.
- Full-archive search may require a higher access level than recent search.
- Recent search is for the last 7 days.
- Endpoint limits and billing can change by plan, so the live phase must read
  response headers and handle 429 with `x-rate-limit-reset`/backoff.

## Recommended Configuration Location

Use a tracked example plus an ignored local file:

- `data/x_buzz_genres.yml.example`
- `data/x_buzz_genres.yml` ignored by git

Reason:

- genre rules are data/config, not code
- `data/` already holds source-account and reference-post CSV inputs
- a tracked `.example` documents the expected shape without exposing private
  account lists or experimental keywords

If the project later accumulates several config files, move examples under
`config/` and keep generated/private files in `data/`.

## Configuration File Draft

```yaml
version: 1
defaults:
  endpoint: recent_search
  max_results_per_request: 100
  max_pages: 2
  exclude_retweets: true
  exclude_replies: true
  lang: ja
  min_created_at: ""
  max_created_at: ""
  score_weights:
    like_count: 1.0
    repost_count: 3.0
    reply_count: 1.5
    quote_count: 2.5
    bookmark_count: 0.5
    impression_count: 0.0
  thresholds:
    min_like_count: 100
    min_repost_count: 10
    min_reply_count: 0
    min_quote_count: 0
    min_score: 150

genres:
  - id: romance
    label: 恋愛
    query_keywords:
      - 恋愛
      - 復縁
      - 片思い
    target_accounts:
      - example_account_1
    search_query_extra: "-is:retweet -is:reply"
    thresholds:
      min_like_count: 500
      min_repost_count: 30
      min_score: 800

  - id: work_relationships
    label: 仕事・人間関係
    query_keywords:
      - 職場
      - 人間関係
      - しんどい
    target_accounts: []
    thresholds:
      min_like_count: 300
      min_score: 500

  - id: loneliness_life
    label: 孤独・日常
    query_keywords:
      - 孤独
      - 夜
      - 疲れた
    target_accounts: []
    thresholds:
      min_like_count: 200
      min_quote_count: 5
      min_score: 350
```

Query builder rule:

- combine `query_keywords` with OR
- add `from:<handle>` filters when a genre has `target_accounts`
- add default safety filters such as `-is:retweet`, `-is:reply`, and `lang:ja`
- keep final query within the endpoint query-length limit

## Score Design

Base score:

```text
buzz_score =
  like_count * like_weight
  + repost_count * repost_weight
  + reply_count * reply_weight
  + quote_count * quote_weight
  + bookmark_count * bookmark_weight
```

Recommended default:

```text
like_count * 1.0
+ repost_count * 3.0
+ reply_count * 1.5
+ quote_count * 2.5
+ bookmark_count * 0.5
```

Optional derived scores:

- `engagement_count = like + repost + reply + quote + bookmark`
- `engagement_rate = engagement_count / impression_count` when impressions are
  present and greater than zero
- `velocity_score = buzz_score / max(age_hours, 1)` for posts collected during a
  short window
- `genre_rank` after filtering and sorting within each genre

Notes:

- Reposts and quotes should weigh more than likes because they indicate
  propagation.
- Replies can be noisy, so keep their default weight below reposts/quotes.
- Do not require impressions because availability may vary by access or plan.
- Keep the formula configurable per genre.

## CSV Column Draft

Recommended output:

```text
genre_id
genre_label
post_id
post_url
text
author_id
author_username
author_name
created_at
collected_at
query
matched_keywords
source_type
source_account
like_count
repost_count
reply_count
quote_count
bookmark_count
impression_count
engagement_count
engagement_rate
age_hours
buzz_score
velocity_score
genre_rank
lang
possibly_sensitive
conversation_id
referenced_tweets
media_keys
excluded
exclusion_reason
```

Minimum viable CSV can reuse the existing `RAW_POST_FIELDS` plus:

- `genre_id`
- `genre_label`
- `query`
- `matched_keywords`
- `bookmark_count`
- `buzz_score`
- `velocity_score`
- `genre_rank`

## Future File Structure

```text
data/
  x_buzz_genres.yml.example
  x_buzz_genres.yml                 # ignored
  x_buzz_posts/
    raw_posts.csv                   # ignored
    scored_posts.csv                # ignored
    mock_raw_posts.csv.example

docs/
  x_genre_buzz_collector_design.md

reports/
  x_genre_buzz_collector_report.md

tools/
  x_collect_genre_buzz_posts.py
  x_score_genre_buzz_posts.py

x_auto_ops/
  genre_buzz_config.py
  genre_buzz_posts.py
  x_read_client.py                  # future injected live client boundary

tests/
  test_genre_buzz_config.py
  test_genre_buzz_posts.py
```

## Mock Test Plan

No test should read `.env`, create tokens, or call the network.

Core tests:

- config loader accepts exactly three genres
- defaults merge into each genre and genre-specific thresholds override defaults
- query builder creates safe queries and enforces query length
- dry-run collector uses fixture responses and never calls the injected failing
  live client
- normalizer maps `public_metrics.retweet_count` to `repost_count`
- missing metric fields become empty string or zero according to column policy
- threshold filter works per genre
- score formula is deterministic and configurable
- duplicate `post_id` is deduplicated across keyword/account collection paths
- CSV writer preserves the declared column order
- rate-limit errors are classified but not retried in unit tests

Useful fixture shape:

```python
{
    "id": "123",
    "text": "sample",
    "author_id": "456",
    "created_at": "2026-05-30T00:00:00.000Z",
    "public_metrics": {
        "like_count": 120,
        "retweet_count": 20,
        "reply_count": 5,
        "quote_count": 8,
        "bookmark_count": 4,
        "impression_count": 10000,
    },
}
```

## Implementation Steps

1. Add config example and schema/loader tests.
2. Add query builder with dry-run fixtures only.
3. Add normalizer and CSV writer reusing existing `write_csv` patterns where
   possible.
4. Add scorer with per-genre weights and thresholds.
5. Add CLI commands that default to dry-run/mock mode.
6. Add report generation summarizing top posts per genre.
7. Only after explicit approval, add an injected live read client for X recent
   search.
8. Only after separate approval, configure credentials outside git.

## Security and Operational Notes

- Do not edit `.env` in this feature.
- Do not print or save bearer tokens, request headers, or raw auth errors.
- Default CLI mode should be dry-run/mock, with live mode requiring an explicit
  flag and injected client.
- Keep generated raw/scored CSVs ignored by git.
- Store only public post metadata needed for analysis.
- Avoid posting, liking, replying, reposting, or following from this feature.
- Respect X rate limits, response headers, usage billing, and access-plan
  constraints before enabling live collection.
- Treat source post text as reference data for analysis only. Do not copy or
  closely rewrite source wording into generated posts.

## Mock Skeleton Implemented

Implemented on 2026-05-30 as a mock-only CLI skeleton.

Added files:

- `data/x_buzz_genres.json.example`
- `x_auto_ops/mock_buzz_collector.py`
- `tools/mock_buzz_collector.py`
- `tests/test_mock_buzz_collector.py`
- `reports/mock_buzz_report.md`

Generated but not intended for commit:

- `data/mock_buzz_posts.csv`

The implementation uses JSON rather than YAML so it can run with only the
Python standard library. A future phase can add YAML support if the project
accepts a dependency such as PyYAML.

Current config shape:

```json
{
  "version": 1,
  "defaults": {
    "min_likes": 100,
    "min_reposts": 10,
    "min_replies": 0,
    "min_quotes": 0,
    "days_back": 7,
    "score_weights": {
      "likes": 1,
      "reposts": 3,
      "replies": 2,
      "quotes": 2
    }
  },
  "genres": [
    {
      "id": "yokaze",
      "keywords": ["night", "feeling", "relationship"],
      "min_likes": 400,
      "min_reposts": 25,
      "min_replies": 5,
      "days_back": 7
    }
  ]
}
```

Current CLI:

```powershell
python tools/mock_buzz_collector.py --dry-run
```

In this environment, use the bundled Python runtime:

```powershell
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\mock_buzz_collector.py --dry-run
```

Current behavior:

- loads `data/x_buzz_genres.json.example`
- generates deterministic mock posts for `yokaze`, `ai_side_business`, and
  `daily`
- filters by likes, reposts, replies, quotes, and `days_back`
- computes `score = likes * 1 + reposts * 3 + replies * 2 + quotes * 2`
- writes `data/mock_buzz_posts.csv`
- writes `reports/mock_buzz_report.md`
- refuses non-dry-run mode
- never reads `.env`, tokens, cookies, or API keys
- never calls X or any external API

## Genre Detection and Ranking Implemented

Implemented on 2026-05-31 as a mock-only extension.

Current classification:

- rule-based keyword scoring
- `detection_keywords` are configured per genre in
  `data/x_buzz_genres.json.example`
- each matched keyword adds `1` to the genre score
- `min_genre_score` controls the minimum score required for classification
- the genre with the highest score becomes `detected_genre`
- ties are resolved by `tie_break_priority`
- ties between genres outside `tie_break_priority` fall back to stable config
  order
- if no keyword matches, `detected_genre` becomes `unknown`
- short ASCII keywords such as `ai` are matched with word boundaries to avoid
  false positives such as `plain`
- multi-word and Japanese keywords use substring matching

Configured target genres:

- `yokaze`: hurt people, women trying hard, relationships, night, loneliness,
  healing, quiet support
- `ai_side_business`: AI use, side business, workflow automation, papers,
  monetization, non-engineer productivity
- `daily`: everyday life, coffee, room, Sunday night, before work, habits, light
  jokes

CSV columns now include:

```text
genre,post_id,author,text,likes,reposts,replies,quotes,score,detected_genre,
genre_score,genre_reason,buzz_score,rank_in_genre,created_at
```

Ranking:

- rows are grouped by `detected_genre`
- each group is sorted by `buzz_score` descending
- `rank_in_genre` starts at `1` for each detected genre
- `unknown` is ranked as its own group

CLI filtering:

```powershell
python tools/mock_buzz_collector.py --dry-run --genre yokaze
python tools/mock_buzz_collector.py --dry-run --genre ai_side_business
python tools/mock_buzz_collector.py --dry-run --genre daily
```

The `--genre` option filters by `detected_genre`, not by the mock seed genre.

## Safety and Read Client Boundary Implemented

Implemented on 2026-05-31 as a mock-only safety extension.

Git ignore safety:

- `data/mock_buzz_posts.csv`
- `data/mock_buzz_posts_*.csv`
- `data/x_buzz_genres.json`

Tracked example remains allowed:

- `data/x_buzz_genres.json.example`

Config now includes:

```json
{
  "min_genre_score": 1,
  "tie_break_priority": ["yokaze", "ai_side_business", "daily"]
}
```

Read client interface:

- `x_auto_ops/buzz_read_client.py`
- `BuzzReadClient` protocol with `fetch_posts(config)`
- `BuzzPost` normalized post dataclass
- `MockBuzzReadClient` for local deterministic dry-run data
- `XApiBuzzReadClient` placeholder that raises `NotImplementedError`

The mock collector now obtains posts through `MockBuzzReadClient` by default.
The future X API client should implement the same `fetch_posts(config)` boundary
without changing scoring, classification, ranking, CSV output, or reports.

## Read Client Contract Finalized Before X API Connection

Implemented on 2026-05-31 as a mock-only interface hardening step.

`fetch_posts(config)` returns `BuzzFetchResult`:

```text
posts: list[dict]
rate_limited: bool
retry_after_seconds: int | None
partial_result: bool
next_token: str
request_window: str
```

Each post dict must contain these stable keys:

```text
post_id
author_id
author_username
text
created_at
like_count
repost_count
reply_count
quote_count
impression_count
source_query
source_genre
fetched_at
metrics_missing
```

Compatibility aliases are also emitted for the current mock collector:

```text
genre
author
likes
reposts
replies
quotes
```

Nullable and missing data handling:

- `impression_count` may be `None`.
- missing `impression_count` is recorded in `metrics_missing`.
- missing `author_id` / `author_username` is recorded in `metrics_missing`.
- missing `quote_count` is treated as `0` and recorded in `metrics_missing`.
- missing public metrics are treated as `0` so the collector can continue.

Score source:

- `score_source=impression_adjusted` when `impression_count` is available.
- `score_source=engagement_fallback` when `impression_count` is missing.
- fallback score uses likes, reposts, replies, and quotes only.
- CSV now includes `impression_count`, `score_source`, and `metrics_missing`.

Current score formula:

```text
base = like_count * likes_weight
     + repost_count * reposts_weight
     + reply_count * replies_weight
     + quote_count * quotes_weight

if impression_count exists:
  buzz_score = base + impression_count * impressions_weight
else:
  buzz_score = base
```

Config additions:

```json
{
  "search_queries": [],
  "target_accounts": [],
  "exclude_keywords": [],
  "max_results_per_genre": 50,
  "include_impressions_if_available": true,
  "min_buzz_score": 0
}
```

Rate-limit and pagination design:

- `rate_limited`: true when a read client hit a limit.
- `retry_after_seconds`: seconds to wait before retrying, from `Retry-After` or
  computed from `x-rate-limit-reset` in a future live client.
- `partial_result`: true when only part of the requested result set was
  returned.
- `next_token`: pagination cursor for continuing a query.
- `request_window`: the current request window label, such as `15min`.

X API notes checked against official docs on 2026-05-31:

- public metrics can include reposts, likes, replies, quotes, and impressions
  through `public_metrics`, but availability can depend on endpoint/access.
- recent search is limited to a recent window and endpoint result limits.
- `next_token` is used for pagination.
- rate limit response headers include limit, remaining count, and reset time.
- 429 responses should be handled with backoff/retry-after behavior.

References:

- https://docs.x.com/x-api/fundamentals/metrics
- https://docs.x.com/x-api/fundamentals/rate-limits
- https://docs.x.com/x-api/posts/search/quickstart/recent-search
- https://docs.x.com/x-api/posts/search/integrate/paginate

## X API Response Normalizer Implemented

Implemented on 2026-05-31 with mock fixtures only. No X API request, token
lookup, `.env` read, or posting is performed.

Normalizer:

```text
x_auto_ops/x_response_normalizer.py
normalize_recent_search_response(response_json, source_query, source_genre)
```

Input assumptions:

- Recent-search-like JSON with `data`, optional `includes.users`, and optional
  `meta`.
- Post fields may include `id`, `text`, `created_at`, `author_id`, and
  `public_metrics`.
- `public_metrics` may include `like_count`, `retweet_count`, `reply_count`,
  `quote_count`, and `impression_count`.
- `includes.users` links author data by `author_id`.

Output:

- `BuzzFetchResult`
- normalized `BuzzPost` dictionaries in `posts`
- rate-limit/pagination metadata from `meta` or top-level mock fields

Missing-field behavior:

- missing `includes.users` does not fail
- missing `public_metrics` does not fail
- missing `impression_count` becomes `None`
- missing `quote_count` becomes `0`
- missing `author_id` / username become empty strings
- missing fields are recorded in `metrics_missing` with values such as:
  - `missing_impression_count`
  - `missing_author_username`
  - `missing_public_metrics`
  - `missing_quote_count`

Fixture coverage:

- `tests/fixtures/recent_search_response_minimal.json`
- `tests/fixtures/recent_search_response_with_metrics.json`
- `tests/fixtures/recent_search_response_missing_metrics.json`
- `tests/fixtures/recent_search_response_partial.json`

The normalizer is the intended next boundary for a future `XApiBuzzReadClient`:
the live client should fetch JSON, pass it to the normalizer, then return the
same `BuzzFetchResult` contract used by the mock collector.

Current tests:

- config loading and default merging
- score calculation
- filtering
- CSV output column order
- mock collection
- non-dry-run blocking
- `yokaze` / `ai_side_business` / `daily` classification
- `unknown` classification
- mixed-genre winner by highest score
- per-genre ranking by `buzz_score`
- report sections for genre rankings and top buzz posts
- generated CSV and local config are gitignored
- tracked config example is not ignored
- `min_genre_score` below-threshold classification becomes `unknown`
- `tie_break_priority` resolves tied genre scores
- `MockBuzzReadClient` returns normalized posts
- `XApiBuzzReadClient` placeholder raises without external API access
- CLI dry-run still works

Next live-read phase should add a separate injected read client boundary instead
of modifying the mock collector to call X directly.
