# X API Plan and Field Availability Research

Research date: 2026-06-03

Scope: public documentation research only. No X API call, HTTP API request,
credential lookup, token lookup, cookie access, `.env` change, real data fetch,
or posting was performed.

## Sources

- X API pricing: <https://docs.x.com/x-api/getting-started/pricing>
- Search Posts introduction: <https://docs.x.com/x-api/posts/search/introduction>
- Recent Search endpoint: <https://docs.x.com/x-api/posts/search-recent-posts>
- Recent Search quickstart: <https://docs.x.com/x-api/posts/search/quickstart/recent-search>
- Fields: <https://docs.x.com/x-api/fundamentals/fields>
- Metrics: <https://docs.x.com/x-api/fundamentals/metrics>
- Search operators: <https://docs.x.com/x-api/posts/search/integrate/operators>
- Build a query: <https://docs.x.com/x-api/posts/search/integrate/build-a-query>
- Rate limits: <https://docs.x.com/x-api/fundamentals/rate-limits>

## Plan Availability

Current official docs describe the X API pricing model as pay-per-usage rather
than a Free / Basic / Pro subscription table. The pricing page says reads are
charged per returned resource and lists `Posts: Read` at `$0.005 per resource`.

The current Search introduction says:

- Recent Search searches posts from the last 7 days.
- Recent Search is available to all developers.
- Full-Archive Search is available to pay-per-use and Enterprise customers.

Because the old Free / Basic / Pro / Enterprise plan names are not presented as
the current primary access table in the official docs, the implementation should
not encode those plan names. Treat plan access as account/console-dependent and
verify it immediately before live implementation.

| Plan / access label | Recent Search status from current docs | Notes |
| --- | --- | --- |
| Free | Not confirmed as a current official read tier | Do not assume read access. Confirm in Developer Console. |
| Basic | Not confirmed as a current official subscription tier in current docs | If account is legacy, confirm endpoint access and caps. |
| Pro | Not confirmed as a current official subscription tier in current docs | If account is legacy, confirm endpoint access and caps. |
| Pay-per-use | Recent Search appears available to all developers | Pricing is per resource returned. |
| Enterprise | Recent Search available; higher query length likely available | Enterprise query length is 4,096 chars. |

## Recent Search Constraints

| Item | Current finding | Design implication |
| --- | --- | --- |
| Endpoint | `GET /2/tweets/search/recent` | Keep read-only transport scoped to this endpoint. |
| Time range | Last 7 days | `days_back` must be capped to 7 for recent search. |
| `max_results` | Default 10, allowed 10-100 | Keep safe default at 10-50; allow max 100. |
| Pagination | `meta.next_token`; send as `next_token` / `pagination_token` | Existing `next_token` design is correct. |
| Query length | Docs show 512 chars for self-serve recent search, 4,096 for Enterprise; endpoint reference also shows 1-4096 | Use conservative 512 unless account is confirmed Enterprise. |
| Sort | `recency` or `relevancy` | Default should remain recency unless a genre config explicitly opts into relevancy. |

## Field Availability

| Common field | X response field | Required parameters | Availability / risk | Current design status |
| --- | --- | --- | --- | --- |
| `post_id` | `id` | Default field | Available by default | OK |
| `text` | `text` | Default field | Available by default | OK |
| `created_at` | `created_at` | `tweet.fields=created_at` | Optional field; request explicitly | OK |
| `author_id` | `author_id` | `tweet.fields=author_id` | Optional field; request explicitly | OK |
| `author_username` | `includes.users[].username` | `expansions=author_id&user.fields=username` | Missing if expansion omitted or user unavailable | Keep nullable/missing handling |
| `like_count` | `public_metrics.like_count` | `tweet.fields=public_metrics` | Public metric | OK |
| `repost_count` | `public_metrics.retweet_count` | `tweet.fields=public_metrics` | X uses `retweet_count`; normalizer maps to repost | OK |
| `reply_count` | `public_metrics.reply_count` | `tweet.fields=public_metrics` | Public metric | OK |
| `quote_count` | `public_metrics.quote_count` | `tweet.fields=public_metrics` | Public metric, may be absent if metrics omitted | Keep missing handling |
| `impression_count` | `public_metrics.impression_count` | `tweet.fields=public_metrics` | Current metrics docs list it as public; still keep nullable because examples vary and plan/account behavior may differ | Keep optional |

## public_metrics and impression_count

Current metrics docs list these post metrics under `public_metrics`:

- `retweet_count`
- `quote_count`
- `like_count`
- `reply_count`
- `impression_count`
- `bookmark_count`

