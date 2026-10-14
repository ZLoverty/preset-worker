# Release Notes

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
