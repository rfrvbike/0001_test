# Live API Minimal Test Plan Review

Date: 2026-06-05

This document defines the proposed conditions for the first future live X API
connectivity test. It is a design review only. It does not enable live mode,
perform HTTP communication, call the X API, use an HTTP library, read
credentials, modify `.env`, read environment variables, fetch real data, or
post to X.

## Review Decision

Plan status: `NEEDS_REVIEW`

Execution status: `BLOCKED`

The first live connectivity test should be a deliberately narrow, read-only
recent-search test. It must prove only that one approved request can travel
through the reviewed read pipeline and return a normalizable response. It must
not test pagination, retries, scoring, CSV output, or broad collection.

## First Live Connection Minimum Scope

Recommended first-live test envelope:

| Setting | First-live value | Reason |
| --- | --- | --- |
| API scope | read-only recent search only | prevents write actions |
| genre count | 1 | minimizes query and classification variables |
| query count | 1 | enforces one-request review |
| `max_results` | 10 | smallest conservative result count |
| `max_pages` | 1 | prevents pagination |
| request window | recent 7 days | matches recent-search design |
| pagination | prohibited | first test validates one response only |
| retry | prohibited | prevents repeated live requests |
| RetryQueue | not used | prevents delayed or automatic requests |
| score calculation | not used | connectivity test only |
| CSV output | prohibited | avoids real-data persistence |
| report output | redacted summary only | no post text, raw response, or credentials |

Additional restrictions:

- one approved `GET /2/tweets/search/recent` request only
- one response or one mapped failure only
- no `next_token` follow-up
- no retry after timeout, rate limit, server error, or network error
- no raw response body persistence
- no full post text in diagnostics
- no public-metric requirement for success
- no impression-count requirement for success

## Success Conditions

The first live connectivity test is successful only when all required
conditions are met.

| Condition | Required | Success Interpretation |
| --- | --- | --- |
| HTTP status is `200` | yes | approved recent-search request succeeded |
| `status_code` is captured | yes | transport response boundary works |
| response headers are captured | yes | header boundary works; values remain non-logged |
| `json_body` is captured | yes | response can be passed to the normalizer |
| ResponseNormalizer completes | yes | response shape is safely consumable |
| at least one `post_id` is obtained | yes, unless valid empty result is explicitly approved | common post identity is available |
| `text` is obtained | yes for returned posts | common post text is available in memory only |
| `created_at` is obtained | preferred | missing value is recorded without crashing |
| missing `public_metrics` is tolerated | yes | missing metrics do not fail connectivity test |
| missing optional metrics are recorded | yes | normalizer missing-field behavior remains intact |
| redacted summary contains no credential markers | yes | leak protection remains intact |
| only one HTTP request occurred | yes | One Request Rule remains intact |

A valid empty result should be reviewed separately before being accepted as a
successful first-live test, because an empty response cannot prove post-field
normalization.

Success does not require:

- `public_metrics`
- `impression_count`
- scoring
- genre classification
- CSV output
- report output beyond a redacted summary
- pagination
- retry

## Failure Conditions

Every failure ends the first-live test immediately. No retry, pagination,
fallback live request, or RetryQueue enqueue is allowed.

| Failure Type | Expected Behavior | First-live Result |
| --- | --- | --- |
| `auth_error` | map safely, redact details, stop immediately | failed; rollback |
| `timeout` | map timeout, do not retry or sleep | failed; rollback |
| `network_error` | map network failure, do not retry | failed; rollback |
| `rate_limited` | preserve redacted rate-limit metadata, do not retry or enqueue | failed; rollback |
| `server_error` | preserve status, do not retry | failed; rollback |
| `client_error` | preserve status, do not alter query and resend | failed; rollback |
| `json_parse_error` | do not emit raw body, stop normalization | failed; rollback |
| `schema_error` | record redacted schema summary, stop | failed; rollback |

Immediate stop conditions also include:

- more than one HTTP request attempt
- any pagination attempt
- any retry or backoff attempt
- any write endpoint attempt
- any non-recent-search endpoint attempt
- any credential marker in diagnostics
- any raw response or post data written to CSV/report

## Rollback Procedure

Any failed condition or unexpected behavior immediately restores:

```text
live_mode=false
transport=mock
credential_loader=fake
http_client=disabled
dry_run=true
```

Rollback sequence:

1. Stop the live test process.
2. Restore all five fail-closed settings.
3. Confirm no retry task or pagination request is pending.
4. Confirm no real response data was written to CSV or report files.
5. Confirm redacted diagnostics contain no credential markers.
6. Run the mock dry-run pipeline.
7. Keep live mode blocked until the failure is reviewed.

Rollback is required even for apparently temporary failures such as timeout,
rate limit, network error, or server error. The first-live test does not retry.

