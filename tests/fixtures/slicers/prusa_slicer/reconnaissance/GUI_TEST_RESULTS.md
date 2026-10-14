# PrusaSlicer P7.6-A GUI Test Results

Test installation: **PrusaSlicer 2.9.6**  
Test status: **Completed**

Test the baseline first, then each variant. Do not edit the files manually. Use the same PrusaSlicer installation that generated the source. Record whether the filename is displayed as the preset name, whether a new preset is created, and whether PrusaSlicer rewrites the file on export.

| Variant | Import succeeds? | Visible preset name | Created new preset? | Overwrote/replaced existing preset? | Duplicate/conflict warning? | Other visible behavior | Re-exported filename |
|---|---|---|---|---|---|---|---|
| `00_baseline.ini` | yes | 00_baseline | yes | no | no | no | `00_baseline copy.ini` |
| `01_name_only.ini` | yes | 01_name_only | yes | no | no | no | `01_name_only copy.ini` |
| `02_name_filament_settings_id.ini` | yes | 02_name_filament_settings_id.ini (P7PS_NAME_ID) | yes | no | no | cannot export: cannot overwrite an external profile | none |
| `03_custom_metadata.ini` | yes | 03_custom_metadata | yes | no | no | no | `03_custom_metadata copy.ini` |

Additional observations to record:

- Does PrusaSlicer treat `pla_test.ini` / `P7PS_NAME_ONLY.ini` as the visible preset name? **No; the imported filename stem is the visible preset name.**
- Does `inherits = Generic PLA @COREONEINDX HF0.4` survive import and re-export? **No; it is cleared in all supplied re-exports.**
- Are `temperature`, `first_layer_temperature`, `bed_temperature`, `filament_density`, `filament_diameter`, and `filament_max_volumetric_speed` unchanged? **Yes.**
- Does `filament_settings_id = P7PS_NAME_ID` survive, get regenerated, or have no visible effect? **It imports, but PrusaSlicer cannot export it as an external profile because it cannot overwrite the external profile. Round-trip persistence is unresolved.**
- Does `pm_method_version = P7PS_TEST` survive, get removed, get rewritten, or cause rejection? **The variant imports; the key is absent from the re-export, so it is removed or ignored on export.**
- Exact output files are preserved with `copy` suffixes in this folder.
