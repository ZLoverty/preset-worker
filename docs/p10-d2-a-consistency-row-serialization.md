# P10-D2-A Consistency Row Serialization Fix

## 1. Scope and baseline

This phase implemented only the confirmed flattened Consistency row serialization fix. It did not change Native Diff, Consistency target coverage, Feishu schema, Miaoda code, or public schema version.

Baseline before implementation:

- Branch: dev
- Revision: f413c7fd00e47430237424317e52f9cd285590b7
- Existing untracked file: docs/p10-d2-a.md
- Focused baseline: 64 tests passed
- Full baseline: 269 tests passed, 2 skipped
- compileall: passed

## 2. Confirmed root cause

For a valid Snapmaker slot selection, compare_parameter() already selected the correct project operand. For example, a four-element project array and slot 1 produced:

    selected value: "0.98"
    source path: $.filament_flow_ratio[0]
    original array: ["0.98", "0.98", "0.98", "0.98"]

When the Preset parameter was absent, compare_parameter() returned with no comparison elements. native_consistency._rows() then used the project's raw_value, exposing the entire four-element array in the flattened row.

This was a Worker serialization defect, not a slot-resolution defect.

Status remains MISSING_IN_PRESET. No missing operand is converted to MATCH.

## 3. Implementation

Changed files:

- src/preset_worker/three_mf/comparison_core.py
- src/preset_worker/three_mf/native_consistency.py
- tests/test_comparison_core.py
- tests/test_p9_d3.py
- docs/p10-d2-a-consistency-row-serialization.md

### Comparison object

The comparison object now retains selected operands explicitly:

- preset.selected_value
- project.selected_value

Existing raw_value and original_array fields remain available.

This avoids repeating slot selection in the serializer and keeps comparison_core as the only selection source.

### Flattened rows

The no-elements row path now emits selected values:

    preset_value = preset.selected_value
    project_value = project.selected_value

It also exposes optional evidence fields:

    preset_original_array
    project_original_array

For rows with elements, the same original-array evidence is added without changing existing element values, source paths, statuses, or normalized values.

Expected valid-selection output:

    {
      "parameter_id": "filament_flow_ratio",
      "preset_value": null,
      "project_value": "0.98",
      "project_original_array": ["0.98", "0.98", "0.98", "0.98"],
      "project_source_path": "$.filament_flow_ratio[0]",
      "status": "MISSING_IN_PRESET"
    }

## 4. Edge-case behavior

The implementation preserves the existing rules:

- Single-element project arrays can resolve to their only value.
- Arrays whose length equals the explicit slot count resolve using the selected one-based slot.
- Missing Preset values remain MISSING_IN_PRESET.
- Missing 3MF values remain MISSING_IN_3MF.
- Equal operands remain MATCH.
- Unequal operands remain MISMATCH.
- Invalid numeric operands remain UNRESOLVED.
- Shape-incompatible operands remain NOT_COMPARABLE.
- Ambiguous or unresolved selection does not fabricate a scalar.
- When slot_id is None, selected_value remains the original array.
- Original arrays remain available through original_array and flattened *_original_array evidence.

No second slot-selection algorithm was introduced.

## 5. Snapmaker regression evidence

The committed pair remains:

- tests/fixtures/slicers/orca_slicer_snapmaker/pla_test.json
- tests/fixtures/slicers/orca_slicer_snapmaker/snapmaker-orca.3mf

The report still resolves:

    selection.status = UNIQUE
    filament_slot_id = 1
    matching_slot_ids = [1]
    summary = MATCH: 3, MISSING_IN_PRESET: 5

All eight targets are asserted.

For the five missing-Preset targets, tests now assert:

- preset_value is None;
- project_value is the selected slot-1 scalar;
- project_original_array retains the four-slot source array;
- project_source_path identifies slot index 0;
- status remains MISSING_IN_PRESET.

For the three MATCH targets, tests assert the selected scalar and slot source path remain unchanged.

## 6. Source versus canonical artifact audit

Confirmed flow:

1. process_candidate() downloads the submitted Preset into source_artifact.
2. process_artifact() produces canonical_artifact.
3. Native Diff is calculated against canonical_artifact.
4. canonical_artifact is uploaded/persisted as canonical_json.
5. Both Preview and formal Submit call build_consistency_report().
6. build_consistency_report() currently passes candidate.source_artifact to the validator.

Current Orca-compatible normalization is a deep copy. Company policy primarily injects canonical metadata such as name and pm_method_version. The existing code does not establish a general effective-value or inheritance expansion contract in the Consistency path.

Evidence status:

- source/canonical separation: CONFIRMED
- current Consistency input is source_artifact: CONFIRMED
- current canonical artifact persistence: CONFIRMED
- canonicalization changes the target parameter values for current Snapmaker/Orca processors: NOT_VERIFIED as a general product guarantee
- product requirement that Consistency must use canonical_artifact: NOT_VERIFIED

Decision for P10-D2-A: do not change artifact selection.

Changing source_artifact to canonical_artifact without an established product contract could alter historical behavior and silently change inheritance/value semantics. The exact decision should be made in a later phase with a dedicated test where source and canonical target values differ.

The current mismatch remains a documented compatibility risk.

## 7. Compatibility

Preserved:

- p9b2.consistency.v1
- existing comparison status meanings
- existing eight Consistency targets
- selection and identity rules
- P10-B2.3 diagnostics
- Preview/Submit error sanitization
- Feishu fields and publication behavior
- Native Diff behavior

Added fields are optional evidence fields. Existing consumers that ignore unknown fields remain compatible. Existing required fields keep their names and meanings; project_value now correctly represents the selected operand instead of leaking raw source arrays.

No canonical parameter IDs were added in this phase.

## 8. Test results after implementation

Focused Consistency/catalog suite:

    Ran 67 tests
    OK

Preview/Submit/enrichment suite:

    Ran 38 tests
    OK

Full suite:

    Ran 272 tests
    OK (skipped=2)

Additional checks:

- python -m compileall -q src tests: passed
- git diff --check: passed

The full-suite output includes expected test logging for intentionally simulated Feishu failures, validator exceptions, and runtime failure handling. No test failed.

## 9. Remaining limitations

1. Native Diff and Consistency still do not share serialized canonical parameter IDs.
2. The exact Miaoda merge/render implementation remains unavailable.
3. Preview and Submit still compare source_artifact while Native Diff persists canonical_artifact.
4. pressure_advance and textured_plate_temp remain outside the current eight-parameter Consistency target set.
5. Historical reports do not contain selected-value/original-array evidence fields.

## 10. Recommended P10-D2-B work

1. Inspect the actual Miaoda repository and trace parsing, row association, grouping, and status rendering.
2. Decide the source versus canonical artifact contract using a test where target values differ.
3. Add optional catalog-backed canonical IDs to both report families only after verifying all slicer mappings.
4. Add end-to-end Worker-to-Miaoda tests using serialized Snapmaker rows.
5. Keep unresolved association explicit; do not globally remove native array indexes.

