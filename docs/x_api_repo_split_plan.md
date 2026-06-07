# X API Repo Split Plan

Date: 2026-06-07

This document plans how to split the X API buzz-post extraction system from the
shared `rfrvbike/0001_test` repository into a future dedicated repository.

This is a planning document only. It does not create a new GitHub repository,
move files, copy files, enable HTTP communication, enable LiveMode, read real
credentials, connect to X API, post to X, close PRs, merge PRs, or push to
`main`.

## Recommendation

The X API buzz-post extraction system should be split into a dedicated
repository, but not immediately. The split should happen after the current open
planning PRs are settled and after the migration file list is locked.

Recommended timing:

1. Close or supersede old PR #11, PR #12, and PR #13 after their replacement
   PRs are confirmed in GitHub UI.
2. Recreate or refresh PR #3 and PR #4.
3. Refresh or recreate PR #6 through PR #9.
4. Confirm full unittest is green on latest `main`.
5. Freeze the migration include/exclude file list.
6. Create the new repository and migrate only approved files.

## Why Split

### Prevent cross-project diffs

The current repository contains multiple unrelated systems:

- X API buzz-post extraction system
- X posting and reference tooling
- Excel daily poster and manual live posting helpers
- `dating_assistant/`
- stock analyzer and `server/`
- other local tooling

These systems share Git history, test discovery, reports, and `.gitignore`.
That increases the chance that a PR for one project accidentally includes files
from another project.

### Avoid latest_report.md conflicts

The shared `reports/latest_report.md` has repeatedly conflicted because many
independent tasks update the same file. A dedicated repository can move toward
project-scoped reports, for example:

- `reports/x_api/latest_report.md`
- per-task reports such as `reports/live_http_client_implementation_plan.md`
- a top-level latest report updated only during deliberate integration work

### Clarify credential boundaries before Live work

The Live implementation will need strict credential boundaries. Splitting the X
API read-side collector before enabling Live mode reduces ambiguity around what
may read credentials, what must stay mock-only, and what must never be included
in Git.

### Simplify review and Codex working scope

The current repository includes many files that should not be touched by this
thread. A dedicated repository lets Codex and reviewers focus on:

- X API read-side collection
- reference post analysis
- dry-run and mock pipeline safety
- RedactedLiveSummary and diagnostics
- LiveMode gates and preflight validation

## Candidate Repository Names

| Name | Pros | Cons | Recommendation |
| --- | --- | --- | --- |
| `x-buzz-collector` | Short, concrete, focused on collection | Slightly narrow if analysis features grow | Good default |
| `x-api-buzz-system` | Clear X API boundary and system scope | Less product-like, a little broad | Strong candidate |
| `x-post-intelligence` | Covers collection, analysis, and post creation support | Could be confused with posting automation | Good if analysis becomes primary |
| `x-buzz-analysis-system` | Emphasizes downstream analysis | Less explicit about API/read client boundary | Good secondary candidate |

Recommended name:

```text
x-api-buzz-system
```

Reason: it keeps the X API boundary explicit and leaves room for collector,
analysis, diagnostics, and future Live read-only transport work.

## Candidate Migration Scope

The final migration list must be reviewed before any actual file movement. The
following files and directories are candidates.

### Core package

- `x_auto_ops/`

This currently contains:

- buzz read client contracts
- mock buzz collector
- dry-run recent search pipeline
- query builder
- request builder
- preflight validation
- response normalizer
- rate limit parser
- HTTP client interface and disabled LiveHttpClient skeleton
- LiveRecentSearchTransport disabled skeleton
- HTTP error mapping
- retry policy and retry queue
- pagination controller
- redaction utilities
- RedactedLiveSummary
- fake and disabled real credential loader skeletons
- reference post tooling
- yokaze reference generation
- account policy and provider routing used by X/reference tooling

### CLI tools

Include:

- `tools/mock_buzz_collector.py`
- `tools/mock_recent_search_pipeline.py`
- `tools/x_collect_reference_posts.py`
- `tools/x_analyze_reference_posts.py`
- `tools/x_score_reference_posts.py`
- `tools/x_import_reference_posts_manual.py`
- `tools/x_generate_yokaze_from_reference.py`

