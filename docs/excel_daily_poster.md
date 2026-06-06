# Excel Daily Poster

This tool is only for the one legacy X account that already existed before the
new three-account automation. It is intentionally separate from
`x_auto_ops.provider_routing` and does not target `yokaze_daily`, `ai_pickup`,
or `new_account_daily`.

## Safety Defaults

- The Windows runner uses `--dry-run`.
- The default live client is blocked and cannot call the real X API.
- No `.env` file or API key is created or changed by this tool.
- Dry-run prints the selected row and post text, then exits without writing the queue.
- Live mode writes the queue only after the injected poster succeeds or fails.
- Live mode also creates a sidecar `.lock` file to prevent overlapping runs.

## Queue Columns

The queue must be a CSV file, or an XLSX file when `openpyxl` is already
available locally. CSV is the no-install path.

Required columns:

- `post_text`
- `status`
- `scheduled_date`
- `posted_at`
- `tweet_id`
- `error`

Rows with blank `status`, `pending`, or `retry` can be selected. Rows marked
`posted`, `skipped`, `content_error`, `system_error`, or `error` are never
selected automatically. A `scheduled_date` in the future is ignored until that
date. Dates must use `YYYY-MM-DD`.

## Error Handling

Row-only problems are classified as `content_error`. The runner then checks the
next eligible row, while still allowing at most one successful post per run.

`content_error` examples:

- Empty `post_text`
- `post_text` longer than 280 characters
- Broken `scheduled_date` format
- Post text validation failure

In dry-run, these rows are reported as `content_error` equivalents but the queue
is not written. In live mode, `content_error` rows are written only when the run
finishes without an API/system failure.

API/system errors stop the whole run and do not advance to the next row. This
includes authentication errors, missing keys, `.env` problems, 401/403/429,
network failures, temporary X-side failures, unreadable queue files, missing
required columns, lock-file errors, and any unknown error that may affect the
next row too.

Future X API clients should raise the exception classes in
`tools/excel_daily_poster/x_client.py`:

- `XAuthError` for authentication and permission failures, including 401 and 403
- `XRateLimitError` for 429 rate limits
- `XNetworkError` for connection, DNS, timeout, and transport failures
- `XTemporaryError` for X-side temporary failures, including 5xx responses
- `XConfigError` for missing API keys, missing `.env` values, or invalid config
- `XClientError` for other client/API failures that should stop the run

`classify_http_status()` maps failed HTTP status codes into these classes.
`require_config_value()` validates required future config values without reading
or writing `.env`.

## Dry-Run

Copy `data/manual_account_posts.csv.example` to `data/manual_account_posts.csv`
outside of this change, then run:

```powershell
python tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv --dry-run
```

## Local Queue Preparation

Create the production queue from the example file:

```powershell
copy data\manual_account_posts.csv.example data\manual_account_posts.csv
```

`data/manual_account_posts.csv` is ignored by Git because it is local operating
data. Keep `data/manual_account_posts.csv.example` as the shareable template.

When editing the CSV in Excel:

- Keep the required header names unchanged.
- Save as CSV, not a new workbook format, unless you deliberately switch to
  `.xlsx`.
- Do not delete `status`, `scheduled_date`, `posted_at`, `tweet_id`, or `error`.
- Use `YYYY-MM-DD` for `scheduled_date`.
- Leave `status` blank or set it to `pending` / `retry` for rows that may post.
- Use `skipped` for rows that should never post.
- Do not manually set `posted` unless you are recording a post that already
  happened outside the tool.
- Close Excel before running the poster so the file is not locked.

Before any manual live test:

1. Create `data/manual_account_posts.csv`.
2. Review the first eligible row by eye.
3. Run dry-run.
4. Confirm the displayed row number and post text match your intent.
5. Confirm there are no unexpected `content_error` messages.
6. Proceed to the manual one-row wrapper only after explicit human approval.

## One-Row-Per-Day CSV Format

`data/manual_account_posts.csv.example` is a UTF-8 with BOM CSV template so
Japanese text opens cleanly in Excel. Use it as the starting point for the local
production CSV.

Basic Excel columns:

