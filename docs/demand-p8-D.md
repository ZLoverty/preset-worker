# P8-D — Worker Lifecycle Performance Optimization

## Goal

Extend the successful Preview performance optimizations to other Worker lifecycle transitions.

Primary targets:

1. `VALIDATING → READY_FOR_REVIEW`
2. `APPROVING → APPROVED`

Reduce unnecessary Feishu API requests and processing latency while preserving all existing business semantics.

The previous Preview optimization reduced measured processing time from approximately 29.8 seconds to 6.8 seconds.

Use the same evidence-based approach.

## 1. Audit Both Execution Paths

Locate the actual Worker code responsible for:

- Validation processing
- Review readiness
- Approval processing
- PresetVersion publication
- Preset current-version updates
- Final Submission status updates

Identify all functions executed between processing START and COMPLETED.

Do not assume both transitions use the same implementation.

Document the actual sequence of reads, calculations, writes, and state changes.

## 2. Extend Performance Instrumentation

Reuse the existing Preview timing infrastructure where practical.

Introduce generic lifecycle timing support rather than duplicating logging implementations.

Record:

- Submission ID
- Action
- Attempt ID
- Stage name
- Duration in milliseconds
- API operation
- Request and response sizes
- HTTP status
- Retry count
- Retry/backoff duration

Use `time.perf_counter()` for local durations.

Preserve existing Preview timing logs and behavior.

Do not log credentials, signed URLs, attachment tokens, or sensitive artifact contents.

## 3. Optimize Submission Retrieval

Inspect whether the Worker re-fetches a Submission after discovering it during polling.

Where safe, reuse the discovered Submission record.

Avoid repeated paginated `list_records` calls.

Preserve:

- Native Feishu record identity
- Logical Submission identity
- Migrated-record compatibility
- Required freshness checks
- Existing concurrency safeguards

Do not reuse stale data for operations requiring authoritative current state.

In particular, approval must verify that the Submission remains eligible for publication.

## 4. Optimize Validation Path

For `VALIDATING → READY_FOR_REVIEW`, inspect:

- Submission retrieval
- Original artifact download
- SlicerProcessor execution
- Canonicalization
- Preset lookup
- Diff generation
- Canonical attachment handling
- Result persistence
- Final status update

Identify redundant API requests.

Reuse already available data where safe.

Avoid repeated downloads of identical artifacts within the same processing attempt.

Evaluate whether result fields and final status can be written together, following the proven Preview optimization pattern.

Preserve existing validation and failure semantics.

## 5. Optimize Approval Path

For `APPROVING → APPROVED`, inspect:

- Submission eligibility verification
- Preset lookup
- PresetVersion lookup
- Version number allocation
- PresetVersion creation
- Preset current-version update
- Photo projection
- Submission final status update
- Audit metadata
- Failure recovery and retry logic

Determine which API calls are necessary and which are redundant.

Reuse records already retrieved during the same approval attempt.

Avoid repeated full-table scans.

Prefer direct record retrieval or reliable server-side filtering when supported by the existing data model.

## 6. Preserve Publication Consistency

Approval processing has stricter correctness requirements than Preview.

Do not:

- Mark Submission APPROVED before required publication writes succeed.
- Create duplicate PresetVersion records during retries.
- Allocate duplicate version numbers.
- Overwrite a newer Preset current-version pointer.
- Lose reviewer or publication audit metadata.
- Reuse stale approval eligibility information.
- Treat multiple independent Feishu writes as an atomic transaction.

Preserve existing idempotency, version-allocation, and concurrency mechanisms.

If the current implementation has gaps in these safeguards, document them and avoid optimizations that increase the risk.

Do not redesign the publication protocol as part of this performance task.

## 7. Evaluate Write Consolidation

Inspect multiple writes to the same record.

Where safe, consolidate fields into a single update request.

However:

- Do not combine writes across different Feishu tables as if they were atomic.
- Do not remove intermediate states required for recovery.
- Do not remove checkpoints used for idempotent retries.
- Do not weaken concurrent update safeguards.
- Do not combine writes merely to reduce API counts.

For every proposed consolidation, document why it is safe.

## 8. Audit Feishu API Access

Measure and inspect:

