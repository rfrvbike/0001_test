# X API Initial Copy Manifest

Date: 2026-06-07

Target system:

- X API buzz post extraction system
- Read-only buzz collection, reference post analysis, mock/dry-run tooling, and Live-readiness safety layers

Source repository:

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test
```

Destination repository:

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\x-api-buzz-system
```

This is a dry-run copy plan only. It does not copy, move, stage, commit, or
push any files into the destination repository. It does not enable LiveMode,
HTTP communication, real credential loading, X API access, posting, OAuth live
flows, Excel daily poster execution, stock analyzer work, or dating assistant
work.

`reports/latest_report.md` is intentionally not updated by this task.

## Baseline Safety Status

Old repository status at planning time:

- `git status --short`: clean
- `git status -sb`: `## main...origin/main`
- `origin/main...HEAD`: `0 0`
- latest checked commit: `63eca0a feat: add dating assistant streamlit viewer`

New repository status at planning time:

- repository exists: `https://github.com/rfrvbike/x-api-buzz-system`
- local path exists: `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\x-api-buzz-system`
- initial skeleton commit exists: `3900db1 chore: initialize x api buzz system repo`
- no files were copied into the new repository during this task

## Manifest Rules

Each candidate uses this shape:

```text
copy_candidate:
- source:
- destination:
- reason:
- risk:
- status: include / exclude / hold
```

Status meanings:

- `include`: approved for the first controlled copy pass.
- `exclude`: must not be copied in the first pass.
- `hold`: do not copy unless a later explicit decision approves it.

## Include Candidates

copy_candidate:
- source: `x_auto_ops/__init__.py`
- destination: `x_auto_ops/__init__.py`
- reason: package marker for X API/read-only tooling modules
- risk: low
- status: include

copy_candidate:
- source: `x_auto_ops/account_policy.py`
- destination: `x_auto_ops/account_policy.py`
- reason: account policy support used by X/reference tests
- risk: inspect in copy task for account-specific coupling
- status: include

copy_candidate:
- source: `x_auto_ops/buzz_read_client.py`
- destination: `x_auto_ops/buzz_read_client.py`
- reason: read client interface and mock/live-disabled client boundary
- risk: low, no real API calls expected
- status: include

copy_candidate:
- source: `x_auto_ops/credential_loader.py`
- destination: `x_auto_ops/credential_loader.py`
- reason: fake credential loader and credential bundle interface
- risk: must remain fake/mock only; no real credential values
- status: include

copy_candidate:
- source: `x_auto_ops/dry_run_recent_search_pipeline.py`
- destination: `x_auto_ops/dry_run_recent_search_pipeline.py`
- reason: dry-run pipeline for mock recent search, ranking, reports, and safe summaries
- risk: generated CSV outputs must remain ignored
- status: include

copy_candidate:
- source: `x_auto_ops/http_client.py`
- destination: `x_auto_ops/http_client.py`
- reason: HTTP client interface and disabled HTTP client boundary
- risk: must remain disabled; no requests/httpx/urllib execution
- status: include

copy_candidate:
- source: `x_auto_ops/http_error_mapping.py`
- destination: `x_auto_ops/http_error_mapping.py`
- reason: safe error mapping and retryability metadata
- risk: low
- status: include

copy_candidate:
- source: `x_auto_ops/live_http_client.py`
- destination: `x_auto_ops/live_http_client.py`
- reason: disabled Live HTTP client skeleton
- risk: must stay fail-closed
- status: include

copy_candidate:
- source: `x_auto_ops/live_mode_gate.py`
- destination: `x_auto_ops/live_mode_gate.py`
- reason: fail-closed LiveMode gate
- risk: must not enable LiveMode
- status: include

copy_candidate:
- source: `x_auto_ops/live_recent_search_transport.py`
- destination: `x_auto_ops/live_recent_search_transport.py`
- reason: disabled Live recent search transport skeleton
- risk: must stay fail-closed
- status: include

