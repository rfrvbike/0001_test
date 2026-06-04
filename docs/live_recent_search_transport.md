# LiveRecentSearchTransport Specification

This document fixes the intended live transport boundary before any real X API
connection is implemented. It is a specification only. No API key lookup,
network request, token handling, cookie handling, or posting behavior is added
by this document.

## Responsibility

`LiveRecentSearchTransport` will be the only future component allowed to perform
an HTTP read request to X recent search. Collector, ranking, CSV, reports, query
builder, header parser, and normalizer must remain credential-free.

The transport will be responsible for:

- receiving a query string built elsewhere
- attaching approved read-only authentication in the HTTP layer
- sending a recent-search request only when live mode is explicitly approved
- returning an HTTP-shaped `TransportResponse`
- applying redaction to debug output and exceptions
- never writing credentials to reports, CSV, logs, or exceptions

## Input

Expected method:

```text
send_recent_search(query: str) -> TransportResponse
```

Input is the already-built query string. The transport does not decide genre
logic, target accounts, exclude keywords, or scoring.

## Output

The output must match the existing transport object shape:

```text
TransportResponse(
  status_code: int,
  headers: dict[str, str],
  json_body: dict[str, Any],
)
```

The response is consumed by the header parser and response normalizer.

## Query Builder Relationship

`build_recent_search_query(config)` remains upstream of the transport.
`LiveRecentSearchTransport` must not mutate search terms, add genre rules, or
silently remove filters. If X query length limits are exceeded, that validation
belongs in the query builder or a preflight layer.

## Header Parser Relationship

The transport returns raw response headers. `parse_rate_limit_headers(...)`
interprets:

- `Retry-After`
- `x-rate-limit-reset`
- `x-rate-limit-remaining`

The transport should not implement retry policy directly. It may expose headers
needed for the retry queue.

## Response Normalizer Relationship

The transport returns `json_body` exactly as received, after any safe parsing.
`normalize_recent_search_response(...)` converts X response JSON to `BuzzPost`
and `BuzzFetchResult` fields. Missing metrics remain normalizer concerns.

## Retry Queue Relationship

When a parsed result is rate-limited, pipeline code may enqueue a `RetryTask`:

```text
query
retry_after_seconds
enqueue_time
retry_count
```

The live transport must not sleep, spin, or recursively retry inside
`send_recent_search`. Retry policy belongs to the queue/controller layer.

## Dry-run Gate Relationship

`XApiBuzzReadClient(dry_run=False)` currently raises before any transport call.
That gate remains required until live access is explicitly approved. A future
live transport must also have its own explicit live-mode constructor flag so
accidental invocation fails closed.

Live release approval is governed by `docs/live_mode_release_policy.md`.
`live_mode=true` alone must not activate this transport. Release requires the
combined approval of dry-run disablement, real credential loader selection, live
transport selection, live HTTP client selection, explicit approval, and
read-only recent-search scope enforcement.

## Credential Management Policy

Credentials must not be read by query builder, normalizer, scorer, CSV writer,
report writer, or collector. A future live transport may receive credentials
only from an approved backend/server configuration path. Frontend storage,
localStorage, CSV, reports, fixtures, and debug logs must never hold keys,
tokens, cookies, authorization headers, or secrets.

Current pre-live credential boundary:

- `x_auto_ops/credential_loader.py`
- `CredentialLoader`
- `FakeCredentialLoader`
- `CredentialBundle`
- `select_credential_loader(config)`
- `x_auto_ops/real_credential_loader.py`
- `RealCredentialLoader`
- `RealCredentialLoaderDisabledError`

Only `FakeCredentialLoader` is implemented. It returns fake credential-shaped
values and does not read files, `.env`, environment variables, tokens, cookies,
or network resources.

`RealCredentialLoader` is a backend-only disabled skeleton. It fixes the future
implementation point, but `load()` always raises
`RealCredentialLoaderDisabledError("Real credential loader disabled")`.

Loader selection:

- `fake` -> `FakeCredentialLoader`
- `real` -> disabled `RealCredentialLoader`

Selecting the real loader does not read credentials. Any attempt to load through
it fails closed.

Backend-only policy:

- frontend credential access is prohibited
- browser storage is prohibited
- credential values are prohibited in CSV, reports, fixtures, debug logs, and
  exceptions
- see `docs/backend_credential_policy.md`
- storage review is recorded in `docs/backend_credential_storage_review.md`

Storage review summary:

