# Snapmaker OrcaSlicer Artifact Analysis (P7.7-A)

## Provenance

- Snapmaker OrcaSlicer application version/build: `2.4.0` (provided by user; not encoded in artifact)
- Native preset `version`: `2.3.3.3` (recorded as preset metadata, not assumed to be the application build)
- Source supplied by user: `tests/fixtures/slicers/orca_snapmaker/pla_test.json`
- Preserved original: `source_original.json`
- Source filename: `pla_test.json`
- Source size: `356` bytes
- Source SHA-256: `dd84b9d988d902571fdc72110ef68a6028e2eede07de54b5d0162b1f6183c27c`

## Container and import unit

The source is plain UTF-8 JSON with one top-level object. It is not an archive, 3MF-derived package, or multi-file bundle. GUI evidence confirms that one individual JSON filament preset is the import/export unit.

The existing opaque `Artifact(content: bytes, filename, media_type)` abstraction is currently `SUFFICIENT`. No Artifact or generic workflow change is justified during reconnaissance.

## Observed structure

Top-level keys:

```text
fan_cooling_layer_time
filament_settings_id
from
inherits
is_custom_defined
name
nozzle_temperature
nozzle_temperature_initial_layer
version
```

The source is a user custom filament/material preset: `from = User`, `is_custom_defined = 0`, material temperature fields, and an inheritance reference are present. No Snapmaker-specific machine field, UUID, vendor field, printer compatibility field, `setting_id`, or `filament_id` was observed in this artifact.

## Candidate semantics

| Field | Observed value | Candidate role | Initial classification |
|---|---|---|---|
| `name` | `pla_test` | visible name / primary identity | `SEMANTICS_UNKNOWN` until GUI test |
| `filament_settings_id` | `pla_test` | native material identity | `SEMANTICS_UNKNOWN`; controlled variant generated |
| `inherits` | `Snapmaker PLA` | parent profile | structural inheritance candidate; preserved in variants |
| `from` | `User` | origin metadata | likely native metadata |
| `is_custom_defined` | `0` | custom-state metadata | likely native metadata |
| `version` | `2.3.3.3` | native preset version | preset metadata, not app build |

No fork-specific field can be asserted from this one artifact. The `inherits` value itself is Snapmaker-ecosystem-specific evidence and is retained unchanged in fixtures.

## Comparison with upstream Orca fixture

| Component | Snapmaker fixture | Upstream real fixture | Structural classification |
|---|---|---|---|
| Container | JSON object | JSON object | `IDENTICAL_STRUCTURE` |
| `name` | `pla_test` | `pla_test` | `IDENTICAL_STRUCTURE` |
| `filament_settings_id` | `pla_test` | `pla_test` | `IDENTICAL_STRUCTURE` |
| `inherits` | `Snapmaker PLA` | `Generic PLA @System` | `IDENTICAL_STRUCTURE`, different value/semantics unknown |
| `version` | `2.3.3.3` | `2.3.1.0` | `IDENTICAL_STRUCTURE`, different native version |
| `compatible_printers` | absent | one-element list | `UPSTREAM_ONLY` in compared fixtures |
| `type`, `setting_id`, `filament_id` | absent | absent | `IDENTICAL_STRUCTURE` by absence |
| `is_custom_defined` | present | present | `IDENTICAL_STRUCTURE` |
| custom metadata | not tested | upstream `pm_method_version` behavior known separately | `SEMANTICS_UNKNOWN` |

This is descriptive structure comparison only. It does not establish behavioral equivalence or justify reusing `OrcaSlicerProcessor`.

## Initial assessment

The artifact is structurally close to upstream Orca but has a different native parent and native version. GUI evidence establishes name-only creation, baseline overwrite behavior, inheritance preservation, `filament_settings_id` preservation, and removal of `pm_method_version` on re-export. The tested application is Snapmaker OrcaSlicer `2.4.0`; both cross-import directions also completed without semantic changes. Current classification: `READY_FOR_PROCESSOR`.
