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

## Recent Search Query Builder and Rate Limit Header Parser

Implemented on 2026-05-31 with local config and mock header fixtures only. No X
API request, token lookup, `.env` read, or posting is performed.

Query builder:

```text
x_auto_ops/query_builder.py
build_recent_search_query(config)
```

Input:

- `search_queries`
- `keywords` as fallback when `search_queries` is absent
- `target_accounts`
- `exclude_keywords`
- `source_genre`, `id`, or `genre`
- optional `lang` / `language`, default `ja`

Output:

- `RecentSearchQuery`
- `.query`: recent-search query string
- `.source_genre`: genre identity carried forward for fetch metadata
- `.search_terms`, `.target_accounts`, `.exclude_keywords`: normalized source
  components for logging/tests

Safety behavior:

- empty search query is rejected
- query longer than the configured `max_length` is rejected
- duplicate keywords/accounts/excludes are removed case-insensitively
- target accounts are converted to `from:username`
- exclude keywords are emitted as negative terms
- multi-word terms are quoted
- the builder only formats local values and performs no credential or network
  access

Example:

```text
(AI OR ChatGPT OR Claude) -giveaway lang:ja
```

Rate limit header parser:

```text
x_auto_ops/rate_limit_parser.py
parse_rate_limit_headers(headers, status_code=None, now=None)
```

Input headers:

- `Retry-After`
- `x-rate-limit-remaining`
- `x-rate-limit-reset`

Output:

- `RateLimitInfo.rate_limited`
- `RateLimitInfo.retry_after_seconds`
- `RateLimitInfo.remaining_requests`
- `RateLimitInfo.reset_timestamp`

Parser behavior:

- `Retry-After` seconds are preferred when present
- HTTP-date `Retry-After` values are also accepted
- `x-rate-limit-reset` is converted to wait seconds only when the response is
  rate limited or remaining requests are zero
- missing headers are safe and return `None` values
- invalid header values are ignored instead of raising

Recent search use policy:

- Future live reads should build query strings only through this builder.
- Query strings should be logged without credentials and associated with
  `source_genre`.
- Recent search may be limited to a recent window and plan-specific result
  limits.
- The future client should pass raw JSON to the response normalizer and pass
  response headers to the rate limit parser.

Rate limit policy:

- Respect `Retry-After` when present.
- If remaining requests are zero, compute wait time from `x-rate-limit-reset`.
- Preserve `remaining_requests` and `reset_timestamp` for reports/debugging.
- Do not retry automatically inside the collector until live-read behavior is
  explicitly approved.

## Mock Transport Integration Layer

Implemented on 2026-05-31 with fixture-backed transport only. No X API request,
token lookup, cookie lookup, `.env` read, or posting is performed.

Transport layer:

```text
x_auto_ops/mock_transport.py
MockRecentSearchTransport.send_recent_search(query)
```

Transport response:

```text
TransportResponse(
  status_code,
  headers,
  json_body
)
```

Mock pipeline:

```text
run_mock_recent_search_pipeline(config, transport)
```

Flow:

```text
Query Builder
-> Mock Transport
-> Rate Limit Header Parser
-> Response Normalizer
-> BuzzFetchResult
```

Pipeline output:

- `query`: the `RecentSearchQuery`
- `transport_response`: mock HTTP-shaped response
- `rate_limit`: parsed `RateLimitInfo`
- `fetch_result`: normalized `BuzzFetchResult`
- `debug_log`: credential-redacted local debug summary

Fixture coverage:

- `tests/fixtures/transport_success.json`
- `tests/fixtures/transport_partial.json`
- `tests/fixtures/transport_rate_limited.json`

Credential leak protection:

- The mock pipeline does not read API keys, bearer tokens, cookies, or `.env`.
- Debug output records query length and status metadata, not raw config.
- Leak tests check that `API_KEY`, `TOKEN`, `BEARER`, and `SECRET` do not appear
  in debug logs or rendered CSV output.