- development should keep `FakeCredentialLoader` as the default
- staging should prefer a reviewed secret manager or backend-only managed
  adapter
- production should require a secret manager
- `.env` is not recommended as the project-level primary storage plan
- any repository-local credential file remains prohibited
- credentials must flow only through `CredentialLoader`, `LiveModeGate`,
  `RequestBuilder`, `LiveRecentSearchTransport`, and `LiveHttpClient`

Live mode remains blocked by `x_auto_ops/live_mode_gate.py`:

```text
assert_live_mode_allowed(config)
```

Dry-run mode is allowed. Live mode is always rejected with
`RuntimeError("live mode disabled")`, even when fake credentials are present.

Current disabled live transport skeleton:

- `x_auto_ops/live_recent_search_transport.py`
- `LiveRecentSearchTransport`
- `send_recent_search(query)`

The skeleton implements the transport method shape but performs no HTTP. Any
call raises `RuntimeError("LiveRecentSearchTransport disabled")`. This fixes the
future implementation point while keeping live reads fail-closed.

Current HTTP client boundary:

- `x_auto_ops/http_client.py`
- `HttpRequest`
- `HttpResponse`
- `HttpClient`
- `DisabledHttpClient`
- `x_auto_ops/live_http_client.py`
- `LiveHttpClient`
- `LiveHttpClientDisabledError`
- `docs/live_http_client_disabled.md`
- `docs/live_http_client_review.md`

`LiveRecentSearchTransport` accepts an injected HTTP client, defaulting to
`DisabledHttpClient`. The transport still raises before using the client. This
keeps the future HTTP implementation swappable while preserving fail-closed
behavior.

`LiveHttpClient` now exists as a disabled skeleton. It can be injected into the
transport, but `LiveRecentSearchTransport` still stops before `send(...)`.
Direct `LiveHttpClient.send(...)` calls raise
`LiveHttpClientDisabledError("Live HTTP client disabled")`.

The live HTTP client implementation review fixes this boundary:

- HttpClient sends one prepared request only.
- HttpClient does not generate queries.
- HttpClient does not load credentials.
- HttpClient does not retry.
- HttpClient does not paginate.
- HttpClient does not score, write CSV, or write reports.
- HttpClient must not expose header values in diagnostics.

Dependency injection shape:

```text
CredentialLoader
-> LiveModeGate
-> LiveRecentSearchTransport
-> HttpClient
```

HTTP request builder boundary:

- `x_auto_ops/request_builder.py`
- `build_recent_search_request(...)`
- `RequestBuildResult`

The request builder prepares `HttpRequest` objects from a query and credential
bundle without sending them. It maps authorization, user-agent, and accept
headers internally while exposing only redacted diagnostics.

Preflight validation boundary:

- `x_auto_ops/preflight_validation.py`
- `PreflightValidationError`
- `RecentSearchAllowlistPolicy`
- `ValidationResult`
- `validate_recent_search_request(...)`
- `docs/preflight_validation.md`

The future live transport path must validate the prepared `HttpRequest` before
it reaches `LiveHttpClient`. Preflight allows only `GET` requests to
`https://api.x.com/2/tweets/search/recent` or `/2/tweets/search/recent`,
rejects write endpoint families, rejects empty or over-512-character queries,
and rejects non-positive timeouts. Safe validation summaries expose query length
and header names only, never query text or header values.

Current integration:

- `LiveRecentSearchTransport.send_recent_search(query)` builds a `HttpRequest`
  with `build_recent_search_request(...)`.
- It then calls `validate_recent_search_request(...)`.
- Valid preflight stores `last_preflight_summary`.
- The transport still raises `RuntimeError("LiveRecentSearchTransport disabled")`.
- Invalid preflight raises `PreflightValidationError` before the disabled
  transport error.
- `LiveHttpClient.send(...)` is not called.

Integration reference:

- `docs/preflight_transport_integration.md`

HTTP timeout/error mapping boundary:

- `x_auto_ops/http_error_mapping.py`
- `HttpErrorInfo`
- `map_http_error(...)`

The future live transport should map timeout, network, auth, rate-limit,
server, client, JSON parse, schema, and disabled-client failures through this
boundary. The mapping layer redacts messages and does not perform retries.

Pagination and retry policy boundary:

- `x_auto_ops/pagination_controller.py`
- `PaginationController`
- `PaginationState`
- `PaginationResult`
- `x_auto_ops/retry_policy.py`
- `RetryPolicy`
- `RetryDecision`

