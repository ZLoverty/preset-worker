# P9-D0 Fixture Collection Guide

## Common protocol

For each slicer, collect both files from the same application session:

1. Create a simple cube project.
2. Select one printer and one custom filament Preset.
3. Set recognizable but valid marker values where the slicer permits them.
4. Save/export the project as 3MF after applying the Preset.
5. Export the same filament Preset separately in its native format.
6. Record slicer version, printer model, export mode, filament count, expected identity and slot.
7. Copy original bytes unchanged into the corresponding fixture directory root.

Do not edit the JSON/INI or 3MF after export to manufacture a pair. If the application rewrites or strips a field, record that as evidence.

## OrcaSlicer

Required artifacts: an OrcaSlicer native filament Preset JSON and an Orca project 3MF. Record whether the file is Save Project, Export 3MF, or gcode.3mf. For multi-filament projects record every `filament_settings_id` and the object/plate assignment. Confirm the Preset identity matches one and only one project slot; do not use the display name alone.

Current fixture has a project and JSON but identity is unresolved because `filament_settings_id` differs and the project has four slots.

## Snapmaker OrcaSlicer

Repeat the Orca procedure using Snapmaker OrcaSlicer and record the fork/application version separately. Do not substitute an upstream Orca Preset. Ensure the Preset is copied into `tests/fixtures/slicers/orca_slicer_snapmaker/` at root and update its manifest.

Current fixture now has the project 3MF, `pla_test.json`, and a `pla_test.info` sidecar at root. The JSON is the Preset; the `.info` file is auxiliary identity metadata.

## CrealityPrint

Use the CrealityPrint project-save/export action that produces `creality.3mf`-style output and export the native material Preset JSON separately. Record the Creality application metadata from `Metadata/creality.config` and `Metadata/slice_info.config`. Verify whether `filament_settings_id` and `filament_ids` are stable across one- and two-filament projects.

Current fixture is a usable single-slot pair for stored-value inspection.

## ElegooSlicer

Export a project 3MF and a native material Preset JSON from the same ElegooSlicer session. Record both the application version and any Orca compatibility version in `slice_info.config`. Verify whether `filament_sequence.json` reflects plate assignment or only a print sequence.

Current fixture is a usable single-slot pair for stored-value inspection.

## PrusaSlicer

Save/export a PrusaSlicer project 3MF and export the matching filament profile as `.ini`. Inspect `Metadata/Slic3r_PE.config`, not `Metadata/project_settings.config`. Record the profile filename stem, `filament_settings_id`, `compatible_printers_condition`, and all four profile entries in multi-extruder projects. Confirm how the exported profile maps to the project’s semicolon-separated profile list.

Current fixture contains both files. The Preset identity field is empty, but the filename stem `pla_test` exactly matches one project profile name and occurs only once in the semicolon-separated list, so it uniquely identifies slot 1 for this fixture. Treat the filename as a candidate identity only after exact project-side matching; zero matches remain unresolved and repeated matches require the agreed multi-match policy.

## Post-collection command

Run the read-only inspector from the repository root:

```bash
PYTHONPATH=src .venv/bin/python scripts/inspect_3mf.py \
  --project tests/fixtures/slicers/orca_slicer/orca.3mf \
  --preset 'tests/fixtures/slicers/orca_slicer/L2002CF @BBL P2S.json' \
  --slicer OrcaSlicer
```

Correct the paths for the slicer under test. Review candidate values and identity evidence; do not treat the inspector’s candidate list as a semantic mapping.
