# RealCredentialLoader Implementation Review Skeleton

Date: 2026-06-04

This is an implementation review and disabled skeleton update only. It does not
read real credentials, read local config, read process values, connect to a
secret manager, connect to an operating-system credential store, perform HTTP,
connect to the X API, or post to X.

## Current Decision

`RealCredentialLoader` remains fail-closed.

Current behavior:

```text
RealCredentialLoader.load()
-> RealCredentialLoaderDisabledError("Real credential loader disabled")
```

The storage adapter interface is defined only as a future extension point. No
adapter performs credential reads.

## Loader Responsibilities

Future `RealCredentialLoader` may own:

- backend-only credential loading
- returning a `CredentialBundle`
- selecting or receiving an approved storage adapter
- preserving the redaction boundary
- failing closed when storage is unavailable, unapproved, invalid, or unsafe

Current `RealCredentialLoader` owns only:

- the future extension point
- disabled error behavior
- adapter injection shape

## Explicitly Out of Scope

`RealCredentialLoader` must not own:

- live mode decision
- HTTP communication
- X API calls
- request construction
- pagination
- retry policy
- retry queue enqueue
- report output
- CSV output
- frontend storage
- diagnostic rendering

## Storage Adapter Interface

Defined skeleton:

```text
CredentialStorageAdapter.load_credentials() -> CredentialBundle
```

Disabled adapter skeletons:

- `EnvCredentialAdapter`
- `SecretManagerAdapter`
- `FileCredentialAdapter`
- `OsCredentialAdapter`

All current adapter skeletons raise:

```text
RealCredentialLoaderDisabledError("Real credential loader disabled")
```

They do not read any credential source.

## Error Design

Future error categories:

| Error | Meaning | Retry/Release Notes |
| --- | --- | --- |
| `loader_disabled` | real loading is intentionally unavailable | blocks live mode |
| `credential_not_found` | approved backend store has no credential | blocks live mode until storage fixed |
| `credential_storage_error` | backend store failed | may be retryable only outside loader |
| `credential_validation_error` | loaded value failed shape or scope validation | blocks live mode |

Skeleton classes:

- `RealCredentialLoaderDisabledError`
- `CredentialNotFoundError`
- `CredentialStorageError`
- `CredentialValidationError`

The current disabled error must not include credential-shaped values.

## Redaction Review

The following must not appear in exceptions, debug output, reports, CSV, retry
metadata, pagination metadata, fixtures, or frontend code:

- `Authorization`
- `Bearer`
- `API_KEY`
- `TOKEN`
- `SECRET`
- `COOKIE`

The loader must never expose raw credential values through safe summaries.
Future adapter errors must be redacted before leaving the loader boundary.

## Adapter Candidate Comparison

| Adapter | Fit | Main Risk | Current Status |
| --- | --- | --- | --- |
| Secret Manager | best for staging and production | provider-specific implementation and access policy | skeleton only |
| Environment Variable | common backend deployment path | accidental process dump or test reading real values | skeleton only |
| Local File | useful only for limited local manual testing outside repo | accidental commit and weak production posture | skeleton only |
| OS Credential Store | useful on managed developer machines | portability and automated test complexity | skeleton only |

## Credential Boundary

Allowed future flow:

```text
CredentialLoader
-> LiveModeGate
-> RequestBuilder
-> LiveRecentSearchTransport
-> LiveHttpClient
```

The loader must not pass credentials to:

- Query Builder
- Preflight Validation summaries
- Response Normalizer
- Rate Limit Parser
- Pagination Controller
- Retry Policy
- Retry Queue
- CSV writer
- report writer
- fixtures
- frontend code

## Gap Analysis

### READY

- `RealCredentialLoader` fail-closed behavior
- adapter interface shape
- disabled adapter skeleton classes
- future error category classes
- fake credential loader remains default
- live mode gate remains closed
- existing redaction utilities

### NEEDS_REVIEW

- approved storage backend by environment
- adapter selection policy
- credential validation rules
- rotation owner and procedure
- adapter-specific redaction tests
- leak regression tests for adapter failures
- rollback procedure for failed credential load

### BLOCKED

- real credential reads
- storage adapter implementation
- secret manager connection
- local file reads
- process value reads
- operating-system credential store connection
- live HTTP
- live mode enablement

## Implementation Preconditions

Before real loading can be implemented:

- storage backend selected and approved
- adapter contract reviewed
- rotation policy approved
- rollback policy approved
- frontend leak tests updated
- redaction tests updated
- credential leak regression tests updated
- adapter failure modes mapped
- `RealCredentialLoader` safe summaries prove no credential value exposure
- explicit live release flags remain required

## Final Recommendation

Keep `RealCredentialLoader` disabled. The next safe step is adapter contract
testing with fake-only storage fixtures, still without reading real credentials
or enabling live mode.