| Excel column | CSV header | Purpose |
| --- | --- | --- |
| A | `post_text` | Paste one post per row. |
| B | `status` | Usually `pending` before posting. |
| C | `scheduled_date` | Optional date gate, using `YYYY-MM-DD`. |
| D | `posted_at` | Filled automatically after a successful post. |
| E | `tweet_id` | Filled automatically after a successful post. |
| F | `error` | Filled automatically when an error is recorded. |

Rules:

- Do not delete or rename the header row.
- Paste post text vertically into column A, one cell per post.
- Use `pending` in column B for normal queued rows.
- Leave column C blank unless a row should wait until a specific date.
- Leave columns D, E, and F blank before posting.
- After editing in Excel, save as CSV UTF-8.
- Close Excel before running dry-run or live posting.

Status meanings:

| status | Meaning |
| --- | --- |
| blank | Candidate for posting. |
| `pending` | Candidate for posting. |
| `retry` | Candidate for retry. |
| `posted` | Already posted; never selected automatically. |
| `skipped` | Manually skipped; never selected automatically. |
| `content_error` | Skipped because the row text/date needs correction. |
| `error` | Error requiring manual review. |
| `system_error` | System-level error marker. |

One-row-per-day flow:

- The system reads the CSV from top to bottom.
- It selects the first valid row whose `status` is blank, `pending`, or `retry`.
- Future `scheduled_date` rows are ignored until that date.
- When posting succeeds, that row becomes `posted`.
- The next run selects the next eligible row.
- At most one row can be posted successfully per run.

Production CSV setup:

1. Copy `data/manual_account_posts.csv.example` to `data/manual_account_posts.csv`.
2. Delete the sample rows.
3. Paste the post list into column A from row 2 downward.
4. Put `pending` in column B from row 2 downward.
5. Leave columns C onward blank unless a scheduled date is needed.
6. Save as CSV UTF-8.
7. Close Excel.
8. Run dry-run and confirm the selected row.

CSV example:

```csv
post_text,status,scheduled_date,posted_at,tweet_id,error
投稿文1,pending,,,,
投稿文2,pending,,,,
投稿文3,pending,,,,
```

Excel display image:

| A: post_text | B: status | C: scheduled_date | D: posted_at | E: tweet_id | F: error |
| --- | --- | --- | --- | --- | --- |
| 投稿文1 | pending |  |  |  |  |
| 投稿文2 | pending |  |  |  |  |
| 投稿文3 | pending |  |  |  |  |

Large paste cautions:

- Treat one cell as one post.
- Paste vertically into column A.
- Avoid multi-line posts at first because embedded newlines make CSV review
  harder.
- Rows over 280 characters become `content_error`.
- Excel usually quotes commas and URLs correctly when saving CSV, but confirm the
  file with dry-run after saving.
- Start with 10 to 20 rows before adding a larger queue.
- Do not jump directly from a large paste into automatic operation.

## Windows Task Scheduler

`scripts/run_excel_daily_post.bat` runs dry-run and writes logs to
`logs\excel_daily_poster.log`. It ends with:

```bat
timeout /t 1800 /nobreak
```

Register the daily task:

```bat
scripts\register_excel_daily_post_task.bat
```

The default scheduled time is 09:00. Edit the `/ST` value in the registration
bat if a different time is needed.

## Future Live Posting

Live posting should be enabled only after explicit approval. The live switch is
not just a bat edit: replace `BlockedXPoster` by injecting a reviewed
implementation of the `XPoster` protocol in `tools/excel_daily_poster/x_client.py`
or from a wrapper that calls `run_once`.

`BlockedXPoster` remains the default and raises `XConfigError`, so accidental
live runs stop before any real API call.

`TweepyXPoster` is available as a future real-posting implementation, but it is
not wired into the CLI or Windows bat file. It receives credentials from the
caller through `XApiCredentials`; it does not create or edit `.env` and it is not
used unless a separate wrapper explicitly injects it into `run_once`.

If Pay Per Use is enabled but OAuth 1.0a still returns 403 Forbidden for
`POST /2/tweets`, consider OAuth 2.0 User Context before changing the scheduler.
`OAuth2UserContextXPoster` is prepared for that path, but it is also not wired
into the CLI or Windows bat file.

