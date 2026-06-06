# LiveRecentSearchTransport Implementation Plan

Date: 2026-06-06

Scope: planning only for the X API buzz post extraction system. No live HTTP
communication, X API connection, real credential read, `.env` edit, LiveMode
enablement, real data fetch, posting, write endpoint, stock analyzer change, or
broad dating_assistant change was performed.

## Goal

Define a safe, staged implementation plan for replacing the current
`LiveRecentSearchTransport` disabled skeleton with a future live recent-search
transport. The first implementation must remain read-only, recent-search-only,
redacted, and fail-closed until every live release condition is explicitly
approved.

## Current Recent Search Components

Current components already present in the repository:

- `RecentSearchTransport`
  - protocol with `send_recent_search(query) -> TransportResponse`
  - common boundary for mock and future live transport
- `TransportResponse`
  - currently includes `status_code`, `headers`, and `json_body`
- `MockRecentSearchTransport`
  - fixture-backed transport
  - never opens sockets, never reads credentials, and never touches `.env`
- `LiveRecentSearchTransport`
  - disabled skeleton
  - accepts an injected `HttpClient`
  - accepts an injected `CredentialBundle`
  - builds a request and runs preflight validation
  - then raises `RuntimeError("LiveRecentSearchTransport disabled")`
- `LiveHttpClient`
  - disabled skeleton
  - future one-request / one-response HTTP boundary
- `HttpClient`
  - protocol with `send(HttpRequest) -> HttpResponse`
- `Query Builder`
  - builds safe recent-search query strings from genre configuration
- `Request Builder`
  - builds `HttpRequest` and maps header names without exposing header values
- `Preflight Validation`
  - enforces GET and recent-search-only allowlist
  - blocks write endpoints and invalid request shapes
- `Response Normalizer`
  - converts X recent-search-shaped JSON into `BuzzFetchResult`
- `Rate Limit Parser`
  - parses `Retry-After`, reset, and remaining request headers
- `HTTP Error Mapping`
  - maps live/client failures to `HttpErrorInfo`
- `RetryPolicy` / `RetryQueue`
  - represent retry decisions and queued retry metadata without executing live
    retries
- `PaginationController`
  - owns future page iteration and stop reasons
- `RedactedLiveSummary`
  - provides safe success and error diagnostics

## Responsibility Boundary

`LiveRecentSearchTransport` should eventually be responsible for:

- receiving a query string already produced by `Query Builder`
- building a recent-search `HttpRequest` through `Request Builder`
- running `PreflightValidation` before any HTTP send attempt
- passing the request to an injected `HttpClient`
- converting `HttpResponse` into `TransportResponse`
- preserving status code and headers in memory for downstream parsers
- returning JSON body for downstream `ResponseNormalizer`
- catching transport-layer failures and handing them to `HTTP Error Mapping`
- preserving fail-closed behavior when live mode, credentials, HTTP client, or
  explicit approval are not ready

`LiveRecentSearchTransport` must not be responsible for:

- loading credentials
- deciding whether live mode is allowed
- generating query text from genre config
- doing HTTP itself
- retry loops
- retry queue enqueue
- pagination loops
- score calculation
- genre detection
- CSV output
- report output
- persisting raw responses
- posting, liking, reposting, following, DM, or media upload

## Intended Live Flow

Future live flow:

```text
CredentialLoader
-> LiveModeGate
-> QueryBuilder
-> RequestBuilder
-> PreflightValidation
-> LiveRecentSearchTransport
-> LiveHttpClient
-> HttpResponse
-> TransportResponse
-> RateLimitParser
-> HTTP Error Mapping
-> ResponseNormalizer
-> RedactedLiveSummary
-> PaginationController
-> RetryPolicy / RetryQueue
```

For the first live test, pagination and retry execution should remain disabled.

## Recent Search Endpoint Scope

Allowed first live endpoint:

```text
GET /2/tweets/search/recent
```

Allowed host:

```text
https://api.x.com
```

