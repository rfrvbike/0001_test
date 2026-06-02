# Backend Credential Policy

This policy fixes the credential boundary before any real X API connection is
implemented. No real credential is read by the current code.

## Current State

- `FakeCredentialLoader` returns fake values only.
- `RealCredentialLoader` exists only as a disabled skeleton.
- `RealCredentialLoader.load()` always raises
  `RealCredentialLoaderDisabledError("Real credential loader disabled")`.
- No `.env`, file, environment variable, token, cookie, API key, or HTTP access
  is performed.

## Backend-Only Rule

Future real X credentials must be available only inside backend/server runtime
code. They must never be exposed to:

- frontend code
- browser JavaScript bundles
- `localStorage`
- `sessionStorage`
- CSV files
- reports
- fixtures
- debug logs
- exception messages
- transport debug output

## Frontend Prohibitions

Frontend code must not contain X credential loader fields or header values:

- `bearer_token`
- `api_key`
- `api_secret`
- `authorization`
- `x-api-key`

Existing stock-analysis J-Quants redaction strings are a separate system. They
must not become an X credential path.

## Loader Selection

`select_credential_loader(config)` supports:

- `fake`: returns `FakeCredentialLoader`
- `real`: returns `RealCredentialLoader`

The `real` path remains disabled. Selecting it does not read credentials; using
it raises the disabled error.

## Redaction Rule

Credential-shaped values must be redacted before data can reach:

- reports
- CSV output
- debug logs
- exception messages

Any test fixture or report containing fake credential markers must prove they
are redacted before a future live read path is enabled.