- Number of list_records calls
- Pagination behavior
- Direct record retrieval opportunities
- Repeated Preset/PresetVersion lookups
- HTTP session reuse
- Connection pooling
- Authentication overhead
- Attachment transfers
- Repeated writes
- Retry/backoff behavior

Prefer reducing network round trips over introducing concurrency or caching.

## 9. Avoid Unnecessary Work

Check whether any lifecycle operation repeats work already completed during Preview.

Examples to investigate:

- Re-downloading the same original artifact
- Re-running canonicalization
- Recomputing an unchanged diff
- Re-uploading an identical canonical artifact
- Re-fetching unchanged metadata

Reuse persisted Preview results only when their provenance, artifact identity, and validation freshness are verified.

Do not assume that a previously generated result remains valid after the Submission has been edited.

## 10. Implementation Strategy

Implement changes incrementally.

### P8-D1 — Instrumentation and Root-Cause Audit

Add stage-level timing to both target paths.

Identify the largest latency contributors.

Produce a baseline for each transition.

### P8-D2 — Validation Optimization

Apply safe read reuse, redundant-call elimination, and write consolidation.

Verify correctness and performance.

### P8-D3 — Approval Optimization

Apply safe retrieval and publication-path optimizations.

Preserve idempotency and publication consistency.

Verify correctness and performance.

Do not implement speculative optimizations before obtaining relevant measurements.

## 11. Regression Tests

Validation tests:

- Successful CREATE validation
- Successful UPDATE validation
- Invalid artifact
- Missing attachment
- Processor failure
- Feishu API failure
- Retry after failure
- Repeated validation
- All six slicers

Approval tests:

- First publication
- Publication of a new version
- Repeated approval attempt
- Duplicate task delivery
- Concurrent approval attempts
- PresetVersion creation failure
- Preset update failure
- Submission final-status update failure
- Retry after partial publication
- Version number uniqueness
- Audit metadata preservation
- Migrated Submission compatibility

Use mocks or isolated test data for destructive failure scenarios.

## 12. Performance Verification

Compare before and after:

| Metric | Validation | Approval |
|---|---|---|
| Total duration | Required | Required |
| Feishu read duration | Required | Required |
| Feishu write duration | Required | Required |
| Attachment transfer duration | Required | If applicable |
| Local processing duration | Required | Required |
| API call count | Required | Required |
| Retry count | Required | Required |

Collect multiple representative samples.

Report P50 and P95 where sample size permits.

Distinguish measured results from estimates.

## 13. Scope Constraints

Do not change:

- Feishu Bitable schema
- Submission lifecycle semantics
- SlicerProcessor output contracts
- UnifiedDiff schema
- Canonical artifact format
- Preset identity
- Version identity
- Approval permissions
- Reviewer audit semantics
- Miaoda frontend

Avoid introducing:

- New databases
- Message queues
- Persistent caches
- New scheduling infrastructure
- Unrelated architectural refactoring

## 14. Deliverables

Create:

`p8-D_worker_lifecycle_performance_report.md`

Include:

1. Validation execution sequence
2. Approval execution sequence
3. Per-stage baseline timings
4. API call counts by operation
5. Identified redundant requests
6. Implemented optimizations
7. Before/after performance measurements
8. Validation regression results
9. Publication consistency tests
10. Idempotency and concurrency test results
11. Remaining bottlenecks
12. Files changed
13. Known limitations
14. Final status

Use:

- OPTIMIZED_AND_VERIFIED
- PARTIALLY_OPTIMIZED
- AUDIT_ONLY
- BLOCKED

## Acceptance Criteria

- [ ] Both lifecycle paths instrumented.
- [ ] Actual bottlenecks identified.
- [ ] Redundant API calls reduced where safe.
- [ ] Validation output unchanged.
- [ ] Approval publication semantics unchanged.
- [ ] No duplicate PresetVersion creation.
- [ ] No version allocation regression.
- [ ] Retry and partial-failure behavior preserved.
- [ ] Existing Preview optimization remains intact.
- [ ] Performance improvements measured.
- [ ] Relevant tests pass.

## Implementation Principle

**Apply the proven Preview optimization pattern to the remaining lifecycle paths, but treat approval publication as a consistency-critical operation.**

Optimize network round trips without compromising historical integrity, idempotency, or concurrent publication safety.