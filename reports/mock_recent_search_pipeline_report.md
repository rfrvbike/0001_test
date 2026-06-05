# Mock Recent Search Pipeline Report

Mock-only dry-run report. No X API call, credential lookup, `.env` read, or posting was performed.

## Redacted Live Summary

```json
{"diagnostics_version":"1","endpoint_name":"recent_search","execution_time_ms":1,"fetched_count":2,"method":"GET","metrics_missing_count":2,"next_cursor_present":false,"normalized_post_count":2,"pagination_used":false,"partial_result":false,"query_length":88,"rate_limited":false,"request_id":"mock-dry-run","result_count":2,"retry_after_seconds":null,"retryable":false,"rollback_completed":false,"status":"success","status_code":200,"stop_reason":"completed"}
```

## Request Scope
- endpoint_name: recent_search
- method: GET
- query_length: 88
- source_genre: ai_side_business

## Fetch Summary
- post_count: 2
- ranked_count: 2
- rate_limited: False
- retry_after_seconds: None
- partial_result: False
- next_cursor_present: False
- retry_queue_size: 0
- rate_limited_count: 0
- redaction_status: ok
- credential_loader: FAKE
- live_mode_gate: dry_run_allowed

## Top Posts
- ai_side_business / buzz_score 1574 / rank 1
- ai_side_business / buzz_score 531 / rank 2

## Metrics Missing Summary
- missing_impression_count: 1
- missing_quote_count: 1

## Retry Tasks
- none: 0