OAuth 2.0 User Context configuration to prepare later:

- `X_OAUTH2_CLIENT_ID`: required to identify the app/client.
- `X_OAUTH2_CLIENT_SECRET`: may be required for confidential clients or refresh
  flows; public clients may not use a client secret.
- `X_OAUTH2_ACCESS_TOKEN`: required for the actual `POST /2/tweets` request.
- `X_OAUTH2_REFRESH_TOKEN`: required only if the local flow will refresh expired
  access tokens.
- Scopes: prepare an access token with at least `tweet.read`, `tweet.write`, and
  `users.read`. Include `offline.access` when a refresh token is needed.

`OAuth2UserContextXPoster` validates the access token and required scopes before
posting. Tests use a fake transport only; no real OAuth 2.0 request or tweet is
sent by the test suite.

## OAuth 2.0 PKCE Token Preparation

OAuth 2.0 User Context requires you to open an authorization URL, sign in with
the target X account, and approve the app. The local helpers prepare that flow
without posting and without changing `.env`.

Generate a PKCE authorization URL:

```powershell
set X_OAUTH2_CLIENT_ID=REPLACE_WITH_REAL_VALUE
set X_OAUTH2_REDIRECT_URI=http://127.0.0.1:8765/callback
python tools\excel_daily_poster\oauth2_authorize.py
```

This creates `data/oauth2_state.local.json`, which contains `state` and
`code_verifier`. The file is ignored by Git and must not be shared.

Required scopes:

- `tweet.read`
- `tweet.write`
- `users.read`
- `offline.access`

After approving the app in the browser, X redirects to the configured redirect
URI with `code` and `state`. Check that the returned `state` matches the saved
state before any token exchange.

Validate the returned code and state without HTTP first:

```powershell
python tools\excel_daily_poster\oauth2_exchange_code.py --code REPLACE_WITH_CODE --state REPLACE_WITH_RETURNED_STATE --mock-only
```

To avoid copying `code` and `state` by hand, use the local callback helper
instead. Configure the X Developer Portal callback URL and
`X_OAUTH2_REDIRECT_URI` as:

```text
http://127.0.0.1:8765/callback
```

Then run:

```powershell
set X_OAUTH2_CLIENT_ID=REPLACE_WITH_REAL_VALUE
set X_OAUTH2_REDIRECT_URI=http://127.0.0.1:8765/callback
set X_OAUTH2_CLIENT_SECRET=REPLACE_WITH_REAL_VALUE
python tools\excel_daily_poster\oauth2_local_callback.py --confirm-token-exchange I_UNDERSTAND_THIS_EXCHANGES_OAUTH2_TOKEN
```

`X_OAUTH2_CLIENT_SECRET` is required only for confidential clients. The helper
prints the authorization URL, waits on `http://127.0.0.1:8765/callback`, checks
the returned `state`, exchanges the code immediately, and saves tokens to
`data/oauth2_tokens.local.json`. It does not print the authorization code,
access token, refresh token, client secret, or code verifier.

After code/state validation, the same helper can perform the token exchange only
when an explicit confirmation flag is provided:

```powershell
python tools\excel_daily_poster\oauth2_exchange_code.py --code REPLACE_WITH_CODE --state REPLACE_WITH_RETURNED_STATE --exchange-live --confirm-token-exchange I_UNDERSTAND_THIS_EXCHANGES_OAUTH2_TOKEN
```

The helper posts to:

```text
https://api.x.com/2/oauth2/token
```

Payload:

- `grant_type=authorization_code`
- `client_id`
- `code`
- `redirect_uri`
- `code_verifier`
- `client_secret` is not sent in the body

Use `X_OAUTH2_CLIENT_SECRET` only if your OAuth 2.0 client type requires it.
When `X_OAUTH2_CLIENT_SECRET` is present, the helper sends client authentication
as:

```text
Authorization: Basic base64(client_id:client_secret)
```

