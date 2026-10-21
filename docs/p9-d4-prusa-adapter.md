# P9-D4 PrusaSlicer Consistency Adapter

## Entry point

`validate_prusa_slicer_consistency(...)` is exported from
`preset_worker.three_mf`. It is independently callable and is not connected to
Preview dispatch.

## Format adaptation

PrusaSlicer is not sent through `parse_bambu_3mf()`. The new
`three_mf/prusa_parser.py` uses `SafeZipReader` and reads only
`Metadata/Slic3r_PE.config`.

The project member stores settings as semicolon-prefixed `key = value` lines.
The parser preserves native key names, raw values, source member, line numbers,
comma/semicolon list representation, profile order, and project provenance. It
does not use `configparser`, execute content, or extract the archive.

## Identity and slot selection

The Prusa Preset's native `filament_settings_id` is empty in the real fixture.
The adapter explicitly enables filename-stem identity:

```text
pla_test.ini -> pla_test
pla_test -> project slot 1
```

The identity strategy is recorded as
`FILENAME_STEM_EXACT_PROJECT_PROFILE`. A non-matching filename remains
`UNRESOLVED`; there is no fallback to the first slot, `filament_ids`, or
`base_id`.

## Parameter mapping

The adapter maps only the six verified native keys:

| Canonical | PrusaSlicer key | Fixture result |
|---|---|---|
| `nozzle_temperature` | `temperature` | `MATCH` |
| `nozzle_temperature_initial_layer` | `first_layer_temperature` | `MATCH` |
| `fan_min_speed` | `min_fan_speed` | `MATCH` |
| `fan_max_speed` | `max_fan_speed` | `MATCH` |
| `fan_cooling_layer_time` | `fan_below_layer_time` | `MATCH` |
| `slow_down_layer_time` | `slowdown_below_layer_time` | `MATCH` |

`filament_flow_ratio` and `filament_max_volumetric_speed` remain explicitly
`UNRESOLVED`; `extrusion_multiplier` is not treated as a proven alias.

The comparison core selects the four-value project arrays at slot 1 and keeps
the original array and source index. Native Preset paths are reported as
`ini.<key>` and project paths as
`Metadata/Slic3r_PE.config:<key>[0]`.

## Real fixture result

For `prusa.3mf` + `pla_test.ini`:

- identity: `UNIQUE`, slot 1;
- comparison summary: `MATCH=6`, `UNRESOLVED=2`;
- runtime-effective status: `NOT_ESTABLISHED`;
- report schema: `p9b2.consistency.v1`;
- report source: `PrusaSlicer`.

## Safety and negative coverage

Tests cover missing project member, malformed/invalid UTF-8 project config,
unsafe ZIP paths, filename identity mismatch, selected-slot mismatch, missing
Preset fields, native project list parsing, and unresolved parameter mappings.
Existing SafeZip archive and size limits remain in force.

## Limitations

- Preset inheritance is not expanded.
- Filename identity is enabled only by this Prusa adapter and is not global.
- `filament_flow_ratio` and `filament_max_volumetric_speed` require further
  semantic evidence.
- Runtime-effective values, object/plate assignment, and G-code are outside
  this stored-value validator.
- Preview, Feishu, Miaoda, approval, and publication behavior are unchanged.
