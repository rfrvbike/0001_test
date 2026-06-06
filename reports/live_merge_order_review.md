# Live Merge Order Review

Date: 2026-06-06

This review covers the pending X API buzz-post extraction PRs before any Live
implementation work. It is a review/report-only change. No PR was merged, no
HTTP communication was enabled, no X API call was made, no credential was read,
and LiveMode remains disabled.

## Review Scope

Repository: `rfrvbike/0001_test`

Reviewed PRs:

| PR | Title | Branch | Purpose | Observed local diff status | Merge caution |
| --- | --- | --- | --- | --- | --- |
| #3 | Review live implementation readiness | `codex/feature/x-live-implementation-readiness` | Final integrated review before Live implementation | Stale against latest `origin/main`; diff currently includes unrelated `dating_assistant/`, local posting-tool deletions, and reference-tool deletions | Do not merge as-is. Rebase or recreate on latest `origin/main` and verify docs/report-only X API diff before review. |
| #4 | Plan RealCredentialLoader implementation | `codex/plan/real-credential-loader-v2` | Plan safe RealCredentialLoader implementation | Stale against latest `origin/main`; diff currently includes unrelated local posting/reference-tool deletions | Do not merge as-is. Rebase or recreate on latest `origin/main` and verify only the credential plan/report remain. |
| #5 | Investigate baseline import errors | `codex/fix/baseline-import-error` | Investigate previous baseline import errors | Stale against latest `origin/main`; diff currently includes unrelated local posting-tool deletions | Treat as first dependency only if still needed. Latest `origin/main` should be tested first; if baseline is already OK, close or supersede instead of merging stale diff. |
| #6 | Plan LiveHttpClient implementation | `codex/plan/live-http-client` | Plan LiveHttpClient implementation | Mostly scoped, but still shows `.gitignore` divergence from latest `origin/main` | Refresh on latest `origin/main`; verify expected files only before merge. |
| #7 | Plan LiveRecentSearchTransport implementation | `codex/plan/live-recent-search-transport` | Plan LiveRecentSearchTransport implementation | Mostly scoped, but still shows `.gitignore` divergence from latest `origin/main` | Refresh on latest `origin/main`; verify expected files only before merge. |
| #8 | Plan First Live Dry-Run Gate Test | `codex/plan/first-live-dry-run-gate` | Plan the dry-run gate test before any first live request | Mostly scoped, but still shows `.gitignore` divergence from latest `origin/main` | Refresh on latest `origin/main`; verify expected files only before merge. |
| #9 | Plan First Minimal Live API Test | `codex/plan/first-minimal-live-api-test` | Plan first minimal read-only live X API test conditions | Mostly scoped, but still shows `.gitignore` divergence from latest `origin/main` | Refresh on latest `origin/main`; verify expected files only before merge. |

## Recommended Merge Order

Do not merge the pending PRs in their current stale state. First create updated
PR branches from latest `origin/main` or rebase each branch and confirm the
Files changed view does not include unrelated removals.

Recommended order after refresh:

1. PR #5, only if latest `origin/main` still has the baseline import issue.
   If current main already passes all tests, treat #5 as superseded or replace it
   with a report-only PR.
2. PR #3, after removing stale unrelated `dating_assistant/` and local-tool
   deletion diffs.
3. PR #4, after confirming it is documentation/report-only for
   RealCredentialLoader planning.
4. PR #6, after confirming it is documentation/report-only for LiveHttpClient
   planning.
5. PR #7, after confirming it is documentation/report-only for
   LiveRecentSearchTransport planning.
6. PR #8, after confirming it is documentation/report-only for the first live
   dry-run gate plan.
7. PR #9, after confirming it is documentation/report-only for the first minimal
   live API test plan.

Rationale:

- baseline/test-health findings should be resolved or explicitly superseded
  before merging later planning PRs
- readiness review should precede component-specific Live implementation plans
- credential loading, HTTP client, and transport planning should precede any
  dry-run gate or first-live test plan
- dry-run gate planning must precede the minimal live API test plan
- no implementation should start until all planning PRs are either merged,
  superseded, or intentionally closed

## Live Pre-Implementation Checklist

Before implementing RealCredentialLoader, LiveHttpClient, or
LiveRecentSearchTransport, confirm:

- latest `origin/main` has a full passing unittest run
- all pending planning PRs have clean, isolated diffs
- RealCredentialLoader storage policy is documented and approved
- credential rotation and rollback owner are identified
- LiveHttpClient responsibilities are documented and bounded to one request and
  one response
- LiveRecentSearchTransport responsibilities are documented and exclude
  pagination, retry loops, scoring, CSV output, and report output
- First Live Dry-Run Gate conditions are documented
- First Minimal Live API Test conditions are documented
- write endpoints remain blocked
- read-only recent search is the only allowed Live endpoint
- raw request headers, raw response headers, raw body, raw JSON, full query text,
  full post text, usernames, author IDs, post ID lists, and CredentialBundle
  contents remain blocked from CLI, report, CSV, debug logs, exceptions, retry
  metadata, pagination metadata, fixtures, screenshots, and frontend surfaces
- explicit approval wording is documented before any future Live execution
- rollback returns to `live_mode=false`, `transport=mock`,
  `credential_loader=fake`, `http_client=disabled`, and `dry_run=true`

## Remaining Review Items

These items are not blockers for planning PR review if they are explicitly kept
at plan level, but they are blockers for Live execution:

- credential storage backend
- credential rotation procedure
- HTTP library choice
- connect/read/total timeout values
- request ID diagnostics strategy
- retry queue integration during live phases after first-live
- pagination controller integration during live phases after first-live
- live report retention policy
- rate-limit monitoring policy
- rollback owner and runbook
- live execution approval record

## Recommended Next Work

Recommended next work: `No.017-A merge preflight final PR review`.

Do not proceed directly to `No.017 RealCredentialLoader minimal implementation`
until the pending PRs are refreshed, isolated, and either merged or intentionally
closed. The current safest next step is a merge preflight review, not Live
implementation.

## Safety Confirmation

- no PR merge was performed
- no direct push to `main` was performed
- no HTTP communication was enabled
- LiveMode was not enabled
- no X API connection was made
- no real credential read was enabled
- `.env` was not created or changed
- no token or secret file was created
- no credential value was written
- no Authorization header value was written
- no write endpoint was implemented
- no post, follow, like, DM, or media upload operation was implemented
- no stock analyzer file was changed
- no dating assistant file was changed
- the existing main worktree was not cleaned or reset