Blocked for this transport:

- `POST`
- `PUT`
- `PATCH`
- `DELETE`
- `/2/tweets`
- `/2/users`
- `/2/dm`
- `/2/media`
- `/2/tweets/search/all`
- write endpoints
- posting, liking, reposting, following, DM, media upload

Endpoint enforcement belongs primarily to `PreflightValidation`, but the
transport should preserve a fail-closed stance if it receives a request that
does not match the recent-search-only policy.

## Query Builder Boundary

`Query Builder` owns:

- keyword joins
- account filters
- exclusions
- language filters
- query length constraints
- source genre recording

`LiveRecentSearchTransport` must not log or persist the full query. It may pass
the query to `Request Builder` and safe diagnostics may include only
`query_length`.

## Request Builder Boundary

`Request Builder` owns:

- recent-search endpoint URL
- method
- query params
- authorization header construction from an already loaded credential bundle
- timeout seconds
- safe request build summary with header names only

`LiveRecentSearchTransport` may call `Request Builder`, but must not create,
read, or mutate credentials.

## HttpClient Boundary

`LiveRecentSearchTransport` owns transport orchestration. `LiveHttpClient` owns
the single HTTP send.

Rules:

- injected `HttpClient` only
- no direct HTTP library calls in the transport
- no retry loop in the transport
- no sleep or backoff in the transport
- no pagination loop in the transport
- map errors rather than persisting raw exception details

## Response Normalizer Boundary

`ResponseNormalizer` owns:

- parsing X recent-search-shaped JSON into `BuzzPost` fields
- missing metric handling
- missing author handling
- next token extraction
- partial result metadata

`LiveRecentSearchTransport` should not normalize posts. It should return a
`TransportResponse` shape that lets downstream code normalize safely.

## Retry and Rate Limit Boundary

`RateLimitParser` owns:

- `Retry-After`
- `x-rate-limit-reset`
- `x-rate-limit-remaining`

`RetryPolicy` owns:

- retryable decision
- max retry count
- retry-after decision

`RetryQueue` owns:

- retry task storage
- ready task dequeue

`LiveRecentSearchTransport` must not enqueue retry tasks or retry requests. It
should preserve status and headers in memory so downstream layers can decide.

## Pagination Boundary

`PaginationController` owns:

- next token progression
- max results
- max pages
- fetched count
- stop reason
- partial result state

`LiveRecentSearchTransport` should perform only one query send per call. It
should not loop on `next_token`.

First-live policy:

- `max_results=10`
- `max_pages=1`
- pagination disabled
- retry execution disabled
- CSV live output disabled
- report redacted summary only

## Error Handoff Plan

| Error Type | Source | Transport Responsibility | Retryable | Pagination Continues | Safe Output |
| --- | --- | --- | --- | --- | --- |
| `timeout` | `HttpClient` exception | map through `HTTP Error Mapping` | yes | no for first live | type, retryable |
| `network_error` | `HttpClient` exception | map through `HTTP Error Mapping` | yes | no for first live | type, retryable |
| `auth_error` | status 401/403 | preserve status and map | no | no | type, status |
| `rate_limited` | status 429 or headers | preserve headers for parser | yes | no | type, retry_after |
| `server_error` | status >= 500 | map safely | yes | no | type, status |
| `client_error` | other 4xx | map safely | no | no | type, status |
| `json_parse_error` | `HttpClient` or downstream parse | map safely | no | no | type, status if available |
| `schema_error` | normalizer | downstream mapping | no | no | type, status if available |
| `disabled_http_client` | disabled client | map safely | no | no | type only |
| `disabled_live_transport` | transport gate | stop before send | no | no | type only |
| `unknown_error` | fallback wrapper | map safely | no by default | no | type only |

Raw exception messages, raw headers, raw body, raw JSON, query text, post text,
usernames, author IDs, post ID lists, and credential values must never be
included in safe output.

## Redaction and Safe Output Policy

