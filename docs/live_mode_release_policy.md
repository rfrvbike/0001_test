# Live Mode Release Policy

This document defines the release conditions for enabling real X API recent
search reads. It does not enable live mode, perform HTTP, read credentials,
modify `.env`, or add posting behavior.

## Current Decision

Live mode remains disabled.

The current approved mode is:

```text
dry_run=true
transport=mock
credential_loader=fake
live_mode=false
```

`live_mode=true` by itself must never unlock real X API access.

## Required Test Gates

All of the following must pass before any live read release review can approve
implementation:

- full unittest suite
- redaction tests
- credential leak tests
- pagination tests
- retry policy tests
- retry queue tests
- request builder tests
- preflight validation tests
- rate limit header parser tests
- HTTP error mapping tests
- response normalizer tests
- transport integration tests
- dry-run gate tests
- frontend credential leak tests

Failure in any gate blocks release.

## Required Implementation Items

These items must be implemented and reviewed before live mode can be enabled:

- `RealCredentialLoader`
- live backend credential storage integration
- credential storage and rotation policy
- `LiveHttpClient`
- `LiveRecentSearchTransport`
- HTTP timeout handling
- HTTP error mapping integration
- request builder integration
- preflight validation integration
- header mapping integration
- pagination integration
- retry policy integration
- retry queue integration
- redacted diagnostics for live transport
- read-only recent search scope enforcement

Implementation review references:

- `docs/live_http_client_review.md`
- `docs/live_http_client_disabled.md`
- `docs/live_recent_search_transport_final_review.md`
- `docs/preflight_validation.md`
- `docs/live_transport_release_readiness.md`
- `docs/backend_credential_storage_review.md`

Current incomplete items:

- `RealCredentialLoader` is disabled.
- live HTTP client is not implemented.
- `LiveHttpClient` exists only as a disabled skeleton.
- `LiveRecentSearchTransport` is disabled.
- final transport implementation responsibility is reviewed, but not live
  implemented.
- credential storage policy is not operational.
- backend credential storage review is complete, but exact storage backend and
  rotation policy still need approval before real loading.
- pagination is mock-tested but not live-integrated.
- retry queue is mock-tested but not live-integrated.
- preflight validation is implemented as a skeleton and must be integrated into
  the future live transport path before live release.
- live transport release readiness is `NEEDS_REVIEW` for implementation and
  `BLOCKED` for live API execution.

## Operational Preflight

Before live reads are approved, confirm current X API constraints:

- X API plan supports recent search.
- allowed search window is known.
- allowed `max_results` range is known.
- pagination limits are known.
- request-per-window limit is known.
- `Retry-After` behavior is known.
- `x-rate-limit-reset` behavior is known.
- `x-rate-limit-remaining` behavior is known.
- `public_metrics` availability is confirmed.
- `like_count` availability is confirmed.
- `retweet_count`/repost count availability is confirmed.
- `reply_count` availability is confirmed.
- `quote_count` availability is confirmed.
- `impression_count` availability is confirmed or explicitly treated as
  nullable.
- user expansion and username availability are confirmed.

If any metric is unavailable, the collector must continue with nullable fields
and the engagement-only fallback score.

Current research is documented in `docs/x_api_plan_field_research.md`.

Research conclusions to carry into release review:

- Recent Search is documented as last-7-days and available to all developers.
- Current pricing docs emphasize pay-per-usage, not the old Free / Basic / Pro
  subscription comparison.
- Treat old plan names as account/console-dependent until verified.
- Use 512 characters as the conservative self-serve recent-search query limit.
- Keep `impression_count` nullable even though current metrics docs list it
  under `public_metrics`.
- Default first live test to low result and page counts.

## Live Unlock Flags

Live access requires multiple affirmative conditions. No single flag is enough.

Minimum release-time conditions:

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

Additional constraints:

- `credential_loader=fake` must block live mode.
- `transport=mock` must block live mode.
- `http_client=disabled` must block live mode.
- missing explicit approval must block live mode.
- any redaction failure must block live mode.
- any failed test gate must block live mode.

## Release Procedure

1. Confirm the branch contains no local secret files or generated real output.
2. Run full unittest.
3. Run targeted credential leak and redaction tests.
4. Run mock dry-run pipeline.
5. Review the backend credential storage plan.
6. Confirm the selected storage backend, rotation owner, and rollback path.
7. Review X API plan constraints and recent-search availability.
8. Review live transport implementation diff.
9. Confirm all live unlock flags are explicit.
10. Confirm read-only recent search is the only allowed endpoint.
11. Perform a dry-run with the live config shape but disabled HTTP.
12. Approve a narrow live read-only test window.
13. Capture redacted diagnostics only.
14. Re-disable live flags after the test window unless explicitly approved for
    continued operation.

## Rollback Procedure

Any anomaly must immediately revert runtime configuration to:

```text
live_mode=false
transport=mock
credential_loader=fake
http_client=disabled
dry_run=true
```

Rollback triggers:

- unexpected HTTP endpoint
- any credential-like value in output
- any frontend credential exposure
- rate limit behavior different from the reviewed plan
- unknown schema shape
- unexpected missing metrics
- non-read API request attempt
- repeated retry queue growth
- unhandled exception

Rollback verification:

- live transport is disabled again
- mock dry-run pipeline still succeeds
- generated reports contain no credential markers
- generated CSV contains no credential markers
- retry queue contains no credential values

## Accident Prevention

Only read-only recent search may be considered.

The following actions remain prohibited:

- post API
- write API
- follow API
- like API
- repost API
- delete API
- DM API
- profile update API
- media upload API

Future code must avoid generic X API clients that can perform write actions
unless the write methods are impossible to call from this pipeline.

## Release Review Checklist

Before live mode can be approved, reviewers must confirm:

- all test gates passed
- live implementation is backend-only
- frontend contains no credential path
- no credential values are logged
- no credential values are written to CSV
- no credential values are written to reports
- no credential values are included in exceptions
- real credential loader does not expose values through debug summaries
- selected credential storage is backend-only and approved for the target
  environment
- request builder does not expose header values
- live transport returns `TransportResponse`
- live transport receives a built query and does not mutate query rules
- live transport uses `RequestBuilder` rather than constructing headers ad hoc
- live transport passes exactly one `HttpRequest` to the injected HTTP client
- live transport rejects non-`GET` and non-recent-search endpoints
- preflight validation runs before `LiveHttpClient.send(...)`
- write endpoint attempts fail preflight
- header parser handles rate limit fields
- normalizer tolerates missing metrics
- pagination respects `next_token`, `max_results`, and max page limits
- retry policy respects `max_retry_count`
- retry queue does not sleep or loop inside the transport
- only read-only recent search endpoint is reachable
- rollback config is documented and tested manually in dry-run form

## Release Blockers

Live mode must remain blocked if any of the following is true:

- any unittest failure exists
- any redaction test fails
- any credential leak test fails
- real credential loader is still disabled
- live HTTP client is missing
- live transport is missing or disabled
- live transport can reach write endpoints
- preflight validation is missing or bypassable
- frontend can access credentials
- `.env` or local secret handling is unreviewed
- credential storage backend or rotation policy is undecided
- X API plan constraints are unknown
- rate limit behavior is unknown
- rollback path is untested
