# Refresh Planning PRs Review

Date: 2026-06-06

This report reviews how to refresh, recreate, close, or supersede the currently
pending X API planning PRs before any Live implementation work. It is a
review/report-only change. No PR was merged or closed. No direct push to `main`
was performed. No HTTP communication, X API call, LiveMode enablement, real
credential read, `.env` change, token/secret creation, write endpoint, posting,
follow, like, DM, or media upload work was performed.

## Source State

- Base checked locally: latest fetched `origin/main`
- Review branch: `codex/review/refresh-planning-prs`
- Worktree:
  `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test_worktree_refresh_planning_prs`
- Local test result: `Ran 280 tests / OK`
- GitHub PR open/closed state should still be confirmed in the GitHub UI before
  any merge or close action.

## PR Refresh Matrix

| PR | Current branch | Current purpose | Problem observed from latest `origin/main` | Refresh enough? | Recreate? | Close/supersede? | Desired final artifacts on latest `origin/main` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| #3 | `codex/feature/x-live-implementation-readiness` | Live implementation readiness review | Strong mixed diff: unrelated `dating_assistant/`, local-tool, reference-tool, script, and test deletions appear alongside intended docs | No | Yes | No, content is still useful | `docs/live_implementation_readiness_review.md`, selected related docs, `reports/latest_report.md` only |
| #4 | `codex/plan/real-credential-loader-v2` | RealCredentialLoader implementation plan | Strong mixed diff: unrelated local posting/reference-tool deletions and test changes appear alongside intended plan | No | Yes | No, content is still useful | `docs/real_credential_loader_implementation_plan.md`, `reports/latest_report.md` only |
| #5 | `codex/fix/baseline-import-error` | Baseline import error investigation | Stale and includes unrelated local posting-tool deletions. Latest `origin/main` already passes full unittest locally | No | Only if report still needed | Yes | Prefer close/supersede. If preserved, use a clean report-only branch with `reports/baseline_import_error_investigation.md` only |
| #6 | `codex/plan/live-http-client` | LiveHttpClient implementation plan | Mostly scoped, but `.gitignore` divergence remains visible | Maybe | Preferred if `.gitignore` cannot be cleanly resolved | No | `docs/live_http_client_implementation_plan.md`, `reports/latest_report.md` only |
| #7 | `codex/plan/live-recent-search-transport` | LiveRecentSearchTransport implementation plan | Mostly scoped, but `.gitignore` divergence remains visible | Maybe | Preferred if `.gitignore` cannot be cleanly resolved | No | `docs/live_recent_search_transport_implementation_plan.md`, `reports/latest_report.md` only |
| #8 | `codex/plan/first-live-dry-run-gate` | First Live Dry-Run Gate Test plan | Mostly scoped, but `.gitignore` divergence remains visible | Maybe | Preferred if `.gitignore` cannot be cleanly resolved | No | `docs/first_live_dry_run_gate_test_plan.md`, `reports/latest_report.md` only |
| #9 | `codex/plan/first-minimal-live-api-test` | First Minimal Live API Test plan | Mostly scoped, but `.gitignore` divergence remains visible | Maybe | Preferred if `.gitignore` cannot be cleanly resolved | No | `docs/first_minimal_live_api_test_plan.md`, `reports/latest_report.md` only |
| #10 | `codex/review/merge-order-live-readiness` | Merge-order review | Scoped to report files | Yes, already clean enough locally | No | No | `reports/live_merge_order_review.md`, `reports/latest_report.md` |
| #11 | `codex/review/pr-final-pre-merge-check` | Final pre-merge PR review | Scoped to report files | Yes, already clean enough locally | No | No | `reports/pr_final_pre_merge_check.md`, `reports/latest_report.md` |

## PR #3 Recreate Plan

PR #3 should be recreated from latest `origin/main` instead of trying to merge
or lightly rebase the current branch.

Keep only:

- `docs/live_implementation_readiness_review.md`
- intended updates to:
  - `docs/live_api_minimal_test_plan.md`
  - `docs/live_http_client_review.md`
  - `docs/live_mode_release_policy.md`
  - `docs/live_recent_search_transport.md`
  - `docs/x_genre_buzz_collector_design.md`
  - `reports/latest_report.md`

