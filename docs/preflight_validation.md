# Recent Search Endpoint Allowlist and Preflight Validation

This document describes the preflight validation skeleton added before any real
X API connection. It does not enable live mode, perform HTTP, read credentials,
read `.env`, read environment variables, or post to X.

## Purpose

Preflight validation exists to fail closed before a request reaches the future
live HTTP client. It fixes these rules in code and tests:

- recent search only
- `GET` only
- no write endpoints
- no DM, media, follow, like, repost, or post endpoints
- query must be present
- query length must be at most 512 characters
- timeout must be positive
- safe diagnostics must not expose credential-shaped values

## Implementation

Module:

- `x_auto_ops/preflight_validation.py`

Definitions:

- `PreflightValidationError`
- `RecentSearchAllowlistPolicy`
- `ValidationResult`
- `validate_recent_search_request(...)`

`ValidationResult.safe_debug_summary()` reports only safe metadata:

- allowed flag
- method
- endpoint
- endpoint name
- query length
- validation reason
- redacted header names

It never reports query text or header values.

## Allowlist

Allowed method:

```text
GET
```

Allowed endpoints:

```text
https://api.x.com/2/tweets/search/recent
/2/tweets/search/recent
```

## Denylist

The policy rejects common write or non-recent-search endpoint families,
including:

```text
/2/tweets
/2/users
/2/dm
/2/media
/2/users/:id/following
/2/users/:id/likes
/2/tweets/:id/liking
/2/tweets/:id/retweeted_by
```

The denylist is intentionally conservative. Future live transport work should
add endpoint allowlist tests before expanding any accepted endpoint.

## Query Validation

The validator rejects:

- empty query
- query length greater than 512
- empty endpoint
- empty method
- `timeout_seconds <= 0`

The validator records only `query_length` in diagnostics.

## Fail-Closed Policy

Any validation failure raises `PreflightValidationError` before HTTP can occur.
The future live path must run preflight after request construction and before
`LiveHttpClient.send(...)`.

Reviewed order:

```text
CredentialLoader
-> LiveModeGate
-> QueryBuilder
-> RequestBuilder
-> PreflightValidation
-> LiveRecentSearchTransport
-> LiveHttpClient
```

## Redaction Policy

The following must not appear in debug logs, reports, CSV, exceptions,
validation summaries, fixtures, retry metadata, or pagination metadata:

- `Authorization`
- `Bearer`
- `API_KEY`
- `TOKEN`
- `SECRET`
- `COOKIE`

The current tests inject fake credential-shaped values into headers, query, and
error paths to prove that safe summaries and exceptions do not leak them.

## Live Mode Release Policy Relationship

Preflight validation is a release blocker. Live mode must remain disabled if:

- preflight tests fail
- non-`GET` methods can pass
- non-recent-search endpoints can pass
- write endpoint attempts can pass
- validation diagnostics leak credential-shaped values

Preflight does not replace `LiveModeGate`, credential loading policy, request
builder validation, redaction tests, or the live release checklist. It is one
additional fail-closed layer.

## Transport Integration

Integration with the disabled live transport is documented in
`docs/preflight_transport_integration.md`.

`LiveRecentSearchTransport.send_recent_search(query)` now runs:

```text
build_recent_search_request(...)
-> validate_recent_search_request(...)
-> RuntimeError("LiveRecentSearchTransport disabled")
```

If preflight fails, `PreflightValidationError` is raised before the disabled
transport error. This means invalid methods, write endpoints, overlong queries,
bad timeouts, and allowlist violations never reach the disabled transport or the
HTTP client.