This is also used by the refresh-token helper. Public clients without a client
secret keep the existing behavior: no Basic header and no client secret in the
body.
The code can expire quickly, so exchange it once after confirming the returned
`state`. The helper saves tokens to:

```text
data/oauth2_tokens.local.json
```

`data/oauth2_tokens.local.json` is ignored by Git. Access tokens can expire
quickly. With `offline.access`, a refresh token may be returned and can later be
used by the `oauth2_refresh_token.py` helper design to get a new access token.
The helper prints only success/failure and the save path; it does not print
access tokens, refresh tokens, authorization codes, or client secrets.

Never paste authorization codes, access tokens, refresh tokens, client secrets,
or token files into chat, logs, screenshots, reports, or Git-managed files.

If credentials are stored in `.env` later, keep these rules:

- Do not commit `.env` to Git.
- Keep `.env` outside screenshots, reports, and issue text.
- Validate every required value before creating the poster.
- Map SDK/HTTP failures to `XAuthError`, `XRateLimitError`, `XNetworkError`,
  `XTemporaryError`, `XConfigError`, or `XClientError`.
- The first real post must be a manual one-row test with human confirmation
  before and after the run.

The task runner remains dry-run-only. Do not change
`scripts/run_excel_daily_post.bat` to live mode without explicit approval.

## Manual One-Row Live Wrapper

`tools/excel_daily_poster/manual_live_post_once.py` is prepared for a future
manual one-row live test. It is not used by the scheduler and it is not called
by `scripts/run_excel_daily_post.bat`.

The wrapper requires the exact confirmation value below before it creates a real
poster:

```text
I_UNDERSTAND_THIS_POSTS_ONE_REAL_X_TWEET
```

Future command shape, after human approval and after credentials/dependencies
are handled:

```powershell
python tools\excel_daily_poster\manual_live_post_once.py --queue data\manual_account_posts.csv --confirm I_UNDERSTAND_THIS_POSTS_ONE_REAL_X_TWEET
```

The wrapper reads credentials only from already-provided environment variables:

- `X_API_KEY`
- `X_API_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_TOKEN_SECRET`

It does not create, edit, or load `.env`. If `.env` is used later, load it
outside this wrapper and keep it out of Git.

For a one-time Command Prompt session, set environment variables like this,
using real values only on your local machine:

```bat
set X_API_KEY=REPLACE_WITH_REAL_VALUE
set X_API_SECRET=REPLACE_WITH_REAL_VALUE
set X_ACCESS_TOKEN=REPLACE_WITH_REAL_VALUE
set X_ACCESS_TOKEN_SECRET=REPLACE_WITH_REAL_VALUE
```

Do not paste real keys into chat, logs, reports, screenshots, or Git-managed
files. Do not use this on a shared PC. Close the Command Prompt after the test
if you want to clear the session variables.

An example bat is available at:

```text
scripts\manual_live_post_once.example.bat
```

It contains placeholders and refuses to run as-is. To use it later, copy it to
the Git-ignored local filename below and edit only that local copy:

```text
scripts\manual_live_post_once.local.bat
```

When a live post succeeds, the selected row is updated with:

- `status=posted`
- `posted_at=<current timestamp>`
- `tweet_id=<returned id>`
- `error=`

After the first manual live test, immediately confirm these columns in
`data/manual_account_posts.csv`:

- `status`
- `posted_at`
- `tweet_id`
- `error`

When the poster raises an API/system error, the run stops without writing queued
row changes from that attempt.

## Manual One-Row OAuth 2.0 Live Test

After OAuth 2.0 token exchange succeeds and `data/oauth2_tokens.local.json`
exists, the manual wrapper can use `OAuth2UserContextXPoster` for one explicitly
confirmed run. This is still not automatic operation and is not connected to the
Windows scheduled runner.

Required local files and environment:

- `data/manual_account_posts.csv`
- `data/oauth2_tokens.local.json`
- `X_OAUTH2_CLIENT_ID`
- `X_OAUTH2_CLIENT_SECRET` only if your app/client requires it later

Run dry-run first:

```powershell
python tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv --dry-run
```

Then, only when the selected row is correct, run the OAuth 2.0 manual one-row
command:

