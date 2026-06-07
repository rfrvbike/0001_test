# Migration Include/Exclude Audit

Date: 2026-06-07

Target system:

- X API buzz post extraction system
- Read-only buzz collection, reference post analysis, dry-run/mock tooling, and Live-readiness safety layers

Future repository candidate:

```text
x-api-buzz-system
```

This is an audit/report-only change. It does not create a new GitHub repository,
move files, copy files, close PRs, merge PRs, enable HTTP communication,
enable LiveMode, read real credentials, connect to X API, post to X, or update
`reports/latest_report.md`.

## Current Repository Shape

The current repository contains multiple systems in one working tree:

- X API buzz collection and reference tooling
- Excel daily poster and manual live posting helpers
- `dating_assistant/`
- stock analyzer frontend/backend under `src/`, `server/`, and related files
- general training/demo files

The migration must therefore be path-based and allowlist-driven. The initial
split should not copy the whole repository or rely on broad directory moves
without review.

## Should Migrate

These files are safe candidates for the first read-only X API buzz system split.

### Core Package

- `x_auto_ops/__init__.py`
- `x_auto_ops/account_policy.py`
- `x_auto_ops/buzz_read_client.py`
- `x_auto_ops/credential_loader.py`
- `x_auto_ops/dry_run_recent_search_pipeline.py`
- `x_auto_ops/http_client.py`
- `x_auto_ops/http_error_mapping.py`
- `x_auto_ops/live_http_client.py`
- `x_auto_ops/live_mode_gate.py`
- `x_auto_ops/live_recent_search_transport.py`
- `x_auto_ops/manual_reference_import.py`
- `x_auto_ops/mock_buzz_collector.py`
- `x_auto_ops/mock_transport.py`
- `x_auto_ops/pagination_controller.py`
- `x_auto_ops/preflight_validation.py`
- `x_auto_ops/provider_routing.py`
- `x_auto_ops/query_builder.py`
- `x_auto_ops/rate_limit_parser.py`
- `x_auto_ops/real_credential_loader.py`
- `x_auto_ops/redacted_live_summary.py`
- `x_auto_ops/redaction.py`
- `x_auto_ops/reference_posts.py`
- `x_auto_ops/request_builder.py`
- `x_auto_ops/retry_policy.py`
- `x_auto_ops/retry_queue.py`
- `x_auto_ops/x_response_normalizer.py`
- `x_auto_ops/yokaze_reference_generation.py`

Reason: these modules form the current read-only collector, mock transport,
normalizer, request/preflight, redaction, retry, pagination, credential-boundary
skeleton, and reference-generation foundation.

### CLI Tools

- `tools/mock_buzz_collector.py`
- `tools/mock_recent_search_pipeline.py`
- `tools/x_analyze_reference_posts.py`
- `tools/x_collect_reference_posts.py`
- `tools/x_generate_yokaze_from_reference.py`
- `tools/x_import_reference_posts_manual.py`
- `tools/x_score_reference_posts.py`

Reason: these are directly tied to mock/dry-run buzz collection and reference
post tooling. They do not require real X API access by default.

### Data Examples Only

- `data/source_accounts.csv.example`
- `data/x_buzz_genres.json.example`
- `data/reference_posts/.gitkeep`
- `data/reference_posts/manual_reference_posts.csv.example`
- `data/reference_posts/yokaze_generated_posts.jsonl.example`

Reason: these are sanitized examples or placeholders. They preserve expected
data shapes without moving local/generated/real operational data.

### X API Fixtures

- `tests/fixtures/page_1.json`
- `tests/fixtures/page_2.json`
- `tests/fixtures/page_last.json`
- `tests/fixtures/pipeline_partial.json`
- `tests/fixtures/pipeline_rate_limited.json`
- `tests/fixtures/pipeline_success.json`
- `tests/fixtures/rate_limit_headers_normal.json`
- `tests/fixtures/rate_limit_headers_reset_only.json`
- `tests/fixtures/rate_limit_headers_retry_after.json`
- `tests/fixtures/recent_search_response_minimal.json`
- `tests/fixtures/recent_search_response_missing_metrics.json`
- `tests/fixtures/recent_search_response_partial.json`
- `tests/fixtures/recent_search_response_with_metrics.json`
- `tests/fixtures/transport_partial.json`
- `tests/fixtures/transport_rate_limited.json`
- `tests/fixtures/transport_success.json`

Reason: these support deterministic mock testing without live HTTP calls.

### X API and Reference Tests

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

Reason: these validate the X read-side collector, reference tooling, safety
boundaries, and mock Live-readiness layers.

### X API Documentation

