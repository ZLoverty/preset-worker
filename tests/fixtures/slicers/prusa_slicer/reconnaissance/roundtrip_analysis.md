# PrusaSlicer P7.6-A Round-Trip Analysis

Test installation: PrusaSlicer `2.9.6`.

## Supplied re-exports

| Input | Re-export | SHA-256 | Semantic changes |
|---|---|---|---|
| `00_baseline.ini` | `00_baseline copy.ini` | `d5e99eb108d8f3d56b0706933458ece34918e44815280f023a8265ce628a51a2` | `inherits` cleared; `compatible_printers_condition` cleared; generated timestamp and formatting changed. |
| `01_name_only.ini` | `01_name_only copy.ini` | `c7316a38a6b97a22fb8e9a81cdb290a268f3e4b797fa1059c3cfe9bb35db924c` | `inherits` cleared; `compatible_printers_condition` cleared; generated timestamp and formatting changed. |
| `02_name_filament_settings_id.ini` | none | — | Imported, but PrusaSlicer reported it could not overwrite an external profile; no round-trip output. |
| `03_custom_metadata.ini` | `03_custom_metadata copy.ini` | `d8339594cc34caf1752a39f94ae97ddfeee028b045202f556f88e77e4302d9e3` | `inherits` cleared; `compatible_printers_condition` cleared; `pm_method_version` absent; generated timestamp and formatting changed. |

## Confirmed GUI semantics

- The filename stem is the visible preset name; there is no explicit `name` property in the source INI.
- Baseline imported successfully as a new preset without overwrite or conflict warning.
- All unique-name variants imported successfully as new presets without conflict warnings.
- The `filament_settings_id` variant imported, but could not be exported as an external profile because PrusaSlicer could not overwrite that external profile.

## Parameter preservation

The supplied re-exports preserve representative material/process values:

```text
temperature = 230
first_layer_temperature = 230
bed_temperature = 60
filament_density = 1.24
filament_diameter = 1.75
filament_max_volumetric_speed = 17
filament_colour = #FF8000
filament_type = PLA
```

The same values were retained across the three available outputs. Retraction, cooling, extrusion, and filament G-code values observed in the source were also retained. Changes to `inherits` and `compatible_printers_condition` are semantic, not formatting-only.

## Inheritance and metadata

The source `inherits = Generic PLA @COREONEINDX HF0.4` was cleared by PrusaSlicer on every supplied re-export. This is a slicer round-trip limitation; the Worker should preserve source inheritance in its own canonical artifact unless later processor evidence requires another rule.

The custom `pm_method_version = P7PS_TEST` variant imported successfully but the key was absent from the re-export. Classify it as `REMOVED_ON_REEXPORT`; Worker reinjection from authoritative Submission context remains viable.

## Artifact assessment

The complete import/export unit is one `.ini` file. The existing opaque `Artifact(content, filename, media_type)` abstraction is `SUFFICIENT`; the processor must preserve the filename because it controls visible identity. No architecture escalation is required.
