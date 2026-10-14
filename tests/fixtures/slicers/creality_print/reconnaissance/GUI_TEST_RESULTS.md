# CrealityPrint P7.4-A GUI Test Results

Test installation: **CrealityPrint v7.2.1.5476**  
Test status: **Completed**

Test the baseline first, then each variant. Do not edit the files manually. For successful imports, re-export at least the baseline, the successful name-only or identity variant, and the custom-metadata variant where possible. Record the exact re-export filename.

| Variant | Import succeeds? | Visible preset name | Created new preset? | Overwrote/replaced existing preset? | Duplicate/conflict warning? | Other visible behavior | Re-exported filename |
|---|---|---|---|---|---|---|---|
| `00_baseline.json` | yes | pla_test | no | yes | yes | no | pla_test |
| `01_name_only.json` | yes | P7CP_NAME_ONLY | yes | no | no | no | P7CP_NAME_ONLY |
| `02_name_filament_settings_id.json` | yes | P7CP_NAME_ID | yes | no | no | no | P7CP_NAME_ID |
| `03_name_base_id.json` | yes | P7CP_BASE_ID | yes | no | no | no | P7CP_BASE_ID |
| `04_name_custom_metadata.json` | yes | P7CP_CUSTOM_METADATA | yes | no | no | no | P7CP_CUSTOM_METADATA |

Additional observations:

- Does the parent shown by CrealityPrint remain `Hyper PLA @Creality K2 Pro 0.4 nozzle`? yes
- Are `fan_cooling_layer_time`, `nozzle_temperature`, and `nozzle_temperature_initial_layer` unchanged after import/re-export? yes
- Does the custom metadata field survive, get removed, get rewritten, or cause rejection? Removed on re-export; import succeeds.
- If a preset is re-exported, record its exact filename and preserve the output separately from the input variant. as seen in the current folder

## Observed conclusions

- The untouched baseline imports, but matches/replaces the existing `pla_test` preset and produces a duplicate/conflict warning.
- Changing `name` alone is sufficient to display and create a distinct custom preset.
- All controlled variants imported successfully and created new presets because their names were unique.
- The parent `inherits` value and observed material/process parameters remained unchanged.
- CrealityPrint removed the exploratory `pm_method_version` field from the custom-metadata re-export.
