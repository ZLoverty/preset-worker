# P9-D3 OrcaSlicer & SnapmakerOrcaSlicer Consistency Adapters

## Entry points

- `validate_orca_consistency(...)`
- `validate_snapmaker_orca_consistency(...)`

Both are exported from `preset_worker.three_mf`. They are isolated callable
validators and are not registered with production Preview dispatch.

## Reused infrastructure

The adapters use the existing native processors:

- `OrcaSlicerProcessor`
- `SnapmakerOrcaSlicerProcessor`

They share `native_consistency.validate_native_consistency()`,
`parse_bambu_3mf()`, `SafeZipReader`, `comparison_core.select_slot()`, and
`comparison_core.compare_parameter()`. No second comparison engine, ZIP parser,
or slicer registry was introduced.

## Real fixture results

### OrcaSlicer

- Preset identity: `L2002CF @BBL P2S`
- Matching project slots: `[1, 4]`
- Both matching slots have equivalent values for all eight target parameters.
- Selected slot: `1`
- Selection status: `UNIQUE`
- Internal reason: `MULTIPLE_EQUIVALENT`
- Stored-value result: `MATCH=3`, `MISSING_IN_PRESET=5`

The selected project source paths retain the original slot index, for example
`$.nozzle_temperature[0]`; the complete original four-element array remains in
the comparison evidence.

### SnapmakerOrcaSlicer

- Preset identity: `pla_test`
- Matching project slots: `[1]`
- Selected slot: `1`
- Selection status: `UNIQUE`
- Stored-value result: `MATCH=3`, `MISSING_IN_PRESET=5`

The `.info` sidecar is not used as the Preset object or as a substitute for
`filament_settings_id`. Unrelated slots do not create array ambiguity after
slot selection.

## Report compatibility

Both validators emit `p9b2.consistency.v1` reports with the correct
`source.slicer` value, `selection.matching_slot_ids`, comparison rows, source
paths, original arrays, and existing status vocabulary. Runtime-effective
equivalence is not claimed; every comparison uses
`runtime_effective_status=NOT_ESTABLISHED`.

Identity mismatch or unresolved identity does not produce a misleading MATCH.
Raw values remain available as evidence, while comparison statuses become
`UNRESOLVED` until a project slot is identified.

## Test coverage

The D3 tests cover the real Orca duplicate identity, real Snapmaker unique
identity, selected-slot mismatch, missing identity, missing project member,
malformed project JSON, unsafe ZIP input, report rows, and runtime status. D1
tests continue to cover conflicting and incomplete duplicate identities,
unproven array cardinality, scalar/array mismatch, and numeric normalization.

## Limitations and next step

- Preset inheritance and runtime-effective filament assignment remain outside
  the stored-value validator.
- No Preview, Feishu, Miaoda, approval, or publication behavior changed.
- PrusaSlicer consistency remains unimplemented.

P9-D4 should audit the complete cross-slicer Preview integration boundary and
define the production enablement criteria; it should not enable routing until
those criteria are explicitly approved.
