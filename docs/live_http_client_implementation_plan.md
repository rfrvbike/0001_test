# LiveHttpClient Implementation Plan

Date: 2026-06-06

Scope: planning only for the X API buzz post extraction system. No live HTTP
communication, X API connection, real credential read, `.env` edit, LiveMode
enablement, real data fetch, posting, write endpoint, stock analyzer change, or
broad dating_assistant change was performed.

## Goal

Define a safe, staged implementation plan for replacing the current
`LiveHttpClient` disabled skeleton with a future live HTTP implementation. The
plan keeps all live behavior blocked until the release policy, credential
boundary, redaction rules, and explicit approval gates are satisfied.

## Current HTTP-Related Components

Current components already present in the repository:

- `HttpClient` protocol
  - defines `send(HttpRequest) -> HttpResponse`
  - owns the one-request / one-response HTTP boundary
- `HttpRequest`
  - includes method, URL, headers, query parameters, and timeout seconds
- `HttpResponse`
  - includes status code, response headers, body text, and JSON body
- `DisabledHttpClient`
  - fails closed with `RuntimeError("HTTP client disabled")`
- `LiveHttpClient` disabled skeleton
  - matches the `HttpClient` protocol
  - raises `LiveHttpClientDisabledError("Live HTTP client disabled")`
  - imports no live HTTP libraries
- `RecentSearchTransport` / `MockRecentSearchTransport`
  - mock-only recent search transport path
- `LiveRecentSearchTransport` disabled skeleton
  - accepts an injected `HttpClient`
  - builds requests and runs preflight validation
  - remains disabled before any send
- `HTTP Error Mapping`
  - maps timeout, network, auth, rate limit, server, client, JSON parse,
    schema, and disabled-client failures into `HttpErrorInfo`
- `Rate Limit Parser`
  - parses `Retry-After`, `x-rate-limit-reset`, and remaining request headers
- `RetryPolicy` / `RetryQueue`
  - represent retry decisions and queued retry metadata without executing live
    retries
- `RedactedLiveSummary`
  - provides safe success and error summaries without raw credentials, raw
    responses, query text, post text, usernames, author IDs, or post ID lists

## LiveHttpClient Responsibility Boundary

`LiveHttpClient` should eventually be responsible for:

- receiving a prepared `HttpRequest`
- enforcing one request -> one response behavior
- applying reviewed timeout values
- sending only the prepared request through the approved HTTP library
- returning a bounded `HttpResponse`
- preserving status code and response headers for downstream parsers
- parsing JSON only when the response is JSON and the body is within bounds
- raising or returning errors in a form that can be mapped by
  `map_http_error(...)`
- never retrying internally
- never paginating internally
- never reading credentials
- never building queries
- never writing reports or CSV

`LiveHttpClient` must not be responsible for:

- credential loading
- LiveMode approval
- query generation
- request building
- endpoint allowlist enforcement
- retry loops
- retry queue enqueue
- pagination loops
- score calculation
- genre detection
- response normalization into `BuzzPost`
- report output
- CSV output
- posting, liking, reposting, following, DM, or media upload

## HTTP Library Choice

Recommended initial choice: `requests`, only after explicit live implementation
approval.

Rationale:

- simple synchronous API fits the current synchronous `HttpClient` protocol
- mature timeout handling
- easy to mock with injected test clients
- no async event-loop complexity for the first live read-only test

Alternatives:

- `httpx`
  - useful later if async support or richer timeout configuration becomes
    necessary
  - adds more implementation surface for the first live test
- `urllib`
  - avoids a third-party dependency but makes timeout, JSON, header, and error
    handling more verbose

Current task decision: do not add or import any HTTP library. Keep the plan
only.

## Timeout Policy

Recommended future configuration:

- connect timeout: 3 seconds
- read timeout: 10 seconds
- total timeout: 15 seconds target budget

Implementation notes:

- keep `HttpRequest.timeout_seconds` as the compatibility field
- if the selected HTTP library supports separate connect/read timeouts, derive
  them from reviewed config rather than hard-coding in the client
- timeout values must be validated before live send
- timeout failures map to `error_type=timeout`
- timeout failures are retryable in `HttpErrorInfo`, but `LiveHttpClient` itself
  must not retry

## Request Method and Endpoint Handling

`LiveHttpClient` should send only the already prepared `HttpRequest`.

Method and endpoint validation belongs to `RequestBuilder` and
`PreflightValidation`, not the HTTP client. Even so, the client implementation
should fail closed if it receives an obviously invalid request shape.

Allowed first live scope remains:

```text
GET /2/tweets/search/recent
```

Blocked scopes remain:

- `POST`
- `PUT`
- `PATCH`
- `DELETE`
- write endpoints
- all search endpoint for first live test
- posting, liking, reposting, following, DM, media upload

## Header and Credential Handling

`LiveHttpClient` may receive headers, including `Authorization`, only through
`HttpRequest` after `CredentialLoader`, `LiveModeGate`, and `RequestBuilder` have
run.

Rules:

- do not create credentials inside `LiveHttpClient`
- do not read credentials inside `LiveHttpClient`
- do not log header values
- do not include header values in exceptions
- do not include header values in debug output
- do not include token suffixes or partial token fingerprints
- expose header names only in safe diagnostic surfaces when needed
- keep credentials out of retry metadata and pagination metadata

## Response Handling

`HttpResponse.status_code`:

- required
- preserved exactly for error mapping and diagnostics

`HttpResponse.headers`:

- required for rate limit parsing
- raw values must not be written to reports or debug logs
- allow downstream `RateLimitParser` to inspect in memory only