- Debug field names avoid credential words such as `token`.

Dry-run gate:

- `XApiBuzzReadClient(dry_run=False).fetch_posts(...)` raises `RuntimeError`.
- `XApiBuzzReadClient().fetch_posts({"dry_run": false, ...})` also raises
  `RuntimeError`.
- Dry-run placeholder mode still raises `NotImplementedError` because live X API
  collection is not implemented.

## Transport Injection and Full Dry-run Pipeline

Implemented on 2026-05-31 with injected mock transport only. No X API request,
credential lookup, `.env` read, or posting is performed.

Transport injection:

```text
XApiBuzzReadClient(transport=MockRecentSearchTransport(...), dry_run=True)
```

Behavior:

- `transport` is optional and injected from outside.
- Without a transport, dry-run mode remains a placeholder and raises
  `NotImplementedError`.
- With an injected transport, `fetch_posts(config)` runs:
  - `build_recent_search_query(config)`
  - `transport.send_recent_search(query)`
  - `parse_rate_limit_headers(...)`
  - `normalize_recent_search_response(...)`
  - returns `BuzzFetchResult`
- `dry_run=False` always raises `RuntimeError` before any transport call.

Transport interface:

```text
RecentSearchTransport.send_recent_search(query) -> TransportResponse
```

`MockRecentSearchTransport` implements this interface. A future live transport
should implement the same method but must stay outside collector logic and must
not be enabled without explicit approval.

Full dry-run pipeline:

```text
x_auto_ops/dry_run_recent_search_pipeline.py
run_dry_run_recent_search_pipeline(...)
```

Flow:

```text
Query Builder
-> XApiBuzzReadClient
-> Mock Transport
-> Header Parser
-> Response Normalizer
-> BuzzFetchResult
-> Genre Detection
-> Ranking
-> CSV Export
-> Report
```

CLI:

```text
python tools/mock_recent_search_pipeline.py --dry-run
```

Default outputs:

- `data/mock_recent_search_pipeline_posts.csv` (gitignored)
- `reports/mock_recent_search_pipeline_report.md`

Pipeline report includes:

- query
- source_genre
- post_count
- rate_limited
- retry_after_seconds
- partial_result
- top_posts
- metrics_missing summary

Credential leak protection:

- Regression tests inject `API_KEY`, `TOKEN`, `BEARER`, `SECRET`, and `COOKIE`
  markers into config values.
- Tests assert those markers do not appear in debug logs, reports, CSV output,
  or dry-run gate exceptions.
- Report output redacts sensitive markers before writing.
- Debug output records query length and status metadata instead of raw config.

Future live transport strategy:

- Keep `XApiBuzzReadClient` dependent on an injected `RecentSearchTransport`.
- Implement live HTTP only in a separate transport class.
- Keep query building, header parsing, normalization, scoring, CSV, and reports
  independent from credentials.
- Add redacted request/response logging tests before enabling live reads.

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

## Redaction Policy, Retry Queue, and Live Transport Plan

Added on 2026-06-02 as mock-only pre-live hardening. No X API call, credential
lookup, `.env` read, cookie read, token read, or posting is performed.

### Redaction Policy

`x_auto_ops/redaction.py` provides the shared redaction boundary:

- `redact_sensitive_text(text)`
- `contains_sensitive_marker(text)`
- `assert_redacted(text, context=...)`

The redaction policy covers these markers:

- `API_KEY`
- `TOKEN`
- `BEARER`
- `SECRET`
- `COOKIE`
- `AUTHORIZATION`

Pipeline reports, debug logs, CSV leak-test rendering, and exception surfaces
must not contain those markers. Tests intentionally inject marker-shaped values
and fail if they appear in report, CSV, debug output, or exceptions.

### Retry Queue

`x_auto_ops/retry_queue.py` defines a mock-only in-memory retry queue:

