# Redacted Live Summary Schema Review

Date: 2026-06-05

This is a design review only. It does not enable live mode, perform HTTP
communication, call the X API, use `requests`, use `httpx`, use `urllib`, read
API keys, read tokens, read cookies, read authorization values, create or
modify `.env`, read environment variables, read real credentials, fetch real
data, or post to X.

## Review Decision

Summary schema status: `NEEDS_REVIEW`

Live output status: `BLOCKED`

The first live connectivity test may produce only a redacted diagnostic
summary. The summary exists to prove the request/response path behaved as
expected without persisting raw response data, post text, identities, credentials
or header values.

## Live Summary Responsibilities

The Live Summary is responsible for:

- confirming the first live connectivity result safely
- proving credential leak protection is active
- giving enough retry diagnostics to explain whether a failure was retryable
- giving enough pagination diagnostics to prove pagination did not run
- giving enough rate-limit diagnostics to classify a rate-limit response
- confirming the normal response path reached ResponseNormalizer
- recording a rollback completion signal when applicable

The Live Summary is not responsible for:

- displaying raw responses
- displaying raw JSON
- displaying complete post text
- displaying usernames, author IDs, or post ID lists
- displaying credentials
- displaying authorization headers
- displaying header values
- saving CSV
- preserving real data for analysis
- computing score
- performing genre classification
- triggering retry or pagination

## Output Field Classification

| Field | Classification | Notes |
| --- | --- | --- |
| `request_id` | `SAFE` | generated internal ID only; must not contain query or credentials |
| `endpoint_name` | `SAFE` | use logical name such as `recent_search` |
| `method` | `SAFE` | expected value is `GET` |
| `status_code` | `SAFE` | numeric status is acceptable |
| `query_length` | `SAFE` | length only; never query text |
| `result_count` | `SAFE` | count only |
| `fetched_count` | `SAFE` | count only |
| `partial_result` | `SAFE` | boolean only |
| `stop_reason` | `SAFE` | controlled enum only |
| `rate_limited` | `SAFE` | boolean only |
| `retryable` | `SAFE` | boolean only |
| `retry_after_seconds` | `SAFE` | numeric seconds only |
| `pagination_used` | `SAFE` | boolean only; expected `false` for first live test |
| `next_token_present` | `SAFE` | boolean only; never token value |
| `metrics_missing_count` | `SAFE` | aggregate count only |
| `score_source` | `NEEDS_REVIEW` | allowed only if scoring stays disabled and value is enum-like |
| `execution_time_ms` | `SAFE` | numeric duration only |

Additional recommended fields:

| Field | Classification | Notes |
| --- | --- | --- |
| `diagnostics_version` | `SAFE` | schema version string |
| `rollback_completed` | `SAFE` | boolean only |
| `normalized_post_count` | `SAFE` | count only |
| `header_names` | `NEEDS_REVIEW` | names only; no values; omit if too noisy |
| `missing_field_names` | `NEEDS_REVIEW` | controlled normalizer field names only |

## Explicitly Blocked Output

The summary must never include:

- `Authorization`
- `Bearer`
- `API_KEY`
- `TOKEN`
- `SECRET`
- `COOKIE`
- `CredentialBundle` content
- header values
- raw request headers
- raw response headers
- raw response body
- raw JSON
- full query text
- full post text
- usernames
- author IDs
- post ID lists
- `next_token` value
- credential storage location
- raw exception messages before redaction

For first-live diagnostics, even identifiers that are not credentials should be
treated as non-output data. The first test verifies connectivity, not content
analysis.

## Summary Schema Proposal

Proposed shape:

```text
RedactedLiveSummary(
  diagnostics_version: str,
  status: str,
  request_id: str,
  endpoint_name: str,
  method: str,
  status_code: int | None,
  query_length: int,
  result_count: int,
  fetched_count: int,
  normalized_post_count: int,
  partial_result: bool,
  stop_reason: str,
  rate_limited: bool,
  retryable: bool,
  retry_after_seconds: int | None,
  pagination_used: bool,
  next_token_present: bool,
  metrics_missing_count: int,
  score_source: str | None,
  execution_time_ms: int,
  rollback_completed: bool,
)
```

