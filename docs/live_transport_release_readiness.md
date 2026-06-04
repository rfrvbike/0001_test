# Live Transport Release Readiness Review

Date: 2026-06-04

This is a design review only. It does not implement live transport, perform
HTTP, call the X API, read API keys, read tokens, read cookies, read `.env`,
read environment variables, or post to X.

## Review Decision

Overall status: `NEEDS_REVIEW`

Reason:

- the non-live scaffolding is strong enough to start a narrow
  `LiveRecentSearchTransport` implementation behind disabled gates
- live API release remains `BLOCKED`
- live implementation must still be limited to `LiveHttpClient`,
  `RealCredentialLoader`, and `LiveRecentSearchTransport`
- X API plan, credential storage, and live HTTP behavior must be reviewed again
  before any live read is enabled

## Connection Order

Reviewed order:

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

Status: `READY` for mock and disabled-path testing. `BLOCKED` for live API
release.

## Responsibility Boundaries

| Module | Does | Does Not Do | Status |
| --- | --- | --- | --- |
| Query Builder | builds recent-search query strings, removes duplicates, applies account/exclude filters | send HTTP, load credentials, score posts | READY |
| Request Builder | creates `HttpRequest`, maps header names and query params, hides header values in summaries | send HTTP, retry, paginate, expose credentials | READY |
| Preflight Validation | enforces `GET`, recent-search allowlist, query length, timeout, write endpoint rejection | send HTTP, load credentials, alter query semantics | READY |
| LiveRecentSearchTransport | disabled skeleton now runs request builder and preflight before failing closed | live HTTP, pagination, retry loop, CSV/report, scoring | NEEDS_REVIEW |
| LiveHttpClient | disabled skeleton fixes send interface | real HTTP, credential creation, retry, pagination | BLOCKED |
| Response Normalizer | converts X-like JSON to `BuzzFetchResult`, tolerates missing metrics | fetch data, score, retry, paginate | READY |
| Rate Limit Parser | parses `Retry-After`, reset, remaining headers | sleep, retry loop, HTTP send | READY |
| Retry Policy | decides retryability and retry count limits | execute retry, sleep, send HTTP | READY |
| Retry Queue | stores mock retry tasks and readiness | live scheduling, sleeping, transport send | READY |
| Pagination Controller | manages pages, `next_token`, stop reasons | low-level HTTP, credential loading, retry sleeping | READY |
| Credential Loader | fake loader works, real loader disabled skeleton exists | frontend access, `.env` read, environment read in current state | NEEDS_REVIEW |
| Live Mode Gate | blocks live mode by default | credential loading, HTTP send | READY |

## Fail-Closed Review

| Condition | Expected Stop | Current Status |
| --- | --- | --- |
| `live_mode=false` | live gate / disabled path | READY |
| `credential_loader=fake` with live intent | live release blocked | READY for policy, NEEDS_REVIEW for live implementation |
| `transport=mock` | no live transport path | READY |
| `http_client=disabled` | disabled client / disabled transport | READY |
| write endpoint | `PreflightValidationError` | READY |
| `POST` | `PreflightValidationError` | READY |
| `DELETE` | `PreflightValidationError` | READY |
| `timeout_seconds <= 0` | `PreflightValidationError` | READY |
| query length greater than 512 | `PreflightValidationError` | READY |

Live release remains blocked until `LiveModeGate`, real credential loading,
live HTTP, preflight, redaction, pagination, and retry integration pass together
under explicit approval.

## Minimal Live HTTP Implementation Scope

The next live implementation should be restricted to these files/modules:

- `LiveHttpClient`
- `RealCredentialLoader`
- `LiveRecentSearchTransport`

Status: `NEEDS_REVIEW`

Rationale:

- Query Builder, Request Builder, Preflight Validation, Normalizer, Rate Limit
  Parser, Retry Policy, Retry Queue, and Pagination Controller already define
  their non-live boundaries.
- Expanding beyond the three modules above would raise leak and regression risk.
- Live release still requires tests proving the three modules compose without
  exposing credentials or reaching write endpoints.

## Risk Review

