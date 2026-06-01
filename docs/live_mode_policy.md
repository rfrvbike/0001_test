# Live Mode Policy

This document fixes the live-mode policy before any real X API connection is
implemented. It is design-only except for mock gate behavior already enforced in
tests. No X API call, HTTP request, API key lookup, token lookup, cookie access,
`.env` read, or posting behavior is introduced here.

## Default Mode

- Dry-run is the default and only allowed mode.
- Live mode is disabled by default.
- `assert_live_mode_allowed(...)` rejects live-mode attempts.
- Fake credentials do not unlock live mode.

## Unlock Conditions

Future live mode must require all of the following before any real read request
is allowed:

- explicit user approval for live read-only X API access
- backend-only credential loader implementation
- redaction tests passing for report, CSV, debug log, and exception output
- dry-run gate tests proving accidental live execution is blocked
- timeout and HTTP error mapping tests
- rate-limit retry queue tests
- pagination tests using mock transport

## Credential Loader Policy

Current implementation:

- `FakeCredentialLoader` only
- returns fake values only
- does not read files
- does not read `.env`
- does not read environment variables
- does not perform HTTP

Future live implementation must remain backend-only. Credentials must never be
available to frontend code, browser storage, CSV, reports, fixtures, logs, debug
output, or exception messages.

## Redaction Policy

Credential-shaped values must be redacted before data is written to:

- reports
- CSV leak-test output
- debug logs
- exception messages
- transport diagnostic output

Fake values such as `FAKE_API_KEY`, `FAKE_SECRET`, and `FAKE_TOKEN` are used in
tests to prove the redaction boundary before real credentials exist.

## Live Transport Policy

The future live transport must stay behind:

- `XApiBuzzReadClient` dry-run gate
- `assert_live_mode_allowed(...)`
- an explicit live transport constructor option
- backend-only credential loading

The transport must only perform read-only recent-search requests. Posting,
liking, reposting, following, and any write action remain prohibited.