Remove from the recreated branch:

- all `dating_assistant/` changes
- all stock analyzer/server/src changes if present
- all local posting-tool deletions
- all reference-tool deletions
- unrelated `.gitignore` changes unless specifically required and reviewed

Recommended branch name:

- `codex/feature/x-live-implementation-readiness-v2`

## PR #4 Recreate Plan

PR #4 should also be recreated from latest `origin/main`. The current branch
contains useful planning content but too much unrelated stale diff.

Keep only:

- `docs/real_credential_loader_implementation_plan.md`
- `reports/latest_report.md`

Remove from the recreated branch:

- local posting-tool deletions
- reference-tool deletions
- unrelated test changes
- unrelated `.gitignore` changes unless specifically required and reviewed

Recommended branch name:

- `codex/plan/real-credential-loader-v3`

## PR #5 Close/Supersede Plan

PR #5 is a close/supersede candidate.

Reasoning:

- latest `origin/main` passed `Ran 280 tests / OK` in this review worktree
- the original baseline import error appears resolved or superseded
- the current branch contains unrelated stale deletion diff
- PR #10 and PR #11 already record the need to avoid merging stale mixed diffs

Recommended handling:

- do not merge PR #5 as-is
- close PR #5 if the GitHub UI confirms it still has stale mixed diff
- if preserving the investigation is required, recreate a report-only branch
  from latest `origin/main` with only
  `reports/baseline_import_error_investigation.md`

## PR #6 Through #9 Refresh Plan

PR #6 through PR #9 are much closer to mergeable shape than PR #3 through PR #5,
but each still shows `.gitignore` divergence from latest `origin/main`.

Recommended handling:

1. create a new branch from latest `origin/main`
2. copy the single intended planning doc and `reports/latest_report.md` summary
   from the old branch
3. do not carry over `.gitignore` unless the exact ignore rule is still needed
   and reviewed against latest `origin/main`
4. run full unittest
5. open replacement PR or force-push only if the existing PR branch is known to
   be safe to rewrite

Suggested replacement branch names:

- PR #6: `codex/plan/live-http-client-v2`
- PR #7: `codex/plan/live-recent-search-transport-v2`
- PR #8: `codex/plan/first-live-dry-run-gate-v2`
- PR #9: `codex/plan/first-minimal-live-api-test-v2`

## PR #10 and PR #11 Handling

PR #10 and PR #11 are both report-only and cleanly scoped locally.

Recommended handling:

- merge PR #10 first if GitHub Files changed confirms only:
  - `reports/live_merge_order_review.md`
  - `reports/latest_report.md`
- merge PR #11 second if GitHub Files changed confirms only:
  - `reports/pr_final_pre_merge_check.md`
  - `reports/latest_report.md`

If only one can be merged, PR #11 is the stronger final-state document because
it summarizes PR-by-PR decisions after PR #10. However, merging both preserves
the review trail and is preferred if both are clean.

## Final Recommended Path

Merge candidates:

- PR #10 after GitHub Files changed confirmation
- PR #11 after GitHub Files changed confirmation

Refresh/recreate candidates:

- PR #3: recreate strongly recommended
- PR #4: recreate strongly recommended
- PR #6: refresh/recreate to remove `.gitignore` divergence
- PR #7: refresh/recreate to remove `.gitignore` divergence
- PR #8: refresh/recreate to remove `.gitignore` divergence
- PR #9: refresh/recreate to remove `.gitignore` divergence

Close/supersede candidate:

- PR #5

Live implementation decision:

- do not proceed to RealCredentialLoader minimal implementation yet
- first merge/close/refresh the planning PRs so the Live implementation base is
  clean and auditable

Recommended next work:

- `No.017-C PR #10/#11 merge readiness confirmation`, or
- `No.018 Recreate PR #3 readiness review on latest main`

## Safety Confirmation

- no PR merge was performed
- no PR close was performed
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
