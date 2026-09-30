# CrealityPrint Artifact Analysis (P7.4-A)

## Provenance

- CrealityPrint version: `v7.2.1.5476`
- Source supplied by user: `tests/fixtures/slicers/creality_print/expriments/pla_test.json`
- Preserved original: `source_original.json`
- Source filename: `pla_test.json`
- Source size: `407` bytes
- Source SHA-256: `7ee1291fee97d6edb65ce3cbf20cfedb38d6c58ffee879e237eefa3a5d762e54`

## Container and import-unit assessment

The artifact is valid plain JSON (magic/content inspection; no archive signature), with a top-level object. It is not a ZIP, 3MF, directory, or multi-file package. The supplied artifact therefore represents one individual preset file and is the current candidate for CrealityPrint's import unit. The baseline GUI import still needs human verification.

The existing opaque `Artifact(content: bytes, filename, media_type)` abstraction is sufficient to represent this file unchanged. No Artifact, UnifiedDiff, workflow, or registry change is justified by this reconnaissance.

## Observed structure

Top-level keys:

```text
base_id
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

The source appears to be a user filament/material preset because `from` is `User`, `is_custom_defined` is present, and the object contains material parameters and a parent preset. The source uses string arrays for cooling and nozzle temperature values.

## Candidate semantics (not yet confirmed by GUI)

| Field | Observed value | Candidate role | Confidence |
|---|---|---|---|
| `name` | `pla_test` | visible preset name | candidate; GUI confirmation required |
| `filament_settings_id` | `pla_test` | internal/material preset identity | candidate; tested separately |
| `base_id` | `GFSA04` | base/vendor preset reference or identity component | candidate; tested separately |
| `inherits` | `Hyper PLA @Creality K2 Pro 0.4 nozzle` | parent/inheritance reference | strong structural candidate; intentionally preserved |
| `from` | `User` | source/origin metadata | candidate metadata |
| `is_custom_defined` | `0` | custom-preset state flag | candidate metadata |
| `version` | `26.8.4.20` | native preset/schema compatibility version | candidate version metadata |

No UUID, vendor field, printer field, or separate profile ID was observed.

## Parameter preservation baseline

The controlled variants preserve `fan_cooling_layer_time`, `nozzle_temperature`, and `nozzle_temperature_initial_layer`. They also preserve `inherits` except where explicitly stated in future experiments. GUI import and re-export are required before concluding that CrealityPrint preserves these values.

## `pm_method_version`

`04_name_custom_metadata.json` adds the unknown top-level field `pm_method_version` while preserving all source fields. This is an exploratory extensibility test only. Whether CrealityPrint accepts, strips, rewrites, or preserves it is unknown until GUI round-trip evidence is available. `Submission.pm_method_version` remains authoritative.

## GUI and round-trip conclusion

The artifact is a single plain-JSON preset and can be carried by the current Artifact contract without loss. The GUI baseline imported and conflicted with the existing same-name preset. A unique `name` alone created a distinct preset. The `filament_settings_id` mutation was retained in the re-export, while the `base_id` mutation was normalized back to `GFSA04` and the original `filament_settings_id` was restored; neither mutation is therefore established as the primary visible identity key. The `inherits` field and observed material/process parameters survived all re-exports unchanged. The unknown `pm_method_version` field was stripped by CrealityPrint.

P7.4-A status: `READY_FOR_PROCESSOR`. This means the artifact format and baseline canonicalization shape are sufficiently understood to begin P7.4-B; it does not authorize implementing the production processor in this phase.
