# Backend-Only Real Credential Storage Policy Review

Date: 2026-06-04

This is a design review only. It does not connect to X API, perform HTTP, read
API keys, read tokens, read cookies, read authorization headers, create or
modify `.env`, read environment variables, access browser storage, store real
credentials, post to X, or fetch real data.

## Current State

- `RealCredentialLoader` exists only as a disabled skeleton.
- `RealCredentialLoader.load()` fails closed.
- No real credential is saved in this project.
- No real credential is read by this project.
- Live mode is not enabled.
- Live HTTP is not implemented.

## Non-Negotiable Credential Rules

Credentials must never be available to:

- frontend code
- browser bundles
- `localStorage`
- `sessionStorage`
- CSV files
- reports
- fixtures
- debug logs
- exception messages
- transport debug output

Credential-shaped values must be redacted before any diagnostic surface can be
emitted.

## Credential Boundary

Allowed future credential flow:

```text
CredentialLoader
-> LiveModeGate
-> RequestBuilder
-> LiveRecentSearchTransport
-> LiveHttpClient
```

Credential values must not flow to:

- Query Builder
- Preflight Validation summaries
- Response Normalizer
- Rate Limit Parser
- Pagination Controller
- Retry Policy
- Retry Queue
- score calculation
- genre detection
- CSV writer
- report writer
- fixtures
- frontend code

`RequestBuilder` may create an authorization header internally, but safe
summaries may expose only header names after redaction, never header values.

## Storage Options Compared

| Option | backend-only feasibility | frontend exposure risk | rotation ease | redaction ease | local dev fit | production fit | accidental commit risk | test ease |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. backend local file | Medium: possible if outside repo and backend-only | Medium: low if outside served paths, high if misplaced | Medium | Medium | Good | Weak to Medium | High if placed in repo | Good with temp fake files |
| B. `.env` | Medium: backend-only possible but easy to misuse | Medium | Medium | Medium | Good | Medium | High | Good but easy to accidentally read real values |
| C. environment variables | Medium: backend-only possible | Low to Medium | Medium | Medium | Medium | Good | Low | Medium, but tests must not read real process env |
| D. secret manager | High | Low | High | High | Weak to Medium | Strong | Low | Medium with fake adapter |
| E. OS credential store | High on a managed host | Low | Medium | High | Medium | Medium to Strong | Low | Medium to Hard |

## Option Notes

### A. Backend Local File

Use only if the file is outside the repository and outside any static/frontend
served path.

Pros:

- simple local development story
- easy to mock with temporary fake files
- can be backend-only if path is fixed carefully

Cons:

- high accidental commit risk if placed under the repo
- weak production posture unless combined with strict filesystem permissions
- rotation can become manual and inconsistent

Status: `NEEDS_REVIEW`

### B. `.env`

Not recommended as the primary plan for this project.

Pros:

- familiar for local development
- easy to mock in many stacks

Cons:

- explicit project rule currently prohibits `.env` creation and modification
- high accidental commit and logging risk
- easy to blur backend-only boundaries

Status: `BLOCKED` for current implementation phase

### C. Environment Variables

Possible in a future backend runtime, but not for the current review or tests.

Pros:

- common deployment mechanism
- lower commit risk than files inside the repo
- works well with many hosting systems

Cons:

- tests must not read the real process environment
- rotation depends on host/deploy tooling
- accidental debug dumps can leak values if not redacted

Status: `NEEDS_REVIEW`

### D. Secret Manager

Recommended for staging and production.

Pros:

- best backend-only fit
- strong rotation and audit capabilities
- low accidental commit risk
- can integrate with least-privilege backend identity

Cons:

- needs provider-specific adapter
- local development needs a fake adapter or separate local policy
- tests must mock the adapter

Status: `READY` as the preferred production direction, `NEEDS_REVIEW` for
specific provider selection

### E. OS Credential Store

Useful for local developer machines or managed hosts where an OS credential
store is available.

Pros:

- avoids repo files
- lower browser/frontend exposure risk
- good local security if configured correctly

Cons:

- cross-platform behavior varies
- harder automated tests
- production fit depends on deployment environment

Status: `NEEDS_REVIEW`

## Recommended Storage by Environment

| Environment | Recommended | Forbidden | Notes |
| --- | --- | --- | --- |
| Development | fake loader by default; optional backend local file outside repo or OS credential store after approval | frontend, browser storage, repo files, CSV, reports, fixtures, `.env` in current phase | real credentials should remain unnecessary for ordinary development |
| Staging | secret manager or managed backend-only environment variable adapter after review | frontend, browser storage, repo files, CSV, reports, fixtures, `.env` as primary storage | use short-lived or scoped credentials and strict redaction tests |
| Production | secret manager | frontend, browser storage, repo files, CSV, reports, fixtures, `.env` as primary storage, manual local files | require rotation, audit, least privilege, rollback |

## Recommended Policy

Primary recommendation:

- development: keep `FakeCredentialLoader` as default
- staging: secret manager preferred
- production: secret manager required

Secondary acceptable path after review:

- backend local file outside the repository for limited local manual testing
- OS credential store for developer machines where supported
- environment variable adapter only if tests prove no real process values are
  read during unit tests and no debug path can expose values

Not recommended:

- `.env` as the project-level primary storage plan
- any storage that is inside the repository
- any storage reachable by frontend/static assets

## RealCredentialLoader Implementation Preconditions

Before implementing real loading:

- storage method selected for each environment
- rotation procedure documented
- rollback procedure documented
- backend-only path reviewed
- frontend leak test updated
- redaction tests updated
- credential leak regression tests updated
- fake adapter remains default
- real adapter disabled unless explicit release flags are present
- no safe summary exposes credential values
- no exception includes credential values
- no report/CSV/debug output includes credential values

Implementation review skeleton:

- `docs/real_credential_loader_review.md`
- `CredentialStorageAdapter.load_credentials() -> CredentialBundle`
- disabled skeletons for environment variable, secret manager, local file, and
  operating-system credential adapters
- future error categories for disabled loader, missing credential, storage
  failure, and validation failure

The adapter interface is now defined, but adapter implementations remain
blocked. Every current real-loader path still raises
`RealCredentialLoaderDisabledError("Real credential loader disabled")`.

## Gap Analysis

### READY

- backend-only rule exists
- fake loader exists
- real loader disabled skeleton exists
- live mode gate blocks live mode
- request builder hides header values in safe summaries
- preflight summaries do not expose header values
- redaction and leak tests exist for fake credential-shaped values

### NEEDS_REVIEW

- exact storage backend for development
- exact storage backend for staging
- exact storage backend for production
- rotation frequency and owner
- secret manager provider or adapter shape
- OS credential store portability
- local manual test procedure
- redaction coverage for real loader failure modes

### BLOCKED

- reading real credentials
- enabling live mode
- live HTTP calls
- `.env` creation or modification
- browser storage usage
- writing credentials to CSV, reports, fixtures, logs, or exceptions
- committing any local credential file

## Final Decision

Real credential loading is not ready to implement until the storage backend and
rotation policy are approved. The safest next design step is to define a
provider-agnostic `RealCredentialLoader` adapter contract while keeping all real
credential reads disabled.