Needs review before inclusion:

- `tools/excel_daily_poster/`

The Excel daily poster and manual live posting tools are X-related, but they
perform a different job from the read-only buzz collector. They should either
be kept as a separate local X posting toolkit, or moved only after a separate
decision. They should not be mixed into the first X API read-collector split.

### Data examples

Include examples only:

- `data/x_buzz_genres.json.example`
- `data/source_accounts.csv.example`
- `data/reference_posts/manual_reference_posts.csv.example`
- `data/reference_posts/yokaze_generated_posts.jsonl.example`
- `data/manual_account_posts.csv.example` only if the Excel/manual posting
  scope is intentionally included later

Exclude local or generated data:

- real CSV outputs
- local token files
- OAuth local JSON
- account-specific local CSV files

### Tests and fixtures

Include X API and reference tooling tests:

- `tests/test_account_policy.py`
- `tests/test_credential_loader_live_mode_gate.py`
- `tests/test_dry_run_recent_search_pipeline.py`
- `tests/test_http_client_interface.py`
- `tests/test_http_error_mapping.py`
- `tests/test_live_http_client_disabled.py`
- `tests/test_live_recent_search_transport_disabled.py`
- `tests/test_manual_reference_posts_import.py`
- `tests/test_mock_buzz_collector.py`
- `tests/test_mock_transport_pipeline.py`
- `tests/test_pagination_controller.py`
- `tests/test_preflight_transport_integration.py`
- `tests/test_preflight_validation.py`
- `tests/test_provider_routing.py`
- `tests/test_query_builder_and_rate_limit_parser.py`
- `tests/test_real_credential_loader_review.py`
- `tests/test_redacted_live_summary.py`
- `tests/test_redaction_and_retry_queue.py`
- `tests/test_reference_posts.py`
- `tests/test_request_builder.py`
- `tests/test_x_response_normalizer.py`
- `tests/test_yokaze_reference_generation.py`
- `tests/fixtures/` X API fixture JSON files

Needs review before inclusion:

- `tests/test_excel_daily_poster.py`

Exclude:

- stock analyzer tests
- dating assistant tests
- tests for unrelated local tools

### Documentation

Include X API and reference tooling docs:

- `docs/x_genre_buzz_collector_design.md`
- `docs/x_api_plan_field_research.md`
- `docs/request_builder.md`
- `docs/reference_posts_collector.md`
- `docs/redacted_live_summary.md`
- `docs/redacted_live_summary_review.md`
- `docs/redacted_live_summary_implementation_review.md`
- `docs/real_credential_loader_review.md`
- `docs/preflight_validation.md`
- `docs/preflight_transport_integration.md`
- `docs/pagination_controller.md`
- `docs/manual_reference_posts_import.md`
- `docs/live_transport_release_readiness.md`
- `docs/live_recent_search_transport.md`
- `docs/live_recent_search_transport_review.md`
- `docs/live_recent_search_transport_final_review.md`
- `docs/live_recent_search_transport_disabled.md`
- `docs/live_recent_search_transport_delta_review.md`
- `docs/live_mode_policy.md`
- `docs/live_mode_release_policy.md`
- `docs/live_http_client_review.md`
- `docs/live_http_client_disabled.md`
- `docs/live_http_client_delta_review.md`
- `docs/live_api_minimal_test_plan.md`
- `docs/http_error_mapping.md`
- `docs/http_client_interface.md`
- `docs/backend_credential_storage_review.md`
- `docs/backend_credential_policy.md`
- `docs/yokaze_reference_generation.md`
- `docs/git_push_safety_checklist.md` if it is still applicable after the split

Needs review:

- `docs/excel_daily_poster.md`
- `docs/ACCOUNT_STYLE_GUIDE.md`
- `docs/PROMPT_HISTORY.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/DEVELOPMENT_RULES.md`
- `docs/BUG_HISTORY.md`

### Reports

Include selected X API reports as archive material, but do not keep using the
shared top-level latest report as the main working surface.

Candidates:

- `reports/mock_buzz_report.md`
- `reports/mock_recent_search_pipeline_report.md`
- `reports/live_merge_order_review.md`
- `reports/pr_final_pre_merge_check.md`
- `reports/refresh_planning_prs_review.md`
- `reports/merge_readiness_confirmation.md`
- `reports/post_merge_sync_review.md`
- `reports/superseded_pr_close_check.md` after it is merged
- future `reports/x_api_repo_split_plan_report.md`

Recommended future layout:

```text
reports/
  x_api/
    latest_report.md
    migration/
    live_readiness/
    dry_run/
```

## Do Not Migrate

The following must not be moved to the new repository:

- `.env`
- token, secret, credential, Authorization, or Bearer values
- real credential files
- `data/local/`
- `outputs/local/`
- OAuth local files such as:
  - `data/oauth2_state.local.json`
  - `data/oauth2_tokens.local.json`
- `data/manual_account_posts.csv` if it contains real operational data
- `data/*.local.csv`
- generated real CSV outputs
- partner real data
- `dating_assistant/data/local/`
- stock analyzer app files
- `server/`
- Discord exports
- screenshots, zip files, xlsx files, or other generated artifacts unless
  separately reviewed and sanitized
- personal information or real post/account data not explicitly approved as an
  example fixture

## Excel Daily Poster and Manual Live Posting

The Excel daily poster and manual live posting tools are related to X, but they
are not the same subsystem as the read-only X API buzz collector.

Recommended handling:

- First split only the read-side X API buzz collection and reference analysis
  system.
- Keep Excel/manual live posting out of the first migration unless the user
  explicitly decides to include it.
- If included later, place it in a separate package or repository section such
  as:

```text
x_posting_tools/
```

- Keep its local token/state files excluded and documented as local-only.
- Do not merge posting/write endpoint work into the first read-only collector
  migration.

## latest_report.md Operating Change

To reduce recurring conflicts:

- Do not update shared `reports/latest_report.md` for every project task after
  the split.
- Use task-specific reports.
- Use project-specific latest reports, for example:

```text
reports/x_api/latest_report.md
```

- Update a top-level latest report only for deliberate integration summaries.
- Keep migration reports separate from implementation reports.

## Migration Procedure

Recommended safe sequence:

1. Finish old PR cleanup: close or supersede PR #11, PR #12, and PR #13 after
   GitHub UI review.
2. Resolve current X API planning PRs: recreate or refresh PR #3 and PR #4.
3. Refresh or recreate PR #6 through PR #9 one at a time.
4. Confirm latest `main` has full unittest passing.
5. Create a locked migration include list.
6. Create a locked migration exclude list.
7. Choose the new repository name.
8. Create the new repository.
9. Initialize repository metadata:
   - README
   - `.gitignore`
   - test command notes
   - dry-run safety notes
   - credential policy
10. Copy only approved files.
11. Confirm excluded files are absent.
12. Run tests in the new repository.
13. Fix import paths only if necessary.
14. Add a migration note to the old repository.
15. Start future Live implementation work in the new repository only.

## Risks If Migrating Now

- Existing open PRs #3 through #9 may need refresh or recreation anyway.
- The split could miss files if the include list is not locked first.
- `.gitignore` entries could be incomplete for local credential or generated
  data.
- Test discovery could pull in unrelated tests if not scoped carefully.
- Import paths may change after package extraction.
- Codex thread instructions may still refer to the old shared repository.
- Report history may be duplicated or lost if report ownership is not decided.

## Work To Finish Before Migration

Recommended prerequisites:

- Close/supersede old PR #11, PR #12, and PR #13.
- Decide whether PR #3 and PR #4 should be recreated from latest `main`.
- Refresh or recreate PR #6 through PR #9.
- Confirm full unittest on latest `main`.
- Freeze the migration include/exclude lists.
- Decide whether Excel daily poster/manual live posting is in scope.
- Decide whether the new repository name is `x-api-buzz-system` or another
  candidate.

## Final Recommendation

Proceed with the split, but not as an immediate file move. Treat No.018 as the
planning checkpoint. The next safe action is to resolve the remaining open PRs
and then create a migration include/exclude audit before creating the new
repository.
