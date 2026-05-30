# latest_report.md

## 2026-05-24 10:21 Codex Report

Added Windows AC sleep setting support files and documentation for daily
automation. No real post, external communication, Task Scheduler modification,
Windows power setting change, `.env` edit, GitHub push, or existing dry-run
runner live conversion was performed by Codex.

Changed files:

- `scripts/check_power_settings.example.bat`
- `scripts/set_ac_no_sleep.example.bat`
- `scripts/restore_ac_sleep_30min.example.bat`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260524_1021.md`
- `reports/latest_report.md`

Behavior:

- Added a read-only power settings checker that runs `powercfg /getactivescheme`,
  `powercfg /query`, and `powercfg /waketimers`.
- Added a locked AC no-sleep example that changes only
  `standby-timeout-ac` to `0` after copying to `.local.bat` and enabling the
  local safety flag.
- Added a locked restore example that changes only `standby-timeout-ac` to `30`
  after copying to `.local.bat` and enabling the local safety flag.
- Docs now explain GUI and command-line sleep settings, wake-from-sleep Task
  Scheduler checks, AC-only recommendations, and cautions about heat, power, and
  security.
- `scripts/run_excel_daily_post.bat` remains dry-run-only.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 102 tests in 0.194s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: ここに1日目の投稿文を入力してください
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-24 09:42 Codex Report

Added CSV write-safety preflight and post-success CSV recovery logging for the
legacy single-account poster. No real post, external communication, Task
Scheduler registration, `.env` edit, GitHub push, or existing dry-run runner
live conversion was performed by Codex.

Changed files:

- `tools/excel_daily_poster/excel_queue.py`
- `tools/excel_daily_poster/daily_post.py`
- `tools/excel_daily_poster/manual_live_post_once.py`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260524_0942.md`
- `reports/latest_report.md`

Behavior:

- Manual OAuth 2.0 live runs check that the CSV is writable before OAuth refresh
  or X API posting.
- Existing `.tmp` files stop the run before posting so recovery state can be
  inspected.
- Live `run_once` checks writability again under the queue lock.
- If X posting succeeds but CSV replacement fails, a critical recovery log
  records row number, `posted_at`, and `tweet_id` without tokens/secrets/full
  post text.
- Recovery errors instruct the user to close Excel/pause OneDrive and manually
  mark the row as posted.
- `scripts/run_excel_daily_post.bat` remains dry-run-only.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 99 tests in 0.353s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: ここに1日目の投稿文を入力してください
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-23 21:30 Codex Report

Added a local similar-recent-post guard for the legacy single-account OAuth 2.0
manual/live flow. No real post, external communication, Task Scheduler
registration, `.env` edit, GitHub push, or existing dry-run runner live
conversion was performed by Codex.

Changed files:

- `tools/excel_daily_poster/manual_live_post_once.py`
- `scripts/run_excel_daily_post_oauth2_live.example.bat`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260523_2130.md`
- `reports/latest_report.md`

Behavior:

- Before OAuth 2.0 refresh/post creation, the selected candidate is compared
  against `status=posted` rows from the last 30 days.
- The default threshold is `0.85`; exact matches are blocked.
- The guard uses local normalization and `difflib.SequenceMatcher`.
- Blocking raises `reason_code=similar_recent_post_detected`, does not refresh,
  does not call the X API, does not advance to the next candidate, and does not
  mark the CSV as posted.
- Settings are exposed through:
  `SIMILAR_RECENT_POST_CHECK_ENABLED`,
  `SIMILAR_RECENT_POST_DAYS`, and
  `SIMILAR_RECENT_POST_THRESHOLD`.
- `scripts/run_excel_daily_post.bat` remains dry-run-only.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 96 tests in 0.214s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: ここに1日目の投稿文を入力してください
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-23 14:46 Codex Report

Prepared the OAuth 2.0 daily automation scaffolding for the legacy single
account without enabling live automation. No real post, external communication,
Task Scheduler registration, `.env` edit, GitHub push, or existing dry-run runner
live conversion was performed by Codex.

Changed files:

- `tools/excel_daily_poster/manual_live_post_once.py`
- `scripts/run_excel_daily_post_oauth2_live.example.bat`
- `scripts/register_excel_daily_post_oauth2_live_task.example.bat`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260523_1446.md`
- `reports/latest_report.md`

Behavior:

- Added a one-post-per-day guard before OAuth 2.0 refresh/post creation.
- The OAuth 2.0 live example bat refuses to run as-is, checks required local
  files and environment variables, logs to
  `logs/excel_daily_poster_oauth2_live.log`, warns to close Excel, waits a
  random `0` to `120` minutes, and then calls the manual OAuth 2.0 one-row
  wrapper.
- Added a Task Scheduler registration example that refuses to run as-is and
  targets `scripts\run_excel_daily_post_oauth2_live.local.bat` at `21:30`.
- Docs now describe daily automation, the night random posting window, and the
  one-post-per-day guard.
- `scripts/run_excel_daily_post.bat` remains dry-run-only.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 85 tests in 0.125s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: ここに1日目の投稿文を入力してください
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-17 21:24 Codex Report

Added OAuth 2.0 refresh-token handling before manual one-row OAuth 2.0 posting.
No real post, external communication, `.env` edit, GitHub push, or scheduled
runner live conversion was performed by Codex.

Changed files:

- `tools/excel_daily_poster/manual_live_post_once.py`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260517_2124.md`
- `reports/latest_report.md`

Behavior:

- The manual OAuth 2.0 path refreshes tokens before posting by default.
- Refresh reads `refresh_token` from `data/oauth2_tokens.local.json`.
- Refresh uses local `X_OAUTH2_CLIENT_ID` and optional `X_OAUTH2_CLIENT_SECRET`.
- On refresh success, the token file is updated with the new `access_token`,
  `refresh_token`, `expires_in`, and `scope`.
- Posting then uses the refreshed access token.
- Refresh failure stops before posting.
- `--skip-oauth2-refresh` is available for diagnostics only.
- Token and secret values are not printed in logs or reports.
- `scripts/run_excel_daily_post.bat` remains dry-run-only.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 81 tests in 0.139s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: ここに1日目の投稿文を入力してください
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-17 09:36 Codex Report

Prepared the one-row-per-day CSV/Excel template for the legacy single-account
poster. No real post, external communication, `.env` edit, GitHub push, or
scheduled runner live conversion was performed by Codex.

Changed files:

- `data/manual_account_posts.csv.example`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260517_0936.md`
- `reports/latest_report.md`

Behavior:

- `data/manual_account_posts.csv.example` now uses the required columns in
  A-to-F order for Excel.
- The template contains day 1/day 2 pending examples, a future scheduled sample,
  and a posted sample.
