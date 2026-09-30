# CrealityPrint P7.4-A Round-Trip Analysis

Test installation: CrealityPrint `v7.2.1.5476`  
Input directory: this `reconnaissance` directory  
Output files: `pla_test.json`, `P7CP_NAME_ONLY.json`, `P7CP_NAME_ID.json`, `P7CP_BASE_ID.json`, `P7CP_CUSTOM_METADATA.json`

## Results

| Input | Re-export | Semantic changes observed |
|---|---|---|
| `00_baseline.json` | `pla_test.json` | No semantic changes. Same-name preset conflicted with/replaced existing preset. |
| `01_name_only.json` | `P7CP_NAME_ONLY.json` | `name` remained `P7CP_NAME_ONLY`; all other fields and parameters remained unchanged. |
| `02_name_filament_settings_id.json` | `P7CP_NAME_ID.json` | `name` and `filament_settings_id` remained `P7CP_NAME_ID`; all other fields and parameters remained unchanged. |
| `03_name_base_id.json` | `P7CP_BASE_ID.json` | `name` remained `P7CP_BASE_ID`; `base_id` normalized from `P7CP_BASE_ID` to `GFSA04`; `filament_settings_id` normalized/restored to `pla_test`; all other fields and parameters remained unchanged. |
| `04_name_custom_metadata.json` | `P7CP_CUSTOM_METADATA.json` | `name` remained `P7CP_CUSTOM_METADATA`; unknown `pm_method_version` was removed; all native fields and parameters remained unchanged. |

## Identity and display-name semantics

The GUI result establishes that `name` controls the visible preset name and that changing it alone is sufficient to create a new preset. The baseline's same-name conflict demonstrates that name participates in logical identity. `filament_settings_id` is a credible native identity/material-settings field because CrealityPrint preserved the changed value in the corresponding round-trip, but this experiment does not prove whether it is independently required when `name` changes. `base_id` is not a free-form identity field: CrealityPrint normalized the mutation back to the source base ID.

## Inheritance and parameters

`inherits` remained `Hyper PLA @Creality K2 Pro 0.4 nozzle` in every observed re-export. The following values remained unchanged: `fan_cooling_layer_time`, `nozzle_temperature`, and `nozzle_temperature_initial_layer`. No flattening or unexpected material/process mutation was observed.

## Custom metadata

The `pm_method_version` experiment imported successfully but the field was absent from `P7CP_CUSTOM_METADATA.json`. CrealityPrint strips this unknown top-level metadata during export. A future processor must treat `Submission.pm_method_version` as authoritative and inject it into the canonical artifact after CrealityPrint-specific normalization, if the canonical contract requires it; it must not rely on CrealityPrint preserving the field.

## Artifact assessment

The complete import/export unit is one plain JSON file. The existing opaque `Artifact(content: bytes, filename, media_type)` contract is sufficient; no architecture escalation is required.
