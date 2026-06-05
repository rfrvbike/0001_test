# Mock Recent Search Pipeline Report

Mock-only dry-run report. No X API call, credential lookup, `.env` read, or posting was performed.

## Redacted Live Summary

```json
{"diagnostics_version":"1","endpoint_name":"recent_search","execution_time_ms":0,"fetched_count":0,"method":"GET","metrics_missing_count":0,"next_cursor_present":false,"normalized_post_count":0,"pagination_used":false,"partial_result":true,"query_length":88,"rate_limited":true,"request_id":"mock-rate_limited","result_count":0,"retry_after_seconds":120,"retryable":true,"rollback_completed":false,"status":"error","status_code":429,"stop_reason":"rate_limited"}
```

## Request Scope
- endpoint_name: recent_search
- method: GET
- query_length: 88
- source_genre: ai_side_business

## Fetch Summary
- post_count: 0
- ranked_count: 0
- rate_limited: True
- retry_after_seconds: 120
- partial_result: True
- next_cursor_present: False
- retry_queue_size: 0
- rate_limited_count: 1
- redaction_status: ok
- credential_loader: FAKE
- live_mode_gate: dry_run_allowed

## Top Posts
- No posts ranked.

## Metrics Missing Summary
- none: 0

## Retry Tasks
- none: 0
