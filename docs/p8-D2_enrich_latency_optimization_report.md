# P8-D2 Enrich latency optimization report

## Final status

`AUDITED_NO_SAFE_OPTIMIZATION`

The measured Enrich path was audited and regression-tested. The remaining attachment download cannot be removed safely with the current data model because its bytes are used for an integrity-preserving canonical attachment comparison. No speculative optimization was introduced.

## Root-cause findings

### Original artifact

`SubmissionEnrichment.process_candidate` downloads the Submission `preset data` attachment and passes its bytes to `process_artifact`. The processor performs parsing, validation, canonicalization, and produces the UnifiedDiff. This work is required to reproduce the persisted canonical artifact and validation result. It cannot be replaced by Preview metadata without changing correctness guarantees, especially when the Submission was edited after Preview.

### Existing canonical artifact

`_canonical_attachment` downloads the existing `canonical_json` attachment, compares its exact bytes with `candidate.canonical_artifact.content`, and reuses the existing `file_token` only on an exact match. Otherwise it uploads the new canonical artifact.

The bytes are therefore required for an integrity check. Filename, attachment name, size, or token alone cannot prove content identity. Removing this download would either upload duplicates on every retry or risk associating a Submission with the wrong canonical content. The download remains intentionally.

When no existing `canonical_json` attachment is present, no existing-canonical download occurs. When an existing attachment matches exactly, the upload is avoided while the reference is safely reused.

## Preset lookup

The production Feishu client uses the P8-B exact server-side `preset_key` filter. `_find_preset` retains exact client-side matching and duplicate detection. There is no additional safe lookup reduction available without changing CREATE/UPDATE detection or uniqueness semantics.

## HTTP latency audit

The client uses `urllib.request.urlopen` per request. It does not explicitly create a persistent session or connection pool. Authentication tokens are reused and refreshed only when required. Existing P8 instrumentation records end-to-end duration, status, retry count, request bytes, and response bytes, but does not separate TCP setup, proxy time, or Feishu server processing.

The reported 3,843-byte update body is now observable through `lifecycle_api` request-byte logs. No evidence is available that request size is the cause of the 3,110.7 ms write latency. No new HTTP library or unverified connection-management change was introduced.

## Existing execution sequence

For a normal runtime Enrich attempt:

1. The Worker polling query discovers the Submission; the default service reuses that record.
2. The original uploaded artifact is downloaded.
3. The slicer processor parses, validates, and canonicalizes it.
4. Preset is looked up using the exact server-side filter.
5. UPDATE loads the current PresetVersion and downloads its base canonical artifact; CREATE skips this branch.
6. The diff is generated.
7. Existing canonical bytes are downloaded when a prior reference exists and compared exactly; upload occurs only when needed.
8. Enrichment fields and `READY_FOR_REVIEW` are persisted in one Submission update.

## Changes in this D2 pass

- Added a regression fixture proving an existing canonical reference is downloaded before reuse.
- Preserved the original artifact download and processor execution.
- Preserved exact canonical byte comparison and upload idempotency.
- Retained P8-A/P8-D lifecycle timing and byte-count instrumentation.

The actual speedups already available to Enrich are the P8-D discovered-record reuse, P8-B filtered Preset lookup, and P8-C single result/status write. D2 found no further safe network round trip to remove.

## Before/after measurements

Available baseline:

- Total duration: 8,501.6 ms
- Feishu reads: 2,351.1 ms
- Attachment downloads: 3,038.8 ms
- Feishu writes: 3,110.7 ms
- Processor: 0.1 ms
- Diff: 0.1 ms
- API calls: 4
- Retries: 0

No live Feishu credentials or equivalent production samples were available for after measurements. Therefore median, P95, and latency gains are not fabricated. Collect comparable `action=enrich` lifecycle summaries for CREATE/UPDATE and both existing/missing canonical attachment cases.

## Tests

The targeted suite covers:

- Existing canonical attachment download and exact-reference reuse.
- Validation CREATE and UPDATE.
- Discovered Submission reuse.
- Processor, attachment, Feishu, and retry-related failure behavior already present in the suite.
- All supported slicer-specific regression modules in the repository remain unchanged.

After the added integrity test, the targeted lifecycle suite passed 44 tests. Full live integration was not run.

## Remaining bottlenecks

The measured bottlenecks remain Feishu attachment transfer and Submission write latency. A future optimization would require an authoritative content hash/checksum exposed by Feishu or a schema-approved persisted artifact identity; neither is available in this phase. HTTP connection pooling should only be changed after a trace separates connection setup from server-side request latency.

## Files changed

- `tests/test_submission_enrichment.py`
- `docs/p8-D2_enrich_latency_optimization_report.md`
