# First Live Dry-Run Gate Test Plan

Date: 2026-06-06

Scope: planning only for the X API buzz post extraction system. No live HTTP
communication, X API connection, real credential read, `.env` edit, LiveMode
enablement, real data fetch, posting, write endpoint, stock analyzer change, or
broad dating_assistant change was performed.

## Goal

Define the safety gate that must pass before any future first live X API
connectivity test. This gate is not the live test itself. It is a reviewed
pre-live checklist and test plan that proves the system will fail closed unless
all first-live conditions are explicitly satisfied.

## Why This Gate Exists

The first live X API request has several risks:

- accidental credential exposure
- accidental write endpoint execution
- accidental repeated requests
- accidental pagination
- accidental retry after a timeout, rate limit, or server error
- accidental raw response persistence
- accidental broad query or sensitive query text exposure
- unexpected X API plan or rate-limit usage

The dry-run gate must prove that the future live path remains blocked unless
the approved first-live envelope is selected.

## Gate Conditions

The first live dry-run gate requires all of the following:

| Condition | Required Value | Confirmed By | Failure Behavior | Safe Report Output |
| --- | --- | --- | --- | --- |
| `dry_run` | `false` for the future live test | live gate config review | fail closed | setting name only |
| `live_mode` | `true` | `LiveModeGate` | fail closed | setting name only |
| `explicit_approval` | `true` | release checklist | fail closed | approval present flag |
| `credential_loader` | `real` | credential loader selection | fail closed | loader type only |
| `transport` | `live` | transport selection | fail closed | transport type only |
| `http_client` | `live` | client selection | fail closed | client type only |
| `read_only_recent_search` | `true` | preflight policy | fail closed | read-only flag |
| `write_actions` | `false` | preflight policy | fail closed | write disabled flag |
| `max_pages` | `1` | pagination config | fail closed | numeric value |
| `max_results` | `10` | query/request config | fail closed | numeric value |
| `retry_execution` | `false` | retry policy config | fail closed | retry disabled flag |
| `pagination_execution` | `false` | pagination config | fail closed | pagination disabled flag |
| `live_csv_output` | `false` | output config | fail closed | CSV disabled flag |
| `redacted_report_only` | `true` | output config | fail closed | redacted-only flag |

The gate must fail closed if any condition is missing, false, oversized, or set
to a broader mode than the first-live envelope.

## Validation Layers

Recommended validation order:

```text
Config Review
-> Credential Loader Selection Review
-> LiveModeGate
-> QueryBuilder
-> RequestBuilder
-> PreflightValidation
-> LiveRecentSearchTransport
-> LiveHttpClient
-> RedactedLiveSummary
```

The dry-run gate should stop before `LiveHttpClient` can send. It may construct
and validate safe local objects, but it must not perform HTTP communication.

## First-Live Query and Genre Plan

Recommended first-live query envelope:

- one genre only
- one query only
- Japanese language filter
- no sensitive personal terms
- no username or account targeting unless separately approved
- no broad operator-heavy query
- `max_results=10`
- no pagination
- no retry execution

Candidate genre:

```text
daily
```

Reason:

- lower sensitivity than relationship or personal-wound themes
- useful for validating recent-search connectivity
- easier to phrase with generic, non-personal keywords

Candidate query shape:

```text
(日常 OR 仕事前 OR コーヒー) lang:ja
```

The full query text should not be persisted in safe summaries or reports. Safe
diagnostics should record only `query_length`, endpoint name, method, and
result counts.

## Empty Result Policy

For the first live API test, an empty result can be considered a transport
success only if all of the following are true:

- HTTP status is `200`
- response JSON parses successfully
- `ResponseNormalizer` completes without schema error
- `result_count=0`
- no retry or pagination is attempted
- redacted summary contains no raw response or query text

If the goal is to prove post field normalization, an empty result is
insufficient and should be classified as `NEEDS_REVIEW`, not a failed transport.

## Preflight Validation Requirements

Before any future live request is allowed, preflight must confirm:

- method is `GET`
- endpoint is `https://api.x.com/2/tweets/search/recent`
- endpoint path is `/2/tweets/search/recent`
- query is non-empty
- query length is within the reviewed limit
- timeout is positive
- write endpoints are denied
- all-search endpoint is denied for first-live
- raw response persistence is disabled
- live CSV output is disabled
- retry execution is disabled
- pagination execution is disabled
- `max_pages=1`
- `max_results=10`