```powershell
set X_OAUTH2_CLIENT_ID=REPLACE_WITH_REAL_VALUE
python tools\excel_daily_poster\manual_live_post_once.py --queue data\manual_account_posts.csv --use-oauth2 --confirm I_UNDERSTAND_THIS_POSTS_ONE_REAL_X_TWEET
```

The OAuth 2.0 path reads `access_token`, optional `refresh_token`, and `scope`
from:

```text
data/oauth2_tokens.local.json
```

Before posting, the wrapper refreshes OAuth 2.0 tokens by default. This handles
the common case where a previously successful OAuth 2.0 post later fails with
`401 Unauthorized` because the saved access token expired.

Refresh requirements:

- `access_token` must exist in `data/oauth2_tokens.local.json`
- `refresh_token` must exist in `data/oauth2_tokens.local.json`
- `X_OAUTH2_CLIENT_ID` must be set locally
- `X_OAUTH2_CLIENT_SECRET` may be needed for confidential clients

On refresh success, `data/oauth2_tokens.local.json` is updated with the new
`access_token`, `refresh_token`, `expires_in`, and `scope` before posting. The
post then uses the refreshed access token.

On refresh failure, posting does not start. Missing token files, missing
`access_token`, missing `refresh_token`, missing `X_OAUTH2_CLIENT_ID`, missing
required scopes, or refresh API errors stop with the X client error hierarchy.
Token values are not printed by the wrapper.

If the `refresh_token` itself expires or is revoked, run
`tools/excel_daily_poster/oauth2_local_callback.py` again and re-authorize the
target X account to create a new local token file. Before any automatic
operation, confirm by hand that a manual OAuth 2.0 post can refresh tokens and
then post exactly one row.

For diagnostics only, `--skip-oauth2-refresh` can use the saved access token
without refreshing first. Do not use this for normal operation after seeing a
token-expiry 401.

Do not paste token file contents, authorization codes, access tokens, refresh
tokens, or client secrets into chat, logs, screenshots, reports, or Git-managed
files.

The wrapper still requires the exact manual live confirmation string and still
posts at most one row per execution. API/system errors stop the run and do not
advance to the next candidate row.

`scripts/run_excel_daily_post.bat` remains dry-run-only. Do not add `--use-oauth2`
or live posting to scheduled scripts without a separate explicit approval.

## OAuth 2.0 Local Environment Setup

For repeated manual OAuth 2.0 runs, avoid typing `X_OAUTH2_CLIENT_ID`,
`X_OAUTH2_CLIENT_SECRET`, and `X_OAUTH2_REDIRECT_URI` into every PowerShell
session. Use either Windows user environment variables or a Git-ignored
`.local.bat` file.

Do not store these values in `.env` for this workflow. Do not paste Client
Secret, access tokens, refresh tokens, or token file contents into chat,
screenshots, GitHub, reports, issue text, or Git-managed files.

Option A: Windows user environment variables

Run these once in PowerShell or Command Prompt on your local PC, replacing only
the placeholder values locally:

```bat
setx X_OAUTH2_CLIENT_ID "REPLACE_WITH_REAL_VALUE"
setx X_OAUTH2_CLIENT_SECRET "REPLACE_WITH_REAL_VALUE"
setx X_OAUTH2_REDIRECT_URI "http://127.0.0.1:8765/callback"
```

After `setx`, close and reopen PowerShell or Command Prompt. Existing terminals
do not automatically receive the new environment variables.

Confirm only that the variable names exist. Do not print real secrets into logs
or screenshots. For example, avoid sharing command output that contains the
actual Client Secret.

Option B: Git-ignored `.local.bat`

For a local bat workflow, copy an example file and edit only the local copy:

```bat
copy scripts\run_excel_daily_post_oauth2_live.example.bat scripts\run_excel_daily_post_oauth2_live.local.bat
```

Then put local values only in:

```text
scripts\run_excel_daily_post_oauth2_live.local.bat
```

The pattern `*.local.bat` is ignored by Git, so this file is not meant to be
committed. Keep Client Secret values out of the example bat and out of all
Git-tracked files.

The existing scheduled dry-run runner must remain unchanged:

