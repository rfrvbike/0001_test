# LiveHttpClient Implementation Delta Review

Date: 2026-06-04

This is a design review only. It does not implement a live HTTP client, perform
HTTP communication, call the X API, run `requests`, run `httpx`, run `urllib`,
perform socket communication, read API keys, read tokens, read cookies, read
authorization values, read `.env`, read environment variables, read real
credentials, fetch real data, or post to X.

## Review Decision

Overall implementation delta status: `NEEDS_REVIEW`

Live HTTP execution status: `BLOCKED`

The current `LiveHttpClient` disabled skeleton fixes the future implementation
point. The future live implementation should be limited to low-level
send/receive behavior for one prepared `HttpRequest`. It must not broaden into
request construction, credential loading, retry, pagination, scoring, CSV, or
reporting.

## Current Responsibility

Current implementation:

```text
LiveHttpClient.send(HttpRequest)
-> LiveHttpClientDisabledError("Live HTTP client disabled")
```

Current responsibilities:

- provide the future class name and module location
- satisfy the `HttpClient` protocol shape
- accept a `HttpRequest` parameter
- fail closed on every call
- avoid importing or running HTTP libraries
- avoid credential reads and environment reads

Current non-responsibilities:

- no HTTP communication
- no X API call
- no request execution
- no credential loading
- no retry
- no pagination
- no response parsing
- no CSV or report output

## Future Responsibility

Future implementation target:

```text
LiveHttpClient.send(HttpRequest)
-> HTTP request
-> HttpResponse
```

Future responsibilities:

- receive one prepared `HttpRequest`
- apply configured timeout values
- send exactly one HTTP request
- return one `HttpResponse`
- preserve `status_code`
- preserve response headers
- preserve `body_text` in memory
- preserve parsed `json_body` when JSON parsing succeeds
- expose failures so `map_http_error(...)` can classify them
- keep diagnostic output redacted

## Increased Responsibilities

The move from disabled skeleton to live implementation should add only these
responsibilities:

- `HttpRequest` receipt validation at the low-level client boundary
- timeout application
- one send attempt
- `HttpResponse` construction
- status code preservation
- response header preservation
- bounded raw `body_text` handling
- JSON parse attempt where supported by the chosen library
- error surfacing for HTTP Error Mapping

## Responsibilities Not To Add

`LiveHttpClient` must not gain these responsibilities:

- query generation
- `RequestBuilder`
- credential loading
- authorization header creation
- live mode approval
- endpoint allowlist decision
- pagination
- retry loop
- retry queue enqueue
- score calculation
- genre detection
- CSV output
- report output
- raw response persistence

## One Request Rule

Allowed behavior:

```text
1 request
-> 1 response or 1 mapped failure
```

Forbidden behavior:

- retry loop
- `while retry`
- recursive retry
- sleep
- backoff
- pagination
- next-token advancement
- RetryQueue enqueue

Retry and pagination remain outside the HTTP client:

```text
LiveHttpClient.send(...)
-> HttpResponse or exception
-> map_http_error(...)
-> RetryPolicy
-> RetryQueue
```

## Timeout Review

Recommended future timeout policy:

| Timeout | First-live recommendation | Status |
| --- | ---: | --- |
| connect timeout | 3 seconds | `NEEDS_REVIEW` before library selection |
| read timeout | 10 seconds | `NEEDS_REVIEW` before library selection |
| total timeout | 15 seconds | compatible with current `HttpRequest.timeout_seconds` |

Current skeleton alignment:

- `HttpRequest.timeout_seconds` already exists as a total timeout field.
- Preflight rejects `timeout_seconds <= 0`.
- Separate connect/read timeout fields should be added only if the selected
  HTTP library supports them cleanly and tests cover them.

The HTTP client should not implement sleep or backoff. Timeout failures should
surface to HTTP Error Mapping as `timeout`.

## HttpResponse Review

Current shape:

```text
HttpResponse(
  status_code,
  headers,
  body_text,
  json_body,
)
```

| Field | Requirement | Redaction / Handling |
| --- | --- | --- |
| `status_code` | required | safe to log as numeric status |
| `headers` | required | header names may be logged; values must be redacted |
| `body_text` | optional for downstream surfaces, useful in memory | never write raw body to report, CSV, debug, retry metadata, or pagination metadata |
| `json_body` | optional | required only when JSON parse succeeds |

Review result:

- keep `HttpResponse.body_text` as an in-memory client boundary field
- allow `json_body` to be absent or `None` when parsing fails
- map invalid JSON as `json_parse_error`
- never include raw body text in exceptions unless redacted and bounded

## Error Mapping Review

`LiveHttpClient` should surface errors in a way that lets
`map_http_error(...)` produce `HttpErrorInfo`.

