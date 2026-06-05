# Live Transport / Live Client Implementation Readiness Review

Review date: 2026-06-06

Scope: design review only. No implementation, HTTP communication, X API call,
credential lookup, token lookup, cookie lookup, authorization lookup, `.env`
creation or change, environment variable read, real credential read, LiveMode
enablement, real data fetch, or posting was performed.

## Current Baseline

The following pre-live components are available and tested in mock, disabled,
or documentation-only form:

- `RedactedLiveSummary`
- redacted success summary
- redacted error summary
- mock recent-search pipeline integration
- synthetic error mode
- report and CLI safe summary surfaces
- Query Builder
- Request Builder
- Preflight Validation
- `HttpClient` interface
- `LiveHttpClient` disabled skeleton
- `LiveRecentSearchTransport` disabled skeleton
- `RealCredentialLoader` disabled skeleton
- `LiveModeGate`
- Rate Limit Parser
- Response Normalizer
- HTTP Error Mapping
- Retry Policy / Retry Queue
- Pagination Controller

## Overall Decision

Overall implementation readiness: `NEEDS_REVIEW`

Live execution status: `BLOCKED`

Rationale:

- The safe diagnostic surface now covers success and error paths in mock mode.
- Request, preflight, response, error, retry, pagination, and redaction
  boundaries are defined.
- The three live implementation points remain intentionally disabled:
  `RealCredentialLoader`, `LiveHttpClient`, and `LiveRecentSearchTransport`.
- Live execution cannot be approved until real credential storage, HTTP library
  choice, one-request client tests, transport integration tests, and explicit
  release approval are complete.

## Connection Order Review

Reviewed future connection order:

```text
CredentialLoader
-> LiveModeGate
-> QueryBuilder
-> RequestBuilder
-> PreflightValidation
-> LiveRecentSearchTransport
-> LiveHttpClient
-> HttpResponse / TransportResponse
-> RateLimitParser
-> HTTP Error Mapping
-> ResponseNormalizer
-> RedactedLiveSummary
-> PaginationController
-> RetryPolicy / RetryQueue
```

| Component | Status | Review |
| --- | --- | --- |
| CredentialLoader | `NEEDS_REVIEW` | Fake loader and disabled real loader exist. Real storage adapter, validation, rotation, and rollback remain undecided. |
| LiveModeGate | `READY` | Current gate blocks live mode and allows dry-run only. Future live unlock must require multiple explicit flags. |
| QueryBuilder | `READY` | Generates recent-search query strings with conservative validation. It must remain credential-free. |
| RequestBuilder | `READY` | Builds `HttpRequest` and maps headers without exposing header values. It must not send HTTP. |
| PreflightValidation | `READY` | Enforces `GET` and recent-search allowlist, query length, endpoint, and timeout checks. |
| LiveRecentSearchTransport | `NEEDS_REVIEW` | Disabled skeleton exists. Future delta is narrow but not implemented. |
| LiveHttpClient | `NEEDS_REVIEW` | Disabled skeleton exists. HTTP library choice and timeout implementation remain open. |
| HttpResponse / TransportResponse | `NEEDS_REVIEW` | Core shapes exist. `body_text` handling remains an implementation-time decision with strict redaction. |
| RateLimitParser | `READY` | Parses retry-after, reset, remaining, and rate-limited state from mock headers. |
| HTTP Error Mapping | `READY` | Maps timeout, network, auth, rate limit, server, client, JSON parse, schema, and disabled-client failures. |
| ResponseNormalizer | `READY` | Converts recent-search-like JSON to `BuzzFetchResult` and tolerates missing metrics. |
| RedactedLiveSummary | `READY` | Success and error summary paths are implemented and mock-tested. |
| PaginationController | `NEEDS_REVIEW` | Skeleton and tests exist. First live test disables pagination; later live pagination needs separate review. |
| RetryPolicy / RetryQueue | `NEEDS_REVIEW` | Skeleton and tests exist. First live test disables retry; later live retry needs separate review. |

## Minimal Live Implementation Scope

The smallest live implementation area should remain limited to:

```text
RealCredentialLoader
LiveHttpClient
LiveRecentSearchTransport
```

### RealCredentialLoader

Implement:

- backend-only loading from one approved storage adapter
- `CredentialBundle` validation
- fail-closed errors for missing, invalid, or unavailable credentials
- redacted exception and debug boundaries
- loader selection that still blocks unless live release flags are complete

Do not implement yet:

- frontend credential access
- localStorage/sessionStorage access
- CSV/report/fixture credential persistence
- broad adapter support in one step
- automatic live enablement after loading credentials

Required tests:

- storage adapter success with fake test values only
- missing credential error
- invalid credential error
- storage error mapping
- no `.env`, `os.environ`, or `getenv` access unless that adapter is explicitly approved in a later task
- credential values never appear in exceptions, debug logs, reports, CSV, retry metadata, pagination metadata, or frontend files

Fail-closed conditions to preserve:

- real loader unavailable
- storage adapter not selected
- storage adapter disabled
- validation failure
- redaction failure
- live release flags incomplete

### LiveHttpClient

Implement:

- one prepared `HttpRequest` in
- one `HttpResponse` or one mapped failure out
- timeout application
- status code preservation
- response header preservation in memory
- body text kept in memory only when required
- JSON parse attempt with `json_parse_error` mapping

Do not implement yet:

- query generation
- credential loading
- request building
- retry loop
- sleep or backoff
- pagination
- CSV/report output
- generic write-capable X API client

Required tests:

- one-request rule
- timeout mapping
- network error mapping
- 401/403 auth mapping
- 429 rate limit mapping
- 5xx server mapping
- invalid JSON mapping
- no retry loop
- no pagination loop
- no credential/header value leak
- no write endpoint reachability

Fail-closed conditions to preserve:

- disabled client selected
- unsupported method
- write endpoint request
- timeout <= 0
- redaction failure
- unapproved live flags

### LiveRecentSearchTransport

Implement:

- receive a query already built by QueryBuilder
- use RequestBuilder to create `HttpRequest`
- run PreflightValidation before any HTTP send
- call injected `LiveHttpClient.send(...)` exactly once per page request
- convert `HttpResponse` into `TransportResponse`
- hand failures to HTTP Error Mapping
- keep RateLimitParser and ResponseNormalizer downstream

Do not implement yet:

- credential loading
- live mode approval
- pagination loop
- retry loop
- retry queue enqueue
- score calculation
- genre detection
- CSV output
- report output

Required tests:

- request builder integration
- preflight success then one HTTP call
- preflight failure prevents HTTP call
- disabled HTTP client fail-closed
- auth, timeout, rate limit, server, client, JSON parse, schema failure paths
- redacted error summary can be generated downstream
- no credential/header/query/post/user/ID leak

Fail-closed conditions to preserve:

- `live_mode=false`
- `dry_run=true` while live transport is requested
- `credential_loader=fake` while live transport is requested
- `transport=mock`
- `http_client=disabled`
- `explicit_approval=false`
- `write_actions=true`
- non-recent-search endpoint
- non-`GET` method
- preflight validation failure

## First Live Connectivity Conditions

The first live test envelope remains sufficient and intentionally narrow:

```text
read-only recent search only
1 genre
1 query
max_results=10
max_pages=1
pagination disabled
retry disabled
CSV live output disabled
report redacted summary only
no write endpoints
```

Additional confirmation before first live test:

- exact query and genre are reviewed
- valid empty result handling is decided
- execution time window and operator approval are recorded
- rollback settings are ready before execution
- first-live report contains only `RedactedLiveSummary`
- raw response and raw JSON are not persisted
- no retry or pagination task is scheduled during the first test

## Live Unlock Flags

Live execution must require all of these conditions:

```text
dry_run=false
live_mode=true
credential_loader=real
transport=live
http_client=live
explicit_approval=true
read_only_recent_search=true
write_actions=false
```

Fail closed when any condition is missing or contradictory:

- `dry_run=true`
- `live_mode=false`
- `credential_loader=fake`
- `transport=mock`
- `http_client=disabled`
- `explicit_approval=false`
- `read_only_recent_search=false`
- `write_actions=true`
- unknown release flag
- failed redaction, preflight, credential, or unittest gate

## Redaction Boundary Review

The following values must never appear in any output surface:

```text
Authorization
Bearer
API_KEY
TOKEN
SECRET
COOKIE
CredentialBundle contents
raw request headers
raw response headers
raw response body
raw JSON
full query text
full post text
username
author_id
post_id lists
```