```text
RetryTask(
  query,
  retry_after_seconds,
  enqueue_time,
  retry_count,
)

RetryQueue.enqueue(...)
RetryQueue.dequeue_ready(now)
RetryQueue.size()
```

The queue never sleeps, opens sockets, or performs a retry by itself. It only
records tasks that a future controller could retry after the parsed delay.

Dry-run pipeline behavior:

- if `BuzzFetchResult.rate_limited` is true, enqueue the built query
- set `retry_queue_size`
- report `rate_limited_count`
- list mock `retry_tasks`
- emit `redaction_status: ok`

### Live Transport Plan

`docs/live_recent_search_transport.md` specifies the future
`LiveRecentSearchTransport` boundary. The planned transport will implement the
same interface as `MockRecentSearchTransport`:

```text
send_recent_search(query: str) -> TransportResponse
```

The future live transport must remain behind both:

- `XApiBuzzReadClient` dry-run gate
- its own explicit live-mode configuration

Allowed future responsibility:

- perform approved read-only recent-search HTTP calls
- return status code, headers, and parsed JSON body
- expose rate-limit headers to the parser

Disallowed responsibility:

- genre classification
- scoring
- CSV writing
- report writing
- logging credentials
- retry sleeping/looping inside `send_recent_search`

Before live connection, tests must continue to prove that credentials cannot
appear in report, CSV, debug log, or exception output.

## LiveRecentSearchTransport Implementation Review

Added on 2026-06-02 as a design-only review before any live X API connection.
See `docs/live_recent_search_transport_review.md` for the full checklist, field
matrix, pagination review, rate-limit review, credential-loader policy, gap
analysis, and risk list.

Review outcome:

- Do not enable HTTP in the next step.
- Keep `XApiBuzzReadClient` fail-closed for `dry_run=False`.
- Add a future live transport only behind explicit live approval.
- Keep Query Builder, Header Parser, Response Normalizer, Retry Queue,
  redaction, scoring, CSV, and report generation separated.
- Treat `impression_count` as nullable and preserve the engagement-only fallback
  score path.
- Preserve `next_token`, `request_window`, and `partial_result` so pagination
  and rate-limit interruptions are visible to downstream code.
- Keep credentials backend-only and absent from frontend code, logs, reports,
  CSV, exceptions, fixtures, and debug output.

Current gaps before live transport:

- live transport class remains intentionally missing
- backend-only credential loader remains intentionally missing
- HTTP client and timeout/error mapping remain intentionally missing
- endpoint-specific header mapping must be verified against the selected X API
  plan
- pagination controller must be implemented outside the transport
- `max_retry_count` policy must be added to the controller layer

## Credential Loader and Live Mode Gate

Added on 2026-06-02 as mock-only safety scaffolding. No X API call, HTTP
request, API key lookup, token lookup, cookie read, `.env` read, environment
variable read, or posting is performed.

Credential loader boundary:

- `x_auto_ops/credential_loader.py`
- `CredentialLoader`
- `FakeCredentialLoader`
- `CredentialBundle`

Only `FakeCredentialLoader` is implemented. It returns fake credential-shaped
values for interface tests and does not read files, `.env`, environment
variables, cookies, tokens, or network resources. The dry-run pipeline loads the
fake bundle only to verify the future execution order:

```text
CredentialLoader
-> LiveModeGate
-> Mock Transport
```

Live mode gate:

- `x_auto_ops/live_mode_gate.py`
- `assert_live_mode_allowed(config)`

Current behavior:

- `dry_run=True` and `live_mode=False` is allowed
- `dry_run=False` or `live_mode=True` is rejected
- fake credentials do not unlock live mode
- the error message is fixed as `live mode disabled`

Report/debug behavior:

- report and debug output may show the safe credential source, such as `FAKE`
- fake credential values are not written to report, CSV, debug log, or
  exception text
- redaction regression tests cover fake marker-shaped values before real
  credentials exist

Related policy:

