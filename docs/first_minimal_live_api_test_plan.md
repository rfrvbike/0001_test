# First Minimal Live API Test Plan

Date: 2026-06-06

Scope: planning only for the X API buzz post extraction system. No live HTTP
communication, X API connection, real credential read, `.env` edit, LiveMode
enablement, real data fetch, posting, write endpoint, stock analyzer change, or
broad dating_assistant change was performed.

## Goal

Define the exact conditions for a future first minimal live X API connectivity
test. This document is not an approval to run that test. It is the final
pre-execution plan that describes the smallest safe live request, the success
criteria, the stop conditions, the redacted report shape, and the rollback
rules.

## What the First Minimal Test Proves

The first minimal live test should prove only that:

- one explicitly approved read-only recent-search request can be built
- the request passes preflight validation
- the request can be sent once through the reviewed live transport and live HTTP
  client
- status, headers, and JSON can be received into the backend boundary
- the response can be normalized or safely classified as empty
- a redacted diagnostic report can be produced
- no credentials, query text, post text, user identifiers, raw JSON, or raw
  response data are persisted

It must not prove:

- production collection readiness
- retry behavior
- pagination behavior
- scoring quality
- ranking quality
- CSV persistence of live data
- broad query coverage
- long-running operation

## Required Pre-Execution Conditions

Before this test can be executed, all of the following must be true:

| Requirement | Required State | If Not Met |
| --- | --- | --- |
| PR review status | PR #3 through PR #8 reviewed as applicable | stop |
| latest main tests | full unittest passes | stop |
| LiveMode | enabled only after explicit approval | stop |
| credential loading | real loader approved and user-confirmed | stop |
| endpoint | read-only recent search only | stop |
| write actions | disabled | stop |
| `max_results` | `10` | stop |
| `max_pages` | `1` | stop |
| retry execution | disabled | stop |
| pagination execution | disabled | stop |
| live CSV output | disabled | stop |
| raw response save | disabled | stop |
| report mode | redacted summary only | stop |
| user approval | explicit for the exact test window | stop |

Live execution remains blocked until every condition is reviewed and approved in
a separate implementation task.

## Test Envelope

First minimal live test envelope:

| Item | Value |
| --- | --- |
| endpoint | `https://api.x.com/2/tweets/search/recent` |
| method | `GET` |
| API action | read-only recent search |
| genre | `daily` recommended |
| query count | `1` |
| result count cap | `max_results=10` |
| page count cap | `max_pages=1` |
| retry | disabled |
| pagination | disabled |
| CSV output | disabled |
| report output | redacted summary only |
| response persistence | raw response disabled |
| execution count | one request only |

Recommended first query shape:

```text
(日常 OR 仕事前 OR コーヒー) lang:ja
```

The full query text must not be written to CLI output, report files, CSV,
debug logs, retry metadata, pagination metadata, exceptions, screenshots, or
frontend surfaces. Safe diagnostics may record only `query_length`.

## User Confirmation Text

The future live test should require an explicit confirmation such as:

```text
I approve one read-only X recent-search request with max_results=10, max_pages=1, no retry, no pagination, no live CSV, and redacted summary only.
```

Any broader, ambiguous, or missing confirmation must fail closed.

## Execution Flow

