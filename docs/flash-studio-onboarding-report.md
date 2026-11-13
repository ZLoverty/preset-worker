# Flash Studio Onboarding Report

## Result

Flash Studio is now registered under the canonical Worker ID `FlashStudio`.
Native JSON processing uses a dedicated facade over the shared Orca-compatible
JSON mechanics, while preserving a distinct slicer identity in registry,
classification, errors, and consistency reports.

## Implemented

- Added `FlashStudioProcessor` with fixture-backed `version` validation,
  normalization, company policy, serialization, and native diff behavior.
- Added Flash-specific catalog paths for the proven target fields, pressure
  advance, textured plate temperature, and lower nozzle range.
- Added Flash-specific system metadata paths.
- Added dedicated `validate_flash_studio_consistency()` and Preview/Submit
  dispatch registration.
- Added registration, Native, 3MF consistency, mismatch, Preview, and Submit
  regression coverage.

## Evidence

The supplied pair remains unchanged:

- `tests/fixtures/slicers/flash_studio/pla ff creator 5.json`
- `tests/fixtures/slicers/flash_studio/pla ff creator 5.3mf`

The real pair produces `source.slicer = FlashStudio`, duplicate-equivalent
selection with matching slots `[1, 2, 3, 4]`, and eight `MATCH` target rows.
A controlled change to all matching project slot nozzle temperatures produces
`MISMATCH`.

Verification: `268` unittest cases passed, with `2` pre-existing skips.

## Deliberate limitations

- `hot_plate_temp` is preserved as an ordinary native field and is not a
  consistency target; its computed firmware semantics are not proven.
- `textured_plate_temp` is classified as a stored native setting, but no
  runtime-effective claim is made.
- The Bambu/Orca metadata in the 3MF proves parser compatibility only. It does
  not prove Flash Studio's upstream fork, export provenance, or semantic
  identity with BambuStudio/OrcaSlicer.
- Four equivalent slots are accepted only through the existing equivalence
  proof; no first-slot fallback was introduced.
- Density, extruder variant, plate temperatures, and other non-target fields
  remain outside the 3MF consistency target set.
