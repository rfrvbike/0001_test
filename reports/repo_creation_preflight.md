# X API Repository Creation Preflight

Date: 2026-06-07

Target system:

- X API buzz post extraction system
- Read-only buzz collection, reference post analysis, dry-run/mock tooling, and Live-readiness safety layers

Proposed new repository:

```text
x-api-buzz-system
```

This is the final preflight report before creating a future dedicated
repository. It is based on:

- `docs/x_api_repo_split_plan.md`
- `reports/x_api_repo_split_plan_report.md`
- `reports/migration_include_exclude_audit.md`
- `reports/migration_scope_lock.md`
- `reports/pr3_9_strategy_review.md`

This is a report-only change. It does not create a new GitHub repository, move
files, copy files, close PRs, merge PRs, enable HTTP communication, enable
LiveMode, read real credentials, connect to X API, post to X, or update
`reports/latest_report.md`.

## Repository Name Confirmation

Recommended repository name:

```text
x-api-buzz-system
```

Purpose:

- X API buzz post extraction
- read-only recent-search collection design
- mock/dry-run collection and analysis
- reference post import and generation support
- Live-readiness safety layers before any real API connection

Out of scope:

- Excel daily poster
- manual live posting
- OAuth helper execution
- stock analyzer
- `server/`
- `dating_assistant/`
- Discord export or unrelated local tooling

Name comparison:

| Candidate | Decision | Reason |
| --- | --- | --- |
| `x-api-buzz-system` | Recommended | Keeps X API boundary explicit and leaves room for collection, analysis, and Live-readiness work |
| `x-buzz-collector` | Acceptable alternative | Shorter, but narrower if analysis and diagnostics continue to grow |
| `x-buzz-analysis-system` | Secondary alternative | Good for analysis, less explicit about the API boundary |
| `x-post-intelligence` | Not recommended for first split | Could blur read-only collection with posting/content automation |

Preflight decision: use `x-api-buzz-system` unless the user explicitly chooses a
different name before repository creation.

## Public / Private Recommendation

Recommendation:

```text
private
```

Rationale:

- The repository will contain implementation plans for future X API credential
  boundaries and Live transport.
- Even without real credentials, the docs describe operational boundaries,
  endpoint choices, and test strategy.
- Keeping the repository private reduces accidental exposure while the Live
  implementation is still being designed.
- Real credentials, local data, token files, OAuth local JSON, and real CSVs
  must still be excluded even in a private repository.

Public may be reconsidered later only after:

- all examples are confirmed sanitized
- no operational account data is present
- docs are reviewed for sensitive implementation details
- the project has a clear open-source posture

## Final Initial Migration Include List

Move these categories first:

- `x_auto_ops/`
- read-only/mock/reference tools
- X API fixtures
- X API/reference/Live-readiness tests
- X API-related docs
- sanitized example data
- selected X API reports as archive

Locked include paths:

```text
x_auto_ops/
tools/__init__.py
tools/mock_buzz_collector.py
tools/mock_recent_search_pipeline.py
tools/x_analyze_reference_posts.py
tools/x_collect_reference_posts.py
tools/x_generate_yokaze_from_reference.py
tools/x_import_reference_posts_manual.py
tools/x_score_reference_posts.py
data/source_accounts.csv.example
data/x_buzz_genres.json.example
data/reference_posts/.gitkeep
data/reference_posts/manual_reference_posts.csv.example
data/reference_posts/yokaze_generated_posts.jsonl.example
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

Selected reports may be copied later as archive material under:

```text
reports/x_api/archive/
```

Do not copy `reports/latest_report.md` as-is.

## Final Initial Migration Exclude List

Do not move these categories:

- credentials and local secrets
- OAuth local JSON
- local/generated CSVs
- real operational data
- Excel daily poster/manual live posting
- stock analyzer
- `server/`
- `dating_assistant/`
- Discord export
- unrelated local/demo/training files

Locked exclude paths/patterns:

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
tools/excel_daily_poster/
tests/test_excel_daily_poster.py
docs/excel_daily_poster.md
scripts/*excel*
scripts/*oauth*
scripts/*manual_live*
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
reports/latest_report.md
```

## Hold For Decision

These remain intentionally unresolved before the first repository creation:

