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
