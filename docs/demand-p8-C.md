# P8-C — Feishu Write Latency Audit & Safe Optimization

## Goal

Investigate and safely optimize the Feishu Bitable write operations during Worker Preview.

Current measured baseline:

| Metric | Value |
|---|---:|
| Total Preview duration | 8,380.7 ms |
| `write_preview_result` | 2,276.8 ms |
| `write_preview_status` | 1,900.5 ms |
| Total Feishu write duration | 4,177.3 ms |
| Total API requests | 5 |
| HTTP retries | 0 |

The two write operations account for approximately 49.8% of total Preview processing time.

**Primary objective: determine exactly what is written, why two requests are necessary, and whether one request can safely replace them.**

## 1. Trace Both Write Operations

Locate the actual implementations of:

- `write_preview_result`
- `write_preview_status`
- Their underlying Feishu `update_record` calls

For each operation, document:

- Exact Feishu table
- Record identifier
- Field names
- Field types
- Purpose of each field
- Approximate serialized request-body size
- Whether existing values are overwritten
- Whether the update triggers downstream processing

Do not assume the operations only write canonical JSON, diff, or status. Verify the actual implementation.

Do not log sensitive field values, credentials, attachment tokens, or signed URLs.

## 2. Audit State Transition Dependencies

Trace the complete Preview state transition.

Determine:

- The state before processing
- The state during processing
- The final successful state
- How processing failures are represented
- Whether the frontend can observe intermediate states
- Whether another Worker operation depends on the intermediate state
- Whether result persistence and status updates must be ordered

Inspect both normal execution and exception-handling paths.

Identify whether the second write is required for correctness or merely reflects the current implementation structure.

## 3. Audit HTTP Connection Management

Inspect the Feishu API client implementation.

Determine:

- Whether requests reuse a persistent HTTP session
- Whether HTTP keep-alive is enabled
- Whether connection pooling is used
- Whether a new client/session is created per request
- Whether requests use a proxy
- Whether authentication refresh adds latency
- Whether the same client is shared safely across Worker operations

Record the findings.

Do not introduce a new HTTP client library unless necessary.

If connection reuse is absent, propose the smallest safe improvement using the existing HTTP stack.

## 4. Distinguish Request Size From Network Latency

Measure:

- Request-body size in bytes
- Response-body size in bytes
- End-to-end HTTP duration
- HTTP status
- Retry count
- Backoff duration

Where feasible, distinguish connection establishment from request/response time.

Do not assume that a large request body causes the latency.

Do not claim server-side latency has been measured unless the available instrumentation supports that conclusion.

## 5. Evaluate Combining the Two Writes

Investigate whether Preview results and the final status can be written in one `update_record` request.

Potential transformation:

Before:

```python
update_record(record_id, result_fields)
update_record(record_id, status_fields)
```

After:

```python
update_record(
    record_id,
    {
        **result_fields,
        **status_fields,
    },
)
```

This is conceptual pseudocode, not a required implementation.

Only combine the operations if all of the following are satisfied:

- The intermediate state is not required by the business workflow.
- The final state is written only after all required artifacts are available.
- The frontend cannot observe an invalid completed result.
- Failure recovery remains correct.
- Retries remain safe and idempotent.
- No required audit information is lost.
- Concurrent Worker processing cannot introduce incorrect state transitions.
- The existing Feishu API supports the combined update.

If any condition cannot be established, retain the two writes and explain why.

## 6. Minimal Optimization

If safe, implement the combined write with minimal code changes.

Prefer reusing the existing repository/service methods.

Do not introduce:

- A new database
- A message queue
- A new state machine
- A generic transaction framework
- A new caching layer
- Unrelated asynchronous refactoring

If connection reuse is demonstrably inefficient, apply a similarly small correction.

Keep optimizations isolated and independently testable.

## 7. Preserve Existing Behavior

Do not change:

- Submission lifecycle semantics
- CREATE/UPDATE detection
- SlicerProcessor behavior
- UnifiedDiff schema
- Canonical artifact format
- PresetVersion publication
- Approval/rejection behavior
- Feishu Bitable schema
- Frontend field contracts

Preserve all six supported slicers.

## 8. Regression Tests

Verify at least:

1. Successful CREATE Preview.
2. Successful UPDATE Preview.
3. Correct canonical artifact reference.
4. Correct diff persistence.
5. Correct final Preview status.
6. Attachment upload failure.
7. Feishu update failure.
8. Retry after transient failure.
9. No false successful status after partial failure.
10. Repeated Preview on the same Submission.
11. Existing migrated Submission compatibility.
12. Concurrent processing safeguards.

Use mocks for failure injection where appropriate.

Do not modify production records for destructive tests.

## 9. Performance Verification

Keep the existing P8-A timing instrumentation.

Compare before and after:

- Number of `update_record` calls
- Total Feishu write duration
- Total Preview duration
- API request count
- Retry count
- Error rate

Collect multiple comparable samples.

Report median and P95 where sufficient data is available.

Do not report estimated performance gains as measured results.

## 10. Deliverable

Create:

`p8-C_feishu_write_optimization_report.md`

Include:

1. Exact fields written by each PUT
2. Request-body sizes
3. Current state-transition sequence
4. Failure-recovery dependencies
5. HTTP session and connection-pooling findings
6. Whether combining writes is safe
7. Changes implemented, if any
8. Before/after API request counts
9. Before/after latency measurements
10. Regression-test results
11. Remaining bottlenecks
12. Files changed
13. Final status

Use one of:

- OPTIMIZED_AND_VERIFIED
- AUDITED_NO_SAFE_OPTIMIZATION
- PARTIALLY_COMPLETE
- BLOCKED

## Acceptance Criteria

- [ ] Exact fields in both PUT requests identified.
- [ ] Request-body sizes measured.
- [ ] HTTP connection reuse audited.
- [ ] State-transition dependencies verified.
- [ ] Combined-write safety evaluated.
- [ ] Safe optimization implemented where justified.
- [ ] No incorrect completion state introduced.
- [ ] Failure recovery remains correct.
- [ ] CREATE/UPDATE regression tests pass.
- [ ] Performance results are measured and documented.

## Implementation Principle

**Eliminate unnecessary network round trips without weakening data consistency or workflow correctness.**

Correctness takes priority over saving approximately two seconds.