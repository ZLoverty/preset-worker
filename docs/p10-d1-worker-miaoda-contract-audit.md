# P10-D1 Worker–Miaoda Diff/Consistency Data Contract Audit

## Executive summary

This is a read-only Worker-side audit. The Worker repository is available; no Miaoda frontend repository was found in the configured GitHub workspace.

Confirmed findings:

1. Snapmaker slot selection is not the cause of the mixed display. The committed fixture resolves pla_test uniquely to slot 1.
2. comparison_rows has a serialization defect. Matched rows expose the slot-selected 3MF scalar, but missing-Preset rows fall back to the original 3MF array.
3. Native Diff and Consistency use different identities: Diff paths contain native paths such as nozzle_temperature[0]; Consistency rows use raw target names such as nozzle_temperature.
4. P10-B2.2 canonical parameter IDs are used by the catalog but are not serialized into either report.
5. Preview consistency receives candidate.source_artifact, while Native Diff is generated from candidate.canonical_artifact. This can make the displayed New Preset and the Consistency operand differ.
6. Miaoda association, status mapping, and rendering are NOT_VERIFIED because its source was unavailable.

No production code, tests, schemas, or fixtures were modified.

## Repository baseline

Worker:

- Path: C:\Users\zhengyang\Documents\GitHub\preset-worker
- Branch: dev
- Revision: 596b5aa4e8eb951a9a390a41674946c399f02e9a
- Working tree: ?? docs/p10-d1.md before this audit

The configured workspace also contains HEPiC, ws_doc, ETP, hepic_server, Boralus, zloverty.github.io, and other repositories. A search for comparison_rows, consistency_report, and the screenshot's UI labels found no Miaoda frontend source. Miaoda revision and code path are therefore NOT_VERIFIED.

## Native Diff contract

The serialized Diff shape is produced by serialize_unified_diff() in src/preset_worker/diff.py:

    {
      "schema_version": 1,
      "changes": [
        {
          "path": "nozzle_temperature[0]",
          "old_value": null,
          "new_value": "230",
          "change_type": "ADDED",
          "category": "IMPORTANT_PARAMETER"
        }
      ]
    }

Confirmed fields:

- native field path, including array index;
- old/new value;
- change type;
- category;
- schema version.

Not serialized:

- P10-B2.2 canonical parameter ID;
- native index as a separate field;
- filament identity or 3MF slot.

parameter_catalog.py supplies canonical IDs and path classification, but DiffChange does not carry the ID into the persisted Diff JSON.

## Consistency contract

p9b2.consistency.v1 contains source, selection, comparisons, comparison_rows, summary, warnings, and errors.

A Consistency row can contain:

- parameter_id, currently a raw target name such as nozzle_temperature;
- path, usually without the native [0];
- index;
- preset_value, project_value;
- native/project source paths;
- normalized operands;
- status;
- diagnostics.

Report-level selection contains filament_slot_id, matching_slot_ids, and identity evidence. Parameter rows do not contain explicit slot_index or filament_identity.

## Deterministic Snapmaker reproduction

Fixture pair:

- tests/fixtures/slicers/orca_slicer_snapmaker/pla_test.json
- tests/fixtures/slicers/orca_slicer_snapmaker/snapmaker-orca.3mf

Observed:

    selection.status = UNIQUE
    filament_slot_id = 1
    matching_slot_ids = [1]
    summary = MATCH: 3, MISSING_IN_PRESET: 5

| Parameter | Status | Preset value | Project value | Project path |
|---|---|---|---|---|
| filament_flow_ratio | MISSING_IN_PRESET | null | four-element array | $.filament_flow_ratio[0] |
| filament_max_volumetric_speed | MISSING_IN_PRESET | null | four-element array | $.filament_max_volumetric_speed[0] |
| nozzle_temperature | MATCH | 230 | 230 | $.nozzle_temperature[0] |
| nozzle_temperature_initial_layer | MATCH | 230 | 230 | $.nozzle_temperature_initial_layer[0] |
| fan_min_speed | MISSING_IN_PRESET | null | four-element array | $.fan_min_speed[0] |
| fan_max_speed | MISSING_IN_PRESET | null | four-element array | $.fan_max_speed[0] |
| fan_cooling_layer_time | MATCH | 50 | 50 | $.fan_cooling_layer_time[0] |
| slow_down_layer_time | MISSING_IN_PRESET | null | four-element array | $.slow_down_layer_time[0] |

