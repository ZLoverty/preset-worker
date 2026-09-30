# ElegooSlicer P7.5-A GUI Test Results

Test installation version: **ElegooSlicer 1.5.2.5**  
Native preset version: `1.5.3.5`  
Test status: **Completed**

Test the baseline first, then each variant. Do not edit the files manually. For successful imports, re-export at least the baseline, the successful name-only or identity variant, and the custom-metadata variant where possible. Record exact re-export filenames.

| Variant | Import succeeds? | Visible preset name | Created new preset? | Overwrote/replaced existing preset? | Duplicate/conflict warning? | Other visible behavior | Re-exported filename |
|---|---|---|---|---|---|---|---|
| `00_baseline.json` | yes | pla_test | no | yes | yes | baseline export is `pla_test.json` | pla_test.json |
| `01_name_only.json` | yes | `P7ES_NAME_ONLY` | yes | no | no | native fields observed unchanged in re-export | `P7ES_NAME_ONLY.json` |
| `02_name_filament_settings_id.json` | yes | `P7ES_NAME_ID` | yes | no | no | `filament_settings_id` observed unchanged in re-export | `P7ES_NAME_ID.json` |
| `03_name_custom_metadata.json` | yes | `P7ES_CUSTOM_METADATA` | yes | no | no | `pm_method_version` absent from re-export | `P7ES_CUSTOM_METADATA.json` |

Additional observations:

- Does the parent remain `Elegoo PLA @EC`? **Yes in all supplied re-exports.**
- Are `fan_cooling_layer_time`, `fan_min_speed`, `filament_extruder_variant`, `nozzle_temperature`, and `nozzle_temperature_initial_layer` unchanged after import/re-export? **Yes in all supplied re-exports.**
- Does `pm_method_version` survive, get removed, get rewritten, or cause rejection? **Import/re-export succeeded, and the field was removed from the supplied re-export.**
- If a preset is re-exported, preserve the output separately from the input variant and record its exact filename. **Done for the three supplied re-exports.**

The baseline overwrote the existing `pla_test` preset and showed a conflict warning. All uniquely named variants created new presets and imported without conflict warnings.