`status` should be a controlled enum:

- `success`
- `failed`
- `rolled_back`
- `blocked`

`stop_reason` should be a controlled enum:

- `completed`
- `empty_result`
- `auth_error`
- `timeout`
- `network_error`
- `rate_limited`
- `server_error`
- `client_error`
- `json_parse_error`
- `schema_error`
- `preflight_failed`
- `rollback_required`

## `safe_debug_summary()` Proposal

`safe_debug_summary()` should return a compact text or dictionary view using
only allowlisted fields.

Allowed example:

```text
status=failed endpoint=recent_search method=GET status_code=429
query_length=42 result_count=0 rate_limited=true retryable=true
retry_after_seconds=60 pagination_used=false next_token_present=false
rollback_completed=true
```

The method must not include:

- query text
- post text
- usernames
- author IDs
- post IDs
- header values
- raw response text
- raw JSON
- credential-shaped strings

## Error Summary Policy

| Error | Allowed Summary | Blocked Details |
| --- | --- | --- |
| `auth_error` | `status_code`, `stop_reason=auth_error`, `retryable=false`, rollback flag | Authorization value, credential source, raw auth response |
| `timeout` | `stop_reason=timeout`, `retryable=true`, timeout class if controlled | socket details, raw exception with host/query/headers |
| `network_error` | `stop_reason=network_error`, `retryable=true` | raw network exception before redaction |
| `rate_limited` | `status_code=429`, `rate_limited=true`, `retry_after_seconds`, `retryable=true` | full headers, reset token-like values, raw body |
| `server_error` | `status_code`, `stop_reason=server_error`, `retryable=true` | raw response body |
| `client_error` | `status_code`, `stop_reason=client_error`, `retryable=false` | query text, raw body, raw request |
| `json_parse_error` | `stop_reason=json_parse_error`, `retryable=false`, body length if needed | raw body, raw JSON fragment |
| `schema_error` | `stop_reason=schema_error`, `retryable=false`, controlled missing-field count | raw JSON, post IDs, author data, post text |

Every error summary must be redacted before report/debug/exception surfaces are
generated. No error summary may trigger retry or pagination during the first
live test.

## Redaction Boundary

Blocked output surfaces:

- report
- CSV
- debug log
- exception
- retry metadata
- pagination metadata
- fixtures
- screenshots
- frontend

The same blocked fields apply to all surfaces. There is no exception for debug
mode. Debug output may contain counts, booleans, enums, and timing, but not raw
values.

## Gap Analysis

### READY

- existing redaction policy
- credential marker denylist
- request/query length reporting
- status/count/boolean diagnostics
- rollback setting from the minimal live test plan
- ResponseNormalizer missing-field aggregate concept
- retry and pagination metadata boundaries

### NEEDS_REVIEW

- final `RedactedLiveSummary` code location
- exact schema serialization format
- whether `header_names` should be included
- whether `missing_field_names` should be included
- whether `score_source` is needed when scoring is disabled
- whether empty result can be summarized as success
- maximum allowed `safe_debug_summary()` length

### BLOCKED

- writing live summaries before live implementation is approved
- including raw response data
- including post text, usernames, author IDs, or post ID lists
- including header values or credentials
- writing live data to CSV
- exposing live summary data in frontend or screenshots
- using the summary to trigger retry or pagination

## Safety Confirmation

This review defines the safe output boundary only. It does not implement
summary generation and does not approve live API execution.

## Implementation Review Reference

The implementation placement, data structure, serialization, size limit, report
boundary, and error integration review is recorded in
`docs/redacted_live_summary_implementation_review.md`.

The recommended first implementation location is
`x_auto_ops/redacted_live_summary.py`. The canonical serialization boundary
should be an explicit allowlisted `to_safe_dict()`, with
`safe_debug_summary()` generated only from that safe dictionary. Standalone
JSON export remains blocked for the first live test.
