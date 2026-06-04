# Git Push Safety Checklist

## Purpose

Use this checklist immediately before pushing to GitHub so an unintended HEAD
move, staged diff, or sensitive value does not get shipped by accident.

This document is especially important for live, credential, HTTP, transport,
OAuth, X API, and stock-analysis related commits.

## Required Checks Before Push

Run these commands before every push:

```powershell
git status --short
git diff --cached --stat
git log -1 --oneline
git rev-parse HEAD
git ls-remote origin main
```

Confirm all of the following:

- The current HEAD is the exact commit intended for push.
- `git diff --cached --stat` is empty unless the staged diff is intentionally
  part of the push.
- No unreviewed commit appeared on top of the intended commit.
- The remote `main` hash is understood before pushing.
- Existing untracked files are not being implicitly committed.

## Stop Conditions

Do not push if any of these are true:

- HEAD differs from the already-reviewed commit.
- A staged diff remains unexpectedly.
- A new commit appeared on HEAD without review.
- Tests failed.
- An API key, token, cookie, authorization value, bearer value, secret, or
  `.env` value may be present.
- Live HTTP, live transport, credential loading, or API calls may have been
  enabled unintentionally.
- X write actions, posting, follow, like, repost, delete, DM, media upload, or
  profile update might be reachable.
- The change may expose credentials to frontend code, localStorage, responses,
  logs, reports, or documentation.
- You are unsure whether the pushed commit set is the intended commit set.

## Required Checks For Live / Credential / HTTP Commits

For commits touching live mode, credential handling, HTTP transport, or X API
design, verify all of the following:

- Live HTTP communication remains disabled unless explicitly approved.
- `live_mode=true` alone does not unlock network communication.
- Credential loading remains fake-only or fail-closed unless explicitly
  approved.
- Real credential loaders and storage adapters do not read real values.
- `.env`, `os.environ`, `process.env`, or environment reads are not introduced.
- API keys, tokens, cookies, authorization headers, bearer values, and secrets
  do not appear as real values.
- Credentials are not sent to frontend code, localStorage, responses, logs,
  reports, or docs.
- X/Twitter write APIs are not enabled.
- Read-only API paths do not perform real network calls unless explicitly
  approved.
- Preflight validation and endpoint allowlists still run before transport.
- Fail-closed behavior remains the default.

Useful grep pattern for suspicious markers:

```powershell
git show HEAD | rg "JQUANTS_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI|API_KEY|TOKEN|SECRET|x-api-key|Authorization|Bearer|Cookie|credential|credentials|\.env|process\.env|localStorage|console\.log|console\.error|live_mode|LIVE_MODE|tweet.write|POST /2/tweets|DM|delete|follow|like|repost|media upload|profile update|requests\.|fetch\(|httpx|urllib|aiohttp|https://|http://"
```

Matches are not automatically unsafe. Review the context and confirm whether
they are safe policy text, test assertions, documentation, or real executable
behavior.

## Push Command

Push only after the checks above pass:

```powershell
git push origin main
```

Do not use:

- `git add .`
- `git add -A`
- `git commit -am`
- broad staging of unrelated files
- destructive cleanup commands while unsure

## Required Checks After Push

Run these commands after a successful push:

```powershell
git log -1 --oneline
git rev-parse HEAD
git ls-remote origin main
git status --short
```

Confirm:

- `HEAD` and remote `main` point to the expected commit.
- The GitHub commit URL opens for the pushed commit.
- Any remaining local changes are known and were not part of the push.

## Incident Handling

If an unintended commit was pushed:

1. Stop further pushes.
2. Inspect the unintended commit immediately.
3. Confirm whether it contains code changes, credentials, or live/API enablement.
4. Run the suspicious-marker grep against the unintended commit.
5. Report the exact pushed hash and affected files.
6. If no sensitive or live-enabling change exists, document the incident and
   proceed with a corrected safety process.
7. If sensitive material or live behavior was exposed, do not casually revert
   only the visible file. Plan invalidation, rotation, removal, and follow-up
   history handling with explicit approval.

When in doubt, do not push.
