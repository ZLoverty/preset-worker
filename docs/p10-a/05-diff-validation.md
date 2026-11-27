# Diff and Validation

## Diff contract

`diff.py:8-48` defines `ChangeType` (`ADDED`, `REMOVED`, `MODIFIED`), `DiffCategory` (`IMPORTANT_PARAMETER`, `SYSTEM_METADATA`, `OTHER_PARAMETER`), `DiffChange`, and `UnifiedDiff`. Processor-local flatteners compare scalar leaf paths including array indexes and sort by path for deterministic output. Prusa additionally compares artifact filename and INI keys (`slicers/prusa_slicer.py:177-212`).

There is no single important-parameter catalog. Sets are duplicated in `bambu_studio.py:42-57`, `orca_compatible_core.py:13-27`, Creality, Elegoo, Snapmaker, and Prusa's INI mapping. `three_mf/comparison_core.py:13-22` has a separate unit catalog; `three_mf/consistency.py:20-40` has a separate eight-item required set. This is `CONFIRMED` and is the principal source of drift.

The six processors all expose `important_parameter_paths`, but categories are local. The current tests (`tests/test_fixture_field_classification.py:70-145`) demonstrate the intended catalog is broader than the implementation: pressure advance, retraction, chamber/cool-plate and extruder variant are expected important, but currently classify as `OTHER_PARAMETER`.

## Validation

Shared contract statuses are `valid`, `invalid_user_artifact`, `unsupported_slicer`, `internal_processing_failure` (`contracts.py:12-17`). Processor validation is primarily structural and format-specific; unknown fields are preserved, not rejected. No general version compatibility policy or parent existence validation exists. Publication does not automatically block on every warning because warnings are separate from `valid` status.

`enrichment.py:603-628` converts unsupported slicer and processor failures into machine-readable validation; invalid processed artifacts do not upload canonical output. This is mandatory for native processing.

## Regression evidence

Under the available environment, unittest reports five classification failures:

- Elegoo `filament_extruder_variant` expected important.
- Creality/Elegoo/Orca project fields expected important.
- Prusa `filament_density`, `filament_diameter`, `cooling`, `extrusion_multiplier` expected important.

These are existing audit evidence, not repaired in P10-A. One Prusa consistency test also expects missing preset to remain `MISSING_IN_PRESET` but observed `MATCH`, indicating a separate mapping/fixture contract defect.

## Minimum new-slicer validation

Required: exact accepted extension/encoding, top-level shape, slicer preset type, identity fields, context-authoritative name/version metadata, canonical filename/media type, malformed input behavior, and deterministic diff. Conditional: printer compatibility, inheritance, and version support only when the format contains those semantics.
