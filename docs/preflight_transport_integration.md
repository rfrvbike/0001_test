# PreflightValidation Transport Integration

This document describes the fail-closed integration between
`PreflightValidation`, `LiveRecentSearchTransport`, and `LiveHttpClient`. It
does not enable live mode, perform HTTP, call the X API, read real credentials,
read `.env`, read environment variables, or post to X.

## Purpose

The integration fixes the order that every future live recent-search request
must follow:

```text
RequestBuilder
-> PreflightValidation
-> LiveRecentSearchTransport
-> LiveHttpClient
```

The current implementation still stops at:

```text
RuntimeError("LiveRecentSearchTransport disabled")
```

No `LiveHttpClient.send(...)` call is made.

## Current Integration

`LiveRecentSearchTransport.send_recent_search(query)` now:

1. builds a prepared `HttpRequest` with `build_recent_search_request(...)`
2. validates that request with `validate_recent_search_request(...)`
3. stores a redacted validation summary in `last_preflight_summary`
4. raises `RuntimeError("LiveRecentSearchTransport disabled")`

If request building fails because of a preflight-shaped input problem, it is
converted to `PreflightValidationError` so the transport disabled error is not
reached first.

## Fail-Closed Behavior

These cases fail before disabled transport execution:

- `POST`
- `PUT`
- `PATCH`
- `DELETE`
- write endpoints
- query length greater than 512
- `timeout_seconds <= 0`
- endpoint outside the recent-search allowlist

The valid case also fails closed, but after preflight:

```text
GET + recent search endpoint + valid query
-> preflight allowed
-> RuntimeError("LiveRecentSearchTransport disabled")
```

## HTTP Client Boundary

Tests inject a tracking HTTP client and confirm:

- valid preflight does not call `send(...)`
- invalid preflight does not call `send(...)`
- `LiveHttpClient` remains unreachable while transport is disabled

This preserves the current no-network guarantee.

## Redaction

The integration must not expose:

- `Authorization`
- `Bearer`
- `API_KEY`
- `TOKEN`
- `SECRET`
- `COOKIE`

Protected surfaces:

- debug
- report
- CSV
- exception
- validation summary

`last_preflight_summary` contains only safe metadata such as method, endpoint,
query length, endpoint name, validation reason, and redacted header names. It
does not contain query text or header values.

## Release Policy Relationship

This integration is still pre-live scaffolding. It does not replace:

- `LiveModeGate`
- credential loader policy
- endpoint allowlist policy
- live HTTP client review
- live mode release policy

Live API access remains blocked until all release gates are complete.
