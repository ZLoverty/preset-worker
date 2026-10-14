# OrcaSlicer fixtures

`valid/pla_test.json` is a real OrcaSlicer GUI-exported filament preset
provided for P7.3.1. It has no top-level `type` field and uses
`filament_settings_id` plus filament settings to identify the preset.

`valid/filament.json` remains a small upstream-structure compatibility fixture
for the alternate profile shape.

Reference: OrcaSlicer `resources/profiles_template/Template/filament`.

Required follow-up before claiming full import compatibility: manually import
the canonical output into the matching OrcaSlicer version and verify whether
Orca requires recalculating any opaque setting/filament IDs after renaming.
