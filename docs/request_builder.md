# Request Builder

This document records the mock-only HTTP request builder skeleton for future X
recent-search reads. No HTTP communication, request execution, API key lookup,
token lookup, cookie access, `.env` read, or posting behavior is implemented.

## Implementation Point

```text
x_auto_ops/request_builder.py
```

Public API:

```text
build_recent_search_request(...)
```

Returns:

```text
RequestBuildResult
```

## Request Generation Flow

The future live-read preparation path is:

```text
Query Builder
-> Credential Loader
-> Request Builder
-> HttpRequest
-> LiveRecentSearchTransport
-> HttpClient
```

The current implementation stops at request construction. It does not send the
request.

## RequestBuildResult

Fields:

- `endpoint_name`
- `request`
- `query`
- `query_params`
- `header_names`
- `timeout_seconds`

`request` is the internal prepared `HttpRequest`. `header_names` is the safe
diagnostic surface. Header values must not be copied into debug logs, reports,
CSV output, or exceptions.

## Header Mapping

Generated headers:

- `Authorization`
- `User-Agent`
- `Accept`

Current mapping:

```text
Authorization: Bearer <credential_bundle.bearer_token>
User-Agent: x-auto-ops-runtime/0.1 dry-run-prelive
Accept: application/json
```

The fake credential value may exist only inside the internal `HttpRequest` in
tests. It must not be written to output surfaces.

## Query Parameters

Generated query parameters:

- `query`
- `tweet.fields`
- `expansions`
- `user.fields`

Default values:

- `tweet.fields=created_at,public_metrics,author_id`
- `expansions=author_id`
- `user.fields=username`

## Authorization Handling

`FakeCredentialLoader` may provide `FAKE_BEARER_TOKEN` to build a local
`HttpRequest`, but the token value must not appear in:

- debug logs
- reports
- CSV output
- exceptions
- docs-generated examples

Diagnostics should use header names only, and those names should pass through
redaction before being rendered.

## Validation Policy

The builder rejects:

- empty query
- empty endpoint
- non-positive timeout
- non-numeric timeout

Validation errors must not include credential values or header values.

## Redaction Policy

`RequestBuildResult.safe_debug_summary()` redacts credential-shaped header names
and never includes header values.

Tests verify that authorization, bearer, API key, token, and secret marker text
do not leak to report, CSV, debug log, or exception surfaces.