| Risk | Current Mitigation | Status |
| --- | --- | --- |
| credential leak | redaction utility, fake loader, backend policy, leak tests | NEEDS_REVIEW for real loader |
| query runaway | query builder limits plus 512-char preflight | READY |
| pagination runaway | max pages/results and stop reasons | NEEDS_REVIEW for live loop integration |
| retry runaway | max retry count and retry queue skeleton | NEEDS_REVIEW for live scheduling integration |
| unexpected endpoint | recent-search allowlist and write endpoint denylist | READY |
| rate limit | parser, retry policy, retry queue | NEEDS_REVIEW for live response handling |
| raw response exposure | normalizer and reporting boundaries | NEEDS_REVIEW for live diagnostics |
| HTTP timeout behavior | error mapping exists, live client missing | BLOCKED |
| X API plan variance | research exists, current account must be rechecked | NEEDS_REVIEW |

## Readiness Classification

### READY

- Query Builder
- Request Builder
- Preflight Validation
- Response Normalizer
- Rate Limit Parser
- Retry Policy
- Retry Queue skeleton
- Pagination Controller skeleton
- Live Mode Gate default block
- disabled transport/client fail-closed tests
- redaction and credential leak tests

### NEEDS_REVIEW

- `LiveRecentSearchTransport` live implementation diff
- `LiveHttpClient` live implementation diff and HTTP library choice
- `RealCredentialLoader` backend-only implementation
- live diagnostic logging format
- live pagination integration
- live retry queue integration
- current X API plan and recent search limits
- whether `TransportResponse.body_text` should be added
- real credential storage and rotation policy

### BLOCKED

- enabling live mode
- real HTTP calls
- real credential reads
- `.env` or environment variable reads
- write endpoints
- posting/like/repost/follow/DM/media APIs
- live release without explicit approval

## Remaining Tasks

### HIGH

- implement `RealCredentialLoader` backend-only with no frontend path
- implement `LiveHttpClient` with timeout/error mapping and no retry loop
- complete the disabled-to-live HTTP client delta checklist in
  `docs/live_http_client_delta_review.md`
- implement `LiveRecentSearchTransport` using Request Builder and Preflight
- complete the disabled-to-live implementation delta checklist in
  `docs/live_recent_search_transport_delta_review.md`
- add live transport tests for 401/403, 429, 500, timeout, JSON parse, schema
  errors
- prove authorization header values never appear in logs, reports, CSV, or
  exceptions
- re-check current X API plan and recent-search availability before live release

### MEDIUM

- decide whether `TransportResponse.body_text` is necessary
- add endpoint allowlist regression tests to the live transport suite
- integrate pagination controller with live transport one page at a time
- integrate retry policy/queue without sleeping or recursive retry
- add rollback dry-run checklist test or script

### LOW

- improve readiness report formatting
- add a manual release checklist template
- add optional redacted diagnostic examples

## Final Recommendation

The system is ready to begin a narrow implementation of live transport
scaffolding, but not ready for live API execution. The next implementation step
should touch only `LiveHttpClient`, `RealCredentialLoader`, and
`LiveRecentSearchTransport`, and must remain fail-closed until every release
gate passes.

## Delta Review Addendum

The implementation delta review is recorded in
`docs/live_recent_search_transport_delta_review.md`.

Delta result:

- `READY`: existing disabled-path boundaries, request building, preflight
  validation, redaction rules, and downstream parser/normalizer interfaces
- `NEEDS_REVIEW`: `TransportResponse.body_text`, live transport tests, live HTTP
  tests, real credential adapter strategy, live diagnostics, pagination and
  retry integration
- `BLOCKED`: live mode, real HTTP, credential reads, process/env reads, write
  endpoints, and any live release without explicit approval

The reviewed live transport delta adds one-request HTTP client execution and
response conversion only. Pagination, retry queue enqueue, credential loading,
score calculation, genre detection, CSV output, and report output remain outside
the transport.

## LiveHttpClient Delta Review Addendum

The LiveHttpClient implementation delta review is recorded in
`docs/live_http_client_delta_review.md`.

Delta result:

- `READY`: `HttpRequest`, `HttpResponse`, `HttpClient` protocol,
  `DisabledHttpClient`, disabled `LiveHttpClient`, HTTP Error Mapping,
  redaction utility, request/preflight boundaries, retry/pagination skeletons
- `NEEDS_REVIEW`: HTTP library selection, connect/read/total timeout shape,
  diagnostics format, JSON parse failure behavior, raw body limits, live HTTP
  tests, live transport/client integration tests
- `BLOCKED`: live HTTP execution, X API calls, socket communication,
  `requests`/`httpx`/`urllib` execution, credential reads, `.env` or process
  reads, live mode, write endpoints

The reviewed HTTP client delta adds one-request send behavior only. Query
generation, RequestBuilder behavior, credential loading, retry loops, retry
queue enqueue, pagination, scoring, genre detection, CSV output, and report
output remain outside the client.
