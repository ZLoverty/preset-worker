# P8-B — Optimize Worker Preview Record Access

## Goal

Reduce Worker Preview processing latency by eliminating unnecessary Feishu Bitable API calls.

Measured baseline:

- Total Preview: 29,797 ms
- Feishu record reads: 23,075 ms
- Feishu record writes: 4,333 ms
- Processor: 0.1 ms
- Diff: 0.1 ms
- API calls: 15
- Retries: 0

Prioritize record-reading optimization.

## 1. Investigate get_submission

The current `get_submission` stage takes 19,592.5 ms and issues nine `list_records` requests.

Trace the exact implementation.

Determine:

- Why nine requests are required
- Whether requests represent pagination or repeated queries
- Whether the Submission has a native Feishu record_id
- Whether the `MIGRATED-` identifier is a logical ID
- Whether the record can be fetched directly
- Whether the caller already possesses the required record data

Do not assume that logical Submission IDs are interchangeable with native Feishu record IDs.

## 2. Optimize Submission Retrieval

Prefer the following approaches in order:

1. Reuse the Submission record already discovered by the polling loop, if it contains all required fields and is sufficiently current.
2. Use Feishu's direct record retrieval API when a valid native record_id is available.
3. Use a server-side filtered query when direct retrieval is unavailable and the query semantics are reliable.
4. Retain paginated scanning only when necessary.

Preserve the existing record identity semantics.

Do not introduce a persistent cache or new database solely for this optimization.

## 3. Optimize preset_lookup

The current `preset_lookup` stage takes 3,482.5 ms and issues two `list_records` requests.

Determine whether these requests are:

- Independent required lookups
- Pagination
- Redundant queries
- Repeated retrieval of already available records

Reduce unnecessary requests without changing CREATE/UPDATE detection.

Preserve exact `preset_key` matching.

## 4. Review Write Operations

The Preview currently performs:

- `write_preview_result`: 2,336 ms
- `write_preview_status`: 1,997 ms

Investigate whether these writes can safely be combined.

Only combine them if:

- The intermediate status has no required observable meaning
- Failure recovery remains correct
- State transitions remain valid
- Existing frontend behavior remains compatible

Otherwise, retain both writes.

Do not prioritize write optimization ahead of the record-reading bottleneck.

## 5. Preserve Correctness

Do not change:

- Submission identity semantics
- CREATE/UPDATE detection
- PresetVersion selection
- UnifiedDiff output
- Canonical artifact content
- Review status semantics
- Approval/publication behavior
- SlicerProcessor implementations

Pay special attention to migrated records and legacy identifiers.

## 6. Performance Verification

Keep the existing P8-A timing instrumentation.

Measure before and after:

- get_submission duration
- get_submission API call count
- preset_lookup duration
- preset_lookup API call count
- Feishu write duration
- Total Preview duration

Use identical or equivalent test records where possible.

Test both CREATE and UPDATE, including migrated records.

Run multiple samples and report median and P95 where sample size permits.

## 7. Deliverable

Create:

`p8-B_preview_record_access_optimization.md`

Include:

1. Root cause of nine list_records requests
2. Actual record ID semantics
3. Changes implemented
4. API calls before and after
5. Per-stage timing before and after
6. CREATE/UPDATE regression tests
7. Migrated-record compatibility
8. Remaining bottlenecks
9. Final status

## Acceptance Criteria

- [ ] Root cause of repeated list_records calls identified.
- [ ] Unnecessary record scans eliminated where safe.
- [ ] No incorrect logical/native ID substitution.
- [ ] Preview output unchanged.
- [ ] CREATE/UPDATE behavior unchanged.
- [ ] Migrated records remain supported.
- [ ] Performance improvement demonstrated with measurements.
- [ ] Existing tests pass.

## Implementation Principle

Optimize data access, not business logic.

Prefer eliminating redundant network round trips over introducing concurrency, caching, or a new infrastructure component.