# Upstream Orca vs Snapmaker Orca Comparison (P7.7-A)

| Behavior | Upstream Orca evidence | Snapmaker Orca evidence | Equivalent? |
|---|---|---|---|
| Artifact format | plain JSON object | plain JSON object | structurally identical |
| Import unit | one JSON preset | one JSON preset | equivalent in tested cross-import |
| Visible-name control | upstream P7.3 GUI evidence: `name` alone | Snapmaker GUI evidence: `name` alone | behaviorally equivalent for tested variants |
| New-preset identity | unique `name` creates new preset | unique `name` creates new preset | equivalent for tested variants |
| `filament_settings_id` | preserved in upstream round-trip | preserved in Snapmaker round-trip | equivalent for tested mutation |
| `inherits` | upstream parent `Generic PLA @System` preserved | Snapmaker parent `Snapmaker PLA` preserved | same field behavior, different native value |
| Unknown fields | upstream custom metadata removed on re-export | Snapmaker `pm_method_version` removed on re-export | equivalent for tested metadata |
| `pm_method_version` | removed on re-export | removed on re-export | equivalent for tested metadata |
| Parameters | tested upstream fields preserved | tested Snapmaker temperature/cooling fields preserved | equivalent for tested fields |
| Cross-import | imported Snapmaker fixture successfully; semantic output unchanged | imported upstream fixture successfully; semantic output unchanged | equivalent in tested directions |

The evidence supports equivalent pure JSON mechanics and tested processor responsibilities, while business identity remains distinct. The implementation relationship is `SHARED_CORE_WITH_DISTINCT_PROCESSOR_FACADES_POSSIBLE`; this is advisory only, and no shared-core refactor is performed during P7.7-A.