| Error Type | Expected Client Delta | Retry Ownership |
| --- | --- | --- |
| `timeout` | surface connect/read/total timeout failures | `RetryPolicy` |
| `network_error` | surface DNS/TLS/socket/client failures | `RetryPolicy` |
| `auth_error` | preserve 401/403 status without credential output | outside client |
| `rate_limited` | preserve 429 status and rate-limit headers | `RetryPolicy` / `RetryQueue` |
| `server_error` | preserve 5xx status and headers | `RetryPolicy` |
| `client_error` | preserve 4xx status and headers | outside client |
| `json_parse_error` | surface invalid JSON without raw body leak | outside client |
| `schema_error` | leave schema validation to normalizer/controller | outside client |
| `disabled_http_client` | current skeleton maps to non-retryable disabled error | no retry |

The HTTP client must not decide retry count, enqueue retry tasks, or advance
pagination after any mapped error.

## Credential Boundary

Allowed future credential flow:

```text
CredentialLoader
-> LiveModeGate
-> RequestBuilder
-> LiveRecentSearchTransport
-> LiveHttpClient
```

Boundary rules:

- `LiveHttpClient` does not generate credentials.
- `LiveHttpClient` does not save credentials.
- `LiveHttpClient` does not read `.env`.
- `LiveHttpClient` does not read environment variables.
- `LiveHttpClient` does not call `getenv`.
- `LiveHttpClient` receives only a prepared `HttpRequest`.
- Authorization header values must not be copied to diagnostics.

## Redaction Boundary

These markers and credential-shaped values must never be emitted:

- `Authorization`
- `Bearer`
- `API_KEY`
- `TOKEN`
- `SECRET`
- `COOKIE`

Prohibited output surfaces:

- debug logs
- reports
- CSV
- exceptions
- retry metadata
- pagination metadata
- test fixtures

Allowed diagnostics:

- method
- endpoint name
- timeout seconds
- status code
- header names without values
- body length, if needed
- JSON parse success/failure boolean

## HTTP Library Candidate Comparison

This is comparison only. No library is selected or executed by this review.

| Candidate | Timeout | Testability | Dependency Size | Sync Simplicity | Redaction Integration | Maintenance |
| --- | --- | --- | --- | --- | --- | --- |
| `requests` | good connect/read timeout support | high; easy to mock session/send | external dependency | simple sync API | must wrap request/response diagnostics carefully | mature, widely used |
| `httpx` | strong timeout model with connect/read/write/pool | high; transport injection is clean | external dependency | sync and async, slightly more surface | good with custom transports, still needs strict redaction | actively maintained |
| `urllib` | basic timeout support, less ergonomic split control | medium; more boilerplate | standard library | sync but verbose | manual header/body handling increases leak risk | stable standard library |

Review result:

- `requests` is the simplest first-live sync candidate if dependency policy
  allows it.
- `httpx` is attractive if transport injection and richer timeout modeling are
  prioritized.
- `urllib` avoids a dependency but increases implementation and redaction
  boilerplate.
- Final selection remains `NEEDS_REVIEW`; no HTTP library should be imported
  until live implementation is explicitly approved.

## Gap Analysis

### READY

- `HttpRequest`
- `HttpResponse`
- `HttpClient` protocol
- `DisabledHttpClient`
- `LiveHttpClient` disabled skeleton
- `LiveHttpClientDisabledError`
- HTTP Error Mapping
- Redaction Utility
- Request Builder boundary
- Preflight timeout validation
- Retry Policy skeleton
- Retry Queue skeleton
- Pagination Controller skeleton
- Live Mode Gate default block

### NEEDS_REVIEW

- HTTP library selection
- exact connect/read/total timeout representation
- live HTTP diagnostics format
- JSON parse failure behavior
- raw body length limits
- live HTTP tests
- real credential loader storage adapter
- live transport/client integration tests
- rate limit response handling under live client

### BLOCKED

- live HTTP execution
- X API calls
- socket communication
- `requests`, `httpx`, or `urllib` execution
- API key/token/cookie/authorization reads
- `.env`, environment variable, or `getenv` reads
- live mode enablement
- write endpoints and posting actions

## Implementation Checklist Before LiveHttpClient Work

- add live HTTP disabled-to-live tests before implementation
- add timeout tests for connect/read/total timeout cases
- add network error mapping tests
- add 401/403 auth error tests
- add 429 rate limit tests preserving headers
- add 5xx server error tests
- add 4xx client error tests
- add JSON parse error tests
- add schema handoff tests
- add redaction regression tests for exceptions and diagnostics
- add no retry loop tests
- add no sleep/backoff tests
- add no pagination tests
- add endpoint allowlist integration tests through transport/preflight
- confirm no header values are logged
- confirm no raw body text reaches report, CSV, retry metadata, or pagination
  metadata

## Safety Confirmation

This review adds no live HTTP implementation and does not unlock live mode.
`LiveHttpClient.send(...)` remains disabled until a future approved
implementation replaces the fail-closed skeleton.