```text
scripts/run_excel_daily_post.bat
```

It should continue to use `--dry-run`. Do not register a live Task Scheduler
task until a separate explicit approval, and do not connect this legacy-account
queue to the three-account automation system.

## Daily Automation with Windows Task Scheduler

Full daily automation should be enabled only after OAuth 2.0 manual posting and
refresh-backed manual posting have both succeeded. Codex does not register the
task or perform a real post.

Before automation:

- OAuth 2.0 manual posting has succeeded.
- OAuth 2.0 refresh-backed posting has succeeded.
- `data/oauth2_tokens.local.json` exists and is ignored by Git.
- Windows environment variables are configured:
  - `X_OAUTH2_CLIENT_ID`
  - `X_OAUTH2_CLIENT_SECRET`
  - `X_OAUTH2_REDIRECT_URI`
- `data/manual_account_posts.csv` contains queued post text.
- Excel is closed.
- Dry-run selects the expected row.
- The one-post-per-day guard is active.

Create the local live runner:

```bat
copy scripts\run_excel_daily_post_oauth2_live.example.bat scripts\run_excel_daily_post_oauth2_live.local.bat
```

Edit only the `.local.bat` copy. It is ignored by Git. Do not place Client
Secret, token values, or local-only settings in the example bat or any
Git-tracked file.

Before registering a task, run the local bat manually once. After it runs:

- Confirm exactly one X post appeared.
- Confirm `status=posted` was written for one CSV row.
- Confirm `posted_at` and `tweet_id` were written.
- Confirm `error` is empty for that row.
- Optionally run it a second time on the same day to confirm the one-post-per-day
  guard stops before another post.

Registering the task is also local-only. Copy the example registration bat:

```bat
copy scripts\register_excel_daily_post_oauth2_live_task.example.bat scripts\register_excel_daily_post_oauth2_live_task.local.bat
```

The local registration bat creates:

- Task name: `X OAuth2 Daily Poster`
- Target: `scripts\run_excel_daily_post_oauth2_live.local.bat`
- Schedule: daily
- Start time: `21:30`

After registration, open Windows Task Scheduler and review the task manually.
Check the trigger time, target path, run history, and whether your PC should
wake from sleep to run the task. If wake-from-sleep is needed, enable the
appropriate Task Scheduler condition locally and confirm Windows power settings
allow wake timers.

In the Task Scheduler Conditions tab, confirm the setting equivalent to "Wake
the computer to run this task." If the PC wakes, posts, waits for
`timeout /t 1800 /nobreak`, and then still returns to sleep, review the Windows
AC sleep setting. Keeping the PC awake for 30 minutes after posting is handled by
the bat timeout; keeping it awake indefinitely on AC power requires changing the
Windows AC sleep timeout, such as `powercfg /change standby-timeout-ac 0`.

For the first several days, check:

- Task Scheduler history
- `logs/excel_daily_poster_oauth2_live.log`
- `data/manual_account_posts.csv`
- The X account's visible post

## Night Random Posting Window

The OAuth 2.0 live local bat is designed for a night posting window.

- Task Scheduler starts the bat at `21:30`.
- The bat waits for a random `0` to `120` minutes.
- The actual posting time is distributed between `21:30` and `23:30`.
- The random delay is logged, for example: `Random delay: 87 minutes`.
- The upper bound is controlled by `RANDOM_DELAY_MINUTES_MAX`.

Default:

```bat
set RANDOM_DELAY_MINUTES_MAX=120
```

The 21:30 to 23:30 window is recommended here because the post tone is better
matched to night usage, people often check X after work, and adult-leaning nuance
is less likely to feel out of place.

## Windows Sleep Settings for Daily Automation

The `X OAuth2 Daily Poster` task can wake the PC at `21:30`, wait a random
amount of time, post, and then keep the command window alive for 30 minutes with
`timeout /t 1800 /nobreak`. Depending on Windows power settings, the PC may still
return to sleep after the task finishes.

If you do not want the PC to return to sleep while connected to AC power, change
the Windows-wide AC sleep setting. This is not specific to the X poster task:
other tasks, including future `yokaze_daily`, `ai_pickup`, or
`new_account_daily` tasks, would also benefit from the PC staying awake on AC.
This change does not modify those systems' code.