Credential existence may be checked as a boolean, but credential values must
not be printed, logged, included in exceptions, or written to reports.

## Redacted Summary Plan

Safe summary may include:

- `status`
- `endpoint_name`
- `method`
- `status_code`
- `query_length`
- `result_count`
- `normalized_post_count`
- `partial_result`
- `stop_reason`
- `rate_limited`
- `retryable`
- `retry_after_seconds`
- `pagination_used`
- `next_token_present`
- `metrics_missing_count`
- `execution_time_ms` or a bounded duration bucket
- `rollback_completed`

Safe summary must not include:

- credential values
- `Authorization` header
- raw request headers
- raw response headers
- raw response body
- raw JSON
- full query text
- post text
- username
- author ID
- post ID list
- access token
- refresh token
- client secret

## Failure Handling

Every failure stops the first-live path immediately. No retry, pagination,
fallback live request, CSV write, or raw report output is allowed.

| Failure | Expected Handling | Retry? | Report |
| --- | --- | --- | --- |
| credential missing | fail closed before request build | no | safe reason only |
| LiveMode disabled | fail closed at gate | no | safe reason only |
| approval missing | fail closed at release gate | no | approval missing flag |
| disabled_http_client | fail closed before send | no | safe error type |
| disabled_live_transport | fail closed before send | no | safe error type |
| timeout | map safely and stop | no for first live | safe error type |
| network_error | map safely and stop | no for first live | safe error type |
| auth_error | map safely and stop | no | status only |
| rate_limited | map safely and stop | no for first live | retry-after only |
| server_error | map safely and stop | no for first live | status only |
| client_error | map safely and stop | no | status only |
| json_parse_error | map safely and stop | no | safe type only |
| schema_error | map safely and stop | no | safe type only |
| empty result | success or needs-review by policy | no | count only |
| raw data exposure risk | fail closed and rollback | no | redacted incident flag |

## Rollback Requirements

Any unexpected behavior restores:

```text
dry_run=true
live_mode=false
credential_loader=fake
transport=mock
http_client=disabled
retry_execution=false
pagination_execution=false
live_csv_output=false
```

Rollback must also confirm:

- no retry task is pending
- no pagination request is pending
- no raw response was written
- no CSV with live data was written
- no credential marker appears in diagnostics
- mock dry-run pipeline still works

## Test Strategy

Future gate tests should verify:

- tests pass without live X API connection
- missing explicit approval fails closed
- `live_mode=false` fails closed
- `credential_loader != real` fails closed
- `transport != live` fails closed
- `http_client != live` fails closed
- `write_actions=true` fails closed
- `max_pages > 1` fails closed
- `max_results > 10` fails closed
- `retry_execution=true` fails closed
- `pagination_execution=true` fails closed
- `live_csv_output=true` fails closed
- raw response persistence enabled fails closed
- preflight blocks non-GET methods
- preflight blocks non-recent-search endpoints
- safe summary excludes credentials, query text, post text, usernames, author
  IDs, and post ID lists
- existing full unittest suite remains green

## Implementation Steps

Recommended staged work:

1. Confirm current LiveModeGate, PreflightValidation, RequestBuilder,
   RedactedLiveSummary, LiveHttpClient, and LiveRecentSearchTransport shapes.
2. Convert this gate condition table into a small config validation spec.
3. Define first-live query and genre in a reviewed local config example.
4. Define safe summary fields for first-live dry-run diagnostics.
5. Add fail-closed tests for every missing or unsafe gate condition.
6. Add redaction tests for gate diagnostics.
7. Add a dry-run command that evaluates the gate without HTTP communication.
8. Keep the first minimal live API test as a separate explicitly approved task.

## Non-Goals

This plan does not implement:

- real HTTP communication
- live X API access
- LiveMode enablement
- real credential reading
- `.env` changes
- token or secret file changes
- write endpoints
- posting, liking, reposting, following, DM, or media upload
- live CSV output
- retry execution
- pagination execution

## Final Recommendation

Implement the first live dry-run gate before any first minimal live API test.
The gate should prove that the future live path cannot run unless every
reviewed first-live condition is present, narrow, read-only, and redacted.
