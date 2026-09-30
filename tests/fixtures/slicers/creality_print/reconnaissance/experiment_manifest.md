# CrealityPrint P7.4-A Experiment Manifest

Source for every variant: `source_original.json` / `pla_test.json`  
Source SHA-256: `7ee1291fee97d6edb65ce3cbf20cfedb38d6c58ffee879e237eefa3a5d762e54`

| Variant | Size | SHA-256 | Fields/components changed | Question |
|---|---:|---|---|---|
| `00_baseline.json` | 407 | `7ee1291fee97d6edb65ce3cbf20cfedb38d6c58ffee879e237eefa3a5d762e54` | none | Does the untouched export import successfully? |
| `01_name_only.json` | 413 | `997f7a2e688d687ddf6a3ac57fad33624dc515230ad55ce4fa720c9cdd2c6fe5` | `name`: `pla_test` → `P7CP_NAME_ONLY` | Does `name` alone control/display a distinct preset? |
| `02_name_filament_settings_id.json` | 415 | `bf4790024854155b5d0ddde58ac074c251996dfbf372196343209222be3da603` | `name`: `pla_test` → `P7CP_NAME_ID`; `filament_settings_id[0]`: `pla_test` → `P7CP_NAME_ID` | Does the material settings ID participate in identity? |
| `03_name_base_id.json` | 417 | `5810e7f2851c4548d891b143982335d0ff0740868cbc3d422118d4d3254cd9b2` | `name`: `pla_test` → `P7CP_BASE_ID`; `base_id`: `GFSA04` → `P7CP_BASE_ID` | Does `base_id` participate in identity or base linkage? |
| `04_name_custom_metadata.json` | 457 | `12ac745acf177eb2b0e280a68867ea9d3734d71b54febdfa7606fd9055706f06` | `name`: `pla_test` → `P7CP_CUSTOM_METADATA`; add `pm_method_version`: `P7CP_TEST` | Does CrealityPrint accept/retain/rewrite unknown custom metadata? |

All variants preserve `inherits` and the observed material/process parameter values. No variant mutates the parent reference. Test the baseline first and avoid importing variants into a contaminated state; use unique names and record overwrite/conflict behavior.
