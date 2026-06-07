# PR #3-#9 Strategy Review

Date: 2026-06-07

This report reviews how to handle PR #3 through PR #9 for the X API buzz-post
extraction system after PR #18 introduced the dedicated repository split plan
for `x-api-buzz-system`.

This is a review/report-only change. No PR was closed or merged. No new GitHub
repository was created. No files were moved or copied. No direct push to `main`
was performed. No GitHub manual conflict resolution, HTTP communication, X API
call, LiveMode enablement, real credential read, `.env` change, token/secret
creation, write endpoint, posting, follow, like, DM, or media upload work was
performed.

## Source State

- Base checked locally: latest fetched `origin/main`
- Base commit: `9e56317 Merge pull request #19 from rfrvbike/codex/review/after-pr-close-check`
- Review branch: `codex/review/pr3-9-strategy`
- Worktree:
  `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test_worktree_pr3_9_strategy`
- Current split recommendation from PR #18:
  - future dedicated repository name: `x-api-buzz-system`
  - avoid updating shared `reports/latest_report.md` for ordinary X API tasks

## Latest Main Safety Check

Command:

```text
python -m unittest discover -s tests -v
```

Result:

```text
Ran 280 tests in 1.803s

OK
```

## PR Status Review Method

This review uses local remote branch diffs against latest `origin/main`.
GitHub PR open/closed/conflict state was not checked via HTTP or GitHub API in
this task. No PR was changed.

## PR-by-PR Review

| PR | Branch | Current observed diff files | Mixed non-X diff? | latest_report diff? | Current repo action | New repo action |
| --- | --- | --- | --- | --- | --- | --- |
| #3 | `origin/codex/feature/x-live-implementation-readiness` | `docs/live_api_minimal_test_plan.md`, `docs/live_http_client_review.md`, `docs/live_implementation_readiness_review.md`, `docs/live_mode_release_policy.md`, `docs/live_recent_search_transport.md`, `docs/x_genre_buzz_collector_design.md`, `reports/latest_report.md` | No obvious non-X files in current diff | Yes | Do not merge as-is; close/supersede or recreate only if needed before split | Recreate as a new readiness review in `x-api-buzz-system` |
| #4 | `origin/codex/plan/real-credential-loader-v2` | `docs/real_credential_loader_implementation_plan.md`, `reports/latest_report.md` | No obvious non-X files in current diff | Yes | Do not merge as-is; close/supersede or recreate only if credential planning is needed before split | Recreate in new repo before RealCredentialLoader implementation |
| #5 | `origin/codex/fix/baseline-import-error` | `reports/baseline_import_error_investigation.md`, `reports/latest_report.md` | No obvious non-X files in current diff | Yes | Close/supersede candidate because latest `origin/main` passes unittest | No recreation needed unless the issue returns |
| #6 | `origin/codex/plan/live-http-client` | `docs/live_http_client_implementation_plan.md`, `reports/latest_report.md` | No obvious non-X files in current diff | Yes | Do not refresh in current repo unless Live work must start before split | Recreate in new repo |
| #7 | `origin/codex/plan/live-recent-search-transport` | `docs/live_recent_search_transport_implementation_plan.md`, `reports/latest_report.md` | No obvious non-X files in current diff | Yes | Do not refresh in current repo unless Live work must start before split | Recreate in new repo |
| #8 | `origin/codex/plan/first-live-dry-run-gate` | `docs/first_live_dry_run_gate_test_plan.md`, `reports/latest_report.md` | No obvious non-X files in current diff | Yes | Do not refresh in current repo unless Live work must start before split | Recreate in new repo |
| #9 | `origin/codex/plan/first-minimal-live-api-test` | `docs/first_minimal_live_api_test_plan.md`, `reports/latest_report.md` | No obvious non-X files in current diff | Yes | Do not refresh in current repo unless Live work must start before split | Recreate in new repo |

## Re-evaluation After Repo Split Plan

