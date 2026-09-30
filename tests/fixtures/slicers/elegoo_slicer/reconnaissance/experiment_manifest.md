# ElegooSlicer P7.5-A Experiment Manifest

Source: `source_original.json` / `pla_test.json`  
Source SHA-256: `e50511ce9a0b9c0a488e13b6c67adc20909fe84b657affa845efa94e18610f62`

| Variant | Size | SHA-256 | Fields/components changed | Question |
|---|---:|---|---|---|
| `00_baseline.json` | 361 | `e50511ce9a0b9c0a488e13b6c67adc20909fe84b657affa845efa94e18610f62` | none | Does the untouched export import successfully? |
| `01_name_only.json` | 367 | `e82976ce63e8e043994f702255353698a8f8607a622b27c8f443b7a65d579fe9` | `name`: `pla_test` → `P7ES_NAME_ONLY` | Does `name` alone control the visible name and create a distinct preset? |
| `02_name_filament_settings_id.json` | 369 | `c3e2a5bca5ebec13a47b829a45bb80e3eb978ee567f578c96cd5382f16a4882e` | `name`: `pla_test` → `P7ES_NAME_ID`; `filament_settings_id[0]`: `pla_test` → `P7ES_NAME_ID` | Does the material settings ID participate in identity or get regenerated? |
| `03_name_custom_metadata.json` | 408 | `2f05d598fbb3b0a5af04a05d5141fb5e392b8c9c579b2c7c624293053f0eb706` | `name`: `pla_test` → `P7ES_CUSTOM_METADATA`; add `pm_method_version`: `P7ES_TEST` | Does ElegooSlicer accept, preserve, rewrite, or remove unknown metadata? |

All variants preserve `inherits`, `filament_extruder_variant`, cooling parameters, nozzle temperatures, `from`, and native `version`. The name-only variant is also the inheritance-preserved experiment: it changes only the intended visible identity while retaining `inherits` exactly.