copy_candidate:
- source: `x_auto_ops/manual_reference_import.py`
- destination: `x_auto_ops/manual_reference_import.py`
- reason: sanitized manual reference post import tooling
- risk: only examples/placeholders should be copied, not real CSV input
- status: include

copy_candidate:
- source: `x_auto_ops/mock_buzz_collector.py`
- destination: `x_auto_ops/mock_buzz_collector.py`
- reason: mock-only buzz collector
- risk: generated output CSV must remain excluded
- status: include

copy_candidate:
- source: `x_auto_ops/mock_transport.py`
- destination: `x_auto_ops/mock_transport.py`
- reason: mock transport for fixture-driven integration tests
- risk: low, no real HTTP
- status: include

copy_candidate:
- source: `x_auto_ops/pagination_controller.py`
- destination: `x_auto_ops/pagination_controller.py`
- reason: pagination controller skeleton and tests
- risk: low
- status: include

copy_candidate:
- source: `x_auto_ops/preflight_validation.py`
- destination: `x_auto_ops/preflight_validation.py`
- reason: recent-search-only preflight allowlist
- risk: low
- status: include

copy_candidate:
- source: `x_auto_ops/provider_routing.py`
- destination: `x_auto_ops/provider_routing.py`
- reason: provider routing support used by X/reference tests
- risk: inspect in copy task for non-X provider coupling
- status: include

copy_candidate:
- source: `x_auto_ops/query_builder.py`
- destination: `x_auto_ops/query_builder.py`
- reason: recent search query builder
- risk: low
- status: include

copy_candidate:
- source: `x_auto_ops/rate_limit_parser.py`
- destination: `x_auto_ops/rate_limit_parser.py`
- reason: rate limit header parser
- risk: low
- status: include

copy_candidate:
- source: `x_auto_ops/real_credential_loader.py`
- destination: `x_auto_ops/real_credential_loader.py`
- reason: disabled real credential loader skeleton
- risk: must remain disabled; no env/file/secret manager reads
- status: include

copy_candidate:
- source: `x_auto_ops/redacted_live_summary.py`
- destination: `x_auto_ops/redacted_live_summary.py`
- reason: safe diagnostic success/error summary
- risk: low
- status: include

copy_candidate:
- source: `x_auto_ops/redaction.py`
- destination: `x_auto_ops/redaction.py`
- reason: redaction utility for diagnostics and reports
- risk: low
- status: include

copy_candidate:
- source: `x_auto_ops/reference_posts.py`
- destination: `x_auto_ops/reference_posts.py`
- reason: reference post collection/analysis model
- risk: copy only code, not real reference output data
- status: include

copy_candidate:
- source: `x_auto_ops/request_builder.py`
- destination: `x_auto_ops/request_builder.py`
- reason: safe request builder and header-name-only debug surface
- risk: credential values must not be logged
- status: include

copy_candidate:
- source: `x_auto_ops/retry_policy.py`
- destination: `x_auto_ops/retry_policy.py`
- reason: retry policy skeleton
- risk: low
- status: include

copy_candidate:
- source: `x_auto_ops/retry_queue.py`
- destination: `x_auto_ops/retry_queue.py`
- reason: mock retry queue
- risk: low
- status: include

copy_candidate:
- source: `x_auto_ops/x_response_normalizer.py`
- destination: `x_auto_ops/x_response_normalizer.py`
- reason: X API fixture response normalizer
- risk: low
- status: include

copy_candidate:
- source: `x_auto_ops/yokaze_reference_generation.py`
- destination: `x_auto_ops/yokaze_reference_generation.py`
- reason: yokaze reference generation from analyzed reference posts
- risk: copy only code and sanitized examples
- status: include

copy_candidate:
- source: `tools/__init__.py`
- destination: `tools/__init__.py`
- reason: tool package marker
- risk: low
- status: include

copy_candidate:
- source: `tools/mock_buzz_collector.py`
- destination: `tools/mock_buzz_collector.py`
- reason: mock buzz collector CLI
- risk: generated CSV output must remain excluded
- status: include

