# P7.3.1 GUI test results

Use the same OrcaSlicer installation that exported `source_original.json`.
Test `00_baseline.json` first. Do not edit the JSON files manually.

| Variant | Import succeeds? | Visible preset name | Created new preset? | Overwrote/replaced existing preset? | Duplicate/conflict warning? | Other visible behavior | Re-exported filename |
|---|---|---|---|---|---|---|---|
| `00_baseline.json` | yes | pla_test | no | yes | no | no | pla_test |
| `01_name_only.json` | yes | P7TEST_NAME_ONLY | yes | no | no | no | P7TEST_NAME_ONLY |
| `02_name_filament_settings_id.json` | yes | P7TEST_NAME_SETTINGS_ID | yes | no | no | no | P7TEST_NAME_SETTINGS_ID |
| `07_name_inherits_preserved.json` | yes | P7TEST_NAME_INHERITS | yes | no | no | no | P7TEST_NAME_INHERITS |

After the identity experiment, import the actual Worker-generated canonical
artifact separately and record whether its name, parameters, inheritance and
`pm_method_version` behave as expected.

## Worker canonical artifact result

The Worker artifact imported successfully. The visible name was
`L2002CF @BBL P2S`; parameters and `inherits` were preserved. Orca's
re-export removed `pm_method_version` and did not change the other compared
fields. See `../roundtrip/roundtrip_analysis.md`.

Production readiness: `VALIDATED_WITH_LIMITATIONS`. Accepted limitation:
Orca removes the custom `pm_method_version` field during re-export.
