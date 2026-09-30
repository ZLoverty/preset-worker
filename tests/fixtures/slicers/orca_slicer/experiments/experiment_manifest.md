# P7.3.1 Orca identity experiment manifest

Source provenance: real GUI-exported filament preset supplied by the user.
The original bytes are preserved at `../real/source_original.json`.

Source SHA-256:

`906d327d6ccc1c4153cf9bd7fa23c0af22d43395ce92ce1af9623b8a62975b82`

| Variant | SHA-256 | Fields changed | Old → new | Question |
|---|---|---|---|---|
| `00_baseline.json` | `906d327d6ccc1c4153cf9bd7fa23c0af22d43395ce92ce1af9623b8a62975b82` | none | — | Can the untouched export be imported? |
| `01_name_only.json` | `51ddd05d08e97691039a6e9dc03bce0360baa4cfacacee69a1cd059e4502853c` | `name` | `pla_test` → `P7TEST_NAME_ONLY` | Does name alone control visible identity? |
| `02_name_filament_settings_id.json` | `10d9921c6d4e11f53c6e9d75407dcb525ad7493621b9ab3dd8fe2549b8698a14` | `name`, `filament_settings_id` | `pla_test` → `P7TEST_NAME_SETTINGS_ID` | Does the GUI-export identity field need to follow name? |
| `07_name_inherits_preserved.json` | `9ff978abe8ccc9c3e5596e210969137d16de6e9a17b552516988cb7af394aa2b` | `name` | `pla_test` → `P7TEST_NAME_INHERITS` | Does name work while preserving `inherits`? |

The source has no `setting_id` or `filament_id`, so variants 02/03/04/05/06
from the generic matrix that require those fields were not generated. Variant
02 above is an additional experiment for the actual identity field present in
this export: `filament_settings_id`.

GUI observations are recorded in `GUI_TEST_RESULTS.md`. The observed result
is that `name` alone is sufficient for visible identity; the Worker rule was
then reduced to name-only identity mutation plus the independent
`pm_method_version` company field. `worker_canonical_candidate.json` is the
next manual import target.