copy_candidate:
- source: `tools/mock_recent_search_pipeline.py`
- destination: `tools/mock_recent_search_pipeline.py`
- reason: mock recent search pipeline CLI
- risk: generated CSV output must remain excluded
- status: include

copy_candidate:
- source: `tools/x_analyze_reference_posts.py`
- destination: `tools/x_analyze_reference_posts.py`
- reason: read-only reference post analysis CLI
- risk: real input CSVs must remain excluded
- status: include

copy_candidate:
- source: `tools/x_collect_reference_posts.py`
- destination: `tools/x_collect_reference_posts.py`
- reason: reference post collection helper
- risk: confirm mock/dry-run boundaries in copy task
- status: include

copy_candidate:
- source: `tools/x_generate_yokaze_from_reference.py`
- destination: `tools/x_generate_yokaze_from_reference.py`
- reason: yokaze generation from reference data
- risk: generated outputs must remain excluded
- status: include

copy_candidate:
- source: `tools/x_import_reference_posts_manual.py`
- destination: `tools/x_import_reference_posts_manual.py`
- reason: manual sanitized reference import CLI
- risk: do not copy real manual input CSV
- status: include

copy_candidate:
- source: `tools/x_score_reference_posts.py`
- destination: `tools/x_score_reference_posts.py`
- reason: reference post scoring CLI
- risk: generated outputs must remain excluded
- status: include

copy_candidate:
- source: `data/source_accounts.csv.example`
- destination: `data/examples/source_accounts.csv.example`
- reason: sanitized account source example
- risk: verify no real account/private data before copy
- status: include

copy_candidate:
- source: `data/x_buzz_genres.json.example`
- destination: `data/examples/x_buzz_genres.json.example`
- reason: sanitized genre config example
- risk: low
- status: include

copy_candidate:
- source: `data/reference_posts/.gitkeep`
- destination: `data/examples/reference_posts/.gitkeep`
- reason: keep example reference directory
- risk: low
- status: include

copy_candidate:
- source: `data/reference_posts/manual_reference_posts.csv.example`
- destination: `data/examples/reference_posts/manual_reference_posts.csv.example`
- reason: sanitized manual reference CSV example
- risk: verify no real post/account content before copy
- status: include

copy_candidate:
- source: `data/reference_posts/yokaze_generated_posts.jsonl.example`
- destination: `data/examples/reference_posts/yokaze_generated_posts.jsonl.example`
- reason: sanitized generated output example
- risk: verify example-only content before copy
- status: include

copy_candidate:
- source: `tests/fixtures/page_1.json`, `tests/fixtures/page_2.json`, `tests/fixtures/page_last.json`
- destination: same paths under `tests/fixtures/`
- reason: mock pagination fixtures
- risk: low, fixture-only
- status: include

copy_candidate:
- source: `tests/fixtures/pipeline_success.json`, `pipeline_partial.json`, `pipeline_rate_limited.json`
- destination: same paths under `tests/fixtures/`
- reason: mock pipeline fixtures
- risk: low, fixture-only
- status: include

copy_candidate:
- source: `tests/fixtures/rate_limit_headers_normal.json`, `rate_limit_headers_reset_only.json`, `rate_limit_headers_retry_after.json`
- destination: same paths under `tests/fixtures/`
- reason: mock rate limit header fixtures
- risk: low, fixture-only
- status: include

copy_candidate:
- source: `tests/fixtures/recent_search_response_minimal.json`, `recent_search_response_missing_metrics.json`, `recent_search_response_partial.json`, `recent_search_response_with_metrics.json`
- destination: same paths under `tests/fixtures/`
- reason: X API response normalizer fixtures
- risk: verify sanitized sample data only
- status: include

copy_candidate:
- source: `tests/fixtures/transport_success.json`, `transport_partial.json`, `transport_rate_limited.json`
- destination: same paths under `tests/fixtures/`
- reason: mock transport fixtures
- risk: low, fixture-only
- status: include