- Whether historical reports should be copied, summarized, or omitted.
- Whether `pyproject.toml` or `requirements.txt` is better for the first
  minimal repository.
- Whether `docs/ACCOUNT_STYLE_GUIDE.md`, `docs/PROMPT_HISTORY.md`,
  `docs/PROJECT_CONTEXT.md`, `docs/DEVELOPMENT_RULES.md`, and
  `docs/BUG_HISTORY.md` should be summarized into the new README instead of
  copied.
- Whether Excel daily poster/manual live posting should become a separate
  repository such as `x-posting-tools`.

None of these should block creating the read-only `x-api-buzz-system` skeleton.

## Initial Repository Layout

Use this starting shape:

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

If dependency packaging is deferred, `requirements.txt` can temporarily replace
`pyproject.toml`, but the first repository should still document the intended
test command.

## New Repository .gitignore

Minimum `.gitignore` content:

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

Preflight decision: write this `.gitignore` before adding migrated files.

## README Direction

The first README should include:

- project purpose: read-only X API buzz collection and analysis
- what is included
- what is explicitly excluded
- current status: mock/dry-run and safety skeletons only
- no real X API connection yet
- no real credential loading yet
- LiveMode disabled by default
- no posting/write endpoints
- credential and secret policy
- test command
- development workflow
- migration note from `rfrvbike/0001_test`

Suggested opening:

```text
This repository contains the read-only X API buzz post extraction system. It is
currently mock/dry-run first and does not enable real X API access, LiveMode,
real credential loading, or posting.
```

## First Copy Policy

When the actual migration task begins:

- Copy only files from the locked include list.
- Do not use broad wildcard copy commands for the whole repository.
- Do not copy files from the locked exclude list.
- Do not copy `reports/latest_report.md`.
- Do not copy real/local/generated data.
- Do not copy Excel daily poster or manual live posting paths.
- Do not use `git add .` or `git add -A`.
- After copying, run `git status --short`.
- Review staged files with `git diff --cached --name-status`.
- Run tests before the first commit.

Recommended copy order:

1. Create repository metadata: README, `.gitignore`, dependency file.
2. Copy `x_auto_ops/`.
3. Copy selected read-only/reference `tools/`.
4. Copy selected `tests/` and `tests/fixtures/`.
5. Copy sanitized example data to `data/examples/`.
6. Copy selected docs.
7. Copy selected reports only if approved.
8. Run tests.
9. Fix import/path issues only if required.

## PR #3 Through PR #9 Handling

After the new repository exists:

```text
PR #3: recreate in the new repository as readiness review
PR #4: recreate in the new repository as RealCredentialLoader plan
PR #5: close/supersede candidate in the current repository
PR #6: recreate in the new repository as LiveHttpClient plan
PR #7: recreate in the new repository as LiveRecentSearchTransport plan
PR #8: recreate in the new repository as First Live Dry-Run Gate plan
PR #9: recreate in the new repository as First Minimal Live API Test plan
```

Preflight decision: do not merge PR #3 through PR #9 into the current shared
repository just to preserve planning content.

## Remaining Checks Before Creating Repository

Still needs user confirmation:

- Create repository now or prepare a creation PR/task first.
- Repository visibility: private recommended.
- Dependency file: `pyproject.toml` recommended unless a minimal
  `requirements.txt` is preferred.
- Whether selected historical reports should be copied into
  `reports/x_api/archive/`.
- Whether to include any general project docs by summary only.
- Whether to keep `x-api-buzz-system` as the final name.

Does not need further confirmation:

- Excel daily poster/manual live posting stays out of the first migration.
- Stock analyzer and `server/` stay out.
- `dating_assistant/` stays out.
- Real credentials and local/generated data stay out.
- `reports/latest_report.md` stays out as-is.

## Preflight Result

Conclusion:

```text
READY_FOR_REPO_CREATION_WITH_USER_CONFIRMATION
```

The migration scope is locked enough to create the new repository safely, as
long as the actual migration follows the include/exclude list and remains
read-only/mock-first.

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
- Real credential loading was not performed.
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

## Recommended Next Work

Next task:

```text
Create x-api-buzz-system repository skeleton
```

The next task should still avoid real X API calls, LiveMode enablement, real
credential reads, and posting. It should create only repository metadata and
then copy approved files in a controlled allowlist-driven pass.