The previous direction was:

- PR #3: recreate/refresh candidate
- PR #4: recreate/refresh candidate
- PR #5: close/supersede candidate
- PR #6: refresh/recreate candidate
- PR #7: refresh/recreate candidate
- PR #8: refresh/recreate candidate
- PR #9: refresh/recreate candidate

After PR #18, the better strategy is to stop spending effort refreshing most
planning PRs in the shared repository. The remaining PRs all carry
`reports/latest_report.md` changes, and the new reporting policy is to avoid
that shared file for ordinary X API work.

## Current Repository vs New Repository

### Finish in current repository

Pros:

- Existing PR URLs and discussions remain attached to the current repository.
- Minimal setup work if only one or two documents are urgent.

Cons:

- Each PR still updates shared `reports/latest_report.md`.
- More conflict resolution work is likely.
- Work continues in a repository that also contains `dating_assistant/`, stock
  analyzer, `server/`, and other unrelated tools.
- The resulting docs may soon need to be copied or recreated into the new repo.

### Recreate after repository split

Pros:

- Aligns with the new `x-api-buzz-system` direction.
- Avoids further shared `latest_report.md` conflicts.
- Lets Live readiness, credential loader, LiveHttpClient, and Live transport
  plans be written against the final repository layout.
- Reduces cross-project review noise.

Cons:

- Requires creating the new repository and migration baseline first.
- Existing PRs #3 through #9 need close/supersede handling.
- Some useful report content must be manually carried into new repo docs.

## Recommendation

### Current repo refresh/recreate and merge

Recommended:

- None by default.

Conditional exception:

- PR #3 and PR #4 may be recreated in the current repository only if Live work
  must continue before the new repository exists.

### Close/supersede candidates

Recommended:

- PR #5

Reason:

- It was a baseline import error investigation.
- Latest `origin/main` passed full unittest in this review.
- No active fix appears needed now.

Likely close/supersede after preserving useful content:

- PR #3
- PR #4
- PR #6
- PR #7
- PR #8
- PR #9

Reason:

- Their useful content is planning/review material.
- They should be recreated in the future `x-api-buzz-system` repository using
  project-specific reports instead of shared `reports/latest_report.md`.

### Recreate after new repo split

Recommended:

- PR #3: Live implementation readiness review
- PR #4: RealCredentialLoader implementation plan
- PR #6: LiveHttpClient implementation plan
- PR #7: LiveRecentSearchTransport implementation plan
- PR #8: First Live dry-run gate test plan
- PR #9: First minimal Live API test plan

### Not necessary now

Recommended:

- PR #5

Reason:

- The baseline is green and the investigation report is no longer blocking.

## Priority Order

Recommended next work:

1. Create or review the PR for No.019 strategy report.
2. Decide whether to proceed with creating the new `x-api-buzz-system`
   repository.
3. If yes, create a migration include/exclude audit before moving files.
4. Close/supersede PR #5 if GitHub UI confirms it is still open and no longer
   needed.
5. For PR #3, PR #4, and PR #6 through PR #9, preserve useful content and
   recreate it after the split.

## Safety Confirmation

- No PR close was performed.
- No PR merge was performed.
- No new GitHub repository was created.
- No files were moved.
- No files were copied.
- No direct push to `main` was performed.
- No GitHub manual conflict resolution was performed.
- No HTTP communication was enabled.
- LiveMode was not enabled.
- No X API connection was made.
- Real credential loading was not enabled.
- `.env` was not created or changed.
- No token/secret file was created or changed.
- No credential value or Authorization header was recorded.
- No write endpoint, posting, follow, like, DM, or media upload work was done.
- No Excel daily poster/manual live posting work was performed.
- No stock analyzer, `server/`, `dating_assistant/`, or Discord export files
  were changed.
- No `git add .` or `git add -A` was used.
- No `git reset`, `git clean`, force push, or force-with-lease push was used.
