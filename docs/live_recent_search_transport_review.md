# LiveRecentSearchTransport Implementation Review

This is a pre-implementation review for the future X recent-search live read
transport. It is design-only. No X API call, HTTP transport, credential lookup,
token handling, cookie handling, `.env` read, or posting behavior is introduced
by this document.

## Implementation Checklist

### Required Responsibilities

- Accept a query string produced by `build_recent_search_query(...)`.
- Send only read-only recent-search requests when live mode is explicitly
  enabled in a backend-only execution context.
- Return the existing `TransportResponse` shape:
  `status_code`, `headers`, and `json_body`.
- Preserve raw rate-limit headers for `parse_rate_limit_headers(...)`.
- Preserve response JSON for `normalize_recent_search_response(...)`.
- Raise typed, redacted errors for network, authentication, authorization,
  rate-limit, malformed JSON, and unexpected status cases.
- Keep retry policy outside `send_recent_search(...)`.
- Keep scoring, genre detection, CSV output, and report output outside the
  transport.

### Prohibited Behavior

- Do not call the X API unless an explicit live mode gate is approved.
- Do not read credentials from frontend code, CSV, reports, fixtures, or browser
  storage.
- Do not write credentials, request headers, cookies, or authorization values to
  logs, reports, CSV, debug strings, exceptions, or test snapshots.
- Do not perform posting, liking, reposting, following, or any write action.
- Do not retry in a loop or sleep inside the transport.
- Do not mutate the search query built upstream.

### Error Handling

The future live transport should normalize errors into redacted exceptions or
transport results that downstream layers can handle without secrets.

| Case | Expected handling |
| --- | --- |
| Network timeout | raise redacted temporary transport error |
| DNS/connect failure | raise redacted temporary transport error |
| 401/403 | raise redacted auth/config error; do not retry blindly |
| 429 | return headers/body so rate-limit parser and retry queue can handle it |
| 5xx | raise or return temporary error according to client policy |
| malformed JSON | raise redacted parse error with status code only |
| unexpected schema | pass parsed JSON to normalizer; normalizer records missing fields |

### Dry-run Gate

Live access must remain fail-closed:

- `XApiBuzzReadClient(dry_run=False)` currently raises before transport use.
- A future live client path must require a separate explicit live enable flag.
- `LiveRecentSearchTransport` should also reject use unless it is constructed
  with an explicit live-mode option.
- Tests must prove that dry-run mode cannot call the live transport.

### Redaction Points

Redaction must be applied before data leaves these boundaries:

- transport exception messages
- transport debug output
- pipeline debug logs
- reports
- CSV leak-test rendering
- retry task snapshots if they include query/config-derived text

The current redaction utility covers marker-shaped test values for API key,
token, bearer, secret, cookie, and authorization text. Future implementation
should extend the utility if real credential formats require additional
patterns.

### Retry Queue Integration

`send_recent_search(...)` should not retry directly. Rate-limit handling should
flow as:

```text
LiveRecentSearchTransport
-> TransportResponse(headers, json_body)
-> parse_rate_limit_headers(...)
-> normalize_recent_search_response(...)
-> BuzzFetchResult(rate_limited, retry_after_seconds, partial_result, next_token)
-> RetryQueue.enqueue(...)
```

The retry queue should receive:

- query
- retry_after_seconds
- enqueue_time
- retry_count

`max_retry_count` should be enforced by the future controller layer, not inside
the transport.

### Query Builder Integration

`LiveRecentSearchTransport` receives a complete query. It must not:

- add genre terms
- remove exclusion terms
- add account filters
- change language filters
- silently shorten the query

Query length, empty-query checks, duplicate keyword removal, target-account
filters, exclude keywords, and source genre metadata remain upstream concerns.

### Response Normalizer Integration

The transport returns parsed JSON in X response shape. The normalizer remains
responsible for:

- mapping post IDs
- mapping author IDs and usernames
- mapping public metrics
- tolerating missing users and metrics
- preserving pagination metadata
- preserving partial-result and rate-limit metadata

## Field Availability Review

`BuzzPost` should keep the common shape stable even when X API fields are
missing or plan-limited.

| Field | Required in common format | Optional from X | Missing tolerated | Used in score |
| --- | --- | --- | --- | --- |
| `post_id` | yes | no | no | no |
| `text` | yes | no | no | no |
| `created_at` | yes | possibly | yes | no |
| `author_id` | yes | possibly | yes | no |
| `author_username` | yes | yes | yes | no |
| `like_count` | yes | possibly | yes, default 0 | yes |
| `repost_count` | yes | possibly | yes, default 0 | yes |
| `reply_count` | yes | possibly | yes, default 0 | yes |
| `quote_count` | yes | possibly | yes, default 0 | yes |
| `impression_count` | yes, nullable | yes | yes, default `None` | yes, when present |

Notes:

- `impression_count` is nullable because access may depend on X API product,
  endpoint behavior, and field availability.
- If public metrics are absent, the collector should not crash. Missing metrics
  should be recorded in `metrics_missing`.
- If author expansion is unavailable, use a stable fallback such as
  `author_username=""` and record `missing_author_username`.

## Pagination Policy

Current design already includes:

- `next_token`
- `max_results_per_genre`
- `request_window`
- `partial_result`

Future live behavior should follow these rules:

- The query builder prepares one query per source genre/config slice.
- `max_results` should be bounded by config and by X endpoint limits.
- A live fetch should stop when `max_results_per_genre` is reached.
- If X returns `next_token`, preserve it in `BuzzFetchResult.next_token`.
- If rate limit, timeout, or partial upstream response interrupts collection,
  set `partial_result=True`.
- `request_window` should capture the logical window used for the request, such
  as recent-search lookback and fetch timestamp, without implying historical
  completeness beyond the API plan.
- Pagination should be controlled outside the transport so tests can inject
  mock pages and rate-limit cases deterministically.

## Rate Limit Operation Review

Inputs to rate-limit handling:

- `Retry-After`
- `x-rate-limit-reset`
- `x-rate-limit-remaining`

Current supporting components:

- `parse_rate_limit_headers(...)`
- `BuzzFetchResult.rate_limited`
- `BuzzFetchResult.retry_after_seconds`
- `RetryQueue.enqueue(...)`

Recommended future policy:

- Prefer `Retry-After` when present.
- Fall back to `x-rate-limit-reset` when `Retry-After` is absent.
- Preserve `remaining_requests` for reporting/diagnostics only.
- Do not sleep in the transport.
- Enqueue retry tasks with a configured `max_retry_count`.
- Treat repeated 429 responses as `partial_result=True` and leave further retry
  decisions to the controller.
- Keep rate-limit logs redacted and limited to status, wait seconds, reset time,
  remaining count, and source genre.

## Credential Loader Policy

Implementation is explicitly out of scope for this review. Future credential
loading should follow this policy:

- Backend/server-side only.
- No frontend access.
- No localStorage/sessionStorage.
- No CSV/report/fixture storage.
- No raw credential logging.
- No raw credential values in exception messages.
- No raw request headers in debug output.
- The loader should return only the minimum credential object needed by the
  live transport.
- The loader should be tested with fake values and redaction assertions before
  any live call is enabled.

## Gap Analysis

| Area | Current status | Needed before live transport |
| --- | --- | --- |
| Query Builder | complete for mock recent-search query generation | confirm X plan query length and operators |
| RecentSearchTransport interface | complete | keep as stable injection boundary |
| MockRecentSearchTransport | complete | keep fixtures aligned with live response shape |
| Header Parser | complete for Retry-After/reset/remaining | verify header names against chosen X endpoint |
| Response Normalizer | complete for fixtures and missing metrics | add fixtures if live schema differs |
| BuzzFetchResult | complete for rate-limit/partial/next token metadata | confirm pagination fields after plan selection |
| Redaction Utility | complete for marker-based regression tests | extend with real credential format patterns if needed |
| Retry Queue | mock-only complete | add controller policy and max retry count |
| Dry-run Gate | complete | keep fail-closed until explicit live approval |
| Live Transport | missing by design | implement only after this checklist is accepted |
| Credential Loader | missing by design | backend-only fake-tested loader needed |
| HTTP Client | missing by design | choose timeout, headers, JSON parsing, error mapping |
| Header Mapping | partially designed | confirm endpoint-specific rate-limit headers |
| Pagination Controller | partially designed | implement outside transport |

## Risk Review

| Risk | Impact | Mitigation |
| --- | --- | --- |
| X API plan changes | fields, limits, or endpoint access may differ | keep fields nullable and document plan assumptions |
| rate-limit changes | retry timing may be wrong | parse both Retry-After and reset headers; keep retry queue external |
| missing metrics | scoring may be incomplete | use `metrics_missing` and fallback buzz score |
| missing impressions | impression-based scoring unavailable | record `score_source` and use engagement-only fallback |
| pagination changes | partial collection or duplicate pages | keep `next_token` and request window visible |
| auth changes | live calls fail or leak risk increases | isolate backend credential loader and redact all outputs |
| raw-response logging | accidental sensitive metadata exposure | prohibit raw logs and test marker leakage |
| query syntax mismatch | empty/invalid searches | validate in Query Builder and add endpoint-specific fixtures |

## Implementation Decision

The project is ready to design the live transport class, but not to enable live
traffic. The next implementation step should still be mock-first:

1. Add a disabled `LiveRecentSearchTransport` skeleton.
2. Add a fake credential loader interface with fake-value tests only.
3. Add endpoint-specific request-building tests without HTTP.
4. Add pagination-controller tests with mock transports.
5. Keep `dry_run=False` blocked until explicit live approval.
