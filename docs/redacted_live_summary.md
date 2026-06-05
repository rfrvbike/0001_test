# RedactedLiveSummary

`RedactedLiveSummary` is a backend-only diagnostic value object for a future
first-live recent-search connectivity check. It does not perform HTTP, read
credentials, enable live mode, trigger retry, paginate, score posts, or persist
live data.

## Location

```text
x_auto_ops/redacted_live_summary.py
```

## Fields

Required fields:

- `diagnostics_version`
- `status`
- `request_id`
- `endpoint_name`
- `method`
- `query_length`
- `result_count`
- `normalized_post_count`
- `partial_result`
- `stop_reason`
- `rate_limited`
- `retryable`
- `pagination_used`
- `next_token_present`
- `metrics_missing_count`
- `execution_time_ms`
- `rollback_completed`

Optional fields:

- `status_code`
- `retry_after_seconds`
- `fetched_count`

`score_source` is intentionally not implemented.

## Validation

Construction fails closed when:

- a required text field is empty
- a required text field contains a credential marker
- a string field exceeds 64 characters
- a count or timing value is negative
- a required boolean is not a boolean
- an optional integer is negative

Validation errors do not echo rejected sensitive values.

## `to_safe_dict()`

`to_safe_dict()` returns only the reviewed allowlist. Values are JSON-compatible
scalars and optional fields are represented as `None` when absent.

The method rejects nested collections and credential-shaped values. It does not
return query text, post text, usernames, author IDs, post IDs, headers, raw
responses, raw JSON, or credentials.

## `safe_debug_summary()`

`safe_debug_summary()`:

- is generated only from `to_safe_dict()`
- returns compact JSON on one line
- sorts keys for stable output
- renders `next_token_present` as `next_cursor_present` so debug output does
  not contain a credential marker word
- is limited to 1,024 characters
- fails closed if a credential marker is detected

It is suitable for controlled debug or redacted report embedding after the
calling surface is separately approved.

## Redaction Boundary

The summary must never contain:

- authorization values
- bearer values
- API keys
- tokens
- secrets
- cookies
- query text
- post text
- usernames
- author IDs
- post IDs
- header values
- raw response data

Standalone JSON export, CSV output, frontend display, retry triggering, and
pagination triggering remain outside this model.

## Mock Pipeline Integration

The mock-only `run_dry_run_recent_search_pipeline(...)` creates one
`RedactedLiveSummary` after normalization and ranking. It is available as:

```python
result.redacted_live_summary
```

The CLI prints only `safe_debug_summary()`. The mock pipeline report embeds the
same safe one-line summary and does not expose the query text, post text,
username, author ID, post ID, raw response, or raw JSON.

The summary is not added to the ranked-post CSV. The CSV remains a post-ranking
artifact, while the diagnostic summary remains a separate safe diagnostic
surface.

Mock status mapping:

- normal result: `status=success`, `stop_reason=completed`
- partial fixture: `status=partial`, `stop_reason=partial_result`
- rate-limited fixture: `status=rate_limited`, `stop_reason=rate_limited`,
  `retryable=true`

`pagination_used` remains false because the dry-run pipeline sends one mock
request only. `next_token_present` records whether a cursor was returned without
exposing its value.

## Error Summary Mapping

`build_redacted_error_summary(...)` converts a mapped `HttpErrorInfo` into a
safe `RedactedLiveSummary` for failed mock or future first-live checks.

The helper records only stable metadata:

- `status=error`
- `stop_reason=<error_type>`
- `status_code`
- `retryable`
- `retry_after_seconds`
- `partial_result`
- zero result, fetched, normalized-post, and metrics-missing counts

Supported error types:

- `auth_error`
- `timeout`
- `network_error`
- `rate_limited`
- `server_error`
- `client_error`
- `json_parse_error`
- `schema_error`
- `disabled_http_client`

Raw exception messages, response bodies, response headers, query text, post
text, usernames, author IDs, post IDs, authorization values, bearer values,
API keys, tokens, secrets, cookies, raw JSON, and raw responses are not copied
into the summary.

Example:

```python
from x_auto_ops.http_error_mapping import map_http_error
from x_auto_ops.redacted_live_summary import build_redacted_error_summary

error = map_http_error(status_code=429, headers={"Retry-After": "90"})
summary = build_redacted_error_summary(error, query_length=88)

safe_data = summary.to_safe_dict()
debug_line = summary.safe_debug_summary()
```

## Example

```python
from x_auto_ops.redacted_live_summary import RedactedLiveSummary

summary = RedactedLiveSummary(
    diagnostics_version="1",
    status="success",
    request_id="request-001",
    endpoint_name="recent_search",
    method="GET",
    query_length=24,
    result_count=2,
    normalized_post_count=2,
    partial_result=False,
    stop_reason="completed",
    rate_limited=False,
    retryable=False,
    pagination_used=False,
    next_token_present=False,
    metrics_missing_count=0,
    execution_time_ms=120,
    rollback_completed=False,
    status_code=200,
)

safe_data = summary.to_safe_dict()
debug_line = summary.safe_debug_summary()
```
