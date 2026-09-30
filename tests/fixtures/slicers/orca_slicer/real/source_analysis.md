# Real Orca GUI export analysis

Source: `source_original.json`, supplied from the user's OrcaSlicer GUI export.
SHA-256: `906d327d6ccc1c4153cf9bd7fa23c0af22d43395ce92ce1af9623b8a62975b82`.

The artifact is a JSON object with 10 top-level fields:

| Field | Observed value/type | Identity or compatibility note |
|---|---|---|
| `type` | absent | The real GUI export does not use the synthetic fixture's type marker. |
| `name` | string `pla_test` | Visible/custom preset identity candidate. |
| `setting_id` | absent | Not available for this export; no experiment variants generated. |
| `filament_id` | absent | Not available for this export; no experiment variants generated. |
| `filament_settings_id` | one-element string list `['pla_test']` | Actual identity-looking field; tested separately. |
| `inherits` | string `Generic PLA @System` | Preserved in all variants. |
| `version` | string `2.3.1.0` | Preserved. |
| `from` | string `User` | Preserved. |
| `instantiation` | absent | No assumption added. |
| `compatible_printers` | list containing `Snapmaker U1 (0.4 nozzle)` | Preserved. |

Other observed fields are `fan_cooling_layer_time`, `is_custom_defined`,
`nozzle_temperature`, and `nozzle_temperature_initial_layer`.

## Comparison with synthetic fixture

The synthetic fixture has `type: filament`, `instantiation: true`,
`filament_type`, `filament_vendor`, `filament_flow_ratio`,
`filament_max_volumetric_speed`, and `future_unknown_field`; the real export
has none of those. The real export instead has `version`,
`is_custom_defined`, `fan_cooling_layer_time`, and explicit nozzle temperature
fields. Both have `name`, `inherits`, `from`, `compatible_printers`, and
`filament_settings_id`, but the values and casing differ.

The current processor therefore accepts both shapes: an explicit
`type: filament` profile and a GUI-export shape with `filament_settings_id` or
other `filament_*` fields. No identity conclusion is drawn until GUI results
are recorded.
