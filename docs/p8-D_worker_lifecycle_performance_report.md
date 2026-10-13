# P8-D Worker lifecycle performance report

## Final status

`PARTIALLY_OPTIMIZED` — Validation and Approval paths now have lifecycle timing, safe record-access reductions, and regression coverage. Live before/after Feishu measurements were not available, so no unmeasured latency gain is claimed.

## Validation execution sequence

The Worker discovers `VALIDATING` Submission records. The default enrichment service now reuses the complete discovered record, validates its current status field, downloads the uploaded artifact, runs the slicer processor, looks up Preset, optionally looks up PresetVersion and downloads its canonical artifact for UPDATE, generates the diff, handles the canonical attachment, and writes all enrichment fields plus `READY_FOR_REVIEW` in one Submission PUT.

Standalone calls without a discovered record retain the existing Submission lookup behavior. Validation failure writes validation data and `VALIDATION_FAILED` in the existing single PUT. Processor and attachment failure behavior is unchanged.

## Approval execution sequence

Approval deliberately does not trust the discovered record as the authoritative state. When the production Feishu client supports native record retrieval, the default Worker path refreshes the discovered native `record_id` with one direct record GET. This preserves the eligibility check while avoiding a full paginated Submission scan. Test doubles and standalone callers without this capability retain the existing lookup fallback.

The publication path then reads the PresetVersion table once to find a version sourced from the Submission. It reads Preset using the exact server-side `preset_key` filter where supported. For UPDATE, the already-loaded PresetVersion records are reused to find the current version number; the old second full Version scan is removed. It then creates or repairs the PresetVersion, updates the Preset current-version pointer, projects process-photo fields in one Preset PUT, and finally updates the Submission with `published_version_id` and `APPROVED`.

Existing recovery behavior remains: an existing source version is repaired rather than duplicated, newer current versions are not rolled back, and `APPROVED` is written only after publication and projection succeed.

## Instrumentation

`profiling.py` now supports both the existing Preview events and generic lifecycle events:

- `preview_stage`, `preview_api`, `preview_timing_summary` remain unchanged in purpose and are retained for Preview.
- `lifecycle_stage`, `lifecycle_api`, `lifecycle_timing_summary` include `action=enrich` or `action=publish`.
- API events include operation, method, endpoint category, duration, status, retry count, retry/backoff fields, request bytes, and response bytes.
- No credentials, signed URLs, attachment tokens, or artifact contents are logged.

## Identified redundant requests

- Validation previously re-fetched the Submission after polling; the default path now reuses the discovered record.
- Approval previously performed a full Submission scan after polling; the default production path now performs one authoritative native-record GET.
- Approval UPDATE previously loaded PresetVersion records once to find the source version and again to find the current version number; one loaded list is now reused.
- Preset lookup uses the P8-B exact server-side filter when available.

No persistent cache or concurrency refactoring was introduced.

## API call comparison

Exact counts depend on CREATE/UPDATE, pagination, and retries. For the common UPDATE approval path, code inspection gives this reduction:

| Operation | Before | After |
|---|---:|---:|
| Submission retrieval | paginated logical-ID scan | 1 native record GET in default Feishu path |
| Source PresetVersion lookup | 1 Version list | 1 Version list |
| Current PresetVersion lookup | second Version list | reused first list |
| Preset lookup | full list | 1 exact filtered list where supported |
| Publication writes | create Version, update Preset, projection PUT, Submission PUT | unchanged |

Validation removes its extra Submission scan; its remaining reads and one result PUT are unchanged. These are API-count conclusions from the implementation, not measured latency results.

## Performance measurements

The prior Preview measurement (approximately 6.8 seconds after P8-B/C) is retained as context. No equivalent live Validation or Approval samples were available in this environment. The new lifecycle summaries should collect P50/P95 for:

- `action=enrich`: `get_submission`/reuse, attachment download, processor, diff, canonical handling, writes, and total duration.
- `action=publish`: authoritative Submission GET, Version source lookup, Preset lookup, create/update/projection writes, Submission final status write, and total duration.

The logs distinguish request/response size from end-to-end HTTP duration but do not claim server-side processing time or TCP setup time separately.

## Regression results

The targeted lifecycle suite ran 43 tests successfully, including:

- Validation CREATE/UPDATE and discovered-record reuse.
- Preview behavior and failure handling.
- First publication and UPDATE publication.
- Native-record refresh for discovered Approval records.
- Repeated publication recovery without duplicate PresetVersion creation.
- Version conflict handling, projection failure recovery, newer-version protection, and metadata preservation.
- Feishu authentication compatibility and Worker dispatch behavior.

Full integration against Feishu was not run. The repository's unrelated existing Diff-category test remains the known full-suite failure.

## Publication consistency and known limitations

- The Submission is refreshed authoritatively for the default Approval path before eligibility is checked.
- Publication writes across PresetVersion, Preset, projection, and Submission remain separate; they are not treated as an atomic transaction.
- Existing retry/idempotency checkpoints are preserved.
- Validation reuse trusts the discovered polling record after checking its status; if the deployment requires an authoritative status refresh under concurrent edits, disable reuse for that deployment rather than changing publication semantics.
- HTTP connection pooling remains unchanged because the current environment provides no evidence separating connection setup from Feishu server latency.

## Files changed

- `src/preset_worker/profiling.py`
- `src/preset_worker/runtime.py`
- `src/preset_worker/services/enrichment.py`
- `src/preset_worker/services/publication.py`
- `tests/test_submission_enrichment.py`
- `tests/test_submission_publication.py`
