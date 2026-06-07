# X API Repo Split Plan Report

Date: 2026-06-07

This report summarizes the repository split plan for the X API buzz-post
extraction system. It is a planning/report-only change. No new GitHub
repository was created. No files were moved or copied. No PR was merged or
closed. No direct push to `main` was performed. No HTTP communication, X API
call, LiveMode enablement, real credential read, `.env` change, token/secret
creation, write endpoint, posting, follow, like, DM, or media upload work was
performed.

## Added Files

- `docs/x_api_repo_split_plan.md`
- `reports/x_api_repo_split_plan_report.md`

## latest_report.md

`reports/latest_report.md` was intentionally not changed in this task. The
split plan recommends moving future X API work to project-specific reports, such
as `reports/x_api/latest_report.md`, to avoid recurring cross-project conflicts.

## Conclusion

The X API buzz-post extraction system should be split into a dedicated
repository, but only after the remaining planning PRs are settled and the
migration include/exclude lists are locked.

Recommended repository name:

```text
x-api-buzz-system
```

## Why Split

- Prevent accidental cross-project diffs with `dating_assistant/`, stock
  analyzer, `server/`, and other local tooling.
- Reduce recurring `reports/latest_report.md` conflicts.
- Clarify Live implementation and credential boundaries before real API work.
- Keep X API read-side collector, reference analysis, dry-run pipeline, and
  safety tests reviewable in one focused repository.

## Candidate Migration Scope

Include candidates:

- `x_auto_ops/`
- X API and reference tooling CLI scripts under `tools/`
- X API fixtures under `tests/fixtures/`
- X API, reference tooling, RedactedLiveSummary, preflight, retry, pagination,
  request builder, response normalizer, credential boundary, and Live readiness
  tests
- X API and reference tooling docs
- selected X API reports as archive material
- example-only config/data files such as `data/x_buzz_genres.json.example`

Needs separate decision:

- `tools/excel_daily_poster/`
- `tests/test_excel_daily_poster.py`
- `docs/excel_daily_poster.md`
- manual live posting support files

Recommended first split:

- read-only X API buzz collector
- reference post analysis
- mock/dry-run pipelines
- safety and Live readiness skeletons

Recommended later decision:

- Excel daily poster and manual live posting as separate X posting tooling.

## Must Not Migrate

- `.env`
- token, secret, credential, Authorization, or Bearer values
- OAuth local JSON
- local token/state files
- real operational CSVs
- `data/local/`
- `outputs/local/`
- `dating_assistant/data/local/`
- partner real data
- stock analyzer files
- `server/`
- Discord exports
- screenshots, zip, xlsx, generated artifacts unless separately reviewed
- personal information or unsanitized real data

## latest_report.md Operating Recommendation

- Stop updating shared `reports/latest_report.md` for every project-level task
  after the split.
- Use task-specific reports by default.
- Add `reports/x_api/latest_report.md` in the new repository.
- Update top-level summary reports only during deliberate integration work.

## Migration Procedure

1. Close or supersede old PR #11, PR #12, and PR #13 after GitHub UI review.
2. Recreate or refresh PR #3 and PR #4.
3. Refresh or recreate PR #6 through PR #9.
4. Confirm full unittest on latest `main`.
5. Freeze include/exclude lists.
6. Decide whether Excel/manual live posting is in scope.
7. Create the new repository.
8. Copy only approved files.
9. Confirm excluded/local/credential files are absent.
10. Run tests in the new repository.
11. Add a migration note to the old repository.
12. Continue future Live implementation work in the new repository only.

## Risks If Migrating Immediately

- Open PR #3 through PR #9 may still need refresh/recreation.
- Import paths may need adjustment after extraction.
- `.gitignore` may miss generated or local credential paths.
- Codex prompts and reports may still point to the shared repository.
- Excel/manual posting scope may blur the read-only collector boundary.

## Safety Confirmation

- No new repository was created.
- No real file movement or copy was performed.
- No secret, local, or credential file was inspected for contents or migrated.
- `reports/latest_report.md` was not changed.
- No PR was merged or closed.
- No direct push to `main` was performed.
- No `git add .` or `git add -A` was used.
- No `git clean`, `git reset`, force push, or force-with-lease push was used.
- No HTTP communication was enabled.
- LiveMode was not enabled.
- No X API connection was made.
- Real credential loading was not enabled.
- `.env` was not created or changed.
- No token/secret file was created or changed.
- No credential value or Authorization header was recorded.
- No Excel daily poster/manual live posting work was performed.
- No stock analyzer, `server/`, `dating_assistant/`, or Discord export files
  were changed.