- `docs/live_mode_policy.md`

## LiveRecentSearchTransport Disabled Skeleton

Added on 2026-06-02 as a fail-closed implementation placeholder. No HTTP
communication, request library import, API key lookup, token lookup, cookie
read, `.env` read, or posting is performed.

Implementation point:

- `x_auto_ops/live_recent_search_transport.py`
- `LiveRecentSearchTransport`
- `send_recent_search(query)`

Current behavior:

```text
raise RuntimeError("LiveRecentSearchTransport disabled")
```

The skeleton satisfies the same transport method shape as
`MockRecentSearchTransport`, so `XApiBuzzReadClient` can accept either transport
through dependency injection. `MockRecentSearchTransport` remains the only
successful dry-run transport. `LiveRecentSearchTransport` always fails closed.

Integrated live-order policy:

```text
CredentialLoader
-> LiveModeGate
-> Transport
```

Current gate behavior means live mode should stop at `LiveModeGate` before
reaching the disabled transport. If a caller reaches `LiveRecentSearchTransport`
anyway, the disabled transport still raises.

Related document:

- `docs/live_recent_search_transport_disabled.md`

## HTTP Client Interface Skeleton

Added on 2026-06-02 as a mock-only interface layer. No HTTP communication,
request execution, API key lookup, token lookup, cookie read, `.env` read, or
posting is performed.

Implementation point:

- `x_auto_ops/http_client.py`
- `HttpRequest`
- `HttpResponse`
- `HttpClient`
- `DisabledHttpClient`

Request shape:

- `method`
- `url`
- `headers`
- `query_params`
- `timeout_seconds`

Response shape:

- `status_code`
- `headers`
- `body_text`
- `json_body`

Current behavior:

```text
DisabledHttpClient.send(request)
-> RuntimeError("HTTP client disabled")
```

`LiveRecentSearchTransport` now accepts an injected HTTP client, but still
raises `RuntimeError("LiveRecentSearchTransport disabled")` before using it.

Dependency injection order:

```text
CredentialLoader
-> LiveModeGate
-> LiveRecentSearchTransport
-> HttpClient
```

`MockRecentSearchTransport` remains the only successful dry-run pipeline
transport. The HTTP client interface is only a future live implementation
insertion point.

Related document:

- `docs/http_client_interface.md`

## HTTP Timeout and Error Mapping Skeleton

Added on 2026-06-02 as a mock-only error classification layer. No HTTP
communication, request execution, API key lookup, token lookup, cookie read,
`.env` read, or posting is performed.

Implementation point:

- `x_auto_ops/http_error_mapping.py`
- `HttpErrorInfo`
- `map_http_error(...)`

Mapped error types:

- `timeout`
- `network_error`
- `auth_error`
- `rate_limited`
- `server_error`
- `client_error`
- `json_parse_error`
- `schema_error`
- `disabled_http_client`

Retryable:

- `timeout`
- `network_error`
- `rate_limited`
- `server_error`

Not retryable:

- `auth_error`
- `client_error`
- `json_parse_error`
- `schema_error`
- `disabled_http_client`

Rate-limit handling:

- `status_code=429` maps to `rate_limited`
- `Retry-After` maps to `retry_after_seconds`
- reset/remaining headers are parsed by `parse_rate_limit_headers(...)`

Redaction:

- error messages are passed through `redact_sensitive_text(...)`
- credential-shaped markers must not appear in mapped message fields

RetryQueue relationship:

```text
map_http_error(...)
-> HttpErrorInfo(retryable, retry_after_seconds)
-> future controller
-> RetryQueue.enqueue(...)
```

The mapping layer does not enqueue, sleep, read files, or call the network.

Related document:

- `docs/http_error_mapping.md`

## HTTP Request Builder and Header Mapping Skeleton

Added on 2026-06-02 as a mock-only request construction layer. No HTTP
communication, request execution, API key lookup, token lookup, cookie read,
`.env` read, or posting is performed.