The fields docs also state that requesting `public_metrics` returns all metrics
as a group, not individual subfields. However, the Recent Search quickstart
example shows `retweet_count`, `reply_count`, `like_count`, and `quote_count`
without `impression_count`. Therefore:

- `public_metrics` should be requested for live reads.
- `impression_count` should remain nullable.
- `score_source=impression_weighted` may be used only when
  `impression_count` is present and numeric.
- `score_source=engagement_fallback` should remain the default-safe behavior.

## Query / Operator Constraints

| Operator / syntax | Finding | Design implication |
| --- | --- | --- |
| `lang:` | Supported; Japanese uses `lang:ja` | Query builder can append `lang:ja`. |
| `from:` | Supported standalone user operator | Target account support is aligned. |
| `OR` | Supported logical operator | Keep grouped `(a OR b)` generation. |
| Exact phrase | Supported with quoted phrases | Quote phrase keywords safely. |
| Exclusion | `-keyword` and negation supported | `exclude_keywords` maps well. |
| Grouping | Parentheses supported | Current query grouping is aligned. |
| Conjunction-required operators | Must be combined with at least one standalone operator | Query builder should reject queries made only of `lang:`, `has:`, `is:` etc. |
| Negated grouped operators | Not supported; docs recommend separate negations | Avoid `-(a OR b)`; emit `-a -b`. |
| Query length | Self-serve recent search 512 chars; Enterprise 4,096 chars | Default validation should use 512. |
| Broad queries | Docs warn broad queries consume usage quickly | Require at least one keyword, phrase, or `from:` account. |

## Rate Limits

Current rate-limit docs show:

| Endpoint | Per app | Per user | Notes |
| --- | ---: | ---: | --- |
| `GET /2/tweets/search/recent` | 450 / 15 min | 300 / 15 min | 10 default, 100 max results; 512 query length |
| `GET /2/tweets/search/all` | 1/sec, 300 / 15 min | 1/sec | 10 default, 500 max results; 1024 query length |
| `GET /2/tweets/counts/recent` | 300 / 15 min | n/a | 512 query length |

The rate-limit docs list these response headers:

- `x-rate-limit-limit`
- `x-rate-limit-remaining`
- `x-rate-limit-reset`

`Retry-After` is already included in the local parser design and should remain
supported for 429 handling even if not present in every documented example.

## Gap Analysis

### Current Design OK

- `BuzzPost.impression_count` is nullable.
- `metrics_missing` is already represented.
- `score_source` supports impression-aware and fallback scoring.
- `next_token` / pagination controller aligns with Recent Search pagination.
- Rate limit parser already handles reset and remaining headers.
- Query builder supports keywords, account filters, excludes, and `lang:ja`.
- Live transport is read-only and disabled.

### Design Changes Recommended

- Treat 512 characters as the default query length limit unless Enterprise is
  explicitly confirmed.
- Add a future query validation rule: reject conjunction-only queries.
- Add a future query validation rule: reject negated grouped expressions.
- Cap `days_back` to 7 for Recent Search.
- Default `max_results_per_genre` to a conservative value such as 10 or 25.
- Keep `impression_count` optional even though metrics docs list it as public.

### Plan Dependent

- Whether old Free / Basic / Pro labels apply to the account.
- Whether Enterprise query length is available.
- Whether spending limits or account caps are configured in Developer Console.
- Whether `impression_count` appears consistently in Recent Search responses for
  the account.

### User Confirmation Required Before Live

- Which X access model/account is available: pay-per-use, legacy tier, or
  Enterprise.
- Allowed monthly spend or read cap.
- Desired `max_results_per_genre`.
- Whether to include impressions in scoring when available.
- Whether broad keyword queries are acceptable given usage cost.

## Recommended Defaults

- `include_impressions_if_available=true`
- `score_source=engagement_fallback` as the safe default
- use `impression_weighted` only when `impression_count` exists
- `max_results_per_genre=10` for first live test
- `request_window=recent_7_days`
- `days_back <= 7`
- `max_pages=1` for first live test
- self-serve query length limit: 512 chars
- Enterprise query length limit: 4,096 chars only after confirmation
- request fields:
  - `tweet.fields=created_at,author_id,public_metrics`
  - `expansions=author_id`
  - `user.fields=username`

## Live Release Impact

The live release policy should require explicit confirmation of:

- access model and spending limit
- Recent Search availability
- 7-day search window
- 100 max results per request
- self-serve query length limit
- public metrics behavior
- impression availability
- rate-limit behavior

No live implementation should proceed until this confirmation is documented.
