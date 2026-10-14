# P8-A — Worker Preview Performance Profiling

## Goal

Investigate why a single Preview operation takes approximately 45 seconds between the Worker's START and COMPLETED log events.

The delay has already been confirmed to occur inside the Worker processing interval.

Focus on identifying the exact internal bottleneck before making optimizations.

## 1. Trace the Actual Execution Path

Locate the existing Preview START and COMPLETED log statements.

Identify every synchronous and asynchronous operation executed between them.

Inspect the real code path rather than assuming a predefined sequence.

Include:

- Feishu Bitable API operations
- Attachment downloads
- Artifact processing
- Canonical artifact uploads
- Preset / PresetVersion lookups
- Diff generation
- Submission writeback
- Retries, backoff, and sleeps
- Any other blocking operations

## 2. Add Stage-Level Timing

Instrument each meaningful operation using `time.perf_counter()`.

Record duration in milliseconds.

Example:

```python
start = time.perf_counter()

result = perform_operation()

duration_ms = (time.perf_counter() - start) * 1000

logger.info(
    "preview_stage stage=%s duration_ms=%.1f",
    "operation_name",
    duration_ms,
)
```

Use the project's existing logging conventions.

Include submission ID and attempt/correlation ID where available.

Do not log credentials, attachment tokens, signed URLs, or artifact contents.

## 3. Instrument External API Calls

For every Feishu API request on the Preview path, record:

- Operation name
- HTTP method
- Endpoint category (not sensitive full URLs)
- Request duration
- HTTP status
- Retry count
- Retry/backoff duration
- Whether the request succeeded

Identify repeated requests and unnecessary sequential dependencies.

Do not change retry behavior in this phase.

## 4. Instrument Artifact Processing

Measure separately:

- Download
- Parse
- Validation
- Canonicalization
- Diff generation
- Serialization
- Upload

Ensure local CPU operations are distinguished from network I/O.

## 5. Produce Per-Preview Timing Summary

At the end of each Preview, log a summary similar to:

```text
preview_timing_summary
  submission_id=...
  total_ms=45000
  feishu_read_ms=...
  attachment_download_ms=...
  processor_ms=...
  diff_ms=...
  attachment_upload_ms=...
  feishu_write_ms=...
  retry_backoff_ms=...
  other_ms=...
```

Ensure stage durations are measured consistently.

Avoid double-counting nested operations.

If there is unaccounted time, report it explicitly.

## 6. Test

Run representative Preview operations:

- CREATE with JSON
- UPDATE with JSON
- CREATE or UPDATE with INI
- Small and larger artifact files

Collect multiple samples for each relevant case.

If integration credentials or test data are unavailable, implement instrumentation and provide instructions for collecting real measurements.

Do not fabricate performance results.

## 7. Deliverable

Create:

`p8-A_worker_preview_profiling.md`

Include:

1. Actual Worker Preview execution path
2. START and COMPLETED log locations
3. Timing instrumentation added
4. API call counts
5. Per-stage latency
6. Retry/backoff observations
7. Top three bottlenecks
8. Recommended optimizations, ranked by expected benefit and risk
9. Files changed
10. Tests performed
11. Remaining uncertainties

## 8. Constraints

This phase is diagnostic only.

Do not change:

- Worker polling behavior
- Submission lifecycle
- SlicerProcessor output semantics
- Canonical artifact format
- UnifiedDiff schema
- Feishu Bitable schema
- Retry policies
- Approval/publication logic

Do not introduce concurrency, caching, or asynchronous refactoring yet.

## Acceptance Criteria

- [ ] Worker START-to-COMPLETED duration is measurable.
- [ ] All major internal stages are timed.
- [ ] Individual Feishu API durations are visible.
- [ ] Attachment download/upload durations are visible.
- [ ] Processor and Diff durations are visible.
- [ ] Retry/backoff time is visible.
- [ ] Unaccounted time is explicitly reported.
- [ ] No business behavior changed.