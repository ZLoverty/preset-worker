# PrusaSlicer P7.6-A Experiment Manifest

Source: `source_original.ini` / `pla_test.ini`  
Source SHA-256: `d3583016b6a6a0e3e1950886b8e54c6bf1a5c04e5a9e0675d402b1a1920c54ea`

| Variant | Size | SHA-256 | Exact changes | Semantic question |
|---|---:|---|---|---|
| `00_baseline.ini` | 2991 | `d3583016b6a6a0e3e1950886b8e54c6bf1a5c04e5a9e0675d402b1a1920c54ea` | none; byte-identical to source | Does the real exported INI import successfully? |
| `01_name_only.ini` | 2991 | `d3583016b6a6a0e3e1950886b8e54c6bf1a5c04e5a9e0675d402b1a1920c54ea` | filename `pla_test.ini` → `01_name_only.ini`; INI body unchanged | Does filename-only identity control visible name and create a new preset? |
| `02_name_filament_settings_id.ini` | 3001 | `9deba46e90d6cd64dc649e14110180deb0d1cf4e0a8602e9ac8bf3a4f1a6fc2e` | `filament_settings_id`: empty string → `P7PS_NAME_ID`; filename is `02_name_filament_settings_id.ini` | Does the native identity candidate survive import/re-export or affect identity? |
| `03_custom_metadata.ini` | 3021 | `67361a5630eba9764f1478a4f29017c9a6ff55909ef9d6e56dd498d968e625f7` | add `pm_method_version = P7PS_TEST`; filename is `03_custom_metadata.ini` | Does PrusaSlicer accept and preserve unknown metadata? |

The filename-only variant is also the inheritance-preserved experiment: its INI body, including `inherits`, is unchanged. No native ID was invented because the source contains no populated UUID/base/profile ID.