Approved minimal flow:

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
-> HTTP Error Mapping
-> ResponseNormalizer
-> RedactedLiveSummary
```

Excluded from the first live test:

- PaginationController execution
- RetryQueue enqueue
- RetryPolicy execution beyond classification
- scorer
- genre ranking
- CSV writer
- full report writer
- write API paths

## Success Criteria

The test is successful only if the selected success policy is met.

### Transport Success

Required:

- one HTTP request attempted
- method is `GET`
- endpoint is recent search
- status code is captured
- headers are captured in memory only
- raw header values are not reported
- JSON parse succeeds or empty JSON is safely classified
- RedactedLiveSummary is generated
- no credential marker appears anywhere in safe output
- no raw response is persisted
- no retry occurs
- no pagination occurs
- no live CSV is written

### Data Success

If posts are returned:

- `normalized_post_count >= 1`
- each returned post can be normalized in memory
- missing optional metrics are tolerated
- `impression_count` remains nullable
- no post text, username, author ID, or post ID list is reported

### Empty Result Success

An empty result may be accepted as a connectivity success if:

- HTTP status is `200`
- JSON parse succeeds
- normalizer completes without schema error
- `result_count=0`
- `normalized_post_count=0`
- redacted summary reports `stop_reason=completed` or a reviewed empty-result
  stop reason

However, empty result does not prove post-field normalization. It should be
reported as connectivity success with data-normalization coverage still pending.

## Failure Classification and Stop Conditions

Every failure stops immediately. No retry, no pagination, no second query, no
fallback live request, no RetryQueue enqueue, and no live CSV output are allowed.

| Failure | Classification | Action |
| --- | --- | --- |
| credential missing | config failure | stop before request |
| approval missing | release gate failure | stop before request |
| LiveMode disabled | release gate failure | stop before request |
| disabled_http_client | blocked implementation | stop before send |
| disabled_live_transport | blocked implementation | stop before send |
| auth_error | live failure | stop and rollback |
| rate_limited | live failure | stop and rollback |
| timeout | live failure | stop and rollback |
| network_error | live failure | stop and rollback |
| server_error | live failure | stop and rollback |
| client_error | live failure | stop and rollback |
| json_parse_error | response failure | stop and rollback |
| schema_error | response failure | stop and rollback |
| raw data exposure risk | safety failure | stop and rollback |
| unexpected write action path | safety failure | stop before request |
| `max_results > 10` | scope failure | stop before request |
| `max_pages > 1` | scope failure | stop before request |
| retry enabled | scope failure | stop before request |
| pagination enabled | scope failure | stop before request |
| live CSV enabled | scope failure | stop before request |

## Redacted Report Design

Allowed report fields:

- `status`
- `endpoint_name`
- `method`
- `status_code`
- `query_length`
- `result_count`
- `normalized_post_count`
- `rate_limited`
- `rate_limit_present`
- `rate_limit_remaining_present`
- `request_id_present`
- `next_token_present`
- `stop_reason`
- bounded duration bucket or `execution_time_ms`
- `partial_result`
- `error_type`
- `retryable`
- `retry_after_seconds`
- `rollback_completed`

Blocked report fields:

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

The report should be useful for connectivity validation without enabling data
inspection. The first live test is a transport and safety test, not a content
analysis task.

## Rollback Procedure

Any failure or unexpected behavior immediately restores:

```text
dry_run=true
live_mode=false
transport=mock
credential_loader=fake
http_client=disabled
retry_execution=false
pagination_execution=false
live_csv_output=false
raw_response_save=false
```

Rollback verification:

- mock dry-run pipeline still works
- live flags are disabled
- no live CSV exists
- no raw response file exists
- no retry task is pending
- no pagination token is scheduled for follow-up
- redacted summary contains no credential markers
- report contains no query text, post text, username, author ID, or post ID list

## Staged Implementation Plan

Recommended sequence before the first live call:

1. Complete and review this first minimal live API test plan.
2. Review the first live dry-run gate plan and convert it into tests.
3. Implement and test `RealCredentialLoader` in fail-closed stages.
4. Implement and test `LiveHttpClient` with no retry and no raw persistence.
5. Implement and test `LiveRecentSearchTransport` integration.
6. Run dry-run gate tests with mock and disabled components.
7. Run mock first-live-equivalent success and failure cases.
8. Request explicit user approval for exactly one read-only recent-search call.
9. Execute one minimal live request only.
10. Produce redacted report and immediately re-disable live settings unless a
    separate follow-up approval is granted.

## Test Strategy

Before any real live call, tests should verify:

- no live X API connection is needed for the test suite
- missing approval fails closed
- LiveMode disabled fails closed
- write action path fails closed
- `max_results > 10` fails closed
- `max_pages > 1` fails closed
- retry execution enabled fails closed
- pagination execution enabled fails closed
- live CSV output enabled fails closed
- raw response save enabled fails closed
- redacted report excludes credentials, query text, post text, usernames,
  author IDs, and post ID lists
- existing full unittest suite remains green

## Non-Goals

This plan does not implement:

- live HTTP communication
- X API connection
- LiveMode enablement
- real credential reading
- `.env` changes
- token or secret file changes
- write endpoints
- posting, liking, reposting, following, DM, or media upload
- production collection
- live CSV output
- retry execution
- pagination execution

## Final Recommendation

Do not run the first minimal live API test until the dry-run gate is implemented
and passes, the live client and transport implementations are reviewed, the
credential loader is reviewed, and the user gives exact one-request approval.
