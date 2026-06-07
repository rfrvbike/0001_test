# X API Buzz System Migration Notice

## Status

The X API buzz post extraction system has been split into a dedicated repository.

New repository:

https://github.com/rfrvbike/x-api-buzz-system

## Purpose

The new repository is used for:

- read-only X API buzz post collection
- reference post analysis
- scoring / reporting
- mock and dry-run first development
- live API preparation with strict safety gates

## Do Not Continue X API Buzz Development Here

Do not continue new X API buzz post extraction development in this repository unless explicitly required for migration cleanup.

Use the dedicated repository instead:

https://github.com/rfrvbike/x-api-buzz-system

## Still Out of Scope

The new repository does not include:

- Excel daily poster
- manual live posting
- OAuth local token operation
- dating_assistant
- stock analysis system
- server / stock analyzer
- Discord export
- real credentials
- local private data

## Safety Notes

- Do not copy `.env`, tokens, secrets, credentials, OAuth local JSON, real CSVs, local data, or private data.
- Do not mix dating_assistant or stock analysis changes into X API buzz system work.
- Do not enable LiveMode or real X API access without explicit approval.

## Migration State

Initial skeleton, safe copy, test triage, test fixes, and README/docs/reports organization have been completed in the new repository.

Current new-repo baseline:

- Repository: https://github.com/rfrvbike/x-api-buzz-system
- Tests: `Ran 186 tests / OK`
