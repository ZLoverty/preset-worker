# P9-B2 Implementation Report

## Status

COMPLETE_WITH_LIMITATIONS

The visible p9-b.md document ends during section 6, immediately after “If”. The implementation therefore follows all requirements visible before that point and records the missing remainder as a limitation.

## Added

- src/preset_worker/three_mf/consistency.py
- src/preset_worker/three_mf/validator_cli.py
- tests/test_p9_b2.py

The package export now includes validate_bambu_consistency.

## Behavior

The validator:

1. Uses BambuStudioProcessor to parse and validate submitted preset JSON.
2. Preserves original and canonical preset SHA-256 fingerprints.
3. Parses the 3MF through the P9-B1.1 parser.
4. Matches a project filament slot by exact filament_settings_id.
5. Compares exactly eight parameters.
6. Normalizes numeric strings with Decimal.
7. Produces MATCH/MISMATCH only when both values are reliably resolved.
8. Produces MISSING_IN_PRESET, MISSING_IN_3MF, UNRESOLVED, AMBIGUOUS, and NOT_APPLICABLE-style evidence instead of guessing.
9. Keeps fan_cooling_layer_time and slow_down_layer_time independent.
10. Emits a serializable p9b2.consistency.v1 report.
11. Emits deterministic flat comparison_rows using the existing UnifiedDiff leaf-path convention, such as nozzle_temperature[0].

## CLI

    .venv/bin/python -m preset_worker.three_mf.validator_cli compare preset.json project.3mf --output report.json

The CLI is standalone and does not require Feishu credentials.

## Tests

The P9-B1.1 and P9-B2 focused tests pass: 20 passed after the element-wise and table-row updates.

The current fixture used for verification is:

    downloads/3mf-fixture/PPS100CF10 H2D (1).json
    downloads/3mf-fixture/PPS100CF10 H2D (1).3mf

Its comparison produced:

- flow ratio, maximum volumetric speed, and both nozzle temperature parameters: index 0 MATCH; index 1 MISSING_IN_PRESET because the preset stores nil.
- fan_min_speed and fan_max_speed: MISSING_IN_PRESET because the preset JSON omits them.
- fan_cooling_layer_time and slow_down_layer_time: index 0 MATCH.
- every array element is also emitted as a flat row, for example filament_flow_ratio[0] and filament_flow_ratio[1].

No comparison result is inferred from a default or from the first array element.

The full pytest suite currently reports 149 passed, 1 skipped, and 1 pre-existing failure in test_diff_contract.py concerning the classification of the generic temperature field.

## Limitations

- No complete Bambu inheritance engine.
- No runtime G-code verification.
- No multiple-slot real fixture.
- No Worker lifecycle or Feishu integration.
- The source p9-b.md is incomplete, so requirements after section 6 could not be verified.

## P9-B2.1 update

Stored arrays are now compared element by element. The validator does not require slot or nozzle-variant resolution for this comparison. Equal-length arrays compare same indexes; different lengths are AMBIGUOUS and preserve unmatched elements; scalar versus array is NOT_COMPARABLE. Numeric strings and numbers use the existing parameter-specific numeric normalization.

The report separates parameter-level status from element-level status and includes comparison_scope, original arrays, source paths, normalized values, and runtime_effective_status. Equal stored elements do not imply runtime-effective consistency.

It also exposes comparison_rows, a deterministic flat list using the existing UnifiedDiff path convention. Array elements are rows such as nozzle_temperature[0] and nozzle_temperature[1], with no need for frontend-side array splitting.
