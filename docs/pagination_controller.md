# Pagination Controller and Retry Policy

This document records the mock-only pagination controller and max retry policy
skeleton for future X recent-search reads. No HTTP communication, request
execution, credential lookup, `.env` read, or posting behavior is implemented.

## Implementation Points

```text
x_auto_ops/pagination_controller.py
x_auto_ops/retry_policy.py
```

## Pagination Flow

The future live-read flow is:

```text
Query Builder
-> Request Builder
-> Transport page fetch
-> Response Normalizer
-> PaginationController
-> RetryPolicy / RetryQueue when needed
```

The current controller receives an injected `fetch_page(query, next_token)`
function. Tests use mock fixtures only.

## PaginationState

Fields:

- `current_page`
- `next_token`
- `fetched_count`
- `max_results`
- `page_count`
- `partial_result`

## PaginationResult

Fields:

- `posts`
- `pages_fetched`
- `final_next_token`
- `partial_result`
- `stopped_reason`
- `retry_decision`

## Stop Reasons

- `completed`
- `max_results_reached`
- `max_pages_reached`
- `no_next_token`
- `rate_limited`
- `transport_error`
- `retry_limit_reached`

## next_token Policy

- The first page is fetched with no token.
- A response `next_token` becomes the token for the next page.
- The final result preserves `final_next_token`.
- If max results or max pages stop collection while a token remains,
  `partial_result=True`.
- Sensitive-looking token text must be redacted from debug summaries.

## partial_result Policy

`partial_result=True` when:

- a response marks partial result
- max results stops before all pages are exhausted
- max pages stops before all pages are exhausted
- rate limit stops collection
- transport error stops collection
- retry limit is reached

## RetryPolicy

`RetryPolicy` produces `RetryDecision`.

Fields:

- `retryable`
- `retry_after_seconds`
- `retry_count`
- `max_retry_count`
- `should_retry`

Default:

```text
max_retry_count = 3
```

The policy only decides. It does not sleep and does not retry.

## RetryQueue Relationship

When a page result is rate-limited or a retryable error occurs:

```text
RetryPolicy.decide(...)
-> RetryDecision
-> RetryQueue.enqueue(...)
```

The queue stores retry intent only. No retry execution is performed in this
phase.

## Redaction Policy

Pagination debug summaries must redact sensitive-looking:

- next tokens
- retry metadata
- error metadata

Credential-shaped marker text such as API key, token, bearer, secret, cookie,
and authorization wording must not appear in debug summaries, reports, CSV
output, or exceptions.
