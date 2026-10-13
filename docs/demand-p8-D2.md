# P8-D2 — Optimize Enrich Lifecycle Latency

## Goal

Optimize the Worker `enrich` action based on the measured execution trace.

Baseline:

- Total duration: 8,501.6 ms
- Feishu reads: 2,351.1 ms
- Attachment downloads: 3,038.8 ms
- Feishu writes: 3,110.7 ms
- Processor: 0.1 ms
- Diff: 0.1 ms
- API calls: 4
- Retries: 0

## 1. Trace Existing Canonical Download

Locate the implementation of:

- `existing_canonical_download`
- `canonical_attachment`
- `write_enrichment_result`

Determine exactly how the downloaded canonical bytes are used.

Establish whether the enrichment operation needs to inspect or transform the canonical artifact, or only preserve its existing Feishu attachment reference.

If the artifact bytes are not needed, reuse the existing attachment reference and remove the unnecessary download.

If the bytes are required for validation, comparison, or integrity checks, retain the download.

Do not remove integrity checks or infer artifact identity from filename alone.

## 2. Trace Original Artifact Download

Determine which operations consume the downloaded original artifact.

Check whether the enrich path needs to execute the slicer processor again, or whether it only needs metadata already available from the Submission.

Do not skip processor or validation work without proving that the resulting persisted data remains correct.

Avoid repeated downloads within a single processing attempt where safe.

## 3. Optimize Preset Lookup

The current `preset_lookup` takes 2,351.1 ms and issues one `list_records` request.

Inspect the exact query, filters, pagination behavior, and returned fields.

Determine whether an exact server-side filter or direct record retrieval can reduce latency.

Reuse records already available within the current attempt only when their identity and freshness are reliable.

Preserve CREATE/UPDATE detection and uniqueness checks.

## 4. Audit Feishu HTTP Latency

The final Submission update takes 3,110.7 ms for a request body of 3,843 bytes.

Inspect the existing HTTP client implementation:

- Session reuse
- Connection pooling
- Keep-alive
- Proxy configuration
- Authentication overhead
- Request/response timing
- Response-body parsing

Use the existing HTTP stack and instrumentation.

Do not assume request size is the cause.

Do not introduce a new HTTP library without evidence.

## 5. Preserve Behavior

Do not change:

- Submission identity semantics
- Canonical artifact format
- UnifiedDiff schema
- SlicerProcessor contracts
- CREATE/UPDATE detection
- Workflow status semantics
- Approval/publication behavior
- Feishu schema

Preserve migrated Submission compatibility and existing error handling.

## 6. Tests

Verify:

- Enrich with an existing canonical attachment
- Enrich when canonical content must be downloaded
- Correct canonical attachment reference after enrichment
- Correct enrichment fields
- Processor failure handling
- Feishu read/write failures
- Retry safety
- Migrated Submission compatibility
- All supported slicers

Use isolated fixtures or mocks for failure tests.

## 7. Performance Verification

Compare before and after:

- Total enrich duration
- Original artifact download duration
- Existing canonical download duration
- Preset lookup duration
- Feishu write duration
- API call count
- Retry count

Run multiple comparable samples and report median/P95 where sample size permits.

Do not report estimated gains as measured results.

## 8. Deliverable

Create:

`p8-D2_enrich_latency_optimization_report.md`

Include root causes, code changes, tests, before/after timings, API counts, remaining bottlenecks, and final status.

Use one of:

- OPTIMIZED_AND_VERIFIED
- AUDITED_NO_SAFE_OPTIMIZATION
- PARTIALLY_COMPLETE
- BLOCKED

## Implementation Principle

Remove unnecessary network round trips, especially redundant artifact downloads, while preserving canonical artifact integrity and workflow correctness.