`HttpResponse.body_text`:

- useful for JSON parsing and debugging failures
- must be bounded in memory
- must not be persisted to report, CSV, debug log, or exception text
- raw response body is blocked from `RedactedLiveSummary`

`HttpResponse.json_body`:

- populated only after safe JSON parse
- never persisted raw
- passed onward to `ResponseNormalizer` when status and schema are acceptable

## JSON Parse Boundary

Recommended future flow:

1. Receive `HttpResponse` body text.
2. If status is 204 or body is empty, return empty JSON body.
3. If content type is JSON or body looks JSON-shaped, parse once.
4. On parse failure, map to `json_parse_error`.
5. Do not include raw body in the mapped error.
6. Do not retry inside `LiveHttpClient`.

Schema validation belongs to `ResponseNormalizer`, not the HTTP client. Schema
failures should map to `schema_error` downstream.

## Error Mapping Plan

Error handling by type:

| Error Type | Detection Layer | Retryable | Summary Output | Report Output |
| --- | --- | --- | --- | --- |
| `timeout` | HTTP library timeout exception | yes | type, retryable, status if any | safe summary only |
| `network_error` | HTTP library connection exception | yes | type, retryable | safe summary only |
| `auth_error` | status 401/403 | no | type, status | safe summary only |
| `rate_limited` | status 429 or rate limit headers | yes | type, status, retry_after | safe summary only |
| `server_error` | status >= 500 | yes | type, status | safe summary only |
| `client_error` | status 400-499 except auth/rate limit | no | type, status | safe summary only |
| `json_parse_error` | JSON parsing failure | no | type, status | safe summary only |
| `schema_error` | normalizer/schema validation | no | type, status if any | safe summary only |
| `disabled_http_client` | disabled skeleton | no | type only | safe summary only |
| `unknown_error` | fallback wrapper | no by default | type only | safe summary only |

Raw exception messages must be redacted before they reach `HttpErrorInfo`,
reports, debug output, or `RedactedLiveSummary`.

## Rate Limit Handling

`LiveHttpClient` should preserve response status and headers in memory so that
`RateLimitParser` can detect:

- `Retry-After`
- `x-rate-limit-reset`
- `x-rate-limit-remaining`

The client must not sleep, back off, enqueue, or retry. Rate limit decisions are
owned by `RetryPolicy` and `RetryQueue`.

## Diagnostics Request ID

Recommended future behavior:

- generate request IDs outside or at the transport boundary
- pass request ID into `RedactedLiveSummary`
- do not derive request ID from credentials, query text, post IDs, usernames, or
  response body
- allow a UUID or monotonic local identifier

## Redaction and Safe Output Policy

The following must never appear in logs, reports, CSV, exceptions, retry
metadata, pagination metadata, fixtures, screenshots, or frontend surfaces:

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

Safe surfaces may include only allowlisted metadata such as endpoint name,
method, status code, query length, result count, retryability,
`retry_after_seconds`, and redacted diagnostics status.

## Implementation Steps

Recommended staged work:

1. Re-confirm current `HttpClient`, `HttpRequest`, and `HttpResponse` shapes.
2. Freeze the first-live timeout config shape.
3. Add tests around future `LiveHttpClient` construction without sending.
4. Add a fake injectable live-library adapter for unit tests only.
5. Implement one-request / one-response send behavior behind a fail-closed live
   approval flag.
6. Map timeout, network, auth, rate limit, server, client, JSON parse, schema,
   disabled, and unknown errors to `HttpErrorInfo`.
7. Add redaction regression tests for exception, debug, report, summary, retry,
   and pagination metadata.
8. Confirm no retry loop, no sleep, no backoff, no pagination, and no credential
   read inside `LiveHttpClient`.
9. Connect to `LiveRecentSearchTransport` only after the client passes disabled,
   mock, and no-leak tests.
10. Keep first live API test as a separate explicitly approved task.

## Test Strategy

Required future tests:

- tests pass without real HTTP communication
- `DisabledHttpClient` still never sends
- `LiveHttpClient` remains disabled until explicitly implemented and approved
- timeout maps to a safe `timeout` error
- network exceptions map to `network_error`
- 401/403 map to `auth_error`
- 429 maps to `rate_limited`
- 5xx maps to `server_error`
- other 4xx maps to `client_error`
- JSON parse failure maps to `json_parse_error`
- schema failure remains downstream and maps safely
- `Authorization` and bearer values never appear in logs, reports, summaries,
  exceptions, CSV, retry metadata, or pagination metadata
- response body text is never persisted raw
- live mode disabled means no send path is reachable
- CI does not require real HTTP or real credentials
- existing full unittest suite remains green

## Files for Future Implementation

Likely implementation files:

- `x_auto_ops/live_http_client.py`
- `x_auto_ops/http_client.py`
- `x_auto_ops/http_error_mapping.py`
- `tests/test_live_http_client_disabled.py`
- future `tests/test_live_http_client.py`
- relevant docs and `reports/latest_report.md`

Out of scope for the first LiveHttpClient implementation:

- `RealCredentialLoader` real storage adapters
- `LiveRecentSearchTransport` live send behavior
- pagination execution
- retry execution
- live CSV output
- write endpoints
- posting / liking / reposting / following / DM / media upload

## Final Recommendation

Proceed with `LiveHttpClient` implementation only after the RealCredentialLoader
and live release policies are reviewed. The first implementation should remain
backend-only, read-only, one-request-only, no-retry, no-pagination, fully
redacted, and fail-closed by default.