- `docs/backend_credential_policy.md`
- `docs/backend_credential_storage_review.md`
- `docs/http_client_interface.md`
- `docs/http_error_mapping.md`
- `docs/live_api_minimal_test_plan.md`
- `docs/live_http_client_delta_review.md`
- `docs/live_http_client_disabled.md`
- `docs/live_http_client_review.md`
- `docs/live_mode_policy.md`
- `docs/live_mode_release_policy.md`
- `docs/live_recent_search_transport.md`
- `docs/live_recent_search_transport_delta_review.md`
- `docs/live_recent_search_transport_disabled.md`
- `docs/live_recent_search_transport_final_review.md`
- `docs/live_recent_search_transport_review.md`
- `docs/live_transport_release_readiness.md`
- `docs/manual_reference_posts_import.md`
- `docs/pagination_controller.md`
- `docs/preflight_transport_integration.md`
- `docs/preflight_validation.md`
- `docs/real_credential_loader_review.md`
- `docs/redacted_live_summary.md`
- `docs/redacted_live_summary_implementation_review.md`
- `docs/redacted_live_summary_review.md`
- `docs/reference_posts_collector.md`
- `docs/request_builder.md`
- `docs/x_api_plan_field_research.md`
- `docs/x_api_repo_split_plan.md`
- `docs/x_genre_buzz_collector_design.md`
- `docs/yokaze_reference_generation.md`

Reason: these describe the collector design, Live-readiness safety layers,
credential boundaries, and reference tooling.

## Should Not Migrate

These files and directories must be excluded from the first split.

- `.env`
- `.env.*`
- token, secret, credential, Authorization, or Bearer values
- OAuth local JSON, including `data/oauth2_state.local.json` and
  `data/oauth2_tokens.local.json`
- `data/manual_account_posts.csv`
- `data/*.local.csv`
- `data/local/`
- `outputs/local/`
- generated dry-run CSVs such as `data/mock_buzz_posts.csv` and
  `data/mock_recent_search_pipeline_posts.csv`
- generated reference outputs:
  - `data/reference_posts/manual_reference_posts.csv`
  - `data/reference_posts/raw_posts.csv`
  - `data/reference_posts/scored_posts.csv`
  - `data/reference_posts/analyzed_posts.jsonl`
  - `data/reference_posts/yokaze_generated_posts.jsonl`
- `dating_assistant/`
- `dating_assistant/data/local/`
- partner real data
- stock analyzer frontend/backend:
  - `src/`
  - `server/`
  - `stock-analyzer.html`
  - `tests/stock-analyzer.test.js`
- Discord exports
- screenshots, zip files, xlsx files, and generated artifacts unless separately
  reviewed and sanitized
- personal information, real account data, or real post data

Reason: these either belong to another project, contain or may contain local
operational data, or are outside the read-only X API buzz collector boundary.

## Needs Review Before Migration

These paths are X-related but should not be part of the first read-only split
unless explicitly approved.

### Excel Daily Poster / Manual Live Posting

- `tools/excel_daily_poster/`
- `tests/test_excel_daily_poster.py`
- `docs/excel_daily_poster.md`
- `scripts/manual_live_post_once.example.bat`
- `scripts/register_excel_daily_post_oauth2_live_task.example.bat`
- `scripts/register_excel_daily_post_task.bat`
- `scripts/run_excel_daily_post.bat`
- `scripts/run_excel_daily_post_oauth2_live.example.bat`
- `data/manual_account_posts.csv.example`

Recommendation: keep these out of the initial split. They are X-related, but
they are posting/OAuth/manual-live tooling, not read-only buzz collection. If
they are migrated later, place them in a separate package or repository section
such as `x_posting_tools/`, with local token/state files excluded.

### General Project Docs

- `docs/ACCOUNT_STYLE_GUIDE.md`
- `docs/BUG_HISTORY.md`
- `docs/DEVELOPMENT_RULES.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/PROMPT_HISTORY.md`
- `docs/git_push_safety_checklist.md`

Recommendation: review individually. Some may be useful as historical context,
but they are not required for the initial read-only collector repository.

### Historical Reports

- `reports/codex_report_*.md`
- `reports/live_merge_order_review.md`
- `reports/merge_readiness_confirmation.md`
- `reports/post_merge_sync_review.md`
- `reports/pr3_9_strategy_review.md`
- `reports/pr_final_pre_merge_check.md`
- `reports/refresh_planning_prs_review.md`
- `reports/x_api_repo_split_plan_report.md`
- `reports/mock_buzz_report.md`
- `reports/mock_recent_search_pipeline_report.md`

Recommendation: migrate only selected X API history under a project-scoped
archive, for example `reports/x_api/archive/`. Do not carry over the shared
`reports/latest_report.md` unchanged because it has been a repeated conflict
surface.

## Initial Migration Target

