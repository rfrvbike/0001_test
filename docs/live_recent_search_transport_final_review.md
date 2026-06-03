# LiveRecentSearchTransport Final Implementation Review

This document is the final pre-implementation review for
`LiveRecentSearchTransport`. It does not enable live mode, perform HTTP, call
the X API, read credentials, read `.env`, read environment variables, or add
posting behavior.

## Current Decision

`LiveRecentSearchTransport` remains disabled.

Approved current mode:

```text
dry_run=true
live_mode=false
transport=mock
credential_loader=fake
http_client=disabled
```

Any future live implementation must stay read-only and limited to X recent
search.

## Implementation Responsibilities

Future `LiveRecentSearchTransport` may own only the transport boundary between a
prepared recent-search query and an HTTP-shaped transport response.

It may:

- receive a query that has already been built by `QueryBuilder`
- call `RequestBuilder` to create a `HttpRequest`
- pass that `HttpRequest` to an injected `LiveHttpClient`
- receive a `HttpResponse`
- convert `HttpResponse` into `TransportResponse`
- preserve `status_code`
- preserve response `headers`
- preserve parsed `json_body`
- preserve `body_text` if the transport response shape is extended
- return a shape that `RateLimitParser` and `ResponseNormalizer` can consume
- convert failures into values that can be passed to `map_http_error(...)`
- apply redaction before any exception or diagnostic leaves the boundary

It must not:

- load credentials
- decide live mode
- read `.env`
- read environment variables
- paginate
- retry in a loop
- enqueue retry tasks
- calculate buzz scores
- detect genres
- rank posts
- write CSV
- write reports
- write logs containing raw headers or credentials
- call write, post, like, repost, follow, DM, profile, delete, or media APIs

## Connection Order

The reviewed live-read path is:

```text
CredentialLoader
-> LiveModeGate
-> QueryBuilder
-> RequestBuilder
-> LiveRecentSearchTransport
-> LiveHttpClient
-> TransportResponse
-> RateLimitParser
-> ResponseNormalizer
-> PaginationController
-> RetryPolicy / RetryQueue
```

Boundary notes:

- `CredentialLoader` owns credential retrieval only.
- `LiveModeGate` owns live-mode approval only.
- `QueryBuilder` owns query syntax and length validation.
- `RequestBuilder` owns request and header mapping.
- `LiveRecentSearchTransport` owns one transport call boundary.
- `LiveHttpClient` owns one low-level HTTP send/receive boundary.
- `RateLimitParser` owns rate-limit header interpretation.
- `ResponseNormalizer` owns X response JSON to `BuzzFetchResult` conversion.
- `PaginationController` owns `next_token`, max page, and max result flow.
- `RetryPolicy` and `RetryQueue` own retry decisions and scheduling.

## Fail-Closed Conditions

The implementation must stop before HTTP when any of these are true:

- `live_mode=false`
- `dry_run=true` while a live transport is requested
- `credential_loader=fake` while a live transport is requested
- `http_client=disabled`
- `explicit_approval=false`
- `write_actions=true`
- `read_only_recent_search=false`
- request endpoint is not recent search
- request method is not `GET`
- authorization header is missing when live mode is approved
- redaction preflight fails
- any release-policy test gate fails

Current disabled components already fail closed:

- `RealCredentialLoader`
- `LiveModeGate`
- `LiveRecentSearchTransport`
- `LiveHttpClient`
- `DisabledHttpClient`

## Redaction Boundary

The transport must treat the following as sensitive:

- `Authorization` header values
- bearer tokens
- `API_KEY`
- `TOKEN`
- `SECRET`
- `COOKIE`
- credential-shaped request header values
- credential-shaped exception messages

Sensitive values must not appear in:

- debug logs
- reports
- CSV
- exceptions
- test fixtures
- raw diagnostic snapshots
- retry metadata
- pagination metadata

Allowed diagnostics are limited to:

- endpoint name
- request method
- query length
- source genre
- status code
- rate-limited boolean
- retry-after seconds
- remaining request count
- partial-result boolean
- sanitized error type

## TransportResponse Shape

The current required transport shape is:

```text
TransportResponse(
  status_code: int,
  headers: dict[str, str],
  json_body: dict[str, Any],
)
```

The final review recommends allowing an optional `body_text` field only if it is
kept redacted and never written to report/CSV by default. `json_body` remains
the value consumed by `normalize_recent_search_response(...)`.

## Error Mapping Connection

The transport should not invent retry behavior. It should expose enough
information for `map_http_error(...)` to produce:

- `timeout`
- `network_error`
- `auth_error`
- `rate_limited`
- `server_error`
- `client_error`
- `json_parse_error`
- `schema_error`
- `disabled_http_client`

For `429` or `Retry-After`, rate-limit metadata must remain available for:

- `parse_rate_limit_headers(...)`
- `RetryPolicy`
- `RetryQueue`

## Gap Analysis

Implementation prep OK:

- `QueryBuilder`
- `RequestBuilder`
- `HttpRequest`
- `HttpResponse`
- `HttpClient`
- `DisabledHttpClient`
- `LiveHttpClient` disabled skeleton
- `RecentSearchTransport`
- `MockRecentSearchTransport`
- `LiveRecentSearchTransport` disabled skeleton
- `TransportResponse`
- `RateLimitParser`
- `ResponseNormalizer`
- `HTTP Error Mapping`
- `RetryPolicy`
- `RetryQueue`
- `PaginationController`
- `Redaction Utility`
- `FakeCredentialLoader`
- `RealCredentialLoader` disabled skeleton
- `LiveModeGate`
- `Live Mode Release Policy`
- dry-run pipeline

Needed before implementation:

- finalize whether `TransportResponse` includes `body_text`
- add request method/endpoint preflight tests for recent-search-only `GET`
- add tests that live transport calls `RequestBuilder` but does not load
  credentials
- add tests that live transport passes exactly one `HttpRequest` to the
  injected client
- add tests that disabled/live gates stop before the HTTP client

Needed before live release:

- real backend credential loader
- reviewed credential storage policy implementation
- live-enabled HTTP client
- live-enabled transport implementation
- endpoint allowlist enforcement
- timeout and JSON parse behavior with live client
- live pagination integration
- live retry queue integration
- current X API plan confirmation
- explicit user approval for a narrow read-only test window

## Implementation Test Plan

Minimum tests for the future implementation:

- request builder integration creates a `HttpRequest`
- `LiveHttpClient` receives exactly one request
- `DisabledHttpClient` fails closed
- disabled live mode fails before transport send
- `credential_loader=fake` fails for live transport
- `explicit_approval=false` fails for live transport
- authorization header value is never logged
- bearer token is never logged
- credential markers are redacted from exceptions
- 429 maps to `rate_limited`
- `Retry-After` is preserved
- timeout maps to `timeout`
- 401 and 403 map to `auth_error`
- 500 maps to `server_error`
- invalid JSON maps to `json_parse_error`
- schema mismatch maps to `schema_error`
- pagination uses `next_token` outside the transport
- retry queue enqueue is outside the transport
- write endpoint attempts are rejected

## Final Review Conclusion

The implementation boundary is ready to define, but live access is not approved.
The next code step may implement only the transport orchestration against
disabled or fake components unless the live release policy is explicitly
completed. Real HTTP, real credentials, `.env` access, environment-variable
access, and X API calls remain prohibited.