- The template is saved as UTF-8 with BOM for Japanese Excel editing.
- Docs now explain the one-row-per-day CSV format, status meanings, production
  CSV setup, and large paste cautions.
- `scripts/run_excel_daily_post.bat` remains dry-run-only.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 77 tests in 0.108s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: ここに1日目の投稿文を入力してください
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-17 01:04 Codex Report

Prepared the safe handoff plan for OAuth 2.0 live daily operation after manual
one-row posting succeeded. No real post, scheduled live conversion, GitHub push,
or token/client-id logging was performed by Codex.

Changed files:

- `scripts/run_excel_daily_post_oauth2_live.example.bat`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260517_0104.md`
- `reports/latest_report.md`

Behavior:

- The existing `scripts/run_excel_daily_post.bat` remains dry-run-only.
- The new OAuth 2.0 live runner is an example only and refuses to run as-is.
- Production use requires copying it to
  `scripts/run_excel_daily_post_oauth2_live.local.bat`, which is ignored by Git.
- The example checks for `data/manual_account_posts.csv`,
  `data/oauth2_tokens.local.json`, and local `X_OAUTH2_CLIENT_ID`.
- Docs now describe waiting for several successful manual daily runs before any
  Task Scheduler registration.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 74 tests in 0.134s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: Dry-run sample for the legacy manual account.
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-17 00:55 Codex Report

Connected the manual one-row live wrapper to the prepared OAuth 2.0 User Context
poster behind an explicit `--use-oauth2` option. No real post, external
communication, `.env` edit, GitHub push, or scheduled runner live conversion was
performed by Codex.

Changed files:

- `tools/excel_daily_poster/manual_live_post_once.py`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260517_0055.md`
- `reports/latest_report.md`

Behavior:

- `data/oauth2_tokens.local.json` can be read by the manual wrapper.
- Missing token file, missing `access_token`, missing `X_OAUTH2_CLIENT_ID`, or
  missing required scopes raises `XConfigError`.
- Token values are not included in wrapper config errors.
- `--use-oauth2` selects `OAuth2UserContextXPoster`; default auth remains OAuth
  1.0a compatibility for the manual wrapper.
- The exact manual confirmation string remains required.
- Posting remains capped at one successful row per run.
- API/system errors stop without trying the next row.
- `scripts/run_excel_daily_post.bat` remains dry-run-only.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 72 tests in 0.146s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: Dry-run sample for the legacy manual account.
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-17 00:17 Codex Report

Prepared a localhost OAuth 2.0 callback helper for the legacy single-account
Excel/CSV poster. No real token exchange, real post, external communication,
`.env` edit, GitHub push, or scheduler live conversion was performed by Codex.

Changed files:

- `tools/excel_daily_poster/oauth2_local_callback.py`
- `tools/excel_daily_poster/oauth2_exchange_code.py`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260517_0017.md`
- `reports/latest_report.md`

Behavior:

- `oauth2_local_callback.py` listens on `http://127.0.0.1:8765/callback`.
- It generates and prints the OAuth 2.0 PKCE authorization URL.
- It receives `code` and `state` from the callback, validates `state`, and then
  exchanges the code only when the exact confirmation flag is present.
- Tokens are saved to `data/oauth2_tokens.local.json`.
- `code`, `code_verifier`, client secret, access token, and refresh token are
  not printed.
- If `X_OAUTH2_CLIENT_SECRET` is present, token exchange uses
  `Authorization: Basic base64(client_id:client_secret)`.
- The default poster remains `BlockedXPoster`; manual live posting and
  scheduled bat files are not connected to OAuth 2.0 live posting.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 64 tests in 0.165s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: Dry-run sample for the legacy manual account.
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-16 21:11 Codex Report

Updated OAuth 2.0 token exchange helpers to support confidential-client Basic
authentication when `X_OAUTH2_CLIENT_SECRET` is provided.

Changed files:

- `tools/excel_daily_poster/oauth2_exchange_code.py`
- `tools/excel_daily_poster/oauth2_refresh_token.py`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260516_2111.md`
- `reports/latest_report.md`

Behavior:

- With a client secret, token and refresh exchanges send:
  `Authorization: Basic base64(client_id:client_secret)`.
- With a client secret, `client_secret` is not sent in the request body.
- Without a client secret, public-client behavior is unchanged: no Basic header.
- 401 responses such as `unauthorized_client` remain `XAuthError`.
- client id, client secret, code, code verifier, access token, and refresh token
  are redacted from error messages.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 58 tests in 0.087s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: Dry-run sample for the legacy manual account.
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-16 20:46 Codex Report

Enabled explicit, confirmation-gated OAuth 2.0 token exchange in
`oauth2_exchange_code.py`. No real token exchange was executed by Codex.

Changed files:

- `tools/excel_daily_poster/oauth2_exchange_code.py`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260516_2046.md`
- `reports/latest_report.md`

Behavior:

- Default mode refuses to exchange tokens.
- `--mock-only` validates code/state without HTTP.
- `--exchange-live` requires exact confirmation:
  `I_UNDERSTAND_THIS_EXCHANGES_OAUTH2_TOKEN`
- Live exchange uses `https://api.x.com/2/oauth2/token`.
- Tokens are saved to `data/oauth2_tokens.local.json`.
- Access tokens, refresh tokens, authorization codes, and client secrets are not
  printed.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 53 tests in 0.104s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: Dry-run sample for the legacy manual account.
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-16 18:07 Codex Report

Prepared OAuth 2.0 Authorization Code Flow with PKCE helper tools for the
separated legacy-account Excel/CSV poster.

Changed files:

