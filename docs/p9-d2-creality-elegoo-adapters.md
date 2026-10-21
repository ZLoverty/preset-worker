# P9-D2 CrealityPrint & ElegooSlicer Consistency Adapters

## Implemented entry points

- `validate_creality_consistency(...)`
- `validate_elegoo_consistency(...)`

Both are exported from `preset_worker.three_mf` and are independently callable
with `Artifact` objects. They are not registered with Preview dispatch.

## Architecture

The adapters use:

- `CrealityPrintProcessor` or `ElegooSlicerProcessor` for native JSON parsing,
  validation, and normalization;
- `parse_bambu_3mf()` and `SafeZipReader` for the compatible project archive
  path;
- `comparison_core.select_slot()` for exact identity and slot selection;
- `comparison_core.compare_parameter()` for all stored-value comparison;
- `native_consistency.validate_native_consistency()` for the minimal shared
  report orchestration.

No second comparison engine or slicer registry was added.

## Identity and comparison behavior

The native Preset `filament_settings_id` is matched exactly against project
`filament_settings_id`. The supplied real fixtures resolve `pla_test` to slot 1
with status `UNIQUE`. No fallback to the first slot, `filament_ids`, `base_id`,
or parameter equality is used.

When identity is unresolved, raw values may remain in the report for evidence,
but comparison statuses are changed to `UNRESOLVED`; stored equality is never
reported as a match without slot identity.

Verified project arrays are selected by the D1 shared core. Original values,
source paths, and array indexes remain available in `comparisons` and
`comparison_rows`.

Runtime-effective equivalence is not established for either slicer, so adapter
comparisons use `runtime_effective_status=NOT_ESTABLISHED`.

## Real fixture results

| Slicer | Identity | MATCH | Missing in Preset | Verified matches |
|---|---|---:|---:|---|
| CrealityPrint | slot 1, `pla_test` | 3 | 5 | `nozzle_temperature`, `nozzle_temperature_initial_layer`, `fan_cooling_layer_time` |
| ElegooSlicer | slot 1, `pla_test` | 4 | 4 | `nozzle_temperature`, `nozzle_temperature_initial_layer`, `fan_min_speed`, `fan_cooling_layer_time` |

Reports use `p9b2.consistency.v1` and correctly identify `source.slicer` as
`CrealityPrint` or `ElegooSlicer`.

## Negative coverage

The adapter tests cover missing and mismatched identity, native Preset identity
validation, explicit parameter mismatch, numeric string/number normalization,
missing project configuration, malformed project JSON, and unsafe ZIP input.
The shared D1 tests cover duplicate identities, conflicting values, incomplete
evidence, malformed arrays, scalar/array mismatch, and unproven slot indexing.

## Limitations

- Preset inheritance is not expanded.
- Stored-value equality is not runtime-effective equality.
- PrusaSlicer, OrcaSlicer, and SnapmakerOrcaSlicer are not enabled by this
  phase.
- No Preview, Feishu, Miaoda, approval, or publication behavior changed.

## Test status

Focused D2/D1/Bambu tests pass. The full suite retains the known unrelated
`tests/test_diff_contract.py` baseline failure where `temperature` is classified
as `OTHER_PARAMETER` instead of the test's expected `IMPORTANT_PARAMETER`.
