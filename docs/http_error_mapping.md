# HTTP Error Mapping

This document records the mock-only HTTP timeout/error mapping skeleton for
future X recent-search reads. No HTTP communication, credential lookup, token
lookup, cookie access, `.env` read, or posting behavior is implemented.

## Implementation Point

```text
x_auto_ops/http_error_mapping.py
```

Public API:

```text
map_http_error(...) -> HttpErrorInfo
```

## HttpErrorInfo

Fields:

- `error_type`
- `status_code`
- `retryable`
- `retry_after_seconds`
- `message`
- `redacted_message`
- `partial_result`

`message` and `redacted_message` are both redacted before returning. Raw
credential-shaped text must not leave this boundary.

## Error Types

| error_type | Retryable | partial_result | Notes |
| --- | --- | --- | --- |
| `timeout` | yes | yes | Future request timed out |
| `network_error` | yes | yes | DNS/connect/reset style failures |
| `auth_error` | no | no | 401/403 style failures |
| `rate_limited` | yes | yes | 429 or retry headers |
| `server_error` | yes | yes | 5xx failures |
| `client_error` | no | no | 4xx other than 401/403/429 |
| `json_parse_error` | no | no | Response body could not be parsed |
| `schema_error` | no | no | Parsed body shape was unexpected |
| `disabled_http_client` | no | no | Current fail-closed client |

## Retry-after Policy

Rate-limit mapping uses `parse_rate_limit_headers(...)`.

Sources:

- `Retry-After`
- `x-rate-limit-reset`
- `x-rate-limit-remaining`
- `status_code=429`

When `error_type=rate_limited`, `retry_after_seconds` is preserved when it can
be parsed. Retry scheduling remains outside error mapping.

## Redaction Policy

All error messages are passed through `redact_sensitive_text(...)`.

Credential-shaped marker text such as API key, token, bearer, secret, cookie,
and authorization wording must not appear in:

- `message`
- `redacted_message`
- exceptions rendered from mapped errors
- reports
- debug logs

## Retry Queue Relationship

`HttpErrorInfo` does not enqueue retries by itself. The future controller should
translate retryable rate-limit errors into `RetryTask` records:

```text
HttpErrorInfo(rate_limited)
-> RetryQueue.enqueue(query, retry_after_seconds, retry_count)
```

The mapping layer remains pure and performs no sleeps, network calls, file
reads, or queue writes.