copy_candidate:
- source: `tests/test_account_policy.py`, `tests/test_credential_loader_live_mode_gate.py`, `tests/test_dry_run_recent_search_pipeline.py`, `tests/test_http_client_interface.py`, `tests/test_http_error_mapping.py`, `tests/test_live_http_client_disabled.py`, `tests/test_live_recent_search_transport_disabled.py`, `tests/test_manual_reference_posts_import.py`, `tests/test_mock_buzz_collector.py`, `tests/test_mock_transport_pipeline.py`, `tests/test_pagination_controller.py`, `tests/test_preflight_transport_integration.py`, `tests/test_preflight_validation.py`, `tests/test_provider_routing.py`, `tests/test_query_builder_and_rate_limit_parser.py`, `tests/test_real_credential_loader_review.py`, `tests/test_redacted_live_summary.py`, `tests/test_redaction_and_retry_queue.py`, `tests/test_reference_posts.py`, `tests/test_request_builder.py`, `tests/test_x_response_normalizer.py`, `tests/test_yokaze_reference_generation.py`
- destination: same paths under `tests/`
- reason: X API/read-only/reference/mock safety test suite
- risk: inspect for old repo path assumptions during copy task
- status: include

copy_candidate:
- source: X API docs listed in `reports/migration_scope_lock.md`
- destination: same filenames under `docs/`
- reason: design, safety, Live-readiness, normalizer, request builder, and reference tooling documentation
- risk: inspect for shared-repo references and update after copy if needed
- status: include

## Hold Candidates

copy_candidate:
- source: `reports/mock_buzz_report.md`, `reports/mock_recent_search_pipeline_report.md`, `reports/live_merge_order_review.md`, `reports/post_merge_sync_review.md`, `reports/pr3_9_strategy_review.md`, `reports/pr_final_pre_merge_check.md`, `reports/refresh_planning_prs_review.md`, `reports/merge_readiness_confirmation.md`, `reports/x_api_repo_split_plan_report.md`, `reports/migration_include_exclude_audit.md`, `reports/migration_scope_lock.md`
- destination: `reports/x_api/archive/`
- reason: historical X API project context
- risk: history reports may contain old shared-repo context; review before copying
- status: hold

copy_candidate:
- source: `data/manual_account_posts.csv.example`
- destination: `data/examples/manual_account_posts.csv.example`
- reason: example data may be useful for future posting/reference workflows
- risk: manual account/posting boundary is not part of first migration
- status: hold

copy_candidate:
- source: `docs/ACCOUNT_STYLE_GUIDE.md`, `docs/BUG_HISTORY.md`, `docs/DEVELOPMENT_RULES.md`, `docs/PROJECT_CONTEXT.md`, `docs/PROMPT_HISTORY.md`, `docs/git_push_safety_checklist.md`
- destination: summarized docs in the new repository
- reason: general project history and development rules may be useful
- risk: may include non-X or shared-repo context
- status: hold

copy_candidate:
- source: `tools/excel_daily_poster/`, `tests/test_excel_daily_poster.py`, `docs/excel_daily_poster.md`, `scripts/*excel*`, `scripts/*oauth*`, `scripts/*manual_live*`
- destination: none in first migration
- reason: posting/OAuth/manual live tooling may deserve a separate future repo
- risk: write/live boundaries and credential surfaces
- status: hold

## Exclude Candidates

copy_candidate:
- source: `.env`, `.env.*`, token files, secret files, credential files, OAuth local JSON, Authorization/Bearer values
- destination: none
- reason: credentials and local auth state must never be migrated
- risk: critical credential leak
- status: exclude

copy_candidate:
- source: `data/oauth2_state.local.json`, `data/oauth2_tokens.local.json`
- destination: none
- reason: OAuth local state/token files
- risk: critical credential leak
- status: exclude

copy_candidate:
- source: `data/manual_account_posts.csv`, `data/*.local.csv`, `data/local/`, `outputs/local/`
- destination: none
- reason: local/generated/real operational data
- risk: real data or personal information
- status: exclude