Recommended GUI path:

1. Open Windows Settings.
2. Go to System.
3. Open Power & battery.
4. Open Screen and sleep.
5. For "When plugged in, put my device to sleep after", choose Never.
6. Leave battery sleep settings unchanged unless you deliberately want to change
   battery behavior.

Read-only command check:

```bat
scripts\check_power_settings.example.bat
```

This displays:

- Current active power plan
- AC and DC sleep settings inside `powercfg /query`
- Wake timer settings inside `powercfg /query`
- Active wake timers from `powercfg /waketimers`

It does not change settings.

Command to disable AC sleep:

```bat
powercfg /change standby-timeout-ac 0
```

Safe example:

```bat
copy scripts\set_ac_no_sleep.example.bat scripts\set_ac_no_sleep.local.bat
```

Edit only the `.local.bat` copy and set:

```bat
set ENABLE_AC_NO_SLEEP_EXAMPLE=YES
```

Then run the local copy. It prints the power settings before and after the
change. Administrator privileges may be required.

Restore AC sleep to 30 minutes:

```bat
powercfg /change standby-timeout-ac 30
```

Safe restore example:

```bat
copy scripts\restore_ac_sleep_30min.example.bat scripts\restore_ac_sleep_30min.local.bat
```

Edit only the `.local.bat` copy and set:

```bat
set RESTORE_AC_SLEEP_30MIN_EXAMPLE=YES
```

The initial implementation changes only:

```bat
standby-timeout-ac
```

It does not change battery/DC sleep timeout. It also does not change hibernate
timeout. If hibernation later causes problems, review `hibernate-timeout-ac`
separately before changing it.

Important cautions:

- AC no-sleep is a Windows-wide setting, not an X-poster-only setting.
- The PC may stay awake all night while plugged in.
- Consider electricity cost, heat, screen lock, and physical security.
- Modern Standby and manufacturer power-management tools can behave
  differently from classic sleep settings.
- Confirm actual behavior for one or two nights by checking Task Scheduler
  history, Windows sleep behavior, and `logs/excel_daily_poster_oauth2_live.log`.

## One Post Per Day Guard

The manual live wrapper checks `data/manual_account_posts.csv` before creating a
poster or refreshing OAuth 2.0 tokens. If a row with `status=posted` already has
today's local date in `posted_at`, the run stops with:

```text
Today already has a posted row. Skip posting.
```

When this happens:

- No X API post is attempted.
- OAuth 2.0 refresh is not attempted.
- The CSV is not updated.
- The next candidate row is not selected.

This protects against double posting if Task Scheduler runs twice or if the
local live bat is accidentally launched again on the same day.

## CSV Write Safety and Recovery

Before OAuth 2.0 refresh or X API posting, the manual live wrapper checks that
`data/manual_account_posts.csv` is writable. This is meant to catch cases where
Excel or OneDrive is holding the CSV open. If the check fails, the run stops
before refresh and before posting.

Typical preflight error:

```text
Post queue is not writable. Close Excel and pause OneDrive sync before posting.
```

If a stale temp file exists, the run also stops before posting:

```text
data/manual_account_posts.csv.tmp
```

Do not delete a `.tmp` file blindly after a failure. First compare it with
`data/manual_account_posts.csv` and confirm whether it contains a needed
post-success update.

If X posting succeeds but CSV replacement fails afterward, the log writes a
strong recovery warning with only operational metadata:

```text
excel_daily_poster_csv_update_failed_after_post row_number=<row> posted_at=<timestamp> tweet_id=<id> recovery_required=true
```

No access token, refresh token, Client Secret, or full post text is logged.

Manual recovery steps after a post succeeded but CSV was not updated:

1. Close Excel.
2. Pause or wait for OneDrive sync.
3. Open `logs/excel_daily_poster_oauth2_live.log`.
4. Find `row_number`, `posted_at`, and `tweet_id` in the recovery warning.
5. Open `data/manual_account_posts.csv`.
6. On that row, set `status` to `posted`.
7. Set `posted_at` to the logged timestamp.
8. Set `tweet_id` to the logged id.
9. Clear `error`.
10. Save as CSV UTF-8 and close Excel.
11. If `data/manual_account_posts.csv.tmp` exists, inspect it before deleting it.

