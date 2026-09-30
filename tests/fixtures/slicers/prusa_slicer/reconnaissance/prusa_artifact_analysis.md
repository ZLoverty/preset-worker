# PrusaSlicer Artifact Analysis (P7.6-A)

## Provenance

- PrusaSlicer version: `2.9.6` (from the artifact generation header)
- Source supplied by user: `tests/fixtures/slicers/prusa_slicer/pla_test.ini`
- Preserved original: `source_original.ini`
- Source filename: `pla_test.ini`
- Extension: `.ini`
- Source size: `2991` bytes
- Source SHA-256: `d3583016b6a6a0e3e1950886b8e54c6bf1a5c04e5a9e0675d402b1a1920c54ea`
- Header timestamp: `2026-09-30 05:42:58 UTC`

## Container and import-unit assessment

The artifact is ASCII text in PrusaSlicer's `key = value` configuration format. It is not JSON, ZIP, 3MF, or a directory/package. No archive members or external companion files are present. GUI testing confirmed that one `.ini` file is independently imported and exported as one filament preset.

The current opaque `Artifact(content: bytes, filename, media_type)` abstraction can carry the complete file without loss. The filename is intentionally retained as part of the artifact because the INI body has no explicit visible `name` property.

## Structural summary

The file is a flat key/value profile with 87 assignments and one generated-by comment. It contains:

- material/process parameters: `temperature`, `first_layer_temperature`, `bed_temperature`, `filament_density`, `filament_diameter`, `extrusion_multiplier`, cooling and retraction settings;
- compatibility constraints: `compatible_printers_condition` targeting COREONE variants, 0.4 nozzle, and high-flow nozzle;
- material identity candidates: empty `filament_settings_id`, `filament_type = PLA`, `filament_vendor = Generic`;
- inheritance: `inherits = Generic PLA @COREONEINDX HF0.4`;
- native/version metadata: generated-by header and no separate profile UUID/name field.

The source filename `pla_test.ini` was the strongest visible-name candidate. GUI testing confirmed that the imported filename stem is the visible preset name; no explicit INI `name` property is used in this artifact.

## Candidate semantics

| Element | Observed value | Candidate role | Confidence |
|---|---|---|---|
| Artifact filename | `pla_test.ini` | visible preset name / import identity | candidate; filename-only experiment generated |
| `filament_settings_id` | empty string | native filament identity | candidate; controlled mutation generated |
| `inherits` | `Generic PLA @COREONEINDX HF0.4` | parent profile | strong structural candidate; preserved in all variants |
| `filament_type` | `PLA` | material type | native parameter/metadata |
| `filament_vendor` | `Generic` | vendor metadata | native metadata candidate |
| `compatible_printers_condition` | COREONE and nozzle constraints | printer compatibility | native compatibility rule |
| generated-by comment | `PrusaSlicer 2.9.6` | application/version provenance | strong version evidence |

No explicit `name`, UUID, `base_id`, `inherits` ID, or printer profile ID was observed.

## Comparison with existing slicers

This comparison is descriptive only; shared concepts do not imply shared semantics.

| Aspect | PrusaSlicer | BambuStudio | OrcaSlicer | CrealityPrint | ElegooSlicer |
|---|---|---|---|---|---|
| Container | flat INI text | JSON object | JSON object | JSON object | JSON object |
| Visible-name candidate | filename/possibly config identity | `name` | `name` | `name` | `name` |
| Filament identity | empty `filament_settings_id` candidate | slicer-native JSON fields | `filament_settings_id` candidate | `filament_settings_id` candidate | `filament_settings_id` candidate |
| Inheritance | `inherits` key | JSON field | JSON field | JSON field | JSON field |
| Version evidence | generated-by header | native JSON version | native JSON version | native JSON version | native preset version plus app evidence |
| Unknown metadata | INI key may be accepted; untested | JSON field | JSON field | JSON field | JSON field, stripped on re-export |

## Initial Artifact assessment

`Artifact(content: bytes, filename, media_type)` is currently `SUFFICIENT`: one complete INI file is the candidate import/export unit and filename must remain available to the processor. No generic architecture changes are justified during reconnaissance.

GUI testing established filename-stem visible identity, successful creation for all unique variants, and no baseline conflict/overwrite. Round-trip analysis established parameter preservation, inheritance clearing, and removal of unknown metadata. The `filament_settings_id` variant could not be re-exported as an external profile, so its persistence remains unresolved.