The future live transport should fetch one page at a time. Pagination,
`next_token` management, max result/page limits, retry decisions, and retry
queue scheduling remain outside the transport.

Plan and field research:

- `docs/x_api_plan_field_research.md`

Live transport implementation must account for the current research findings:

- Recent Search is limited to the last 7 days.
- self-serve recent-search query length should be treated as 512 characters.
- `max_results` should stay within 10-100.
- request `tweet.fields=created_at,author_id,public_metrics`
- request `expansions=author_id`
- request `user.fields=username`
- keep `impression_count` optional and do not fail if absent.

## Logging Policy

Allowed logs:

- query length
- source genre
- status code
- rate-limited boolean
- retry-after seconds
- remaining request count
- partial result boolean

Disallowed logs:

- API keys
- bearer tokens
- cookies
- authorization headers
- raw request headers
- full raw responses when they may contain sensitive metadata

## Redaction Policy

All debug output, report text, CSV leak-test rendering, and exception messages
must pass through redaction when user/config/transport values are included.
The current mock implementation redacts:

- `API_KEY`
- `TOKEN`
- `BEARER`
- `SECRET`
- `COOKIE`
- `AUTHORIZATION`

Any output still containing those markers must fail tests before live transport
work can proceed.

## Pre-implementation Review

The implementation review is recorded in
`docs/live_recent_search_transport_review.md`. It confirms that live transport
work must not start by enabling HTTP. The next code step should be a disabled
transport skeleton plus fake-value tests only.

Review conclusions:

- `LiveRecentSearchTransport` must only handle read-only recent-search HTTP
  transport when an explicit live gate is approved.
- Query construction, genre detection, scoring, CSV writing, reporting, and
  retry scheduling remain outside the transport.
- `impression_count` must remain nullable and scoring must keep the
  engagement-only fallback.
- Pagination is controlled outside the transport with `next_token`,
  `max_results`, `request_window`, and `partial_result`.
- Rate limit handling uses parsed headers and the retry queue; the transport
  must not sleep or loop.
- Credentials are backend-only and must never appear in frontend code, logs,
  reports, CSV, exceptions, fixtures, or debug output.
- Live mode must pass `assert_live_mode_allowed(...)` in addition to the
  existing `XApiBuzzReadClient` dry-run gate.
- `LiveRecentSearchTransport` currently exists only as a disabled skeleton; it
  must not be changed to perform HTTP until the live-mode checklist is approved.

The approval and rollback checklist is maintained in
`docs/live_mode_release_policy.md`.

## Final Implementation Review

The final pre-implementation review is recorded in
`docs/live_recent_search_transport_final_review.md`.

The final reviewed transport responsibility is narrow:

- receive a query built by `QueryBuilder`
- use `RequestBuilder` to create a `HttpRequest`
- pass one `HttpRequest` to an injected `LiveHttpClient`
- convert `HttpResponse` to `TransportResponse`
- preserve `status_code`, `headers`, and `json_body`
- expose failures in a shape compatible with `map_http_error(...)`
- keep `RateLimitParser` and `ResponseNormalizer` downstream

The transport must still not own credential loading, live-mode approval,
pagination, retry loops, retry queue enqueue, scoring, genre detection, CSV
output, or report output.

Final reviewed connection order:

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
-> RetryPolicy / RetryQueue
```

Final fail-closed conditions include:

- `live_mode=false`
- `dry_run=true` while live transport is requested
- `credential_loader=fake` while live transport is requested
- `http_client=disabled`
- `explicit_approval=false`
- `write_actions=true`
- non-recent-search endpoint
- non-`GET` method
- preflight validation failure
- redaction preflight failure

Live implementation remains blocked until the release policy is complete.

## Release Readiness Review

The current release readiness review is recorded in
`docs/live_transport_release_readiness.md`.

Review outcome:

- overall status: `NEEDS_REVIEW`
- live API execution status: `BLOCKED`
- ready components include Query Builder, Request Builder, Preflight
  Validation, Response Normalizer, Rate Limit Parser, Retry Policy, Retry
  Queue skeleton, Pagination Controller skeleton, Live Mode Gate, and disabled
  fail-closed tests
- the smallest acceptable live implementation scope is limited to
  `LiveHttpClient`, `RealCredentialLoader`, and `LiveRecentSearchTransport`
- live release remains blocked until real credential storage, live HTTP,
  pagination, retry, redaction, and X API plan checks are reviewed under
  explicit approval