Implementation point:

- `x_auto_ops/request_builder.py`
- `build_recent_search_request(...)`
- `RequestBuildResult`

Build flow:

```text
Query Builder
-> Credential Loader
-> Request Builder
-> HttpRequest
```

Generated request:

- method: `GET`
- endpoint: recent search endpoint
- query params: `query`, `tweet.fields`, `expansions`, `user.fields`
- headers: authorization, user-agent, accept
- timeout: validated positive number

Header handling:

- header values are kept inside the internal `HttpRequest`
- `RequestBuildResult.header_names` records names only
- `safe_debug_summary()` redacts credential-shaped names and never prints
  header values

Validation:

- empty query is rejected
- empty endpoint is rejected
- invalid timeout is rejected

Authorization protection:

- fake bearer token may be used only to build a local `HttpRequest`
- fake bearer token must not appear in report, CSV, debug log, or exception
- authorization/bearer/API key/token/secret marker text is checked by tests

Related document:

- `docs/request_builder.md`

## Pagination Controller and Max Retry Policy Skeleton

Added on 2026-06-02 as a mock-only pagination and retry-decision layer. No HTTP
communication, request execution, API key lookup, token lookup, cookie read,
`.env` read, or posting is performed.

Implementation points:

- `x_auto_ops/pagination_controller.py`
- `PaginationController`
- `PaginationState`
- `PaginationResult`
- `x_auto_ops/retry_policy.py`
- `RetryPolicy`
- `RetryDecision`

Pagination flow:

```text
fetch_page(query, next_token)
-> BuzzFetchResult(posts, next_token, partial_result, rate_limited)
-> PaginationController
-> PaginationResult
```

Stop reasons:

- `completed`
- `max_results_reached`
- `max_pages_reached`
- `no_next_token`
- `rate_limited`
- `transport_error`
- `retry_limit_reached`

Retry policy:

- default `max_retry_count=3`
- retryable decisions can be enqueued to `RetryQueue`
- no sleeping or actual retry execution is performed

Partial result policy:

- max result/page stops can mark partial
- rate limit marks partial
- transport error marks partial
- retry limit reached marks partial

Redaction:

- `PaginationResult.safe_debug_summary()` redacts sensitive-looking next tokens
- retry/error metadata must not expose credential-shaped markers

Related document:

- `docs/pagination_controller.md`

## Backend-Only Real Credential Loader Skeleton

Added on 2026-06-03 as a disabled skeleton for future real X credential loading.
No real credential is read. No X API call, HTTP request, API key lookup, token
lookup, cookie lookup, `.env` read, environment variable read, or posting is
performed.

Implementation points:

- `x_auto_ops/real_credential_loader.py`
- `RealCredentialLoader`
- `RealCredentialLoaderDisabledError`
- `select_credential_loader(config)`
- `docs/backend_credential_policy.md`

Current behavior:

```text
RealCredentialLoader.load()
-> RealCredentialLoaderDisabledError("Real credential loader disabled")
```

Loader selection:

```text
credential_loader=fake -> FakeCredentialLoader
credential_loader=real -> RealCredentialLoader disabled skeleton
```

The real selection path does not read credentials. It only returns the disabled
loader object; loading credentials fails closed.

Backend-only policy:

- frontend credential access is prohibited
- `localStorage` and `sessionStorage` are prohibited for X credentials
- CSV/report/fixture/debug_log/exception output must not contain credentials
- frontend files must not contain X credential loader fields such as
  `bearer_token`, `api_key`, `api_secret`, or `authorization`
- existing stock-analysis J-Quants redaction strings are separate and must not
  become an X credential path

Tests verify:

- fake loader still works
- real loader raises the disabled error
- loader selection routes fake and real correctly
- unknown loader selection is rejected
- dry-run pipeline succeeds with fake loader
- dry-run pipeline fails closed with real loader
- frontend X credential loader fields are absent
- fake credential values do not leak to report, CSV, debug log, or exception

