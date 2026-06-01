# LiveRecentSearchTransport Disabled Skeleton

This document records the disabled live transport skeleton added before any
real X API connection. No HTTP communication, credential lookup, token lookup,
cookie access, `.env` read, or posting behavior is implemented.

## Purpose

The skeleton fixes the future implementation location:

```text
x_auto_ops/live_recent_search_transport.py
```

It also fixes the method shape:

```text
LiveRecentSearchTransport.send_recent_search(query)
```

The method intentionally fails closed:

```text
RuntimeError("LiveRecentSearchTransport disabled")
```

## Current Behavior

`LiveRecentSearchTransport` satisfies the same transport shape as
`MockRecentSearchTransport`, but it never sends a request. If the disabled
transport is injected into `XApiBuzzReadClient` during dry-run tests, the first
transport call raises the disabled error.

Normal future live order remains:

```text
CredentialLoader
-> LiveModeGate
-> Transport
```

Because `LiveModeGate` currently rejects live mode, a live run should not reach
the disabled transport. If it does reach the transport, the disabled transport
still raises.

## Prohibited Until Explicit Live Approval

- HTTP communication
- `requests`
- `urllib`
- `httpx`
- API key lookup
- token lookup
- cookie lookup
- `.env` read or edit
- raw authorization header handling
- posting or any write action

## Future Implementation Point

The future HTTP implementation should be added only inside
`LiveRecentSearchTransport` after live read-only access is explicitly approved.
It must keep this boundary:

- Query Builder creates the query.
- Credential Loader provides backend-only credentials.
- Live Mode Gate authorizes execution.
- Transport performs one read-only recent-search request.
- Header Parser interprets rate-limit headers.
- Response Normalizer maps JSON into `BuzzFetchResult`.
- Retry Queue/controller handles retry timing.

## Unlock Preconditions

Before replacing the disabled behavior:

- live mode approval must be explicit
- backend-only credential loader must exist
- redaction tests must pass
- timeout and HTTP error mapping tests must exist
- rate-limit and pagination tests must exist
- dry-run pipeline must continue to pass with `MockRecentSearchTransport`
