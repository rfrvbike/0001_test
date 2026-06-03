# Live HTTP Client Implementation Review

Review date: 2026-06-03

Scope: design review only. No live HTTP client was implemented. No HTTP
communication, X API call, credential lookup, token lookup, cookie access,
`.env` change, real data fetch, or posting was performed.

## Current Decision

Live HTTP remains disabled.

The only implemented HTTP client is:

```text
DisabledHttpClient
-> RuntimeError("HTTP client disabled")
```

Any future `LiveHttpClient` must be added behind the Live Mode Release Policy.

## Live HttpClient Responsibilities

A future live HTTP client may own only the low-level send/receive boundary:

- receive one prepared `HttpRequest`
- send exactly one HTTP request
- apply configured timeout values
- return one `HttpResponse`
- preserve `status_code`
- preserve response headers
- preserve raw `body_text`
- preserve parsed `json_body` when JSON parsing succeeds
- raise or return errors that can be mapped through `map_http_error(...)`

The expected interface remains:

```text
HttpClient.send(request: HttpRequest) -> HttpResponse
```

## Explicit Non-Responsibilities

The HTTP client must not own:

- query generation
- request building
- credential loading
- authorization header creation
- live mode approval
- pagination control
- retry loops
- retry queue scheduling
- score calculation
- genre detection
- CSV output
- report output
- raw response persistence

## Allowed Endpoint Scope

Only read-only recent search may be considered:

```text
GET /2/tweets/search/recent
```

The client must not expose a generic write-capable X API surface to this
pipeline.

## Prohibited Actions

The following remain prohibited:

- write API
- post API
- like API
- repost API
- follow API
- DM API
- media upload API
- delete API
- profile update API

Any implementation that can reach these actions is a release blocker.

## Error Mapping Alignment

The existing mapping target is:

```text
x_auto_ops/http_error_mapping.py
HttpErrorInfo
map_http_error(...)
```

Supported error types already align with the future live client:

| Error type | Source | Retryable |
| --- | --- | --- |
| `timeout` | connect/read/total timeout | yes |
| `network_error` | DNS/socket/TLS/client exception | yes |
| `auth_error` | 401/403 | no |
| `rate_limited` | 429 or rate-limit headers | yes |
| `server_error` | 5xx | yes |
| `client_error` | 4xx except auth/rate-limit | no |
| `json_parse_error` | invalid JSON response | no |
| `schema_error` | valid JSON with unexpected required shape | no |
| `disabled_http_client` | current fail-closed client | no |

The HTTP client must not perform retries directly. It should surface the failure
so the transport/controller can call `map_http_error(...)`.

## Redaction Review

The following strings and credential-shaped values must never appear in logs,
reports, CSV, exceptions, or transport debug output:

- `Authorization`
- `Bearer`
- `API_KEY`
- `TOKEN`
- `SECRET`
- `COOKIE`

Allowed diagnostics:

- endpoint name
- method
- status code
- query length
- query parameter names
- header names after redaction
- timeout values
- rate limit booleans and counters

Disallowed diagnostics:

- header values
- raw authorization header
- bearer token
- API key
- cookie
- full request object if it includes headers
- full response body when it may contain sensitive metadata

## Credential Boundary

The credential flow remains:

```text
CredentialLoader
-> LiveModeGate
-> LiveRecentSearchTransport
-> RequestBuilder
-> LiveHttpClient
```

Credential rules:

- `HttpClient` must not load credentials.
- `HttpClient` must not read `.env`.
- `HttpClient` must not read environment variables.
- `HttpClient` must not create credentials.
- Authorization headers may only arrive inside a prepared `HttpRequest`.
- Header values must not be copied into debug output.

## Timeout Policy

Recommended future timeout shape:

| Timeout | Recommended first-live value | Notes |
| --- | ---: | --- |
| connect timeout | 3 seconds | Fail fast when network path is unavailable. |
| read timeout | 10 seconds | Avoid hanging on slow responses. |
| total timeout | 15 seconds | Bound one request end-to-end. |

The existing `HttpRequest.timeout_seconds` can remain a total timeout field for
the skeleton. If a future HTTP library supports separate connect/read timeout
values, add explicit fields only after tests cover them.

## Retry Policy

The HTTP client must not retry.

Future flow:

```text
LiveHttpClient.send(...)
-> HttpResponse or exception
-> map_http_error(...)
-> RetryPolicy.decide(...)
-> RetryQueue.enqueue(...)
```

Retryable cases:

- `timeout`
- `network_error`
- `rate_limited`
- `server_error`

Non-retryable cases:

- `auth_error`
- `client_error`
- `json_parse_error`
- `schema_error`
- `disabled_http_client`

## Pagination Policy

The HTTP client sends one request only.

Pagination remains outside:

```text
PaginationController
-> RequestBuilder(next_token)
-> LiveRecentSearchTransport
-> LiveHttpClient
```

`next_token`, max pages, max results, partial results, and stop reasons remain
controller concerns.

## Response Handling Policy

The future live client should:

- keep the numeric status code
- keep response headers as strings
- keep raw body text only in memory
- parse JSON into `json_body` when possible
- map invalid JSON to `json_parse_error`
- avoid writing raw bodies to disk
- avoid including raw bodies in exceptions unless redacted and bounded

## Gap Analysis

### Implementation Preparation Complete

- `HttpRequest`
- `HttpResponse`
- `HttpClient` protocol
- `DisabledHttpClient`
- `map_http_error(...)`
- `HttpErrorInfo`
- `RetryPolicy`
- `RetryQueue`
- `PaginationController`
- `RequestBuilder`
- redaction utility
- live mode release policy

### Implementation Before Live Review

- `LiveHttpClient`
- tests for timeout mapping
- tests for network error mapping
- tests for JSON parse failure
- tests proving header values do not leak
- tests proving write endpoints cannot be reached
- tests proving no retry loop occurs inside the client

### Confirm Before Live Release

- X API access model and spend cap
- exact recent search endpoint availability
- timeout values acceptable for the deployment environment
- HTTP library choice
- whether separate connect/read timeout fields are needed
- redacted diagnostic format
- rollback config

## Release Blockers

Live HTTP client implementation must remain blocked if:

- it can send non-GET requests
- it can reach write endpoints
- it reads credentials directly
- it logs request headers or header values
- it retries internally
- it handles pagination internally
- it writes raw responses to disk
- it bypasses `LiveModeGate`
- any redaction or credential leak test fails