Related document:

- `docs/backend_credential_policy.md`

## Live Mode Release Policy

Added on 2026-06-03 as the release policy for future real X recent-search
reads. This is documentation only. It does not enable live mode, perform HTTP,
read API keys, read tokens, read cookies, modify `.env`, or post anything.

Policy document:

- `docs/live_mode_release_policy.md`

Live mode remains blocked until all release gates pass.

Required test gates:

- full unittest suite
- redaction tests
- credential leak tests
- pagination tests
- retry policy and retry queue tests
- request builder tests
- rate limit header parser tests
- HTTP error mapping tests
- response normalizer tests
- transport integration tests
- dry-run gate tests
- frontend credential leak tests

Live unlock requires multiple affirmative settings. `live_mode=true` alone is
not enough.

Minimum future release shape:

```text
dry_run=false
live_mode=true
credential_loader=real
transport=live
http_client=live
explicit_approval=true
read_only_recent_search=true
write_actions=false
```

Rollback shape:

```text
live_mode=false
transport=mock
credential_loader=fake
http_client=disabled
dry_run=true
```

Accident prevention:

- write APIs remain prohibited
- post APIs remain prohibited
- follow APIs remain prohibited
- like APIs remain prohibited
- repost APIs remain prohibited
- only read-only recent search can be considered

Operational preflight must confirm X API plan, recent-search availability,
`max_results`, pagination limits, public metrics availability,
`impression_count` availability, rate-limit windows, and `Retry-After`
behavior before any live read.

## X API Plan and Field Availability Research

Added on 2026-06-03 as documentation-only research. No X API call, HTTP API
request, credential lookup, token lookup, cookie lookup, `.env` change, real
data fetch, or posting was performed.

Research document:

- `docs/x_api_plan_field_research.md`

Key findings:

- Current official docs describe pay-per-usage pricing rather than the old
  Free / Basic / Pro table.
- Recent Search is documented as available to all developers.
- Recent Search retrieves posts from the last 7 days.
- Recent Search supports up to 100 posts per request.
- Recent Search supports pagination through `next_token`.
- Self-serve recent-search query length should be treated as 512 characters.
- Enterprise query length may be 4,096 characters, but must be confirmed.
- `public_metrics` includes likes, retweets/reposts, replies, quotes, bookmarks,
  and impressions in current metrics docs.
- Recent Search examples do not consistently show `impression_count`, so the
  field must remain optional.

Gap analysis summary:

- Existing nullable `impression_count` design is correct.
- Existing `score_source=engagement_fallback` design should remain the safe
  standard.
- Existing `next_token` and pagination design aligns with Recent Search.
- Query builder should continue using conservative length and operator checks.
- `days_back` must be capped to 7 for Recent Search.

Recommended first-live defaults:

- `max_results_per_genre=10`
- `max_pages=1`
- `days_back <= 7`
- `request_window=recent_7_days`
- query length limit `512`
- request fields:
  `tweet.fields=created_at,author_id,public_metrics`
- request expansion: `expansions=author_id`
- request user fields: `user.fields=username`

## Live HTTP Client Implementation Review

Added on 2026-06-03 as documentation-only implementation review. No live HTTP
client was implemented. No HTTP communication, X API call, credential lookup,
token lookup, cookie lookup, `.env` change, real data fetch, or posting was
performed.

Review document:

- `docs/live_http_client_review.md`

Responsibility boundary:

- receive one prepared `HttpRequest`
- send one request
- apply timeout values
- return one `HttpResponse`
- preserve status code, headers, body text, and parsed JSON

Out of scope:

- query generation
- credential loading
- pagination
- retry loops
- score calculation
- CSV output
- report output

Policies:

