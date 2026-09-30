# ElegooSlicer Artifact Analysis (P7.5-A)

## Provenance

- ElegooSlicer application version: `1.5.2.5`
- Native preset `version`: `1.5.3.5` (recorded as preset metadata, not assumed to be the application version)
- Source supplied by user: `tests/fixtures/slicers/elegoo_slicer/pla_test.json`
- Preserved original: `source_original.json`
- Source filename: `pla_test.json`
- Extension: `.json`
- Source size: `361` bytes
- Source SHA-256: `e50511ce9a0b9c0a488e13b6c67adc20909fe84b657affa845efa94e18610f62`

The application version comes from the user's GUI test report. No version is inferred from the native preset `version` field.

## Container and import-unit assessment

The artifact is valid plain JSON with a top-level object. It has no ZIP/archive/3MF signature and contains no external member files. The evidence confirms one individual JSON preset is the import/export unit. The baseline and three controlled variants all imported successfully and were exported.

The existing opaque `Artifact(content: bytes, filename, media_type)` abstraction can represent this file unchanged. No architecture or generic contract change is justified during reconnaissance.

## Observed structure

Top-level keys:

```text
fan_cooling_layer_time
fan_min_speed
filament_extruder_variant
filament_settings_id
from
inherits
name
nozzle_temperature
nozzle_temperature_initial_layer
version
```

The source appears to be a user filament/material preset because `from` is `User`, `filament_settings_id` is present, and the object includes a parent preset and material/process parameters. Most parameter values are one-element string arrays.

## Candidate semantics (not confirmed until GUI round-trip)

| Field | Observed value | Candidate role | Confidence |
|---|---|---|---|
| `name` | `pla_test` | visible preset name and possible logical identity | candidate; name-only test generated |
| `filament_settings_id` | `pla_test` | internal/material settings identity | candidate; identity test generated |
| `inherits` | `Elegoo PLA @EC` | parent/inheritance reference | strong structural candidate; preserved in all variants |
| `filament_extruder_variant` | `Direct Drive Standard` | extruder compatibility/material metadata | candidate parameter; not mutated |
| `from` | `User` | source/origin metadata | candidate metadata |
| `version` | `1.5.3.5` | native preset/schema version | candidate version metadata |

No `base_id`, UUID, vendor ID, printer ID, or separate profile ID was observed. No identity-looking field besides `filament_settings_id` was mutated.

## Comparison with existing slicers

This is a descriptive comparison only; it does not establish shared semantics.

| Aspect | ElegooSlicer artifact | Orca/Creality observed artifacts | Bambu implementation baseline |
|---|---|---|---|
| Container | plain JSON object | plain JSON object | plain JSON object |
| Visible-name candidate | `name` | `name` | `name` |
| Material identity candidate | `filament_settings_id` | `filament_settings_id` observed | slicer-specific fields vary |
| Inheritance | `inherits: Elegoo PLA @EC` | `inherits` string | `inherits` commonly present |
| Parameter shape | one-element string arrays | one-element string arrays in tested exports | broader JSON shapes |
| Native version | `1.5.3.5` | slicer-specific value | `version` required by Bambu validation |
| Custom metadata | JSON permits exploratory field | must be GUI-tested per slicer | Worker injects metadata in processor |

Shared names and JSON shape are not treated as proof of shared import, identity, or round-trip behavior.

## Initial conclusion

ElegooSlicer is compatible with the existing opaque Artifact boundary as one JSON import unit. The round-trips and GUI results establish name-only creation, baseline overwrite/conflict behavior, inheritance and native parameter preservation, `filament_settings_id` preservation, and removal of unknown `pm_method_version`. Current P7.5-A classification: `READY_FOR_PROCESSOR`.
