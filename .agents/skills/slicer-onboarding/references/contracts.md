# Current contracts

## Native processing

`Artifact` is opaque bytes plus filename and optional media type. `ProcessingContext` carries `pi_code`, `printer`, `slicer`, and `pm_method_version`. A processor supplies `parse`, `validate_source`, `normalize`, `apply_company_policy`, `validate_canonical`, `serialize`, and `diff`; many concrete processors also expose `process`.

Validation statuses are `valid`, `invalid_user_artifact`, `unsupported_slicer`, and `internal_processing_failure`. Native diff changes are `ADDED`, `REMOVED`, or `MODIFIED`, classified as `IMPORTANT_PARAMETER`, `SYSTEM_METADATA`, or `OTHER_PARAMETER`. Diff output must be deterministic.

Do not assume one native format: current processors include UTF-8 JSON and Prusa INI/text. Preserve unknown fields when the existing processor does so. Canonical names and `pm_method_version` are context-authoritative where the processor contract requires them.

## 3MF and consistency

Snapshots retain raw values and source paths. Resolution may select a scalar from an array only when explicit slot/cardinality evidence proves the index. `select_slot` handles identity matching and duplicate-equivalence checks. Numeric comparison normalizes numeric strings; it does not justify unverified unit conversion.

Comparison statuses currently used are exactly: `MATCH`, `MISMATCH`, `MISSING_IN_PRESET`, `MISSING_IN_3MF`, `UNRESOLVED`, `AMBIGUOUS`, and `NOT_COMPARABLE`. Selection/resolution statuses such as `UNIQUE`, `RESOLVED`, `NOT_APPLICABLE`, and `UNSUPPORTED` are different contracts; do not mix them into comparison status.

Interpretation:

- missing: source value/key is absent or empty;
- unresolved: data exists or is expected, but identity, index, mapping, or normalization cannot prove a value;
- ambiguous: multiple/unmatched array or identity interpretations remain;
- not comparable: representations differ in shape or scope;
- mismatch/match: comparable normalized values differ/equal;
- unsupported parameter: implementation coverage is absent and must be disclosed, not represented as a match.

The Feishu consistency envelope is built by `services/consistency_preview.py` and uses the existing report schema. Do not invent statuses or reason-code schemas. Preserve evidence/source paths in onboarding reports and disclose when the outer envelope collapses detailed errors.

## Parameter coverage

Check all current catalogs rather than copying one: processor-local important sets, `three_mf/comparison_core.py:PARAMETER_UNITS`, `three_mf/consistency.py:REQUIRED_PARAMETERS`, and Prusa-specific targets/mappings. For every important native parameter record native source, 3MF source, selection rule, comparison support, and evidence. Extracted-but-unresolved may be legitimate, a coverage gap, or a defect; test the full path before deciding.
