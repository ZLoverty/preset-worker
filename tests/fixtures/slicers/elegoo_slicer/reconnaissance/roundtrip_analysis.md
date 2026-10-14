# ElegooSlicer P7.5-A Round-Trip Analysis

Test application version: ElegooSlicer `1.5.2.5`.  
Native preset version: `1.5.3.5`.

## Supplied re-exports

| Input | Re-export | SHA-256 | Semantic result |
|---|---|---|---|
| `01_name_only.json` | `P7ES_NAME_ONLY.json` | `e82976ce63e8e043994f702255353698a8f8607a622b27c8f443b7a65d579fe9` | `name` remained `P7ES_NAME_ONLY`; all observed native fields remained unchanged. |
| `02_name_filament_settings_id.json` | `P7ES_NAME_ID.json` | `c3e2a5bca5ebec13a47b829a45bb80e3eb978ee567f578c96cd5382f16a4882e` | `name` and `filament_settings_id` remained `P7ES_NAME_ID`; all observed native fields remained unchanged. |
| `03_name_custom_metadata.json` | `P7ES_CUSTOM_METADATA.json` | `4cd0ea32738463125764c78f97f7d9c20f18c3741f9eb5d7cca4d6dc3a3084f0` | `name` remained `P7ES_CUSTOM_METADATA`; unknown `pm_method_version` was removed; all observed native fields remained unchanged. |

The baseline was exported as `pla_test.json` and imported over the existing same-name preset with a conflict/overwrite warning. Its semantic content matches the source baseline.

## Confirmed preservation

Across all three supplied re-exports, these values remained unchanged from their input variants:

- `fan_cooling_layer_time`
- `fan_min_speed`
- `filament_extruder_variant`
- `filament_settings_id` (including the intentional `P7ES_NAME_ID` mutation)
- `from`
- `inherits: Elegoo PLA @EC`
- `nozzle_temperature`
- `nozzle_temperature_initial_layer`
- `version: 1.5.3.5`

## Semantics established so far

- `name` is retained by ElegooSlicer and is the strongest visible-name candidate. The successful name-only re-export is consistent with name being sufficient, but the GUI's new-vs-overwrite result was not recorded.
- `filament_settings_id` is retained when changed. It is a credible native identity field, but independent identity necessity is not established.
- `inherits` survives the name-only round-trip unchanged, so a renamed preset can retain the tested parent reference.
- `pm_method_version` is accepted in the input variant but absent from the re-export, indicating removal by ElegooSlicer rather than rejection.
- No evidence supports synthesizing another ID or mutating native base metadata.

## GUI identity behavior

The baseline overwrote the existing `pla_test` preset and showed a warning. All variants with unique names created new presets and imported without conflict warnings. This establishes that changing `name` alone is sufficient for the tested new-preset behavior.

## Artifact assessment

The complete tested unit is one plain JSON file. The current `Artifact(content: bytes, filename, media_type)` abstraction is sufficient. Exact application version and baseline GUI overwrite/conflict behavior remain open evidence gaps.