- read-only recent search only
- write/post/like/repost/follow/DM/media upload APIs remain prohibited
- timeout errors map through `HttpErrorInfo`
- `HttpClient` must not retry
- `HttpClient` must not handle `next_token`
- header values and credential-shaped values must not appear in logs, reports,
  CSV, or exceptions

Gap analysis:

- implementation prep exists: `HttpRequest`, `HttpResponse`, `HttpClient`,
  `DisabledHttpClient`, `map_http_error`, `RetryPolicy`, `RetryQueue`,
  `PaginationController`, `RequestBuilder`
- still missing: live-enabled HTTP implementation, no-leak live client tests,
  write-endpoint prevention tests, timeout/network/json parse mapping tests

## LiveHttpClient Disabled Skeleton

Added on 2026-06-03 as a fail-closed implementation point. No HTTP
communication, X API call, credential lookup, token lookup, cookie lookup,
`.env` read, environment variable read, real data fetch, or posting was
performed.

Implementation points:

- `x_auto_ops/live_http_client.py`
- `LiveHttpClient`
- `LiveHttpClientDisabledError`
- `docs/live_http_client_disabled.md`

Current behavior:

```text
LiveHttpClient.send(HttpRequest)
-> LiveHttpClientDisabledError("Live HTTP client disabled")
```

Compatibility:

- `LiveHttpClient` matches the `HttpClient` protocol shape.
- `LiveRecentSearchTransport` accepts `LiveHttpClient` via constructor
  injection.
- `LiveRecentSearchTransport` still raises before `LiveHttpClient.send(...)`.
- Direct `LiveHttpClient` errors map through `map_http_error(...)` as
  `disabled_http_client`.

Fail-closed checks:

- no `requests`
- no `httpx`
- no `urllib`
- no `socket`
- no `HTTPConnection`
- no `urlopen`
- no credential-shaped values in disabled exceptions or leak-test surfaces

## LiveRecentSearchTransport Final Implementation Review

Added on 2026-06-03 as a documentation-only final review. No HTTP
communication, X API call, credential lookup, token lookup, cookie lookup,
`.env` read, environment variable read, real data fetch, or posting was
performed.

Review document:

- `docs/live_recent_search_transport_final_review.md`

Final implementation responsibility:

- receive a query that has already been built by `QueryBuilder`
- call `RequestBuilder` to create a `HttpRequest`
- pass one `HttpRequest` to an injected `LiveHttpClient`
- convert `HttpResponse` into `TransportResponse`
- preserve `status_code`, `headers`, and `json_body`
- expose failures to `map_http_error(...)`
- keep `RateLimitParser` and `ResponseNormalizer` downstream

Out of scope for the transport:

- credential loading
- live mode decision
- pagination control
- retry loop
- retry queue enqueue
- score calculation
- genre detection
- CSV output
- report output

Reviewed connection order:

```text
CredentialLoader
-> LiveModeGate
-> QueryBuilder
-> RequestBuilder
-> PreflightValidation
-> LiveRecentSearchTransport
-> LiveHttpClient
-> TransportResponse
-> RateLimitParser
-> ResponseNormalizer
-> PaginationController
-> RetryPolicy / RetryQueue
```

Fail-closed conditions:

- `live_mode=false`
- `dry_run=true` with live transport
- `credential_loader=fake` with live transport
- `http_client=disabled`
- `explicit_approval=false`
- `write_actions=true`
- non-recent-search endpoint
- non-`GET` method
- preflight validation failure
- redaction preflight failure

Implementation gap:

- `TransportResponse.body_text` remains optional and should be added only if it
  is redacted and never written to report/CSV by default.
- Live transport implementation tests still need request-builder integration,
  one-request HTTP client injection, disabled gate ordering, redaction, 429,
  timeout, 401/403, 500, JSON parse, schema, and write-endpoint rejection
  coverage.

## Recent Search Endpoint Allowlist and Preflight Validation Skeleton

Added on 2026-06-03 as a fail-closed preflight layer. No HTTP communication,
X API call, credential lookup, token lookup, cookie lookup, `.env` read,
environment variable read, real data fetch, or posting was performed.