Output surfaces covered:

- CLI
- report
- CSV
- debug log
- exception
- retry metadata
- pagination metadata
- frontend
- fixtures

Current decision:

- `RedactedLiveSummary` is safe for CLI/report when emitted through
  `to_safe_dict()` or `safe_debug_summary()`.
- Ranked-post CSV may contain mock post data in dry-run collection mode.
- First-live CSV output remains disabled.
- Live reports must contain only redacted summary values.

## Gap Analysis

### READY

- RedactedLiveSummary success summary
- RedactedLiveSummary error summary
- synthetic error mode
- mock pipeline safe CLI/report integration
- Query Builder
- Request Builder
- Preflight Validation
- Rate Limit Parser
- HTTP Error Mapping
- ResponseNormalizer
- LiveModeGate fail-closed default
- disabled `LiveHttpClient` skeleton
- disabled `LiveRecentSearchTransport` skeleton
- disabled `RealCredentialLoader` skeleton
- credential/redaction regression tests

### NEEDS_REVIEW

- RealCredentialLoader storage backend
- credential rotation and rollback owner
- HTTP library choice
- connect/read/total timeout representation
- `HttpResponse.body_text` use and limits
- live transport error handoff shape
- first-live query and genre
- valid empty result success rule
- live diagnostics request ID strategy
- pagination after first-live test
- retry after first-live test
- report retention and cleanup policy for live summaries

### BLOCKED

- real credential reads
- LiveMode enablement
- HTTP communication
- X API calls
- write endpoints
- posting, liking, reposting, following, DM, media upload
- live CSV output
- retry execution during first live test
- pagination execution during first live test
- raw response persistence
- frontend credential exposure

## Module-by-Module Status

| Area | Status | Notes |
| --- | --- | --- |
| LiveHttpClient | `NEEDS_REVIEW` | Disabled skeleton exists. Next step is implementation plan, not immediate live HTTP. |
| LiveRecentSearchTransport | `NEEDS_REVIEW` | Disabled skeleton plus preflight integration exist. Needs implementation plan and tests. |
| RealCredentialLoader | `NEEDS_REVIEW` | Disabled skeleton exists. Storage adapter and policy remain open. |
| LiveModeGate | `READY` | Fail-closed behavior exists and should remain until release flags are implemented. |
| RedactedLiveSummary | `READY` | Success/error safe summaries are implemented and mock-tested. |
| PreflightValidation | `READY` | Recent-search-only enforcement exists. |
| ErrorMapping | `READY` | Error types and redaction are implemented. |
| RateLimit | `READY` | Header parser exists; live behavior still depends on HTTP response capture. |
| Retry | `NEEDS_REVIEW` | Policy and queue exist; first live test disables retry. |
| Pagination | `NEEDS_REVIEW` | Controller exists; first live test disables pagination. |
| CLI | `READY` | Mock/dry-run and synthetic error CLI are safe. No live CLI path is approved. |
| report | `READY` | Mock safe summaries exist. Live report must remain redacted summary only. |
| CSV | `NEEDS_REVIEW` | Mock ranking CSV exists. Live CSV output remains blocked for first test. |

## Recommended Implementation Order

1. No.009 RealCredentialLoader implementation plan
   - choose one backend-only storage strategy
   - define adapter tests and leak regression tests
   - keep loader disabled until explicit implementation approval
2. No.010 LiveHttpClient implementation plan
   - select HTTP library
   - fix timeout shape
   - define one-request/no-retry tests
   - keep disabled client as default
3. No.011 LiveRecentSearchTransport implementation plan
   - finalize RequestBuilder and PreflightValidation integration
   - define `HttpResponse` to `TransportResponse` conversion
   - define error handoff tests
4. No.012 First live dry-run gate test
   - exercise live-shaped config with disabled HTTP
   - confirm all missing unlock flags fail closed
   - confirm redacted summary surfaces only
5. No.013 First minimal live API test
   - only after explicit approval
   - one read-only recent-search request
   - no pagination, retry, CSV, scoring, or broad collection

## Safety Confirmation

This review did not implement live code, perform HTTP communication, call the
X API, read credentials, read `.env`, read environment variables, enable
LiveMode, fetch real data, write live CSV, or post to X.
