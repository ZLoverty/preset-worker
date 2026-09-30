# P7.3.1 Worker canonical round-trip

Worker canonical input: `worker_canonical_candidate.json`.

OrcaSlicer re-export: `L2002CF @BBL P2S.json`.

The files are semantically identical except for:

```text
pm_method_version: "2.1" → absent
```

All other compared fields are preserved, including `name`,
`filament_settings_id`, `inherits`, compatible printers, version and nozzle
temperatures.

Identity compatibility is validated for this real export. The required custom
`pm_method_version` metadata is not preserved by Orca import/export. This is an
accepted compatibility limitation; no alternate field encoding is introduced.
Orca support is therefore `VALIDATED_WITH_LIMITATIONS`.
