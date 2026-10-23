# Release Notes

## v0.3.0

3MF-aware consistency validation and cross-slicer workflow integration.

### 3MF inspection and consistency validation

- Added safe 3MF inspection and parsing utilities for project configuration,
  slot identity, stored parameter values, and artifact diagnostics.
- Added element-wise Preset-to-3MF comparison for the canonical process
  parameters, including array index, source paths, normalized values, and
  explicit `MATCH`, `MISMATCH`, missing, unresolved, and ambiguous states.
- Added slot-aware resolution for multi-filament projects, including the
  Snapmaker Orca four-slot fixture and PrusaSlicer native project format.
- Added isolated consistency adapters for BambuStudio, CrealityPrint,
  ElegooSlicer, OrcaSlicer, Snapmaker OrcaSlicer, and PrusaSlicer.
- Added real paired 3MF/Preset fixtures, cross-slicer contract tests, and
  validator regression coverage.

### Preview and formal Submit integration

- Added the `p9b2.consistency.v1` report envelope and persisted reports in the
  existing `consistency_report` Submission field.
- Preview now recomputes consistency from the current Preset and first `preset
  3mf` attachment, writing `READY`, sanitized `ERROR`, or an explicit empty
  value as appropriate.
- Formal Submit now independently regenerates the report from the current
  `CandidateResult.source_artifact`; it does not reuse a previous Preview
  report.
- Added report writeback fallback handling that retries with a sanitized error
  and then explicitly clears the field, preventing stale READY reports.
- Added exact compatibility normalization for the Feishu display label
  `OrcaSlicer (Snapmaker)` to the internal `SnapmakerOrcaSlicer` identity.
- Preserved native enrichment, Preview, approval, and publication state
  transitions while isolating consistency failures from native processing.

### Photo evidence preservation

- Changed approved Update projection to field-level photo patch semantics:
  newly submitted photos replace only their corresponding fields, while
  missing or empty fields preserve existing Preset photos.
- Preserved all attachments submitted for a photo field when replacing that
  field; the Worker does not impose an artificial per-field attachment limit.
- Preserved existing Feishu attachment metadata and idempotent approval
  behavior without introducing new storage or schema fields.
- Documented that PresetVersion currently has no complete effective-photo
  snapshot fields; master Preset projection is corrected, but historical photo
  snapshots require a future schema change.

### Reliability and verification

- Added focused tests for 3MF parsing, six-slicer dispatch, Preview and Submit
  integration, validator isolation, report fallback, photo patch merging, and
  approval recovery.
- Current regression result: 217 tests passed, 1 skipped, with one known
  pre-existing diff-category expectation failure in
  `tests/test_diff_contract.py`.


## v0.2.0

Extended slicer support and unified contract.

### Slicer processing and artifact model

- Introduced an explicit, slicer-independent `SlicerProcessor` contract covering parsing, source validation, normalization, company policy, canonical validation, serialization, and diff generation.
- Added a processor registry and isolated artifact boundary so workflow services no longer depend on slicer-specific JSON/INI details.
- Added support for OrcaSlicer, CrealityPrint, ElegooSlicer, PrusaSlicer, and Snapmaker OrcaSlicer, in addition to the existing Bambu Studio processor.
- Added evidence-based artifact reconnaissance, round-trip fixtures, canonicalization rules, and regression tests for the supported slicers.
- Added a unified, slicer-neutral diff model, including CREATE initial-review diffs, stable parameter paths, change categories, and system/important/other parameter classification.
- Added an explicit whitelist for important parameters and made `pm_method_version` injection authoritative from submission context.

### Worker lifecycle and performance

- Added preview, enrichment, and publication timing instrumentation with per-stage and per-API metrics, retry counts, request/response sizes, and redacted endpoint categories.
- Reused discovered Submission records in Preview and Enrich to avoid redundant full-table scans; added native record retrieval for cases with a real Bitable record ID.
- Switched Preset lookup to an exact server-side `preset_key` filter where supported, while retaining client-side verification and duplicate detection.
- Reduced Preview and Enrich writes by combining result fields with the final status transition into one request, preserving existing lifecycle semantics.
- Optimized publication reads by refreshing the authoritative Submission record directly, reusing already-loaded PresetVersion records, and consolidating safe projection writes.
- Audited the remaining Enrich attachment download and retained it because exact byte comparison is required for canonical-artifact integrity and idempotent retries.

### Operations and reliability

- Added `backfill_slicer_version` for historical Submission records. It matches `created_at` against official slicer release metadata, supports dry-run/limit/overwrite/cache controls, and documents GitHub repository configuration.
- Added bounded retries with exponential backoff for transient Feishu timeouts and HTTP 408/429/5xx responses, while preserving one invalid-token refresh retry.
- Added regression coverage for token refresh, transient network failures, lifecycle behavior, artifact boundaries, all supported slicers, backfill behavior, and the optimized access paths.

No production latency improvement is claimed here because live Feishu before/after samples were not available; the new instrumentation is intended to provide those measurements.

## v0.1.0

- First preset processor. 
- Can validate, enrich and publish presets. 
- Support only Bambu Studio presets
