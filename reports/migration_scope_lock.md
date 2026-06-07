# Migration Scope Lock

Date: 2026-06-07

Target system:

- X API buzz post extraction system
- Read-only buzz collection, reference post analysis, dry-run/mock tooling, and Live-readiness safety layers

Future repository candidate:

```text
x-api-buzz-system
```

This report locks the migration scope before creating a future dedicated
repository. It is based on:

- `docs/x_api_repo_split_plan.md`
- `reports/x_api_repo_split_plan_report.md`
- `reports/migration_include_exclude_audit.md`
- `reports/pr3_9_strategy_review.md`

This is a report-only change. It does not create a new GitHub repository, move
files, copy files, close PRs, merge PRs, enable HTTP communication, enable
LiveMode, read real credentials, connect to X API, post to X, or update
`reports/latest_report.md`.

## Scope Decision

The first split should create a focused read-only repository for:

- X API recent-search buzz collection design and mock/dry-run implementation
- reference post import, analysis, scoring, and yokaze generation
- request/response normalization
- preflight validation
- rate limit parsing
- retry/pagination design
- redaction and safe diagnostic summaries
- disabled Live transport/client/credential skeletons
- tests and fixtures needed for the above

The first split should not include:

- Excel daily poster
- manual live posting
- OAuth helper execution paths
- real credentials
- local token/state files
- real operational CSVs
- stock analyzer
- `server/`
- `dating_assistant/`
- Discord export or unrelated local tooling

## Initial Migration Include List

### Core Package

Move these paths to the new repository:

```text
x_auto_ops/__init__.py
x_auto_ops/account_policy.py
x_auto_ops/buzz_read_client.py
x_auto_ops/credential_loader.py
x_auto_ops/dry_run_recent_search_pipeline.py
x_auto_ops/http_client.py
x_auto_ops/http_error_mapping.py
x_auto_ops/live_http_client.py
x_auto_ops/live_mode_gate.py
x_auto_ops/live_recent_search_transport.py
x_auto_ops/manual_reference_import.py
x_auto_ops/mock_buzz_collector.py
x_auto_ops/mock_transport.py
x_auto_ops/pagination_controller.py
x_auto_ops/preflight_validation.py
x_auto_ops/provider_routing.py
x_auto_ops/query_builder.py
x_auto_ops/rate_limit_parser.py
x_auto_ops/real_credential_loader.py
x_auto_ops/redacted_live_summary.py
x_auto_ops/redaction.py
x_auto_ops/reference_posts.py
x_auto_ops/request_builder.py
x_auto_ops/retry_policy.py
x_auto_ops/retry_queue.py
x_auto_ops/x_response_normalizer.py
x_auto_ops/yokaze_reference_generation.py
```

Reason: these are the current read-only collector, reference tooling, mock
pipeline, safety boundary, and disabled Live-readiness modules.

### CLI Tools

Move these paths:

```text
tools/__init__.py
tools/mock_buzz_collector.py
tools/mock_recent_search_pipeline.py
tools/x_analyze_reference_posts.py
tools/x_collect_reference_posts.py
tools/x_generate_yokaze_from_reference.py
tools/x_import_reference_posts_manual.py
tools/x_score_reference_posts.py
```

Reason: these are read-only/mock/reference tools that do not require real X API
access by default.

### Example Data

Move only sanitized examples and placeholders:

```text
data/source_accounts.csv.example
data/x_buzz_genres.json.example
data/reference_posts/.gitkeep
data/reference_posts/manual_reference_posts.csv.example
data/reference_posts/yokaze_generated_posts.jsonl.example
```

Recommended destination in the new repository:

```text
data/examples/
data/examples/reference_posts/
```

### Tests

Move these test files:

```text
tests/test_account_policy.py
tests/test_credential_loader_live_mode_gate.py
tests/test_dry_run_recent_search_pipeline.py
tests/test_http_client_interface.py
tests/test_http_error_mapping.py
tests/test_live_http_client_disabled.py
tests/test_live_recent_search_transport_disabled.py
tests/test_manual_reference_posts_import.py
tests/test_mock_buzz_collector.py
tests/test_mock_transport_pipeline.py
tests/test_pagination_controller.py
tests/test_preflight_transport_integration.py
tests/test_preflight_validation.py
tests/test_provider_routing.py
tests/test_query_builder_and_rate_limit_parser.py
tests/test_real_credential_loader_review.py
tests/test_redacted_live_summary.py
tests/test_redaction_and_retry_queue.py
tests/test_reference_posts.py
tests/test_request_builder.py
tests/test_x_response_normalizer.py
tests/test_yokaze_reference_generation.py
```

