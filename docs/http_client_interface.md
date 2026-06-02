# HTTP Client Interface

This document records the mock-only HTTP client interface skeleton for future X
recent-search reads. No live communication, credential lookup, token lookup,
cookie access, `.env` read, or posting behavior is implemented.

## Purpose

The HTTP layer is separated from `LiveRecentSearchTransport` so the future
implementation can swap the underlying client without changing query building,
normalization, scoring, CSV output, or reporting.

Current implementation point:

```text
x_auto_ops/http_client.py
```

## HttpRequest

`HttpRequest` is the prepared outbound request shape.

Fields:

- `method`
- `url`
- `headers`
- `query_params`
- `timeout_seconds`

The structure is only a data container at this stage.

## HttpResponse

`HttpResponse` is the inbound response shape.

Fields:

- `status_code`
- `headers`
- `body_text`
- `json_body`

The future live transport can map this shape into the existing
`TransportResponse` used by the normalizer and header parser.

## HttpClient

`HttpClient` is a protocol:

```text
send(request: HttpRequest) -> HttpResponse
```

It does not define credential loading. Credentials remain a separate
backend-only concern handled before the transport layer.

## DisabledHttpClient

`DisabledHttpClient` is the only implemented client.

Behavior:

```text
raise RuntimeError("HTTP client disabled")
```

It performs no communication and reads no credentials.

## Live Transport Relationship

`LiveRecentSearchTransport` now accepts an injected HTTP client:

```text
LiveRecentSearchTransport(http_client=...)
```

The default is `DisabledHttpClient`. The live transport still fails before
using the client:

```text
RuntimeError("LiveRecentSearchTransport disabled")
```

This gives the project a future dependency-injection point while keeping all
live reads blocked.

## Credential Loader Relationship

Credentials must remain outside the HTTP client interface. Future execution
order remains:

```text
CredentialLoader
-> LiveModeGate
-> LiveRecentSearchTransport
-> HttpClient
```

Current behavior stops at `LiveModeGate` for live mode or at
`LiveRecentSearchTransport` if the transport is called directly.

## Fail-Closed Policy

Until explicit live approval:

- `DisabledHttpClient` must remain the default client
- `LiveRecentSearchTransport` must remain disabled
- no credential source may be read by the HTTP layer
- no request headers may be logged
- the dry-run pipeline must continue to use `MockRecentSearchTransport`
