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

Only `FakeCredentialLoader` is implemented. It returns fake credential-shaped
values and does not read files, `.env`, environment variables, tokens, cookies,
or network resources.

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

`LiveRecentSearchTransport` accepts an injected HTTP client, defaulting to
`DisabledHttpClient`. The transport still raises before using the client. This
keeps the future HTTP implementation swappable while preserving fail-closed
behavior.

Dependency injection shape:

```text
CredentialLoader
-> LiveModeGate
-> LiveRecentSearchTransport
-> HttpClient
```

HTTP timeout/error mapping boundary:

- `x_auto_ops/http_error_mapping.py`
- `HttpErrorInfo`
- `map_http_error(...)`

The future live transport should map timeout, network, auth, rate-limit,
server, client, JSON parse, schema, and disabled-client failures through this
boundary. The mapping layer redacts messages and does not perform retries.

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