Move these fixtures:

```text
tests/fixtures/page_1.json
tests/fixtures/page_2.json
tests/fixtures/page_last.json
tests/fixtures/pipeline_partial.json
tests/fixtures/pipeline_rate_limited.json
tests/fixtures/pipeline_success.json
tests/fixtures/rate_limit_headers_normal.json
tests/fixtures/rate_limit_headers_reset_only.json
tests/fixtures/rate_limit_headers_retry_after.json
tests/fixtures/recent_search_response_minimal.json
tests/fixtures/recent_search_response_missing_metrics.json
tests/fixtures/recent_search_response_partial.json
tests/fixtures/recent_search_response_with_metrics.json
tests/fixtures/transport_partial.json
tests/fixtures/transport_rate_limited.json
tests/fixtures/transport_success.json
```

### Documentation

Move these docs:

```text
docs/backend_credential_policy.md
docs/backend_credential_storage_review.md
docs/http_client_interface.md
docs/http_error_mapping.md
docs/live_api_minimal_test_plan.md
docs/live_http_client_delta_review.md
docs/live_http_client_disabled.md
docs/live_http_client_review.md
docs/live_mode_policy.md
docs/live_mode_release_policy.md
docs/live_recent_search_transport.md
docs/live_recent_search_transport_delta_review.md
docs/live_recent_search_transport_disabled.md
docs/live_recent_search_transport_final_review.md
docs/live_recent_search_transport_review.md
docs/live_transport_release_readiness.md
docs/manual_reference_posts_import.md
docs/pagination_controller.md
docs/preflight_transport_integration.md
docs/preflight_validation.md
docs/real_credential_loader_review.md
docs/redacted_live_summary.md
docs/redacted_live_summary_implementation_review.md
docs/redacted_live_summary_review.md
docs/reference_posts_collector.md
docs/request_builder.md
docs/x_api_plan_field_research.md
docs/x_api_repo_split_plan.md
docs/x_genre_buzz_collector_design.md
docs/yokaze_reference_generation.md
```

### Reports

Move these reports as project history only, preferably under
`reports/x_api/archive/`:

```text
reports/mock_buzz_report.md
reports/mock_recent_search_pipeline_report.md
reports/live_merge_order_review.md
reports/post_merge_sync_review.md
reports/pr3_9_strategy_review.md
reports/pr_final_pre_merge_check.md
reports/refresh_planning_prs_review.md
reports/merge_readiness_confirmation.md
reports/x_api_repo_split_plan_report.md
reports/migration_include_exclude_audit.md
reports/migration_scope_lock.md
```

Do not move `reports/latest_report.md` as-is. The new repository should create
its own project-scoped latest report at:

```text
reports/x_api/latest_report.md
```

## Initial Migration Exclude List

Never include these in the first migration payload:

```text
.env
.env.*
token
secret
credential
Authorization
Bearer
data/oauth2_state.local.json
data/oauth2_tokens.local.json
data/manual_account_posts.csv
data/*.local.csv
data/local/
outputs/local/
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
dating_assistant/
dating_assistant/data/local/
partner real data
src/
server/
stock-analyzer.html
tests/stock-analyzer.test.js
Discord export
logs/
output/
zip
xlsx
screenshots
personal information
real account information
real post data
```

Reason: these are credentials/local data/generated artifacts, unrelated
projects, or real operational data surfaces.

## Hold For Decision

Keep these out of the first migration unless there is a separate explicit
decision:

```text
tools/excel_daily_poster/
tests/test_excel_daily_poster.py
docs/excel_daily_poster.md
scripts/manual_live_post_once.example.bat
scripts/register_excel_daily_post_oauth2_live_task.example.bat
scripts/register_excel_daily_post_task.bat
scripts/run_excel_daily_post.bat
scripts/run_excel_daily_post_oauth2_live.example.bat
data/manual_account_posts.csv.example
docs/ACCOUNT_STYLE_GUIDE.md
docs/BUG_HISTORY.md
docs/DEVELOPMENT_RULES.md
docs/PROJECT_CONTEXT.md
docs/PROMPT_HISTORY.md
docs/git_push_safety_checklist.md
reports/codex_report_*.md
```

Decision rule:

- If a file is required for read-only buzz collection, reference analysis, or
  mock/dry-run Live-readiness, include it.
- If a file is for posting, OAuth live posting, scheduling, or manual live
  operation, hold it out of the first migration.
- If the file is history-only, migrate only a summary or place it under
  `reports/x_api/archive/`.

## Excel Daily Poster / Manual Live Posting Boundary

Locked decision for the first split:

- `x-api-buzz-system` is read-only buzz collection and analysis focused.
- Excel daily poster and manual live posting are not part of the first
  migration.
- OAuth helper paths are not part of the first migration.
- Posting/write operations must remain out of scope.

Future option:

```text
x-posting-tools
```

or a separate `x_posting_tools/` package after explicit approval.

## PR #3 Through PR #9 Handling

Use this locked strategy:

```text
PR #3: recreate in the new repository as Live implementation readiness review
PR #4: recreate in the new repository as RealCredentialLoader plan
PR #5: close/supersede candidate; no recreation needed unless the issue returns
PR #6: recreate in the new repository as LiveHttpClient plan
PR #7: recreate in the new repository as LiveRecentSearchTransport plan
PR #8: recreate in the new repository as First Live Dry-Run Gate plan
PR #9: recreate in the new repository as First Minimal Live API Test plan
```

Do not continue refreshing these planning PRs in the shared repository unless
Live work must proceed before the split.

## New Repository Initial Layout

Create the future repository with this initial shape:

```text
README.md
.gitignore
pyproject.toml
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
    reference_posts/
```

Dependency file:

- Prefer `pyproject.toml` if packaging/test tooling is formalized.
- Use `requirements.txt` only if the first split should stay minimal and
  script-oriented.

## New Repository .gitignore Lock

Use at least the following rules:

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

If posting/OAuth tooling is later approved, extend the ignore list before
moving that tooling.

## Checks Required Before Creating The New Repository

Before creating `x-api-buzz-system`, confirm:

- Repository name: `x-api-buzz-system`
- Visibility: public or private
- Whether historical reports are copied, archived, or summarized
- Whether `pyproject.toml` or `requirements.txt` is used
- Exact first migration file list
- Exact first migration exclude list
- Test command to run first in the new repository
- Whether old repo keeps a migration note
- Codex instructions for the new repository path and branch policy
- No `.env`, token, secret, credential, OAuth local JSON, local CSV, or real
  account/post data exists in the migration payload

## First Test Command In New Repository

Recommended first command after copying only approved files:

```text
python -m unittest discover -s tests -v
```

If the new repository intentionally excludes Excel/manual live posting, do not
copy or run `tests/test_excel_daily_poster.py`.

## Safety Confirmation

- No new GitHub repository was created.
- No real files were moved.
- No files were copied.
- No PR was closed.
- No PR was merged.
- No direct push to `main` was performed.
- No GitHub manual conflict resolution was performed.
- No HTTP communication was enabled.
- LiveMode was not enabled.
- No X API connection was made.
- Real credential loading was not enabled.
- `.env` was not created or changed.
- No token/secret file was created or changed.
- No credential value was recorded.
- No Authorization header value was recorded.
- OAuth local JSON contents were not displayed.
- Real data contents were not displayed.
- No write endpoint was implemented.
- No posting, follow, like, DM, or media upload work was done.
- Excel daily poster/manual live posting was not executed.
- Stock analyzer files were not changed.
- `server/` files were not changed.
- `dating_assistant/` files were not changed.
- Discord export was not processed.
- `reports/latest_report.md` was not changed.
- `git add .` and `git add -A` were not used.
- `git reset`, `git clean`, and force push were not used.

## Final Recommendation

The migration scope is ready to use as a locked checklist for creating
`x-api-buzz-system`. The next action should be a new-repository creation plan or
new-repository creation task, using this report as the allowlist/denylist.