## Execution Order Review

Reviewed minimum flow:

```text
CredentialLoader
-> LiveModeGate
-> QueryBuilder
-> RequestBuilder
-> PreflightValidation
-> LiveRecentSearchTransport
-> LiveHttpClient
-> TransportResponse
-> ResponseNormalizer
```

Review result:

- the sequence is appropriate for a first-live connectivity test
- QueryBuilder and RequestBuilder remain upstream of transport
- PreflightValidation must run before the HTTP client
- LiveHttpClient performs one request only
- TransportResponse preserves the response boundary
- ResponseNormalizer proves common-field compatibility
- RateLimitParser may inspect headers for a mapped failure, but must not trigger
  retry
- PaginationController, RetryPolicy, RetryQueue, scorer, genre detection, CSV
  writer, and full report writer are intentionally excluded

## Redacted Summary

The only permitted report output for the first-live test is a redacted summary
containing fields such as:

- test timestamp
- endpoint name
- method
- query length
- requested `max_results`
- request count
- status code
- response header names, without values
- normalized post count
- missing-field counts
- success/failure classification
- rollback completed boolean

The summary must not contain:

- query text
- post text
- raw response
- raw response body
- response header values
- authorization values
- credentials
- usernames or author identifiers

Detailed schema and field classification are reviewed in
`docs/redacted_live_summary_review.md`. The first-live summary must use only
allowlisted count, boolean, enum, timing, and status fields. It must not contain
raw response data, full query text, full post text, header values, usernames,
author IDs, or post ID lists.

## Gap Analysis

### READY

- proposed one-query, one-page, ten-result scope
- read-only recent-search allowlist
- QueryBuilder
- RequestBuilder
- PreflightValidation
- TransportResponse shape
- ResponseNormalizer missing-field tolerance
- redaction policy
- rollback configuration
- mock and disabled-path tests

### NEEDS_REVIEW

- exact first-live query and genre
- whether a valid empty response counts as success
- exact redacted summary schema
- current X API plan and recent-search availability at test time
- first-live test operator and approval owner
- test window and spend limit
- live timeout values
- live implementation tests for all mapped failures

### BLOCKED

- first-live test execution
- LiveMode enablement
- real credential loading
- live HTTP implementation
- live transport implementation
- HTTP library selection and use
- any retry, pagination, RetryQueue use, scoring, CSV persistence, or broad
  collection during the first-live test
- write APIs and posting actions

## Pre-Test Approval Checklist

- all unittest, redaction, and credential leak tests pass
- RealCredentialLoader implementation and storage policy are approved
- LiveHttpClient implementation is approved
- LiveRecentSearchTransport implementation is approved
- recent-search endpoint allowlist remains enforced
- One Request Rule is test-covered
- no-retry and no-pagination behavior is test-covered
- selected query and genre are reviewed
- `max_results=10` and `max_pages=1` are fixed
- rollback settings are ready
- redacted-summary schema is approved
- explicit live test approval is recorded

## Safety Confirmation

This review does not perform the proposed test. Live mode remains disabled, and
the first-live test remains blocked until every implementation and approval gate
is satisfied.
# Mock Validation of Redacted Live Summary

Before any first live connectivity check, the mock/dry-run recent-search
pipeline validates the proposed safe diagnostic surface:

- a typed `RedactedLiveSummary` is generated for success, partial, and
  rate-limited fixtures
- CLI and report output use only the bounded safe debug summary
- query text, post content, user information, IDs, raw response, and raw JSON
  remain outside the diagnostic report
- the ranked-post CSV remains separate from diagnostic summary output

This mock integration does not change any live release condition and does not
enable LiveMode.

## Mock Validation of Error Summaries

Before first live connectivity, failed-connectivity diagnostics can be validated
through `HttpErrorInfo -> RedactedLiveSummary` without making HTTP requests.

The mock error-summary path covers:

- `auth_error`
- `timeout`
- `network_error`
- `rate_limited`
- `server_error`
- `client_error`
- `json_parse_error`
- `schema_error`
- `disabled_http_client`

Each summary uses safe metadata only: status, endpoint name, method, status
code, query length, retryability, retry-after seconds, partial-result flag, and
the stable error type as `stop_reason`. Raw exception messages, raw responses,
raw JSON, query text, post text, user data, IDs, headers, and credentials remain
outside the summary.

The CLI exposes this validation as synthetic mock error mode:

```powershell
python tools/mock_recent_search_pipeline.py --dry-run --mock-error-type rate_limited
```

Synthetic error mode is still outside the first-live execution path. It creates
local `HttpErrorInfo`, builds a redacted summary, writes a safe report summary,
and skips ranked-post CSV output. It does not call mock transport for the error
case, perform HTTP, read credentials, enable LiveMode, retry, paginate, or
persist real response data.