For the first `x-api-buzz-system` repository, include:

- `README.md` created for the new repository
- `pyproject.toml` or `requirements.txt` after dependency review
- `.gitignore` with local/secret/generated exclusions
- `x_auto_ops/`
- selected `tools/` read-only and reference CLIs
- selected `tests/` and X API fixtures
- selected `docs/`
- example-only `data/`
- `reports/x_api/` for project-scoped reports

Do not include Excel/manual live posting in the initial migration unless there
is a separate explicit decision.

## Initial Migration Out Of Scope

- Live HTTP implementation
- real credential loader implementation
- LiveMode enablement
- first live API call
- write endpoints
- posting, liking, reposting, following, DM, media upload
- Excel daily poster execution
- manual live posting execution
- stock analyzer
- dating assistant
- Discord export processing

## Import Path and Package Risks

Risks to verify after copying approved files:

- `tools/` scripts may assume the current repository root.
- Tests may assume fixture paths under `tests/fixtures/`.
- Reports and docs may reference old shared-repository paths.
- Package imports should continue to use `x_auto_ops.*`.
- New repository test discovery should exclude stock analyzer and
  `dating_assistant` tests by construction.
- `reports/latest_report.md` references should be changed to a project-scoped
  path such as `reports/x_api/latest_report.md`.

Recommended new repository layout:

```text
README.md
pyproject.toml
.gitignore
x_auto_ops/
tools/
docs/
reports/
  x_api/
    latest_report.md
    archive/
tests/
  fixtures/
data/
  examples/
```

## New Repository .gitignore Recommendation

Minimum rules:

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.env
.env.*
*.local
*.local.*
*.token
*.secret
*credentials*
tokens/
logs/
*.log
data/*.local.csv
data/local/
outputs/local/
reports/local/
data/oauth2_*.local.json
data/*token*.local.json
data/*secret*.local.json
data/mock_buzz_posts.csv
data/mock_buzz_posts_*.csv
data/mock_recent_search_pipeline_posts.csv
data/mock_recent_search_pipeline_posts_*.csv
data/source_accounts.csv
data/x_buzz_genres.json
data/reference_posts/manual_reference_posts.csv
data/reference_posts/raw_posts.csv
data/reference_posts/scored_posts.csv
data/reference_posts/analyzed_posts.jsonl
data/reference_posts/yokaze_generated_posts.jsonl
data/reference_posts/*.local.*
```

If Excel/manual live posting is later added, keep OAuth/token local files
excluded and document them as local-only.

## Additional Checks Before Creating New Repository

- Confirm PR #3 through PR #9 are closed, recreated, or intentionally deferred.
- Lock the final include list and exclude list in a PR.
- Decide whether Excel daily poster/manual live posting belongs in the first
  repository or a later separate package.
- Confirm the new repository name.
- Confirm dependency file choice: `pyproject.toml` vs `requirements.txt`.
- Confirm whether historical reports should be copied, summarized, or omitted.
- Confirm no real credentials, OAuth local JSON, real CSV, or personal data are
  present in the migration payload.
- Run unittest in the source repository before copying.
- Run scoped tests in the new repository after copying.

## Final Classification

Should migrate:

- X API read-only collector core under `x_auto_ops/`
- mock/dry-run recent search and buzz collector tools
- reference post analysis and yokaze generation tooling
- X API fixtures and tests
- X API safety, Live-readiness, RedactedLiveSummary, preflight, retry,
  pagination, request/response docs
- sanitized example config/data files

Should not migrate:

- local secrets, credentials, OAuth local JSON, generated CSVs, real post data
- `dating_assistant/`
- stock analyzer `src/`, `server/`, and related files
- Discord export or unrelated local tooling
- shared `reports/latest_report.md` as-is

Hold for decision:

- Excel daily poster and manual live posting
- general project docs
- historical reports
- `data/manual_account_posts.csv.example`

Initial split recommendation:

- Move only read-only buzz collection, reference analysis, mock/dry-run
  pipeline, safety skeletons, and sanitized examples.
- Keep posting/OAuth/manual live tools out of the first migration.

Safety confirmation:

- No new GitHub repository was created.
- No files were moved or copied.
- No PR was closed or merged.
- No direct push to `main` was performed.
- No HTTP communication was enabled.
- LiveMode was not enabled.
- No X API connection was made.
- Real credential loading was not enabled.
- `.env` was not created or changed.
- No token/secret file was created or changed.
- No credential value or Authorization header was recorded.
- OAuth local JSON and real data contents were not inspected.
- Excel daily poster/manual live posting was not executed.
- Stock analyzer, `server/`, `dating_assistant/`, and Discord export files were
  not changed.
- `reports/latest_report.md` was not changed.
