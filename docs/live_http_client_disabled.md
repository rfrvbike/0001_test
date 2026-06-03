# LiveHttpClient Disabled Skeleton

Created on 2026-06-03.

This document records the disabled live HTTP client skeleton. No HTTP
communication, X API call, credential lookup, token lookup, cookie access,
`.env` read, environment variable read, or posting behavior is implemented.

## Purpose

The skeleton fixes the future implementation point for live HTTP reads while
keeping all network behavior fail-closed.

Implementation point:

```text
x_auto_ops/live_http_client.py
```

## Current Classes

- `LiveHttpClient`
- `LiveHttpClientDisabledError`

Current behavior:

```text
LiveHttpClient.send(HttpRequest)
-> LiveHttpClientDisabledError("Live HTTP client disabled")
```

## Interface Compatibility

`LiveHttpClient` matches the existing `HttpClient` protocol shape:

```text
send(request: HttpRequest) -> HttpResponse
```

It never returns an `HttpResponse` while disabled.

## Fail-Closed Guarantees

The module must not import or execute:

- `requests`
- `httpx`
- `urllib`
- `socket`
- `HTTPConnection`
- `urlopen`

The class performs no DNS lookup, no socket open, no HTTP request, no
credential lookup, and no environment lookup.

## Transport Relationship

`LiveRecentSearchTransport` can receive a `LiveHttpClient` instance through
constructor injection:

```text
LiveRecentSearchTransport(http_client=LiveHttpClient())
```

The transport remains disabled and raises before any HTTP client send can occur.

## Error Mapping

`LiveHttpClientDisabledError("Live HTTP client disabled")` maps through
`map_http_error(...)` to:

```text
error_type=disabled_http_client
retryable=False
partial_result=False
```

## Redaction Policy

The disabled error message contains no credential-shaped values. The following
must not appear in exceptions, debug logs, reports, or CSV output:

- `Authorization`
- `Bearer`
- `API_KEY`
- `TOKEN`
- `SECRET`
- `COOKIE`

## Future Implementation Notes

A future live implementation must still obey:

- read-only recent search only
- no write APIs
- no internal retry loop
- no pagination handling inside the HTTP client
- no credential loading inside the HTTP client
- no header value logging
- timeout and error mapping through `HttpErrorInfo`
