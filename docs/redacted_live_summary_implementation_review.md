# RedactedLiveSummary Implementation Review

Date: 2026-06-05

This is a design review only. It does not implement `RedactedLiveSummary`,
enable live mode, perform HTTP communication, call the X API, use an HTTP
library, read credentials, create or modify `.env`, read environment variables,
fetch real data, or post to X.

## Review Decision

Implementation readiness: `NEEDS_REVIEW`

Live output status: `BLOCKED`

Recommended first implementation location:

```text
x_auto_ops/redacted_live_summary.py
```

The first implementation should be a small backend-only diagnostic value object
with an allowlisted dictionary serializer and a bounded one-line debug view. It
must not write JSON files, CSV, raw reports, frontend data, or live diagnostics
exports.

## Placement Review

| Candidate | Classification | Review |
| --- | --- | --- |
| `x_auto_ops/redacted_live_summary.py` | `READY` | matches the current flat module structure, makes the security boundary visible, and avoids adding a package before multiple diagnostics models exist |
| `x_auto_ops/diagnostics/redacted_live_summary.py` | `NEEDS_REVIEW` | good future home if several diagnostic schemas appear, but currently adds package structure and ownership decisions without enough reuse |
| `x_auto_ops/models/redacted_live_summary.py` | `BLOCKED` | the object includes redaction, safe-debug, and report-boundary behavior, so placing it in a generic model package could hide its security-specific responsibility |

Recommendation:

- use `x_auto_ops/redacted_live_summary.py` for the first implementation
- reconsider a `diagnostics` package only after multiple redacted diagnostic
  schemas exist
- do not place it in a generic `models` package for the first implementation

## Data Structure Review

Proposed object:

```text
RedactedLiveSummary
```

Field classification:

| Field | Classification | Notes |
| --- | --- | --- |
| `diagnostics_version` | `required` | controlled schema version |
| `status` | `required` | controlled enum |
| `request_id` | `required` | generated internal non-sensitive identifier |
| `endpoint_name` | `required` | controlled logical endpoint name |
| `method` | `required` | controlled method; expected `GET` |
| `status_code` | `optional` | absent before response or for local/preflight failure |
| `query_length` | `required` | integer length only |
| `result_count` | `required` | response result count, default `0` |
| `fetched_count` | `optional` | keep only if distinct from result count |
| `normalized_post_count` | `required` | normalizer output count, default `0` |
| `partial_result` | `required` | boolean, default `false` |
| `stop_reason` | `required` | controlled enum |
| `rate_limited` | `required` | boolean, default `false` |
| `retryable` | `required` | diagnostic boolean only |
| `retry_after_seconds` | `optional` | non-negative integer only |
| `pagination_used` | `required` | boolean, expected `false` for first live test |
| `next_token_present` | `required` | boolean only, never token value |
| `metrics_missing_count` | `required` | aggregate count, default `0` |
| `score_source` | `remove_candidate` | scoring is disabled in the first live test |
| `execution_time_ms` | `required` | non-negative integer |
| `rollback_completed` | `required` | boolean |

Review decisions:

- required count fields should default to `0`
- required boolean fields should have explicit values
- optional values should serialize as `null` or be omitted according to the
  final serialization policy
- `score_source` should be removed from the first implementation
- `fetched_count` remains `NEEDS_REVIEW` because its distinction from
  `result_count` must be defined

## `safe_debug_summary()` Review

Candidate formats:

| Format | Readability | Log Use | Report Use | Redaction Risk | Future CI Use |
| --- | --- | --- | --- | --- | --- |
| allowlisted dictionary | high for structured inspection | good with controlled serializer | high | lower because fields are explicit | high |
| short one-line string | high for humans | excellent | good for compact reports | higher if manually concatenated | medium |

Recommendation:

- canonical safe representation: allowlisted dictionary
- human debug representation: bounded one-line string generated only from the
  canonical safe dictionary
- report representation: formatted allowlisted dictionary or bounded summary,
  never the object's raw internal state

Proposed method boundaries:

```text
to_safe_dict() -> dict[str, safe scalar]
safe_debug_summary() -> str
```

`safe_debug_summary()` rules:

- generate from `to_safe_dict()`
- use only allowlisted keys
- use scalar values only
- never use generic object `repr`
- never include query text, post text, IDs from X, header values, raw JSON,
  raw bodies, credentials, or raw exceptions
- truncate or fail closed if the size limit would be exceeded

## JSON Serialization Policy

Reviewed options:

