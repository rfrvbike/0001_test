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
