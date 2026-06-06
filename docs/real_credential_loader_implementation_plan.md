# RealCredentialLoader Implementation Plan

Date: 2026-06-06

Scope: planning only. No real credential read, `.env` read or write, token file
creation, HTTP communication, X API call, LiveMode enablement, real data fetch,
or posting was performed.

## Goal

Plan the safest path for implementing `RealCredentialLoader` for the X API buzz
collection system. The loader should eventually provide backend-only
credentials to the live read pipeline, while preserving fail-closed behavior
until every release condition is explicitly approved.

## Current Components

Current credential and safety components:

- `FakeCredentialLoader`
  - returns fake credential-shaped values only
  - does not read files, `.env`, environment variables, tokens, cookies, or
    network resources
- `CredentialBundle`
  - common credential shape with `bearer_token`, `api_key`, `api_secret`, and
    `source`
  - provides `safe_summary()` with values redacted
- `RealCredentialLoader`
  - disabled skeleton
  - accepts an optional `CredentialStorageAdapter`
  - `load()` always raises `RealCredentialLoaderDisabledError`
  - does not call adapters yet
- `CredentialStorageAdapter`
  - skeleton protocol with `load_credentials()`
  - future backend-only storage adapter boundary
- disabled adapter skeletons
  - `EnvCredentialAdapter`
  - `SecretManagerAdapter`
  - `FileCredentialAdapter`
  - `OsCredentialAdapter`
- `LiveModeGate`
  - currently allows dry-run only
  - rejects all live mode attempts
- leak and redaction tests
  - fake loader does not read files or environment
  - real loader remains disabled
  - frontend has no credential loader fields
  - pipeline does not leak fake credential values
  - real loader failure does not leak credential-shaped values

## Responsibility Boundary

`RealCredentialLoader` should eventually be responsible for:

- loading credentials only from a reviewed backend-only storage adapter
- returning a validated `CredentialBundle`
- failing closed when credentials are missing, malformed, or unavailable
- preserving redaction boundaries
- never exposing credential values in logs, reports, CSV, debug output, retry
  metadata, pagination metadata, or exceptions

`RealCredentialLoader` must not be responsible for:

- enabling LiveMode
- deciding whether live execution is allowed
- building requests
- sending HTTP
- connecting to X API
- retrying
- paginating
- scoring posts
- writing CSV
- writing reports
- posting, liking, reposting, following, DM, or media upload

## Storage Strategy Decision

### `.env`

Decision: `NEEDS_REVIEW`, not the first implementation target.

Reason:

- easy for local development, but high accidental exposure risk
- project-level `.env` changes are currently prohibited
- tests must not require `.env`
- if allowed later, the file must be gitignored and read only by a backend-only
  adapter with leak tests

### Local JSON or local token file

Decision: `BLOCKED` for first implementation.

Reason:

- high risk of accidental commit
- easy to include raw values in fixtures or reports by mistake
- requires additional path policy, file permission checks, and cleanup rules

### OS credential store

Decision: `NEEDS_REVIEW`.

Reason:

- better local security boundary than repository files
- portability and CI behavior need review
- adapter-specific tests require careful fake storage or dependency injection

### Secret Manager

Decision: preferred for staging/production, `NEEDS_REVIEW` for local first
implementation.

Reason:

- best production posture
- supports rotation and auditability
- requires provider choice, dependency policy, and deployment setup

### Recommended first implementation approach

Implement the loader against an injected storage adapter interface first, using
only fake in-memory test adapters. Do not implement `.env`, local file, OS
store, or secret manager adapters in the first code change.

The first implementation should prove:

- adapter invocation can be wired safely
- returned values can be validated
- failures are redacted and fail closed
- real credentials are not required for CI

## Minimal Implementation Scope

The first implementation should change only:

- `x_auto_ops/real_credential_loader.py`
- tests focused on the real loader boundary
- docs/report updates

Minimal code behavior:

- keep disabled behavior as the default
- require an explicit `enabled=True` or similarly reviewed constructor/config
  flag before calling any adapter
- call only an injected adapter in tests
- validate that required fields exist and are non-empty strings
- return `CredentialBundle(source="REAL")` or a reviewed source label
- raise safe typed errors when missing, invalid, or unavailable

The first implementation must still not:

- read `.env`
- read `os.environ`
- call `getenv`
- open token files
- connect to a secret manager
- use OS credential store APIs
- perform HTTP
- enable LiveMode
- expose credential values

## Proposed Interface

Keep the existing protocol:

```python
class CredentialStorageAdapter(Protocol):
    def load_credentials(self) -> CredentialBundle:
        ...
```

Add explicit loader gating before adapter usage:

```python
RealCredentialLoader(adapter=adapter, enabled=False)
```

Behavior:

- `enabled=False`: raise `RealCredentialLoaderDisabledError`
- `enabled=True` and no adapter: raise `CredentialStorageError` or
  `CredentialNotFoundError`