Implementation points:

- `x_auto_ops/preflight_validation.py`
- `PreflightValidationError`
- `RecentSearchAllowlistPolicy`
- `ValidationResult`
- `validate_recent_search_request(...)`
- `docs/preflight_validation.md`

Allowed method:

- `GET`

Allowed endpoints:

- `https://api.x.com/2/tweets/search/recent`
- `/2/tweets/search/recent`

Denied endpoint families:

- `/2/tweets`
- `/2/users`
- `/2/dm`
- `/2/media`
- `/2/users/:id/following`
- `/2/users/:id/likes`
- `/2/tweets/:id/liking`
- `/2/tweets/:id/retweeted_by`

Query validation:

- empty query is rejected
- query length greater than 512 is rejected
- empty endpoint is rejected
- non-positive timeout is rejected

Safe validation output:

- `allowed`
- `method`
- `endpoint`
- `query_length`
- `endpoint_name`
- `validation_reason`
- redacted header names only

Validation summaries do not expose query text or header values. Tests confirm
fake credential-shaped values do not leak to debug, report, CSV, exception, or
validation summary surfaces.

## PreflightValidation Integration and Fail-Closed Enforcement

Added on 2026-06-03 as a no-network integration between the preflight layer and
the disabled live transport. No HTTP communication, X API call, credential
lookup, token lookup, cookie lookup, `.env` read, environment variable read,
real data fetch, or posting was performed.

Current integrated order inside `LiveRecentSearchTransport.send_recent_search`:

```text
build_recent_search_request(...)
-> validate_recent_search_request(...)
-> RuntimeError("LiveRecentSearchTransport disabled")
```

Integration points:

- `x_auto_ops/live_recent_search_transport.py`
- `x_auto_ops/preflight_validation.py`
- `tests/test_preflight_transport_integration.py`
- `docs/preflight_transport_integration.md`

Fail-closed behavior:

- valid `GET` recent-search request passes preflight and then stops with
  `LiveRecentSearchTransport disabled`
- `POST`, `PUT`, `PATCH`, and `DELETE` fail with `PreflightValidationError`
- write endpoints fail with `PreflightValidationError`
- over-512-character queries fail with `PreflightValidationError`
- non-positive timeouts fail with `PreflightValidationError`
- endpoint allowlist violations fail with `PreflightValidationError`
- injected HTTP clients are not called in either valid or invalid cases

Redaction remains enforced for debug, report, CSV, exception, and validation
summary surfaces. Query text and header values are not emitted by the safe
preflight summary.

## Live Transport Release Readiness Review

Added on 2026-06-04 as a design review only. No implementation, HTTP
communication, X API call, credential lookup, token lookup, cookie lookup,
`.env` read, environment variable read, real data fetch, or posting was
performed.

Review document:

- `docs/live_transport_release_readiness.md`

Overall result:

- `READY`: non-live support modules and disabled-path safety tests
- `NEEDS_REVIEW`: live transport implementation readiness
- `BLOCKED`: live API execution

Reviewed connection order:

```text
CredentialLoader
-> LiveModeGate
-> QueryBuilder
-> RequestBuilder
-> PreflightValidation
-> LiveRecentSearchTransport
-> LiveHttpClient
-> TransportResponse
-> RateLimitParser
-> ResponseNormalizer
-> PaginationController
-> RetryPolicy
-> RetryQueue
```

Minimum live implementation scope:

- `LiveHttpClient`
- `RealCredentialLoader`
- `LiveRecentSearchTransport`

High-priority remaining tasks:

- implement backend-only real credential loading
- implement live HTTP send with timeout/error mapping and no retry loop
- implement live transport using Request Builder and Preflight Validation
- add live tests for auth, rate limit, server, timeout, JSON parse, schema, and
  redaction paths
- re-check current X API plan and recent-search limits before live release