copy_candidate:
- source: `data/mock_buzz_posts.csv`, `data/mock_buzz_posts_*.csv`, `data/mock_recent_search_pipeline_posts.csv`, `data/mock_recent_search_pipeline_posts_*.csv`
- destination: none
- reason: generated mock outputs
- risk: output churn and accidental real-like data persistence
- status: exclude

copy_candidate:
- source: `data/source_accounts.csv`, `data/x_buzz_genres.json`
- destination: none
- reason: local runtime config, not sanitized example config
- risk: account/config leakage
- status: exclude

copy_candidate:
- source: `data/reference_posts/manual_reference_posts.csv`, `raw_posts.csv`, `scored_posts.csv`, `analyzed_posts.jsonl`, `yokaze_generated_posts.jsonl`, `data/reference_posts/*.local.*`
- destination: none
- reason: generated or local reference data
- risk: real post/account content
- status: exclude

copy_candidate:
- source: `dating_assistant/`, `dating_assistant/data/local/`
- destination: none
- reason: separate project and local partner/profile data boundary
- risk: unrelated project and personal data
- status: exclude

copy_candidate:
- source: `src/`, `server/`, `stock-analyzer.html`, `tests/stock-analyzer.test.js`
- destination: none
- reason: stock analyzer system, unrelated to X API buzz collector
- risk: unrelated app mixing
- status: exclude

copy_candidate:
- source: Discord export, logs, output, zip/xlsx, screenshots, personal information, real account/post data
- destination: none
- reason: unrelated generated or sensitive artifacts
- risk: privacy/data leak
- status: exclude

copy_candidate:
- source: `reports/latest_report.md`
- destination: none
- reason: shared-repo latest report should not be copied as-is
- risk: shared project history and conflict churn
- status: exclude

## No.026 Copy Procedure Draft

Do not run these steps in this task. Use them as the controlled plan for the
next task.

1. Confirm old repository is clean and synced.
2. Confirm new repository is clean and synced.
3. Copy only paths marked `include`.
4. Use explicit allowlist copy commands by file or narrow directory.
5. Do not use broad repository copy commands.
6. Do not use `git add .` or `git add -A`.
7. Confirm excluded paths are absent from the destination.
8. Run `git status --short` in the destination repository.
9. Stage only reviewed files by explicit path.
10. Run tests in the destination repository:

```text
python -m unittest discover -s tests -v
```

11. Commit only if tests and safety checks pass.

## No.026 Pre-Copy Checklist

- `x-api-buzz-system` is the active destination repository.
- Destination branch is a new migration branch, not direct `main`.
- No real credentials exist in the copy payload.
- No OAuth local JSON exists in the copy payload.
- No real/local/generated CSV exists in the copy payload.
- `dating_assistant/`, `server/`, `src/`, stock analyzer files, and Discord exports are absent.
- Excel daily poster/manual live posting/OAuth helper paths remain held out.
- `reports/latest_report.md` is not copied.

## Safety Confirmation

- No files were copied to the new repository.
- No files were moved.
- No new repository files were staged.
- No new repository commit was made.
- No new repository push was made.
- No X API connection was made.
- HTTP communication was not enabled.
- LiveMode was not enabled.
- Real credential loading was not enabled.
- `.env` was not created or changed.
- No token/secret/credential file was created or changed.
- No credential value was recorded.
- No Authorization header value was recorded.
- No write endpoint was implemented.
- No posting, follow, like, DM, or media upload work was done.
- Excel daily poster/manual live posting was not executed.
- Stock analyzer files were not changed.
- `server/` files were not changed.
- `src/` files were not changed.
- `dating_assistant/` files were not changed.
- `reports/latest_report.md` was not changed.
- `git add .` and `git add -A` were not used.
- `git reset`, `git clean`, and force push were not used.

## Recommendation

Proceed next with:

```text
作業No.026 x-api-buzz-system 初回移行ファイル safe copy
```

That task should use this manifest as the allowlist/denylist, copy only
`include` candidates, and stop immediately if unexpected destination diffs,
credentials, local data, stock analyzer files, dating assistant files, or
posting/OAuth live paths appear.