This reproduces the screenshot's mixed scalar/array symptom at the Worker boundary.

## Root cause of the mixed 3MF shape

compare_parameter() first computes a slot-selected value through select_project_slot_value(). For a four-slot array and selected slot 1, the selected value is scalar and its path is $.name[0].

However, when the Preset key is absent, compare_parameter() returns immediately with status MISSING_IN_PRESET and no elements.

native_consistency._rows() then takes the no-elements branch and serializes:

    comparison["project"].get("raw_value")

That is the original four-element array, not the already selected scalar. Matched rows use elements and therefore show the selected scalar.

Classification: CONFIRMED WORKER_MAPPING/serialization defect. It is not slot ambiguity.

The safe output shape should be:

    project_value: "0.98"
    project_original_array: ["0.98", "0.98", "0.98", "0.98"]
    project_source_path: "$.filament_flow_ratio[0]"
    status: "MISSING_IN_PRESET"

project_value is for comparison/display; the original array is evidence only.

## Native array flattening

Snapmaker Preset fields are often one-element arrays. select_preset_value() converts a one-element Preset array to a scalar when slot-aware comparison is active. This is intentional comparison normalization; it does not mutate the uploaded artifact.

Native Diff still retains nozzle_temperature[0]. Consistency uses nozzle_temperature plus an index. These can represent the same conceptual parameter, but the Worker does not emit a shared canonical association ID.

## Source versus canonical artifact

CandidateResult contains both source_artifact and canonical_artifact. process_candidate() sets them separately.

Native Diff is calculated from the processed canonical artifact.

Preview consistency currently calls:

    validator(candidate.source_artifact, project)

in src/preset_worker/services/consistency_preview.py.

This is a confirmed source/canonical mismatch risk. If canonicalization or inheritance supplies a value, Native Diff may display a New Preset value while Consistency still sees the original key as absent.

Classification: CONFIRMED WORKER_CONTRACT_GAP / WORKER_MAPPING_DEFECT.

The correct choice depends on the product contract, but the behavior must be made explicit and regression-tested. The screenshot's table implies that consistency should compare the same New Preset artifact that is being displayed.

## Canonical parameter identity

The catalog contains stable IDs, for example:

| Native path | Catalog ID |
|---|---|
| filament_flow_ratio | filament.flow_ratio |
| filament_max_volumetric_speed | filament.max_volumetric_speed |
| pressure_advance | pressure.advance |

Current Diff and Consistency JSON do not expose these IDs.

Therefore a frontend cannot safely associate:

    Native Diff:  nozzle_temperature[0]
    Consistency: nozzle_temperature

by an explicit Worker-provided identity. Globally removing [0] is unsafe because Native indices are not automatically 3MF filament slots and multi-element Native arrays may be meaningful.

Classification: CONFIRMED WORKER_CONTRACT_GAP.

## Parameter trace

The original screenshot payloads were unavailable. The following is based on Worker code and the committed fixture.

| Parameter | Native Diff | Consistency | Classification |
|---|---|---|---|
| nozzle_temperature | native path has [0] | selected slot scalar, path has [0] | same fixture target is plausible; no canonical association ID |
| nozzle_temperature_initial_layer | native path has [0] | selected slot scalar | same limitation |
| fan_max_speed | native path can have [0] | scalar when operand exists; raw array when Preset is missing | Worker row serialization defect |
| fan_cooling_layer_time | native path has [0] | scalar MATCH in fixture | valid fixture comparison; no canonical ID |
| filament_flow_ratio | catalog target | MISSING_IN_PRESET, raw array leaked | Worker row serialization defect |
| filament_max_volumetric_speed | catalog target | MISSING_IN_PRESET, raw array leaked | Worker row serialization defect |
| pressure_advance | Native important parameter can appear | not in current eight-parameter Consistency target list | CONSISTENCY_COVERAGE_GAP |
| textured_plate_temp | Native important parameter can appear | not in current target list | CONSISTENCY_COVERAGE_GAP |

Equal numeric values must not be used to infer a missing mapping.

## Status semantics

Worker semantics are:

| Status | Meaning |
|---|---|
| MATCH | both operands present and normalized equal |
| MISMATCH | both operands present and unequal |
| MISSING_IN_PRESET | Preset operand absent/null |
| MISSING_IN_3MF | 3MF operand absent/null |
| UNRESOLVED | identity, numeric, or mapping unresolved |
| AMBIGUOUS | correspondence not proven |
| NOT_COMPARABLE | operand shapes are incompatible |

The UI must not infer MATCH merely because the 3MF value is non-empty. A row with Preset null and 3MF present is MISSING_IN_PRESET, not MATCH.

Miaoda's exact status translation and whether it preserves P10-B2.3 diagnostics are NOT_VERIFIED.

## Root-cause classification

| Symptom | Classification |
|---|---|
| Mixed scalar/four-element 3MF values | WORKER_MAPPING_DEFECT |
| Native [0] versus Consistency unindexed names | WORKER_CONTRACT_GAP |
| No canonical ID in serialized rows | WORKER_CONTRACT_GAP |
| Native Diff and Consistency use different Preset artifacts | WORKER_MAPPING_DEFECT |
| pressure_advance/textured_plate_temp absent from Consistency | CONSISTENCY_COVERAGE_GAP |
| Four Snapmaker slots cannot be selected | disproved for committed fixture |
| Rows remain separate in Miaoda | NOT_VERIFIED; possible MIAODA_ASSOCIATION_DEFECT |
| Green MATCH with Preset shown as dash | NOT_VERIFIED; possible MIAODA_PRESENTATION_DEFECT or stale report |

## Minimal backward-compatible contract

Worker:

1. Preserve existing fields and schema versions.
2. Add optional canonical identity to Diff and Consistency rows, without changing the meaning of existing parameter_id.
3. Add optional native_index, slot_index, filament_slot_id, and filament_identity only where established by source evidence.
4. Emit selected project_value separately from project_original_array.
5. Decide explicitly whether Consistency uses source or canonical Preset; add a Preview regression test.

Miaoda:

1. Prefer an explicit canonical ID for association.
2. Use exact path/index only as a secondary check.
3. Do not globally strip [0].
4. Preserve unverified rows when metadata is absent.
5. Render Worker status directly.
6. Display selected slot value; show the original array only as evidence.

Historical reports without new fields remain readable but must be treated as unverified for automatic association.

## Ownership

| Concern | Owner |
|---|---|
| Canonical parameter IDs | Worker |
| Native path/index metadata | Worker |
| 3MF slot selection | Worker |
| Selected operand and array evidence | Worker |
| Report parsing | Miaoda |
| Cross-report association | Miaoda, using Worker metadata |
| Grouping and rendering | Miaoda |

Miaoda should not recreate slot selection or maintain an independent full parameter catalog.

## Proposed P10-D2 plan

### D2-A Worker row correction

Fix comparison_rows so missing-Preset rows expose the selected slot scalar and preserve the original array separately. Add Snapmaker regression assertions for all eight target parameters and the absence of false MATCH.

### D2-B Worker identity enrichment

Serialize optional catalog-backed canonical IDs and established slot/index metadata. Keep historical fields and schema versions.

### D2-C Miaoda source audit

Obtain the actual frontend repository, identify parsing/merge/render functions, and reproduce using the exact Worker JSON. Confirm whether [0] normalization or status inference causes the observed separate rows.

### D2-D Miaoda correction

Associate by canonical ID, preserve unverified mappings, render selected values, and faithfully map Worker statuses.

## Evidence limitations

- Miaoda source and revision were unavailable.
- The exact screenshot JSON payloads were unavailable.
- The committed Snapmaker fixture reproduces the mixed array/scalar Worker output but not the screenshot's exact numeric values.
- The report therefore confirms the Worker defect and contract gaps, but not the exact Miaoda association implementation.

## Acceptance status

| Criterion | Status |
|---|---|
| Worker Diff/Consistency contracts documented | CONFIRMED |
| Validation versus Diff ownership | CONFIRMED |
| Worker fixture reproduction | CONFIRMED |
| Snapmaker slot semantics | CONFIRMED |
| Mixed scalar/array defect | CONFIRMED |
| Canonical IDs absent from serialized rows | CONFIRMED |
| Miaoda parser/merge/render pipeline | NOT_VERIFIED |
| Exact screenshot end-to-end reproduction | NOT_VERIFIED |
| Production code modified | NO |
| Report schema modified | NO |

