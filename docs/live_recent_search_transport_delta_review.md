# LiveRecentSearchTransport Implementation Delta Review

Date: 2026-06-04

This is a design review only. It does not implement live transport, perform
HTTP, call the X API, read API keys, read tokens, read cookies, read
authorization values, read `.env`, read environment variables, read real
credentials, fetch real data, or post to X.

## Review Decision

Overall implementation delta status: `NEEDS_REVIEW`

Live API execution status: `BLOCKED`

The current disabled transport is close enough to define the future live
implementation boundary, but the live implementation itself must not start
until the live HTTP client, real credential loader, endpoint allowlist tests,
transport integration tests, redaction regression tests, and timeout/error
mapping tests are approved together.

## Current Responsibility

Current implementation:

```text
LiveRecentSearchTransport.send_recent_search(query)
-> build_recent_search_request(...)
-> validate_recent_search_request(...)
-> RuntimeError("LiveRecentSearchTransport disabled")
```

Current responsibilities:

- receive a query string
- build a `HttpRequest` through `RequestBuilder`
- run `PreflightValidation`
- store a safe, redacted preflight summary
- fail closed before HTTP
- keep the injected HTTP client unused
- preserve the future transport method shape

Current non-responsibilities:

- no HTTP communication
- no X API call
- no credential reading
- no live-mode decision
- no response conversion
- no pagination
- no retry loop
- no scoring
- no genre detection
- no CSV output
- no report output

## Future Responsibility

Future implementation target:

```text
LiveRecentSearchTransport.send_recent_search(query)
-> RequestBuilder
-> PreflightValidation
-> LiveHttpClient.send(HttpRequest)
-> TransportResponse
```

Future responsibilities:

- receive a query that was already built upstream
- use `RequestBuilder` to create one `HttpRequest`
- run `PreflightValidation` before any client call
- pass exactly one request to the injected `LiveHttpClient`
- convert `HttpResponse` to `TransportResponse`
- preserve `status_code`, `headers`, and parsed `json_body`
- expose errors in a shape compatible with `map_http_error(...)`
- keep diagnostics redacted

## Increased Responsibilities

The move from disabled to live implementation should add only these
responsibilities:

- RequestBuilder connection as the single request construction path
- PreflightValidation connection as a mandatory allowlist gate
- HttpClient connection through constructor injection
- one-request transport execution
- `HttpResponse` to `TransportResponse` conversion
- error handoff to HTTP Error Mapping
- redacted diagnostic summaries

## Responsibilities Not To Add

`LiveRecentSearchTransport` must not gain these responsibilities:

- pagination control
- retry loop
- retry queue enqueue
- credential loading
- live mode approval
- score calculation
- genre detection
- CSV output
- report output
- raw credential diagnostics
- write API behavior

## Live Flow

Reviewed future connection order:

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

`LiveRecentSearchTransport` sits between validated request construction and the
single HTTP client call. Everything before it decides whether a request is safe
to send. Everything after it interprets headers, response JSON, pagination, and
retry decisions.

## TransportResponse Review

Current shape:

```text
TransportResponse(
  status_code,
  headers,
  json_body,
)
```

Open question:

- whether to add `body_text`

### `body_text` Benefits

- preserves raw response text for JSON parse error mapping
- can help distinguish empty body, invalid JSON, and schema failures
- gives the transport a cleaner bridge from `HttpResponse.body_text` to
  downstream error mapping

### `body_text` Drawbacks

- increases leak risk if raw bodies are logged or reported
- increases redaction and regression-test burden
- creates pressure to expose raw response data outside the transport boundary
- may duplicate `HttpResponse.body_text` if retained too broadly

### Recommendation

Keep `TransportResponse` at `status_code`, `headers`, and `json_body` for the
normal success path.

Add `body_text` only if error mapping requires it, and then make it optional,
redacted before diagnostics, and prohibited from report/CSV output by default.
Raw body text must not be emitted to debug logs, retry metadata, pagination
metadata, reports, CSV, or fixtures.

## Error Mapping Connection Review

The future live transport must connect errors to `map_http_error(...)` without
owning retry behavior.

