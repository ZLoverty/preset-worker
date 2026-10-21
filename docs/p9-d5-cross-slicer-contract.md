# P9-D5 Cross-Slicer Consistency Contract

## Canonical identifiers and validators

| Slicer identifier | Validator |
|---|---|
| `BambuStudio` | `validate_bambu_consistency` |
| `CrealityPrint` | `validate_creality_consistency` |
| `ElegooSlicer` | `validate_elegoo_consistency` |
| `OrcaSlicer` | `validate_orca_consistency` |
| `SnapmakerOrcaSlicer` | `validate_snapmaker_orca_consistency` |
| `PrusaSlicer` | `validate_prusa_slicer_consistency` |

These identifiers are verified from `slicer_id` declarations and
`default_processor_registry()`. They must be used exactly; display labels must
not be normalized into a different key.

## Input Artifact contract

Each validator accepts:

```python
Artifact(content: bytes, filename: str, media_type: str | None)
```

The Preset is the native artifact already downloaded by
`SubmissionEnrichment.process_candidate`; the project is the first `preset
3mf` attachment. Validators are pure with respect to Feishu and do not mutate
either artifact. Optional `ProcessingContext` is accepted by all current
entry points.

## Common report contract

All six real-fixture reports use `p9b2.consistency.v1` and the following common
top-level fields:

```text
schema_version
source
artifacts
preset
selection
comparisons
comparison_rows
summary
warnings
errors
```

Required common meanings:

| Field | Meaning | Required |
|---|---|---|
| `schema_version` | `p9b2.consistency.v1` | yes |
| `source.slicer` | canonical slicer identifier | yes |
| `artifacts` | Preset/project/canonical SHA-256 evidence | yes when validation reaches artifact processing |
| `preset` | native validity, identity, original parameters | yes |
| `selection` | identity status, selected slot, matching slots, evidence | yes when project processing reaches selection |
| `comparisons` | one item per canonical target parameter | yes for a parsed project |
| `comparison_rows` | flattened element-wise comparison rows | yes for a parsed project |
| `summary` | status counts from `comparisons` | yes for a parsed project |
| `warnings/errors` | non-fatal and fatal diagnostics | yes |

Invalid input may return a partial report with `errors` and no comparisons;
that is an explicit error result, not a successful empty comparison.

## Canonical parameter order

The required order is:

```text
filament_flow_ratio
filament_max_volumetric_speed
nozzle_temperature
nozzle_temperature_initial_layer
fan_min_speed
fan_max_speed
fan_cooling_layer_time
slow_down_layer_time
```

Current validators iterate this tuple. D6 should add a contract test that
asserts both `comparisons` and the first occurrence order in
`comparison_rows`.

## Status semantics

| Status | Meaning | UI treatment |
|---|---|---|
| `MATCH` | Stored values normalize equivalently after identity/slot resolution | positive stored-value result only |
| `MISMATCH` | Both stored values resolve and differ | show difference |
| `MISSING_IN_PRESET` | Project value exists but native Preset field is absent/null | show missing, not mismatch |
| `MISSING_IN_3MF` | Preset value exists but project field is absent | show missing project value |
| `UNRESOLVED` | Identity, mapping, value, or evidence is insufficient | show unresolved reason |
| `AMBIGUOUS` | Multiple possible slots/array interpretations conflict or are incomplete | show ambiguity |
| `NOT_COMPARABLE` | Proven source types/shapes cannot be safely compared | show not comparable |
| `NOT_APPLICABLE` | Parameter is outside the slicer's applicable runtime semantics | do not show as match |
| `NOT_ESTABLISHED` | Runtime-effective equivalence has not been established | uncertainty badge, never verified |

`NOT_ESTABLISHED` is currently a runtime field value, not a comparison status.
The frontend must keep it separate from stored-value status.

## Identity and selection evidence

| Slicer | Identity method | Fixture evidence |
|---|---|---|
| BambuStudio | native `filament_settings_id` | exact slot 1 |
| CrealityPrint | native `filament_settings_id` | exact slot 1 |
| ElegooSlicer | native `filament_settings_id` | exact slot 1 |
| OrcaSlicer | native exact identity with duplicate-equivalent slots | matching `[1,4]`, representative slot 1, reason `MULTIPLE_EQUIVALENT` |
| SnapmakerOrcaSlicer | native exact identity | slot 1 |
| PrusaSlicer | explicit filename stem fallback, exact project profile match | `pla_test.ini` → `pla_test` → slot 1 |

Filename identity is adapter-scoped to PrusaSlicer. It must not become a global
fallback. `matching_slot_ids` and evidence are required for UI explanation.

## Provenance and original values

`comparison_rows` carries parameter ID, path, raw Preset/project values,
normalized values when available, source paths, index, and status. Multi-slot
reports retain the original project array in the comparison object and identify
the selected source index.

Prusa native paths are adapter-specific but explicit, for example:

```text
Preset: ini.temperature
Project: Metadata/Slic3r_PE.config:temperature[0]
```

Orca and Bambu-style paths use JSON paths such as `$.nozzle_temperature[0]`.
This is additive provenance, not a frontend branching requirement.

## Slicer-specific verified limitations

- Orca: duplicate slots 1 and 4 are equivalent for all eight target arrays in
  the supplied fixture; this does not prove runtime assignment.
- Snapmaker: three Preset-side parameters are available; five remain missing.
- Creality: three Preset-side parameters are available; five remain missing.
- Elegoo: four Preset-side parameters are available; four remain missing.
- Prusa: six mappings are verified; flow ratio and max volumetric speed remain
  unresolved.
- Bambu: runtime resolution has Bambu-specific behavior and must not be
  generalized to other slicers.

## Fingerprint and envelope behavior

The report has SHA-256 evidence under `artifacts`, but no dedicated
`fingerprint` field. The complete Feishu value is an outer envelope:

```json
{"status":"READY","generated_at":"...","report":{}}
```

`generated_at` changes per Preview, so a byte-for-byte envelope comparison is
not a stable equality test. D6 should define an input/report fingerprint from
the artifact hashes and validator identity for stale detection and idempotency.

## Feishu and frontend consumption

The current backend writes the compact envelope as text to
`consistency_report`; it does not write a report attachment. The deployed field
type/limit is not verified in this repository. The frontend should parse the
envelope, distinguish empty/READY/ERROR, and use `report.comparison_rows` for a
single unified table.

Without a 3MF, the existing native `diff` remains the Preset-only source. With
a 3MF, the future unified view can add consistency columns without treating
the consistency report as a replacement for the native diff.

Miaoda implementation availability is NOT_VERIFIED. D6 must validate the
actual consumer before removing or duplicating any legacy Diff presentation.

## Contract test requirements for D6

The test should execute all six validators on their paired fixtures and assert:

1. schema ID and required top-level keys;
2. exact canonical parameter order;
3. allowed status vocabulary and value types;
4. correct `source.slicer`;
5. serializability with `allow_nan=False`;
6. stable inner report hash for unchanged inputs;
7. expected selection distinctions for Orca, Snapmaker, and Prusa;
8. additive unknown fields do not break a tolerant consumer;
9. all real report sizes are below the verified Feishu limit.
