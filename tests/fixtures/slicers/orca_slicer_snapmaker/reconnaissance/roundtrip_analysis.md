# Snapmaker OrcaSlicer P7.7-A Round-Trip Analysis

Application version/build: Snapmaker OrcaSlicer `2.4.0`. Native preset version: `2.3.3.3`.

## Supplied re-exports

| Input | Re-export | SHA-256 | Semantic result |
|---|---|---|---|
| `00_baseline.json` | `pla_test.json` | `dd84b9d988d902571fdc72110ef68a6028e2eede07de54b5d0162b1f6183c27c` | Same semantic content; GUI reported existing preset overwrite/selection warning. |
| `01_name_only.json` | `P7SM_NAME_ONLY.json` | `80b6f1265c49b32d0306a7e13ff8b5b369ff813a34eaf4ec9168f0abcb87d3dd` | `name` remained `P7SM_NAME_ONLY`; all other observed fields remained unchanged. |
| `02_name_filament_settings_id.json` | `P7SM_NAME_ID.json` | `c3da234b89bd62dac7f7515d2c0b074d0d0c659254fbacfde9ac2d648b236f2b` | `name` and `filament_settings_id` remained `P7SM_NAME_ID`; all other observed fields remained unchanged. |
| `03_custom_metadata.json` | `P7SM_CUSTOM_METADATA.json` | `9f9cf4cdeea893ebcfe86924917ce36a76d359efdc199e1d8ca974801abf3e6a` | `name` remained `P7SM_CUSTOM_METADATA`; `pm_method_version` was removed; all other observed fields remained unchanged. |

## Native GUI behavior

- Baseline imported and produced the only overwrite warning.
- All unique-name variants imported and created new presets without overwrite warnings.
- `name` alone is sufficient for the tested visible identity/new-preset behavior.
- `filament_settings_id` survives the tested mutation and does not need to track the changed name for the tested creation behavior.
- `inherits = Snapmaker PLA` survives all supplied re-exports.
- `pm_method_version` is accepted on import but removed during re-export (`REMOVED_ON_REEXPORT`).
- No additional Snapmaker-specific field was observed or generated.

## Parameter preservation

The supplied re-exports preserve `fan_cooling_layer_time`, `nozzle_temperature`, and `nozzle_temperature_initial_layer`, as well as `from`, `is_custom_defined`, and native `version`.

## Cross-import

Upstream → Snapmaker produced `cross_upstream_to_snapmaker.json`, semantically identical to the upstream input (SHA-256 `906d327d6ccc1c4153cf9bd7fa23c0af22d43395ce92ce1af9623b8a62975b82`). Snapmaker → upstream produced `cross_snapmaker_to_upstream.json`, semantically identical to the Snapmaker input (SHA-256 `dd84b9d988d902571fdc72110ef68a6028e2eede07de54b5d0162b1f6183c27c`). Both directions completed without observed field loss or rewrite. This establishes tested format compatibility, not merged business identity.