- adapter returns missing fields: raise `CredentialValidationError`
- adapter raises storage failure: raise `CredentialStorageError`
- adapter returns valid values: return `CredentialBundle`

Error messages must include only stable reason codes, not credential values.

## Error Design

Use existing error classes:

- `RealCredentialLoaderDisabledError`
- `CredentialNotFoundError`
- `CredentialStorageError`
- `CredentialValidationError`

Error message policy:

- allowed: stable error category
- allowed: storage source label if reviewed and non-sensitive
- blocked: credential value
- blocked: partial token display
- blocked: header value
- blocked: local secret path if it reveals user/private naming
- blocked: raw adapter exception message unless redacted and bounded

Recommended stable messages:

```text
Real credential loader disabled
Credential adapter not configured
Credential value missing
Credential validation failed
Credential storage unavailable
```

## Security Policy

Required rules:

- credential values are never logged
- credential values are never written to reports
- credential values are never written to CSV
- credential values are never included in exceptions
- token suffix or partial token display is avoided by default
- `.env`, token files, and local secret files must be gitignored before any
  adapter can read them
- CI and unit tests must not require real credentials
- fake or in-memory adapters must cover tests
- LiveModeGate must pass before any live transport uses loaded credentials
- frontend must not import or call credential loaders
- retry and pagination metadata must never contain credentials
- fixtures must never contain real credential values

## LiveModeGate Relationship

Recommended future order:

```text
Config
-> LiveModeGate
-> RealCredentialLoader
-> RequestBuilder
-> LiveRecentSearchTransport
-> LiveHttpClient
```

Reason:

- live-mode flags should be validated before real credential loading
- dry-run and mock modes should never touch real credential sources
- loader tests can still call the loader directly with fake adapters, but
  pipeline integration should gate first

Fail closed unless all live unlock flags are present:

```text
dry_run=false
live_mode=true
credential_loader=real
transport=live
http_client=live
explicit_approval=true
read_only_recent_search=true
write_actions=false
```

## Step-by-Step Implementation Plan

Step 1: Current code confirmation

- review `credential_loader.py`
- review `real_credential_loader.py`
- review `live_mode_gate.py`
- review credential leak tests
- confirm disabled default remains intact

Step 2: Credential source interface refinement

- keep `CredentialStorageAdapter`
- define adapter return contract
- define source label rules
- avoid implementing real adapters yet

Step 3: Minimal RealCredentialLoader specification

- add explicit enabled gate
- call only injected adapters when enabled
- validate `CredentialBundle`
- preserve disabled default

Step 4: Redaction rules confirmation

- confirm errors do not echo adapter values
- confirm `safe_summary()` is used for diagnostic surfaces
- confirm no raw adapter exception is emitted without redaction

Step 5: Test case plan

- disabled default
- enabled without adapter
- valid fake adapter
- missing bearer token
- missing API key
- missing API secret
- adapter storage failure
- no `.env`, `os.environ`, `getenv`, file, HTTP, or secret manager use
- no leak to exception, debug, summary, report, CSV

Step 6: Implementation file list

- `x_auto_ops/real_credential_loader.py`
- `tests/test_real_credential_loader_review.py` or a new focused test module
- `docs/real_credential_loader_implementation_plan.md`
- `reports/latest_report.md`

Step 7: Defer to later work

- concrete `.env` adapter
- local file adapter
- OS credential adapter
- secret manager adapter
- live transport integration
- live HTTP integration
- first live API request

## Test Plan

Tests should prove:

- all tests pass without real credentials
- fake/in-memory adapter can exercise success path
- missing credentials produce safe typed errors
- credential values do not appear in logs, summaries, reports, CSV, or
  exceptions
- LiveMode disabled paths do not load real credentials in pipeline execution
- `.env` absence does not affect mock tests
- existing unittest suite remains green

Expected baseline:

```text
python -m unittest discover -s tests -v
Ran 161 tests
OK
```

## Files Allowed in the Implementation Task

Preferred implementation files:

- `x_auto_ops/real_credential_loader.py`
- `tests/test_real_credential_loader_review.py`
- `docs/real_credential_loader_implementation_plan.md`
- `reports/latest_report.md`

Avoid changing:

- frontend files
- `server/`
- `src/`
- `dating_assistant/`
- generated CSV
- `.env`
- token files
- fixture files containing credential values

## Explicit Non-Goals

Do not implement in the next loader task:

- HTTP communication
- X API connection
- LiveMode enablement
- write endpoints
- posting
- following
- liking
- reposting
- DM
- media upload
- `.env` creation or modification
- token file creation
- local secret file creation

## Decision Summary

The safest next step is not to implement a real storage backend yet. Instead,
implement `RealCredentialLoader` so it can call an injected fake adapter only
when explicitly enabled in tests, validate the returned `CredentialBundle`, and
fail closed with redacted typed errors. Real storage adapters should remain
disabled until a separate storage-specific plan is approved.
