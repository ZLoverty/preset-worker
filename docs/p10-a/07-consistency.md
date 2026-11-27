# Consistency Validator

## Actual path

`consistency_preview.build_consistency_report()` selects a validator by canonical slicer id, downloads the first `preset 3mf` attachment, and invokes the validator (`services/consistency_preview.py:79-104`). Native validators parse/validate the Preset, parse the 3MF, select a slot, map values, normalize numeric values, compare, create rows/summary, and return schema `p9b2.consistency.v1`. Outer Preview/Submit writes an envelope `READY` or `ERROR`.

Native JSON slicers use `validate_native_consistency.py:80-177`; Prusa uses its separate `validate_prusa_consistency.py:58-169`. Bambu has an older dedicated path in `three_mf/consistency.py:251-355`, while Creality/Elegoo/Orca/Snapmaker are wrappers (`consistency.py:358-419`).

## Status vocabulary

Comparison statuses actually emitted: `MATCH`, `MISMATCH`, `MISSING_IN_PRESET`, `MISSING_IN_3MF`, `UNRESOLVED`, `AMBIGUOUS`, `NOT_COMPARABLE`. Resolution model additionally has `RESOLVED`, `UNSUPPORTED`, `NOT_APPLICABLE`; these are not all top-level comparison statuses. Selection uses `UNIQUE`, `UNRESOLVED`, `AMBIGUOUS`. Runtime status is explicitly `NOT_CLAIMED` or `NOT_ESTABLISHED`.

- `MISSING_*`: source key/element absent or empty.
- `UNRESOLVED`: numeric conversion, identity, slot/index, or mapping cannot prove a value.
- `AMBIGUOUS`: arrays or duplicate identity have unmatched/non-proven correspondence.
- `NOT_COMPARABLE`: scalar-vs-array shape mismatch.
- `MATCH/MISMATCH`: normalized numeric values equal/different.

Evidence and source paths are included in comparison rows, but the outer service collapses any `project_issues` or `errors` to generic `CONSISTENCY_VALIDATION_FAILED` (`consistency_preview.py:97-104`). Thus report-level diagnostics are insufficient after persistence to distinguish malformed input from unsupported coverage.

## Extracted value -> UNRESOLVED

This scenario is confirmed. The extractor preserves a parameter in `RawParameterValue`/`project_settings`; `resolve_bambu_project()` returns `UNRESOLVED` when a list has no explicit slot or verified cardinality (`bambu_parser.py:202-216`). `compare_parameter()` also returns `UNRESOLVED` on nonnumeric values (`comparison_core.py:99-106`). Native validators overwrite all comparison elements to `UNRESOLVED` when slot selection is not `UNIQUE` (`native_consistency.py:159-169`); Prusa does likewise for unverified mappings or unresolved filename identity (`prusa_consistency.py:143-150`).

Classification:

- Correctly unresolved: absent slot, ambiguous duplicate identity, unsupported array cardinality, nonnumeric value.
- Coverage gap: parameter is extracted but absent from `REQUIRED_PARAMETERS`, mapping, or unit catalog.
- Implementation defect: mapping exists but comparison uses the wrong source or turns a known missing value into `MATCH`.

The current evidence fields can usually expose the reason inside the detailed report, but the Feishu envelope loses it on `errors/project_issues`; no explicit `coverage_gap` vs `defect` reason code exists.

## Important-parameter coverage

Not complete. Native Diff important sets contain pressure advance, retraction, chamber/plate temperatures and slicer-specific fields, while consistency commonly compares only eight `REQUIRED_PARAMETERS` (`consistency.py:20-29`; Prusa `TARGET_PARAMETERS:17-26`). Several fields are extracted from project settings but never compared. This is a silent omission risk and a `BLOCKER` for claiming complete cross-slicer consistency.
