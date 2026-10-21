# P9-D1 Shared Consistency Engine

## Scope

P9-D1 extracts stored-value comparison and explicit filament-slot selection for
the existing BambuStudio validator. It does not add any slicer to Preview and
does not interpret runtime-effective settings.

## Module boundary

`src/preset_worker/three_mf/comparison_core.py` is slicer-neutral. It receives
already extracted canonical parameter dictionaries and explicit project slot
objects. It provides:

- numeric normalization and existing parameter units;
- comparison statuses and element-level comparison rows;
- proven slot-indexed array selection;
- duplicate identity equivalence checks.

It does not read ZIP members, parse Presets, resolve inheritance, call Preview,
or depend on Feishu. `bambu_parser.py` remains responsible for 3MF extraction
and `consistency.py` remains the Bambu-specific adapter/report wrapper.

## Slot and array rules

Internal slot IDs remain one-based because the existing `FilamentSlot` model and
public report use one-based `slot_id` values. Parameter array indexes in source
paths remain zero-based, for example `$.nozzle_temperature[0]` for slot 1.

An array is selected by slot only when its length exactly equals the explicit
project slot count. A scalar is never indexed. An array with unproven
cardinality is retained as an array and keeps the previous `AMBIGUOUS` or
`NOT_COMPARABLE` behavior. No broadcasting or truncation is performed.

The selected comparison preserves `original_array` and the original source
index in the report, so the result can be rendered in a future comparison
table.

## Identity and duplicate slots

Identity is matched before parameter equality is considered. The shared core
accepts identity candidates supplied by an adapter; it does not invent a
filename fallback. Therefore a Prusa adapter may explicitly pass a unique INI
filename stem, while Bambu-style JSON Presets continue to use their native
identity fields.

Selection behavior is:

- one exact match: select it and report `UNIQUE`;
- no exact match: report `UNRESOLVED`;
- multiple exact matches: inspect every target parameter at every matching
  slot; if all are numeric-equivalent, select the lowest slot and record
  `MULTIPLE_EQUIVALENT`; otherwise report `AMBIGUOUS`;
- missing or unproven parameter evidence prevents deterministic duplicate
  selection.

The existing public report status remains unchanged. `matching_slot_ids` and
selection evidence are additive report details; no new external status is
introduced.

## BambuStudio integration

`validate_bambu_consistency()` still owns Bambu Preset parsing, canonicalization,
project extraction, runtime-effective status, hashes, provenance, and report
assembly. It delegates slot selection and per-parameter comparison to the
shared core. Preview dispatch and the `p9b2.consistency.v1` envelope are
unchanged.

For the old single-slot tests, arrays whose slot association is not proven are
still compared element-wise exactly as before. For verified multi-slot arrays,
the Preset value is compared with the selected project element instead of the
whole project array.

## Fixture coverage

The isolated tests cover:

- Bambu P9-B2 regression behavior and report shape;
- real Orca duplicate identity at slots 1 and 4, with deterministic slot 1
  selection;
- real Snapmaker four-slot selection at slot 1 without false array ambiguity;
- generic duplicate identity mismatch and incomplete-evidence rejection;
- no identity match, missing values, malformed/non-numeric values, scalar vs
  array mismatch, and unproven array cardinality.

Prusa remains an adapter-only normalized-input test concern in this phase. Its
production INI/3MF parser is intentionally not implemented here.

## Known limitations and next scope

- Runtime-effective values, inheritance, plate/object assignment, and G-code
  semantics remain outside this core.
- `filament_flow_ratio` and other missing Preset parameters remain explicitly
  missing rather than inferred.
- New slicer Preview routing is not enabled.

P9-D2 can add slicer-specific adapters, beginning with the Bambu-style
CrealityPrint and ElegooSlicer project inputs, followed by Orca/Snapmaker
provenance and a separately reviewed Prusa adapter.