- `.gitignore`
- `tools/excel_daily_poster/oauth2_authorize.py`
- `tools/excel_daily_poster/oauth2_exchange_code.py`
- `tools/excel_daily_poster/oauth2_refresh_token.py`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260516_1807.md`
- `reports/latest_report.md`

Added helpers:

- `oauth2_authorize.py`: builds PKCE verifier/challenge/state and authorization
  URL, then optionally writes `data/oauth2_state.local.json`.
- `oauth2_exchange_code.py`: validates returned state and supports mocked token
  exchange into `data/oauth2_tokens.local.json`.
- `oauth2_refresh_token.py`: mocked-transport-only refresh-token helper design.

Git ignore now covers:

- `data/oauth2_*.local.json`
- `data/*token*.local.json`
- `data/*secret*.local.json`

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 50 tests in 0.112s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: Dry-run sample for the legacy manual account.
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-16 18:02 Codex Report

Prepared an OAuth 2.0 User Context posting implementation option for the
separated legacy-account Excel/CSV poster.

Changed files:

- `tools/excel_daily_poster/x_client.py`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260516_1802.md`
- `reports/latest_report.md`

Added:

- `OAuth2UserContextCredentials`
- `OAuth2UserContextXPoster`

Notes:

- Existing OAuth 1.0a `TweepyXPoster` remains.
- Default poster remains `BlockedXPoster`.
- OAuth 2.0 poster is not wired into CLI, scheduler, or bat files.
- Tests use fake transports only.
- Docs now mention considering OAuth 2.0 User Context when Pay Per Use is active
  but OAuth 1.0a still returns 403 for `POST /2/tweets`.

Documented OAuth 2.0 config:

- `X_OAUTH2_CLIENT_ID`
- `X_OAUTH2_CLIENT_SECRET` may be needed for confidential clients or refresh
  flows
- `X_OAUTH2_ACCESS_TOKEN`
- `X_OAUTH2_REFRESH_TOKEN`
- Scopes: `tweet.read`, `tweet.write`, `users.read`, and `offline.access` when
  refresh tokens are needed

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 44 tests in 0.062s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: Dry-run sample for the legacy manual account.
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-16 16:47 Codex Report

Ran the final local safety check before a future manual one-row live X post.
No real posting was performed.

Changed files:

- `tools/excel_daily_poster/x_client.py`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260516_1647.md`
- `reports/latest_report.md`

Finding and fix:

- Hardened future SDK/API exception conversion so credential-like values from
  `XApiCredentials` are redacted before being placed in `XClientError`
  messages.

Checks:

- `.env`, `*.local.bat`, `logs/`, `*.log`, `data/manual_account_posts.csv`, and
  queue lock/tmp files are ignored by Git.
- `scripts/run_excel_daily_post.bat` still uses `--dry-run`.
- `scripts/register_excel_daily_post_task.bat` only registers the dry-run bat.
- `manual_live_post_once.py` stops without the exact confirmation string.
- Dry-run does not update CSV.
- Manual live path posts at most one row in mocked tests.
- API/system errors do not advance to the next candidate row in mocked tests.
- Credential-like values are redacted from future SDK exception messages.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 38 tests in 0.065s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: Dry-run sample for the legacy manual account.
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-16 16:43 Codex Report

Prepared local operating documentation and safeguards before any manual one-row
live X post.

Changed files:

- `.gitignore`
- `scripts/manual_live_post_once.example.bat`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260516_1643.md`
- `reports/latest_report.md`

Added docs:

- Production CSV creation from `data/manual_account_posts.csv.example`.
- Excel editing cautions.
- Required dry-run confirmation flow.
- Placeholder-only environment variable setup.
- Secret handling warnings.
- CSV columns to check after a future manual live post.

Git ignore now covers:

- `.env`
- `*.local.bat`
- `logs/`
- `*.log`
- `data/manual_account_posts.csv`
- `data/*.lock`
- `data/*.tmp`

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 36 tests in 0.065s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: Dry-run sample for the legacy manual account.
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-16 16:40 Codex Report

Prepared a manual one-row live wrapper for the separated legacy-account
Excel/CSV poster. It is not connected to the scheduler, and no real X API post
was executed.

Changed files:

- `tools/excel_daily_poster/manual_live_post_once.py`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260516_1640.md`
- `reports/latest_report.md`

Wrapper behavior:

- Requires exact confirmation text before creating a poster.
- Reads credentials only from already-provided environment variables.
- Does not create, edit, or load `.env`.
- Injects `TweepyXPoster` into `run_once(..., dry_run=False, poster=...)`.
- Is not used by `scripts/run_excel_daily_post.bat` or the task scheduler.

Required confirmation:

```text
I_UNDERSTAND_THIS_POSTS_ONE_REAL_X_TWEET
```

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 32 tests in 0.067s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: Dry-run sample for the legacy manual account.
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-16 16:36 Codex Report

Prepared a future real X poster implementation for the separated legacy-account
Excel/CSV daily poster. Existing defaults remain blocked and dry-run-first.

Changed files:

- `tools/excel_daily_poster/x_client.py`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260516_1636.md`
- `reports/latest_report.md`

Added:

- `XApiCredentials`
- `TweepyXPoster`

Default behavior:

- `daily_post.py` still uses `BlockedXPoster` when no poster is injected.
- `scripts/run_excel_daily_post.bat` still runs `--dry-run`.
- No live command was enabled.

Error mapping:

- 401 / 403 -> `XAuthError`
- 429 -> `XRateLimitError`
- 5xx -> `XTemporaryError`
- Timeout / connection / DNS-style failures -> `XNetworkError`
- Missing credentials or missing dependency setup -> `XConfigError`
- Other client/API failures -> `XClientError`

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 29 tests in 0.057s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: Dry-run sample for the legacy manual account.
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-16 16:34 Codex Report

Improved `account_type: new_account_daily` so it no longer centers plain daily
life reports. The account direction is now fixed as a stylish, mature everyday
account that cuts ordinary daily life into a slightly beautiful, calm, lingering
shape.

Changed files:

- `x_auto_ops/account_policy.py`
- `tests/test_account_policy.py`
- `docs/ACCOUNT_STYLE_GUIDE.md`
- `docs/PROMPT_HISTORY.md`
- `reports/codex_report_20260516_1634.md`
- `reports/latest_report.md`

Implemented policy:

- Casual everyday moments: 10-20%
- Stylish mature everyday posts: 40-60%
- Stronger mature aftertaste: 20-30%
- Japanese posts should be 2-4 natural sentences.
- English posts should be calm, mature, stylish, slightly sensual but not
  explicit, and natural for social media.
- Quality checks now reject drafts that are only event reports or life logs.
- Image Need Check now prefers `text_only` when the writing already has
  aftertaste, and recommends `image` only when ambience such as night rooms,
  rain, lighting, coffee, a glass, curtains, or books genuinely strengthens the
  mood.
- Image prompts require no people, no faces, no text, no typography, no labels,
  no panels, no arrows, no checklists, no numbered steps, and no infographics.

Sample draft:

```text
予定のない土曜ほど、部屋の空気を少し整えたくなる。
掃除して、買い出しして、夕方に少しだけ歩いた。
何も特別なことはしてないのに、夜の静けさだけは少し綺麗だった。
```

Image Need Check examples:

- `text_only`: A short everyday joke or a post whose aftertaste is already
  complete in the text.
- `image`: A post where night rooms, rain, warm lighting, coffee, a glass,
  curtains, books, or quiet interiors are central to the atmosphere.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_account_policy tests.test_provider_routing tests.test_excel_daily_poster
Ran 33 tests in 0.051s
OK
```

Safety:

- No real X API, OpenAI API, Gemini API, or image generation API was called.
- Existing provider routing tests still pass.
- `get_account_prompt_policy()` returns the new policy only for
  `new_account_daily`; `yokaze_daily` and `ai_pickup` are unchanged.

## 2026-05-16 16:31 Codex Report

Added the X API error-classification foundation for the separated legacy-account
Excel/CSV poster. Real posting remains blocked by default.

Changed files:

- `tools/excel_daily_poster/x_client.py`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260516_1631.md`
- `reports/latest_report.md`

Implemented classes:

- `XPosterError`
- `XClientError`
- `XAuthError`
- `XRateLimitError`
- `XNetworkError`
- `XTemporaryError`
- `XConfigError`

Implemented helpers:

- `classify_http_status(status_code, message="")`
- `raise_for_http_status(status_code, message="")`
- `require_config_value(name, value)`

Safety:

- `BlockedXPoster` remains the default and raises `XConfigError`.
- No real X post, external communication, `pip install`, `.env` edit, API key
  request, or GitHub push was performed.
- The existing three-account runtime was not changed.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 22 tests in 0.056s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: Dry-run sample for the legacy manual account.
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-16 16:14 Codex Report

Improved Excel/CSV daily poster error handling for the separated legacy X
account queue.

Changed files:

- `tools/excel_daily_poster/daily_post.py`
- `tools/excel_daily_poster/excel_queue.py`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260516_1614.md`
- `reports/latest_report.md`

Implemented behavior:

- Candidate statuses are now only blank, `pending`, and `retry`.
- `posted`, `skipped`, `error`, `content_error`, and `system_error` are not
  auto-selected.
- Row-only issues become `content_error` and the runner checks the next
  candidate row.
- API/system errors stop the whole run and do not advance to the next row.
- A run can still post at most one successful row.
- Dry-run reports `content_error` equivalents without writing the queue.
- Live writes `content_error` only when no API/system failure aborts the run.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 18 tests in 0.048s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: Dry-run sample for the legacy manual account.
DRY-RUN: no X API call and no queue update were performed.
```

## 2026-05-16 15:58 Codex Report

Added a separated dry-run-first Excel/CSV daily poster for only the legacy X
account. The new tool is under `tools/excel_daily_poster/` and is not connected
to the three-account runtime.

Changed files:

- `tools/__init__.py`
- `tools/excel_daily_poster/__init__.py`
- `tools/excel_daily_poster/daily_post.py`
- `tools/excel_daily_poster/excel_queue.py`
- `tools/excel_daily_poster/x_client.py`
- `data/manual_account_posts.csv.example`
- `scripts/run_excel_daily_post.bat`
- `scripts/register_excel_daily_post_task.bat`
- `docs/excel_daily_poster.md`
- `tests/test_excel_daily_poster.py`
- `reports/codex_report_20260516_1558.md`
- `reports/latest_report.md`

Safety:

- No external communication, `pip install`, GitHub push, `.env` edit, API key
  creation, or real X post was performed.
- The default X poster is blocked and raises before any real API call.
- Live success/error queue updates are covered by tests with a mocked poster.

Verification:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_excel_daily_poster tests.test_provider_routing
Ran 13 tests in 0.014s
OK
```

Dry-run:

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv.example --dry-run
DRY-RUN selected row: 2
DRY-RUN post_text: Dry-run sample for the legacy manual account.
DRY-RUN: no X API call and no queue update were performed.
```

更新日: 2026-05-15

## 今回実施した作業内容

今回の作業は、commit `8445a972b9989ee7d3b731c66408a7618076699a` で整理した内容を、最新レポートとして明確に反映すること。

主題は `0001_test` 側の provider routing 基盤説明ではなく、実アプリ本体 `01_context01_myself` 側に入れた修正内容の記録。

実施したこと:

- 実アプリ本体が `01_context01_myself` であることを明記。
- `0001_test` は管理・docs・reports 用であることを明記。
- `yokaze_daily/main.py` の `call_gemini_text(...)` 直呼び問題をどう修正したかを記録。
- `shared/llm/factory.py` の lazy import 化と provider routing の接続状況を記録。
- GUI dry-run / mock 確認結果を記録。
- 実施したモックテストとテスト結果を記録。
- 未解決事項と次にやるべきことを整理。

## フォルダの役割

### 管理・レポート用

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test
```

役割:

- docs / reports 管理
- ChatGPT / Codex / Cursor 共有用
- GitHub に push してURL共有するための管理リポジトリ
- この `reports/latest_report.md` を保存している場所

### 実アプリ本体

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself
```

役割:

- 実際に動作していた X 自動運用システム本体
- GUI設定
- provider routing
- `yokaze_daily`
- `ai_pickup`
- `new_account_daily`
- 本文生成、画像プロンプト生成、品質チェック、draft生成

重要:

- `01_context01_myself` は現時点で Git リポジトリではない。
- そのため、実アプリ側コード修正そのものは GitHub に push できていない。
- GitHub に push できているのは、`0001_test` 側の docs / reports のみ。

## 修正した実アプリ側ファイル

実アプリ本体 `01_context01_myself` 側で修正したファイル:

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\tools\settings_manager.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\shared\llm\factory.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\shared\llm\__init__.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\yokaze_daily\main.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\new_account_daily\main.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\ai_pickup\score_and_draft.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\ai_pickup\recommend_today_post.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\ai_pickup\x_research_analyze.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\shared\draft_pipeline\generate_draft.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\tests\test_provider_routing_runtime.py
```

管理・レポート用 `0001_test` 側で更新したファイル:

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test\reports\latest_report.md
```

## yokaze_daily/main.py の修正内容

問題:

- GUIで `TEXT_LLM_PROVIDER=openai`、`OPENAI_MODEL=gpt-5.4` を選んでも、`yokaze_daily/main.py` 内で `call_gemini_text(...)` を直接呼んでいた。
- そのため、GUI設定が本文生成に反映されず、Gemini固定になる可能性があった。

修正:

- `call_gemini_text(...)` の直接呼び出しを廃止。
- 本文生成を `generate_text_for_role("text", ...)` 経由に変更。
- `generate_text_for_role()` 内で `client_for_role(role, account_type="yokaze_daily")` を呼ぶようにした。
- 画像プロンプト生成は `generate_text_for_role("image_prompt", ...)` 経由に分離。

結果:

- 本文生成は `TEXT_LLM_PROVIDER` を参照。
- 画像プロンプト生成は `IMAGE_PROMPT_LLM_PROVIDER` を参照。
- `TEXT_LLM_PROVIDER=openai` なら OpenAI 側へ分岐。
- `TEXT_LLM_PROVIDER=gemini` なら Gemini 側へ分岐。

## shared/llm/factory.py の修正内容

修正内容:

- `RoutedLLMClient` を追加。
- role別に provider を解決。
- provider と実clientの不一致を `RuntimeError` で停止。
- provider routing のログを追加。
- Gemini/OpenAI client を lazy import に変更。

lazy import の内容:

- 修正前:
  - `factory.py` import 時点で `GeminiClient` / `OpenAIClient` を top-level import。
  - mockテストでも不要な provider client 依存を読み込む可能性があった。
- 修正後:
  - `create_client("gemini")` の中でだけ `GeminiClient` を import。
  - `create_client("openai")` の中でだけ `OpenAIClient` を import。
  - mockテストで実API client を読み込まずに provider routing を検証可能。

ログ出力:

```text
[LLM_ROUTE] account_type=... role=... env=... provider=... model=... function=...
[LLM_CALL] account_type=... role=... provider=... model=... function=... request_label=...
```

## provider routing の接続状況

GUIで管理している provider 設定:

```text
TEXT_LLM_PROVIDER
IMAGE_PROMPT_LLM_PROVIDER
QUALITY_CHECK_LLM_PROVIDER
OPENAI_MODEL
GEMINI_MODEL
```

role別の接続:

```text
本文生成             -> TEXT_LLM_PROVIDER
画像プロンプト生成   -> IMAGE_PROMPT_LLM_PROVIDER
品質チェック         -> QUALITY_CHECK_LLM_PROVIDER
```

アカウント別の接続:

```text
yokaze_daily
  本文生成           -> client_for_role("text", account_type="yokaze_daily")
  画像プロンプト生成 -> client_for_role("image_prompt", account_type="yokaze_daily")

ai_pickup
  本文生成           -> client_for_role("text", account_type="ai_pickup")
  shared draft内     -> image_prompt / quality_check を role別に分離

new_account_daily
  本文生成           -> client_for_role("text", account_type="new_account_daily")
```

## GUI dry-run の確認結果

実APIは呼ばず、GUI相当の保存・生成起動フローを mock / dry-run で確認。

確認内容:

- `tools/settings_manager.py` の `.env` 読み書き処理で、GUI選択相当の provider/model が保存される。
- GUIの「今すぐ生成」では、subprocess 起動前に `save_env(show_message=False)` が実行される。
- これにより、GUIで選んだ provider/model が `.env` に反映されてから実アプリ生成処理が起動する。
- `TEXT_LLM_PROVIDER=openai` の場合、本文生成は `OpenAIClient.generate_text` 側へ分岐。
- `TEXT_LLM_PROVIDER=gemini` の場合、本文生成は `GeminiClient.generate_text` 側へ分岐。
- 画像プロンプト生成は `IMAGE_PROMPT_LLM_PROVIDER` を使う。
- 品質チェックは `QUALITY_CHECK_LLM_PROVIDER` を使う。
- ログに `provider` / `model` / `function` / `account_type` が出る。
- `yokaze_daily` / `ai_pickup` / `new_account_daily` の3アカウントで routing を確認。

## 実施したテスト

実APIは禁止のため、すべて mock / dry-run。

テストファイル:

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\tests\test_provider_routing_runtime.py
```

実施した確認:

- GUI保存相当で `.env` に provider/model が反映される。
- GUI生成フローが subprocess 起動前に `save_env(show_message=False)` を実行する。
- `TEXT_LLM_PROVIDER=openai` で OpenAI 側へ分岐する。
- `TEXT_LLM_PROVIDER=gemini` で Gemini 側へ分岐する。
- `IMAGE_PROMPT_LLM_PROVIDER` が本文providerと混線しない。
- `QUALITY_CHECK_LLM_PROVIDER` が本文providerと混線しない。
- provider mismatch は `RuntimeError` で停止する。
- `yokaze_daily` / `ai_pickup` / `new_account_daily` の各アカウントで `account_type` 付きログが出る。
- 対象ランタイム内に `call_gemini_text(` / `call_gemini(` / `requests.post(` の直呼びが残っていない。

## テスト結果

実API呼び出し:

```text
なし
```

構文確認:

```text
python -m compileall shared\llm tools\settings_manager.py yokaze_daily\main.py new_account_daily\main.py ai_pickup\score_and_draft.py ai_pickup\recommend_today_post.py ai_pickup\x_research_analyze.py shared\draft_pipeline\generate_draft.py tests\test_provider_routing_runtime.py
```

結果:

```text
OK
```

モックテスト:

```text
python -m unittest discover -s tests -v
```

結果:

```text
11 tests OK
```

## 直呼びの残件

対象ランタイム内では、以下の直呼び残件なし。

```text
call_gemini_text(
call_gemini(
requests.post(
```

確認対象:

```text
yokaze_daily/main.py
new_account_daily/main.py
ai_pickup/score_and_draft.py
ai_pickup/recommend_today_post.py
ai_pickup/x_research_analyze.py
```

補足:

以下の provider client 本体内の `requests.post` は、今回禁止した「生成フローからの直呼び」には含めない。

```text
shared/llm/gemini_client.py
shared/llm/openai_client.py
shared/image_pipeline/openai_image_client.py
```

## 未解決事項

- `01_context01_myself` が Git リポジトリではない。
- 実アプリのコード変更そのものは GitHub に push できていない。
- GitHub上で実コード差分をレビューできる状態になっていない。
- 実API疎通確認は未実施。ユーザー許可があるまで実行しない。
- `TEXT_LLM_PROVIDER` 未設定時の default は既存互換の `gemini` のまま。GUI default の `openai` に合わせるかは未決定。

## 次にやるべきこと

1. `01_context01_myself` を GitHub 管理対象にする。
2. 実アプリ側の修正差分を commit / push できる状態にする。
3. GitHub上で以下の差分をレビューできるようにする。
   - `tools/settings_manager.py`
   - `shared/llm/factory.py`
   - `shared/llm/__init__.py`
   - `yokaze_daily/main.py`
   - `new_account_daily/main.py`
   - `ai_pickup/*.py`
   - `shared/draft_pipeline/generate_draft.py`
   - `tests/test_provider_routing_runtime.py`
4. ユーザー許可後、必要最小限の実API疎通確認を行う。
5. 未設定時 default provider を `gemini` のままにするか、GUI default に合わせて `openai` にするか決める。

## 今後の運用メモ

このセッションでは、安全な開発操作は確認なしで進める。

自動で進める操作:

- `git add`
- `git commit`
- `git push`
- `__pycache__` 削除
- reports / docs 更新
- モックテスト実行
- dry-run
- ログ生成
- markdown生成

必ず事前確認する操作:

- 実API呼び出し
- `.env` 変更
- APIキー変更
- requirements変更
- pip install
- ファイル大量削除
- move / rename
- GUI設定変更
- 本番投稿
- 外部通信
- OS設定変更

---

# 2026-05-27 Reference Posts Collector / Yokaze Policy Update

## Summary

Added a dry-run/mock-first reference-post collection and structure-analysis
flow for `yokaze_daily`. The implementation is intentionally local-first:
dry-run collection uses sample data, mock analysis uses deterministic local
logic, and live X/LLM clients must be injected in a later phase.

## Changed Files

- `.gitignore`
- `data/source_accounts.csv.example`
- `data/reference_posts/.gitkeep`
- `docs/reference_posts_collector.md`
- `reports/reference_posts_report.md`
- `reports/latest_report.md`
- `tests/test_account_policy.py`
- `tests/test_reference_posts.py`
- `tools/x_collect_reference_posts.py`
- `tools/x_score_reference_posts.py`
- `tools/x_analyze_reference_posts.py`
- `x_auto_ops/account_policy.py`
- `x_auto_ops/reference_posts.py`

## Implementation

- Added `YOKAZE_DAILY_POLICY` with concrete-wound targeting, love 70% / other
  30% direction, prohibited self-help phrases, and optional no-text atmosphere
  image rules.
- Added source account CSV loading and a strict `--limit` cap of 200.
- Added dry-run reference collection that never calls X and writes
  `data/reference_posts/raw_posts.csv`.
- Added scoring with:
  `score = like_count + repost_count * 3 + reply_count * 2 + quote_count * 2`.
- Added filtering for link-only posts, too-short posts, promotional posts,
  reposts, and replies.
- Added mock/dry-run structure analysis for yokaze fields such as target,
  pain, hidden feeling, structure, emotional flow, ending type, and rewrite
  direction.
- Added report generation at `reports/reference_posts_report.md`.

## Dry-Run Results

Commands were run with the bundled Codex Python because `python` and `py` are
not registered on this machine's PATH.

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools/x_collect_reference_posts.py --dry-run
```

Result:

```text
Target accounts: 1
Estimated posts to fetch: 200
DRY-RUN: wrote 4 posts to data\reference_posts\raw_posts.csv
DRY-RUN: no X API call was performed.
```

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools/x_score_reference_posts.py
```

Result:

```text
Read posts: 4
Excluded posts: 1
Scored posts: 3
Wrote: data\reference_posts\scored_posts.csv
```

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools/x_analyze_reference_posts.py --mock-llm --dry-run
```

Result:

```text
DRY-RUN mock-llm: analyzed 3 posts
Wrote: data\reference_posts\analyzed_posts.jsonl
Report: reports\reference_posts_report.md
DRY-RUN/MOCK: no external LLM call was performed.
```

## Tests

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_reference_posts -v
```

Result: 7 tests OK.

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_account_policy tests.test_provider_routing tests.test_reference_posts -v
```

Result: 20 tests OK.

## Remaining Notes

- Live X collection is not wired yet. Next phase should inject a client that
  resolves user ids, fetches recent posts, and honors `Retry-After` for 429.
- Do not raise `MAX_LIMIT` without reviewing X API cost/rate-limit impact.
- Live LLM analysis should continue through provider routing and injected
  clients; no direct OpenAI/Gemini calls should be added to these tools.
- Reference posts are for structure analysis only. Do not preserve source
  wording, line breaks, metaphors, or sentence order.

---

# 2026-05-28 Yokaze Reference Generation Preview

## Summary

Added a dry-run/mock-first preview generator that reads
`data/reference_posts/analyzed_posts.jsonl` and creates original
`yokaze_daily` draft candidates from structure only. The generator does not
copy or rewrite source posts; it uses target, pain, hidden feeling, theme, and
ending direction as inputs.

## Changed Files

- `.gitignore`
- `data/reference_posts/yokaze_generated_posts.jsonl.example`
- `docs/yokaze_reference_generation.md`
- `reports/latest_report.md`
- `reports/yokaze_reference_generation_report.md`
- `tests/test_yokaze_reference_generation.py`
- `tools/x_generate_yokaze_from_reference.py`
- `x_auto_ops/yokaze_reference_generation.py`

## Implementation

- Added `tools/x_generate_yokaze_from_reference.py`.
- Added `x_auto_ops/yokaze_reference_generation.py` with:
  - analyzed JSONL loading
  - optional `--top-n`
  - optional `--theme`
  - mock/dry-run generation
  - provider-routing-compatible live path with injected clients only
  - `image_recommendation` values: `none`, `ambient_only`, `avoid`
  - `similarity_risk` values: `low`, `medium`, `high`
  - generated report output
- Added docs and example JSONL.
- Added tests for selection, dry-run/mock generation, output shape,
  similarity-risk detection, image recommendation, report generation, and no
  external LLM call in dry-run/mock mode.

## Dry-Run Result

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools/x_generate_yokaze_from_reference.py --mock-llm --dry-run
```

Result:

```text
DRY-RUN mock-llm: generated 3 yokaze drafts
Wrote: data\reference_posts\yokaze_generated_posts.jsonl
Report: reports\yokaze_reference_generation_report.md
DRY-RUN/MOCK: no external LLM call was performed.
```

## Tests

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_yokaze_reference_generation -v
```

Result: 4 tests OK.

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_reference_posts tests.test_yokaze_reference_generation tests.test_account_policy -v
```

Result: 16 tests OK.

## Generated Sample Posts

### Candidate 1

```text
通知が鳴っていないのに
画面を伏せたまま気にしてしまう夜がある。

平気なふりをしていたのは
困らせたくなかったからで
本当は、少しだけ安心させてほしかったんだよね。

重かったんじゃないよ。
ひとりで待つ時間が
長すぎただけだよ。
```

- similarity_risk: low
- image_recommendation: none

### Candidate 2

```text
会いたいと言えなかった日の帰り道ほど
何でもない顔が上手になる。

寂しいって言ったら
面倒に思われそうで
言葉を飲み込むしかなかったんだよね。

わがままじゃないよ。
大事にされたい気持ちを
静かに隠していただけ。
```

- similarity_risk: low
- image_recommendation: none

### Candidate 3

```text
雑に扱われたのに
優しかった日のことだけ思い出してしまう夜がある。

嫌いになれない自分を責めても
それだけ本気で向き合っていた時間は
簡単には消えないよね。

足りなかったのは
あなたの可愛さじゃなくて
大事にする覚悟だったのかもしれない。
```

- similarity_risk: low
- image_recommendation: none

## Remaining Notes

- Current analyzed input contains only love-themed items, so the dry-run report
  shows love 100% / other 0%. The 70/30 policy should be checked when mixed
  analyses are available.
- Human review should still confirm that no source wording, metaphor, line
  structure, or conclusion phrasing is carried over.
- Live generation should stay behind provider routing and injected clients.

---

# 2026-05-28 Yokaze Generation Pattern / Quality Update

## Summary

Improved the `yokaze_daily` reference-generation preview so repeated drafts do
not collapse into the same structure. Added style pattern control, theme-ratio
warnings, style-repetition checks, and per-draft quality scoring.

## Changed Files

- `.gitignore`
- `data/reference_posts/yokaze_generated_posts.jsonl.example`
- `docs/yokaze_reference_generation.md`
- `reports/latest_report.md`
- `reports/yokaze_reference_generation_report.md`
- `tests/test_yokaze_reference_generation.py`
- `tools/x_generate_yokaze_from_reference.py`
- `x_auto_ops/yokaze_reference_generation.py`

## Implementation

- Added `style_pattern` output:
  - `daiben`
  - `joukei`
  - `hitei_kaijo`
  - `kioku`
  - `short_yoin`
- Added CLI options:
  - `--style-pattern`
  - `--target-ratio`
  - `--max-same-pattern`
- Added target ratio parsing such as `romance:0.7,other:0.3`.
- Added theme shortage warnings when other-theme analyses are missing.
- Added `quality_check` with:
  - `target_specificity`
  - `emotional_specificity`
  - `generic_advice_risk`
  - `self_help_tone_risk`
  - `style_repetition_risk`
  - `final_score`
- Added report sections for style counts, theme counts, average score, high
  generic/self-help risks, style repetition warnings, and human review
  candidates.
- Added mock sample analyses for:
  - 職場では笑って家で崩れる女性
  - 人間関係で空気を読みすぎて疲れる女性
  - 相談できず一人で抱える女性

## Dry-Run Command

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools/x_generate_yokaze_from_reference.py --mock-llm --dry-run --style-pattern auto --target-ratio romance:0.7,other:0.3
```

Result:

```text
DRY-RUN mock-llm: generated 3 yokaze drafts
Wrote: data\reference_posts\yokaze_generated_posts.jsonl
Report: reports\yokaze_reference_generation_report.md
DRY-RUN/MOCK: no external LLM call was performed.
```

## Tests

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_yokaze_reference_generation -v
```

Result: 7 tests OK.

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_reference_posts tests.test_yokaze_reference_generation tests.test_account_policy -v
```

Result: 19 tests OK.

## Current Report Results

- Input analyses: 3
- Generated posts: 3
- Romance ratio: 3/3 (100.0%)
- Other ratio: 0/3 (0.0%)
- Average quality score: 86.7
- Style counts:
  - `joukei`: 1
  - `daiben`: 1
  - `kioku`: 1
- Similarity risk:
  - `low`: 3
- Image recommendation:
  - `none`: 3
- Theme warning:
  - Other-theme analyses are missing; do not fabricate other posts.
- High generic advice risk: none
- High self-help tone risk: none
- Style repetition warning: none

## Generated Examples

### joukei

```text
通知が鳴っていないのに
画面を伏せたまま気にしてしまう夜がある。

平気なふりをしていたのは
困らせたくなかったからで
本当は、少しだけ安心させてほしかったんだよね。

重かったんじゃないよ。
ひとりで待つ時間が
長すぎただけだよ。
```

Quality:

```text
target_specificity=high
emotional_specificity=high
generic_advice_risk=low
self_help_tone_risk=low
style_repetition_risk=low
final_score=90
```

---

# 2026-05-28 Manual Reference Posts Import

## Summary

Added a local-only manual import path for reference posts. This allows manually
collected X post text, URLs, and reaction counts to be converted into the
existing `raw_posts.csv` format before enabling any live X API collection.

## Changed Files

- `.gitignore`
- `data/reference_posts/manual_reference_posts.csv.example`
- `docs/manual_reference_posts_import.md`
- `reports/latest_report.md`
- `tests/test_manual_reference_posts_import.py`
- `tools/x_import_reference_posts_manual.py`
- `x_auto_ops/manual_reference_import.py`

## Implementation

- Added `tools/x_import_reference_posts_manual.py`.
- Added `x_auto_ops/manual_reference_import.py`.
- Input:
  - `data/reference_posts/manual_reference_posts.csv`
- Output:
  - `data/reference_posts/raw_posts.csv`
- Required input columns:
  - `post_url`
  - `text`
  - `category`
- Optional input columns:
  - `source_handle`
  - `created_at`
  - `like_count`
  - `repost_count`
  - `reply_count`
  - `quote_count`
  - `impression_count`
  - `note`
- Converts rows to `RAW_POST_FIELDS`.
- Extracts `post_id` from `/status/<id>` URLs.
- Generates `manual_0001` style ids when no URL post id exists.
- Infers `source_handle` from X/Twitter URL when omitted.
- Fills missing count fields with `0`.
- Requires `category`.
- Warns on short text.
- Skips duplicate `post_url`.
- `--dry-run` previews conversion without writing `raw_posts.csv`.
- No external API calls are made.

## Sample Input CSV

```text
source_handle,post_url,text,created_at,like_count,repost_count,reply_count,quote_count,impression_count,category,note
yokaze_ref,https://x.com/yokaze_ref/status/1234567890123456789,"返信が来ないだけで、何度もスマホを見てしまう夜がある。平気なふりをしているだけで、本当はずっと苦しかった。",2026-05-20T21:00:00+09:00,1200,180,42,35,50000,恋愛,返信待ち系の構造参考
,https://x.com/work_ref/status/9876543210987654321,"職場では笑っていたのに、家に帰った瞬間に何もできなくなる。だらしないのではなく、誰にも見えないところで限界だった。",2026-05-21T22:30:00+09:00,830,90,21,18,,仕事・人間関係・孤独,家で崩れる構造参考
```

## Dry-Run Command

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools/x_import_reference_posts_manual.py --dry-run
```

Result:

```text
DRY-RUN: read 2 manual rows
DRY-RUN: imported 2 rows
DRY-RUN: duplicate URLs skipped 0
DRY-RUN preview:
- yokaze_ref / 1234567890123456789 / 恋愛 / 返信が来ないだけで、何度もスマホを見てしまう夜がある。平気なふりをしているだけで
- work_ref / 9876543210987654321 / 仕事・人間関係・孤独 / 職場では笑っていたのに、家に帰った瞬間に何もできなくなる。だらしないのではなく、
DRY-RUN: raw_posts.csv was not written.
No external API call was performed.
```

## Import Command

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools/x_import_reference_posts_manual.py
```

Result:

```text
IMPORT: read 2 manual rows
IMPORT: imported 2 rows
IMPORT: duplicate URLs skipped 0
Wrote: data\reference_posts\raw_posts.csv
No external API call was performed.
```

## Output raw_posts.csv Example

```text
source_handle,post_id,post_url,text,created_at,like_count,repost_count,reply_count,quote_count,impression_count,category,collected_at
yokaze_ref,1234567890123456789,https://x.com/yokaze_ref/status/1234567890123456789,返信が来ないだけで、何度もスマホを見てしまう夜がある。平気なふりをしているだけで、本当はずっと苦しかった。,2026-05-20T21:00:00+09:00,1200,180,42,35,50000,恋愛,...
work_ref,9876543210987654321,https://x.com/work_ref/status/9876543210987654321,職場では笑っていたのに、家に帰った瞬間に何もできなくなる。だらしないのではなく、誰にも見えないところで限界だった。,2026-05-21T22:30:00+09:00,830,90,21,18,0,仕事・人間関係・孤独,...
```

## Tests

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_manual_reference_posts_import -v
```

Result: 8 tests OK.

```text
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_reference_posts tests.test_manual_reference_posts_import tests.test_yokaze_reference_generation tests.test_account_policy -v
```

Result: 27 tests OK.

### daiben

```text
寂しいって言えなかったのは
強かったからじゃなくて
重いと思われるのが怖かったから。

本当は、返事より先に
気にしてくれているって
少しだけ感じたかったんだよね。

責めたかったんじゃない。
ひとりで不安を抱える時間が
長すぎただけ。
```

Quality:

```text
target_specificity=medium
emotional_specificity=high
generic_advice_risk=low
self_help_tone_risk=low
style_repetition_risk=low
final_score=80
```

### kioku

```text
雑に扱われたのに
優しかった日のことだけ思い出してしまう夜がある。

嫌いになれない自分を責めても
それだけ本気で向き合っていた時間は
簡単には消えないよね。

足りなかったのは
あなたの可愛さじゃなくて
大事にする覚悟だったのかもしれない。
```

Quality:

```text
target_specificity=high
emotional_specificity=high
generic_advice_risk=low
self_help_tone_risk=low
style_repetition_risk=low
final_score=90
```
## 2026-05-30 X Genre Buzz Collector Design

Designed a future mock-first feature for extracting growing X posts by three
genres. This was research and design only.

### Scope

- No live X API call.
- No X API key or token access.
- No `.env` edit.
- No real posting, liking, reposting, replying, or following.
- No implementation code added.

### Repository Findings

- X-related collection/scoring code already exists in
  `x_auto_ops/reference_posts.py`.
- Existing CLIs:
  - `tools/x_collect_reference_posts.py`
  - `tools/x_score_reference_posts.py`
  - `tools/x_analyze_reference_posts.py`
  - `tools/x_import_reference_posts_manual.py`
- Existing CSV flow:
  - `data/reference_posts/raw_posts.csv`
  - `data/reference_posts/scored_posts.csv`
  - `data/reference_posts/analyzed_posts.jsonl`
- Existing tests already cover dry-run collection, scoring, CSV writing,
  manual import, and mock analysis.
- Posting-oriented X client code exists in
  `tools/excel_daily_poster/x_client.py`, but it should not be reused directly
  for read collection except for its blocked-by-default and error-classification
  patterns.

### X API Research

Official X docs checked:

- https://docs.x.com/x-api/fundamentals/metrics
- https://docs.x.com/x-api/posts/search/quickstart/recent-search
- https://docs.x.com/x-api/fundamentals/rate-limits
- https://docs.x.com/x-api/posts/search/introduction

Likely public post metrics:

- `public_metrics.like_count`
- `public_metrics.retweet_count`
- `public_metrics.reply_count`
- `public_metrics.quote_count`
- `public_metrics.impression_count`
- `public_metrics.bookmark_count`

Potentially unavailable or restricted:

- URL clicks, profile clicks, and total engagements are non-public metrics.
- Organic/promoted metrics are user-context metrics and generally only useful
  for owned/promoted posts.
- Full-archive search may require higher access than recent search.
- Recent search is limited to the recent window and has endpoint/query/result
  limits that must be rechecked at live implementation time.

### Implementation Direction

- Keep this separate from the existing reference-post collector, but reuse its
  CSV helpers and dry-run-first style.
- Store future config as:
  - `data/x_buzz_genres.yml.example`
  - `data/x_buzz_genres.yml` ignored by git
- Store future outputs under:
  - `data/x_buzz_posts/raw_posts.csv`
  - `data/x_buzz_posts/scored_posts.csv`
- Add future modules:
  - `x_auto_ops/genre_buzz_config.py`
  - `x_auto_ops/genre_buzz_posts.py`
  - `x_auto_ops/x_read_client.py`
- Add future CLIs:
  - `tools/x_collect_genre_buzz_posts.py`
  - `tools/x_score_genre_buzz_posts.py`
- Add future tests:
  - `tests/test_genre_buzz_config.py`
  - `tests/test_genre_buzz_posts.py`

### Config Draft

```yaml
version: 1
defaults:
  endpoint: recent_search
  max_results_per_request: 100
  max_pages: 2
  exclude_retweets: true
  exclude_replies: true
  lang: ja
  score_weights:
    like_count: 1.0
    repost_count: 3.0
    reply_count: 1.5
    quote_count: 2.5
    bookmark_count: 0.5
  thresholds:
    min_like_count: 100
    min_repost_count: 10
    min_reply_count: 0
    min_quote_count: 0
    min_score: 150
genres:
  - id: romance
    label: 恋愛
    query_keywords: [恋愛, 復縁, 片思い]
    target_accounts: [example_account_1]
    search_query_extra: "-is:retweet -is:reply"
    thresholds:
      min_like_count: 500
      min_repost_count: 30
      min_score: 800
  - id: work_relationships
    label: 仕事・人間関係
    query_keywords: [職場, 人間関係, しんどい]
    target_accounts: []
  - id: loneliness_life
    label: 孤独・日常
    query_keywords: [孤独, 夜, 疲れた]
    target_accounts: []
```

### Score Draft

```text
buzz_score =
  like_count * 1.0
  + repost_count * 3.0
  + reply_count * 1.5
  + quote_count * 2.5
  + bookmark_count * 0.5
```

Optional:

- `engagement_count = like + repost + reply + quote + bookmark`
- `engagement_rate = engagement_count / impression_count`
- `velocity_score = buzz_score / max(age_hours, 1)`

### CSV Column Draft

```text
genre_id,genre_label,post_id,post_url,text,author_id,author_username,
author_name,created_at,collected_at,query,matched_keywords,source_type,
source_account,like_count,repost_count,reply_count,quote_count,bookmark_count,
impression_count,engagement_count,engagement_rate,age_hours,buzz_score,
velocity_score,genre_rank,lang,possibly_sensitive,conversation_id,
referenced_tweets,media_keys,excluded,exclusion_reason
```

### Mock Test Plan

- Config loader validates exactly three genres.
- Defaults merge correctly into genre-specific overrides.
- Query builder adds safe filters and respects query length.
- Dry-run collector uses fixtures and never calls a live client.
- Normalizer maps `retweet_count` to `repost_count`.
- Missing metrics are handled safely.
- Threshold filtering is per genre.
- Score formula is deterministic and configurable.
- Duplicate `post_id` rows are deduplicated.
- CSV column order is stable.
- Rate-limit errors can be classified without retrying in unit tests.

### Added Files

- `docs/x_genre_buzz_collector_design.md`

### Verification

- Documentation-only change. Unit tests were not run because no executable code
  was changed.