| Error Type | Expected LiveTransport Handling | Retry Ownership |
| --- | --- | --- |
| `timeout` | catch or receive timeout failure and map to `HttpErrorInfo` | `RetryPolicy` |
| `network_error` | map connection failures with redaction | `RetryPolicy` |
| `auth_error` | map 401/403 without exposing credentials | outside transport |
| `rate_limited` | preserve status/headers for parser and mapping | `RetryPolicy` / `RetryQueue` |
| `server_error` | map 5xx as retryable where policy allows | `RetryPolicy` |
| `client_error` | map 4xx as non-retryable except specific policy cases | `RetryPolicy` |
| `json_parse_error` | map parse failure; do not dump raw body | outside transport |
| `schema_error` | pass malformed response to normalizer/error mapping safely | outside transport |
| `disabled_http_client` | map disabled client failure as non-retryable | no retry |

The transport should not sleep, recursively call itself, enqueue retry tasks, or
advance pagination tokens.

## HTTP Client Connection Review

`LiveHttpClient` boundary:

- input: `HttpRequest`
- output: `HttpResponse`
- sends one request only
- does not build query strings
- does not load credentials
- does not retry
- does not paginate
- does not score or write outputs

`LiveRecentSearchTransport` should pass a validated `HttpRequest` to the
injected client and then convert the result. If the client is disabled, the
failure must remain fail-closed and map to `disabled_http_client`.

## Allowlist Enforcement

LiveTransport must continue to rely on PreflightValidation and should preserve
recent-search-only enforcement.

Allowed:

- method: `GET`
- endpoint: `/2/tweets/search/recent`
- endpoint: `https://api.x.com/2/tweets/search/recent`

Denied:

- `POST`
- `PUT`
- `PATCH`
- `DELETE`
- `/2/tweets`
- `/2/users`
- `/2/dm`
- `/2/media`
- `/2/tweets/search/all`
- follow, like, repost, DM, media upload, and other write endpoint families

Preflight failures must occur before `LiveRecentSearchTransport disabled` and
before any HTTP client call.

## Redaction Boundary

These values must never be emitted:

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
- validation summaries

Allowed diagnostics should stay limited to:

- endpoint name
- method
- query length
- status code
- rate-limited boolean
- retry-after seconds
- remaining request count
- partial result boolean
- header names without values

## Gap Analysis

### READY

- Query Builder
- Request Builder
- Preflight Validation
- `LiveRecentSearchTransport` disabled skeleton
- `LiveHttpClient` disabled skeleton
- HttpClient interface
- Response Normalizer
- Rate Limit Parser
- HTTP Error Mapping
- Retry Policy skeleton
- Retry Queue skeleton
- Pagination Controller skeleton
- Redaction Utility
- Fake Credential Loader
- Real Credential Loader disabled skeleton
- Live Mode Gate default block

### NEEDS_REVIEW

- exact `TransportResponse.body_text` decision
- live transport implementation tests
- live HTTP client implementation tests
- real credential loader storage adapter choice
- real credential validation rules
- live diagnostics format
- pagination integration with live one-page transport
- retry integration without sleeping or recursive transport calls
- current X API plan and field availability at release time

### BLOCKED

- live mode enablement
- real HTTP communication
- real credential reads
- `.env` reads or process environment reads
- API key, token, cookie, or authorization access
- write API endpoints
- posting, liking, reposting, following, DM, or media upload
- live release without explicit approval

## Implementation Checklist Before LiveTransport Work

- confirm `RealCredentialLoader` storage policy and adapter strategy
- implement or keep disabled `LiveHttpClient` tests for fail-closed behavior
- add request-builder integration tests for live transport
- add endpoint allowlist tests for live transport
- add redaction regression tests for transport exceptions and diagnostics
- add timeout mapping tests
- add 401/403 auth error tests
- add 429 rate-limit tests
- add 500 server error tests
- add JSON parse error tests
- add schema error tests
- confirm no retry loop inside transport
- confirm no pagination inside transport
- confirm no credential loading inside transport
- confirm no write endpoint can pass preflight
- confirm no raw header values can appear in debug, report, CSV, exception,
  retry metadata, or pagination metadata

## Safety Confirmation

This review adds no live implementation and does not unlock live mode. The
system remains fail-closed: valid recent-search-shaped requests still stop at
the disabled live transport until live release gates are explicitly approved.