Blocked from all logs, reports, CSV, exceptions, retry metadata, pagination
metadata, fixtures, screenshots, and frontend surfaces:

- `Authorization`
- bearer token values
- API keys
- API secrets
- cookies
- credential bundle contents
- raw request headers
- raw response headers
- raw response body
- raw JSON
- full query text
- full post text
- usernames
- author IDs
- post ID lists

Allowed safe diagnostic fields:

- endpoint name
- method
- status code
- query length
- result count
- normalized post count
- rate limited flag
- retryable flag
- retry-after seconds
- partial result flag
- next token present flag
- stop reason
- execution time

## First-Live Dry-Run Gate Relationship

The later first-live dry-run gate should require explicit configuration before
live send is reachable:

```text
dry_run=false
live_mode=true
credential_loader=real
transport=live
http_client=live
explicit_approval=true
read_only_recent_search=true
write_actions=false
max_pages=1
retry_execution=false
live_csv_output=false
```

If any condition is missing, fail closed before the HTTP client sends.

The first live test should define:

- one genre
- one query
- `max_results=10`
- minimal fields
- no pagination
- no retry execution
- no CSV output
- redacted report only
- explicit user approval

## Empty Result Policy

An HTTP 200 response with an empty `data` array should count as a valid transport
success if:

- status code is 200
- JSON parses successfully
- response normalizer returns zero posts without schema failure
- safe summary records `result_count=0`

Empty result should not be treated as an error by the transport.

## Implementation Steps

Recommended staged work:

1. Re-confirm `RecentSearchTransport`, `TransportResponse`, `HttpClient`, and
   `HttpResponse` shapes.
2. Freeze the minimum live `TransportResponse` shape, including whether
   `body_text` should be added or remain HTTP-client-only.
3. Define `disabled_live_transport` error mapping behavior.
4. Keep `LiveRecentSearchTransport` disabled by default.
5. Add tests for request build -> preflight -> disabled transport order.
6. Add tests for injected `HttpClient` error handoff without real HTTP.
7. Add tests for 401/403, 429, 5xx, and empty result handling through fake
   responses.
8. Add redaction regression tests for debug, report, summary, exception, retry,
   and pagination metadata.
9. Add first-live dry-run gate tests that verify live transport is unreachable
   until all explicit flags are present.
10. Defer actual first live API call to a later explicitly approved task.

## Test Strategy

Required future tests:

- tests pass with no live X API connection
- disabled transport never sends
- mock transport still validates the normal path
- LiveMode disabled blocks before live transport
- request build and preflight happen before disabled transport error
- invalid endpoint fails preflight before transport
- invalid method fails preflight before transport
- `HttpClient` timeout maps to safe error summary
- `HttpClient` network error maps safely
- 401/403 map to `auth_error`
- 429 maps to `rate_limited`
- 5xx maps to `server_error`
- empty result is handled safely
- pagination token metadata is safe
- query text, post text, credentials, username, author ID, and post ID lists do
  not leak to log, report, CSV, summary, retry metadata, pagination metadata, or
  exception text
- existing full unittest suite remains green

## Files for Future Implementation

Likely implementation files:

- `x_auto_ops/live_recent_search_transport.py`
- `x_auto_ops/mock_transport.py`
- `x_auto_ops/http_error_mapping.py`
- `x_auto_ops/redacted_live_summary.py`
- `tests/test_preflight_transport_integration.py`
- future `tests/test_live_recent_search_transport.py`
- relevant docs and `reports/latest_report.md`

Out of scope for the first transport implementation:

- real credential storage adapters
- live HTTP library implementation
- live API execution
- pagination execution
- retry execution
- live CSV output
- write endpoints
- posting, liking, reposting, following, DM, media upload

## Final Recommendation

Implement `LiveRecentSearchTransport` only after `RealCredentialLoader` and
`LiveHttpClient` implementation plans are reviewed. The first implementation
should remain recent-search-only, one-request-only, no-retry, no-pagination,
fully redacted, and fail-closed by default.
