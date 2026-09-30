# Snapmaker OrcaSlicer P7.7-A Experiment Manifest

Source: `source_original.json` / `pla_test.json`  
Source SHA-256: `dd84b9d988d902571fdc72110ef68a6028e2eede07de54b5d0162b1f6183c27c`

| Variant | Size | SHA-256 | Fields changed | Question |
|---|---:|---|---|---|
| `00_baseline.json` | 356 | `dd84b9d988d902571fdc72110ef68a6028e2eede07de54b5d0162b1f6183c27c` | none | Does the untouched Snapmaker export import successfully? |
| `01_name_only.json` | 362 | `80b6f1265c49b32d0306a7e13ff8b5b369ff813a34eaf4ec9168f0abcb87d3dd` | `name`: `pla_test` → `P7SM_NAME_ONLY` | Is `name` alone sufficient for visible identity and new-preset creation? |
| `02_name_filament_settings_id.json` | 364 | `c3da234b89bd62dac7f7515d2c0b074d0d0c659254fbacfde9ac2d648b236f2b` | `name`: `pla_test` → `P7SM_NAME_ID`; `filament_settings_id[0]`: `pla_test` → `P7SM_NAME_ID` | Does the native material ID affect identity or survive round-trip? |
| `03_custom_metadata.json` | 406 | `bfa5f747d9931d7b880ff97664691a63f109a03ebea086cffdcab6dc264375f4` | `name`: `pla_test` → `P7SM_CUSTOM_METADATA`; add `pm_method_version = P7SM_TEST` | Does Snapmaker Orca accept and preserve custom metadata? |

The name-only variant is also the inheritance-preserved experiment: it changes only `name` while retaining `inherits = Snapmaker PLA` exactly. No unobserved native ID or Snapmaker field was invented.