Operational rules:

- Run at most once per day.
- Keep `scripts/run_excel_daily_post.bat` as dry-run-only.
- Add new post text in CSV UTF-8 format.
- Close Excel before running.
- Re-authorize with `oauth2_local_callback.py` if refresh tokens expire.
- Never paste token values or Client Secret into chat, logs, screenshots,
  GitHub, reports, or Git-tracked files.
- Keep this legacy-account queue separate from `yokaze_daily`, `ai_pickup`,
  `new_account_daily`, and every other three-account automation path.

## Similar Recent Post Guard

Even with 500 to 600 queued posts, similar drafts can appear close together in
the CSV. To reduce the risk of posts looking duplicated on X, the manual OAuth
2.0 live path checks the selected candidate against recently posted rows before
OAuth 2.0 refresh or X API posting.

Default behavior:

- Enabled by default.
- Lookback window: `30` days.
- Similarity threshold: `0.85`.
- Exact matches are always blocked.
- Only rows with `status=posted` are comparison targets.
- `posted_at` or `last_posted_at` must contain a date within the lookback
  window.
- Posted rows with blank dates are ignored by this guard.
- The selected candidate is checked only against local CSV history.
- No external API, LLM, or network call is used.

Settings:

```bat
set SIMILAR_RECENT_POST_CHECK_ENABLED=YES
set SIMILAR_RECENT_POST_DAYS=30
set SIMILAR_RECENT_POST_THRESHOLD=0.85
```

When a similar recent post is detected, the run stops with:

```text
reason_code=similar_recent_post_detected
```

When blocked:

- OAuth 2.0 refresh is not attempted.
- X API posting is not attempted.
- The next candidate row is not selected.
- The CSV is not marked as `posted`.
- The full post text and token values are not logged.

The similarity check uses local string normalization and `difflib`-style text
similarity. It is intentionally simple and not perfect: false positives and
misses are possible. Confirm behavior with dry-run/manual checks first, and
adjust `SIMILAR_RECENT_POST_THRESHOLD` only after reviewing examples. A lower
threshold blocks more aggressively; a higher threshold blocks fewer posts.

## After Manual OAuth 2.0 Success

After several successful manual one-row OAuth 2.0 tests, prepare automation
gradually. Do not change the existing dry-run runner first.

Keep this file unchanged until a separate approval:

```text
scripts/run_excel_daily_post.bat
```

It must continue to call:

```text
daily_post.py --queue data\manual_account_posts.csv --dry-run
```

The OAuth 2.0 live runner is provided only as an example:

```text
scripts\run_excel_daily_post_oauth2_live.example.bat
```

It refuses to run as-is. For a real local run later, copy it to the Git-ignored
local filename:

```text
scripts\run_excel_daily_post_oauth2_live.local.bat
```

Then edit only the `.local.bat` copy. Required local inputs:

- `data/manual_account_posts.csv`
- `data/oauth2_tokens.local.json`
- `X_OAUTH2_CLIENT_ID`

The token file must stay local and ignored by Git. Do not paste token contents
or client IDs into chat, logs, screenshots, reports, or Git-managed files.

Operational rules before Task Scheduler:

1. Run dry-run and confirm the selected row by eye.
2. Run the OAuth 2.0 manual/live local bat by hand.
3. Confirm exactly one row changed to `posted`.
4. Confirm `posted_at` and `tweet_id` were written.
5. Confirm `error` is empty for the posted row.
6. Repeat manual daily runs for several days.
7. Register Task Scheduler only after those manual runs are stable.

The intended cadence is once per day. Do not run the live local bat repeatedly
against the same queue unless you deliberately intend to post another eligible
row. Do not connect this legacy-account queue to `yokaze_daily`, `ai_pickup`,
`new_account_daily`, or any other three-account automation path.

Do not reuse the three-account runtime for this queue unless the account
boundary is redesigned deliberately.