| Option | Classification | Policy |
| --- | --- | --- |
| serialize allowlisted summary to an in-memory JSON-compatible dict | `READY` | supports tests and controlled report formatting |
| embed allowlisted summary in a redacted report | `NEEDS_REVIEW` | allowed only after report writer enforces schema and size limits |
| save standalone summary JSON file | `BLOCKED` for first live test | creates a new live diagnostics persistence surface |
| allow diagnostics export | `BLOCKED` | increases leakage and retention risk |
| serialize raw object state | `BLOCKED` | could expose future non-allowlisted fields |

Recommendation:

- permit only `to_safe_dict()` as the canonical serialization boundary
- do not write standalone JSON during the first live test
- permit report embedding only after allowlist and size tests exist
- do not add diagnostics export in the first implementation

## Report Output Policy

The report may contain only the allowlisted summary representation.

Allowed:

- controlled field names
- counts
- booleans
- controlled enums
- numeric timing
- numeric status code

Blocked:

- raw object dumps
- raw JSON
- raw request or response
- raw headers or header values
- query text
- post text
- usernames
- author IDs
- post IDs
- token values
- credential-shaped strings

Reports must not become an alternate live-data storage mechanism.

## Summary Size Limits

Recommended first implementation limits:

| Limit | Proposed Value | Reason |
| --- | ---: | --- |
| maximum schema fields | 24 | allows reviewed fields with small version growth |
| maximum `safe_debug_summary()` length | 1,024 characters | keeps logs compact and bounded |
| maximum serialized safe dictionary JSON size | 4,096 bytes | prevents accidental large values |
| maximum report-embedded summary block | 4,096 characters | matches bounded diagnostics intent |
| maximum string field length | 64 characters | enough for controlled enums and internal request IDs |

Fail-closed behavior:

- reject unreviewed fields
- reject nested objects and lists
- reject strings over the per-field limit
- reject summaries over the total size limit
- never truncate a suspicious value into an apparently safe value
- a size validation failure should produce a controlled `blocked` summary
  without including the rejected value

## Error Summary Integration

Error types should map into the same summary object using controlled
`status`, `stop_reason`, `status_code`, `retryable`, rate-limit fields, and
rollback state.

| Error | Summary Integration |
| --- | --- |
| `auth_error` | `status=failed`, optional 401/403 status, `stop_reason=auth_error`, `retryable=false` |
| `timeout` | `status=failed`, no status required, `stop_reason=timeout`, `retryable=true` |
| `network_error` | `status=failed`, no status required, `stop_reason=network_error`, `retryable=true` |
| `rate_limited` | `status=failed`, status 429, `rate_limited=true`, controlled retry-after seconds, `retryable=true` |
| `server_error` | `status=failed`, 5xx status, `stop_reason=server_error`, `retryable=true` |
| `client_error` | `status=failed`, 4xx status, `stop_reason=client_error`, `retryable=false` |
| `json_parse_error` | `status=failed`, `stop_reason=json_parse_error`, `retryable=false` |
| `schema_error` | `status=failed`, `stop_reason=schema_error`, `retryable=false`, aggregate missing count only |

Error integration rules:

- do not add an `error_message` field for the first implementation
- do not include raw exception text
- do not include response bodies
- do not include header values
- do not trigger retry or pagination from summary creation
- set `rollback_completed` only after rollback verification finishes

## Gap Analysis

### READY

- recommended top-level module location
- core field allowlist
- required/optional/remove-candidate classification
- canonical safe dictionary direction
- bounded one-line debug direction
- no standalone JSON export policy
- proposed summary size limits
- controlled error-to-summary mapping

### NEEDS_REVIEW

- final `fetched_count` semantics
- whether optional fields serialize as `null` or are omitted
- exact controlled enum definitions
- report writer integration
- implementation-time validation error type
- request ID generation strategy
- whether 4,096-byte JSON limit is sufficient
- whether the schema field limit should remain 24
- date-stable dry-run pipeline fixtures or an injected test clock; existing
  fixed fixture dates can fall outside genre `days_back` windows

### BLOCKED

- implementing before an explicit implementation task
- standalone live summary JSON files
- diagnostics export
- generic object serialization
- raw error messages
- raw response/header/query/post/user/ID output
- frontend or screenshot exposure
- summary-triggered retry or pagination

## Implementation Review Checklist

- place the first implementation in `x_auto_ops/redacted_live_summary.py`
- define controlled enums before accepting arbitrary strings
- implement an explicit field allowlist
- implement `to_safe_dict()` as the canonical boundary
- generate `safe_debug_summary()` only from the safe dictionary
- enforce field count, string length, debug length, and JSON size limits
- reject nested values and unreviewed fields
- remove `score_source` from the first implementation
- decide `fetched_count` semantics
- add tests for every blocked field and output surface
- add tests for every error summary mapping
- keep live mode blocked

## Safety Confirmation

This review does not create the model, serializer, report writer, or tests. It
does not approve live output or live API execution.
