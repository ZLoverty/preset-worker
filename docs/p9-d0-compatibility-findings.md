# P9-D0 Compatibility Findings

## Method

Used the new read-only utility `scripts/inspect_3mf.py`, which uses `SafeZipReader`, lists members deterministically, reads only bounded `Metadata/` configuration files, detects JSON/INI/XML, and reports candidate identity/parameter keys without dumping project contents.

The existing Bambu extraction/comparison was run in an isolated harness only. No new slicer was registered in Preview and no production validator behavior was changed.

## Observed project-side values

All four JSON-config projects store the eight target keys under `Metadata/project_settings.config` using the same canonical names:

```text
filament_flow_ratio
filament_max_volumetric_speed
nozzle_temperature
nozzle_temperature_initial_layer
fan_min_speed
fan_max_speed
fan_cooling_layer_time
slow_down_layer_time
```

Observed project identity and values:

| Slicer | `filament_settings_id` | `filament_ids` | Project values summary |
|---|---|---|---|
| OrcaSlicer | `L2002CF @BBL P2S`, `P7TEST_NAME_SETTINGS_ID`, `AliZ PLA @System`, `L2002CF @BBL P2S` | `OGFL99`, `OGFL99`, `AliZ002`, `OGFL99` | all eight present; most arrays length 4 |
| SnapmakerOrcaSlicer | `pla_test`, `Generic PLA`, `Generic PLA`, `Generic PLA` | `OGFSA04`, `GFSL991`, `GFSL991`, `GFSL991` | all eight present; most arrays length 4 |
| CrealityPrint | `pla_test` | `01001` | all eight present as one-element arrays |
| ElegooSlicer | `pla_test` | `EPLAB00` | all eight present as one-element arrays |
| PrusaSlicer | `pla_test;03_custom_metadata;03_custom_metadata;03_custom_metadata` in `Slic3r_PE.config` | not observed as a separate project key | target values are stored in semicolon-prefixed INI lines, mostly four comma-separated values |

The Prusa project does not use `Metadata/project_settings.config`; it uses `Metadata/Slic3r_PE.config`. Its values include:

```text
filament_max_volumetric_speed = 17,17,17,17
temperature = 230,230,230,230
first_layer_temperature = 230,230,230,230
min_fan_speed = 100,100,100,100
max_fan_speed = 100,100,100,100
fan_below_layer_time = 50,50,50,50
slowdown_below_layer_time = 9,9,9,9
```

`filament_flow_ratio` was not observed in the Prusa project or supplied Preset. The likely Prusa candidate `extrusion_multiplier` is not sufficient evidence for a direct mapping.

## Isolated Bambu probe results

| Slicer | Bambu ZIP/project extraction | Slot result using supplied Preset | Comparison summary | Interpretation |
|---|---|---|---|---|
| OrcaSlicer | Reads JSON config and all eight values | Exact Preset id matches slots 1 and 4; accepted by the rule “exact match may select either” | `MISSING_IN_PRESET` 5; the three available Preset values match either slot | Archive extraction reusable; deterministic selection can use the first matching slot |
| SnapmakerOrcaSlicer | Reads JSON config and all eight values | `UNIQUE`, slot 1, exact `filament_settings_id=pla_test` | `MATCH` 3, `MISSING_IN_PRESET` 5, `AMBIGUOUS` 3 due full project arrays vs one-element Preset arrays | Project extraction and identity are evidenced; comparison must select slot before element comparison |
| CrealityPrint | Reads JSON config and all eight values | `UNIQUE`, slot 1, exact `filament_settings_id=pla_test` | `MATCH` 3, `MISSING_IN_PRESET` 5 | Strong evidence for shared project extractor; native Preset adapter still required |
| ElegooSlicer | Reads JSON config and all eight values | `UNIQUE`, slot 1, exact `filament_settings_id=pla_test` | `MATCH` 4, `MISSING_IN_PRESET` 4 | Strong evidence for shared project extractor; verify version and semantics separately |
| PrusaSlicer | Bambu parser reports missing `Metadata/project_settings.config` | Preset is INI; filename stem `pla_test` uniquely matches project slot 1 | Stored-value probe is possible after slot selection; native adapter still required | Separate project/Preset adapter required |

The `MATCH` results for CrealityPrint and ElegooSlicer mean stored values matched for the available Preset keys. They do not prove runtime-effective equivalence or full slicer compatibility.

## Parameter evidence matrix

`DIRECT` below means the same key and stored value were observed on both sides of an actual pair. `MAPPED` is used only for a demonstrated deterministic alias. A project-side key without a corresponding Preset key remains `UNRESOLVED`.

| Canonical parameter | OrcaSlicer | SnapmakerOrcaSlicer | CrealityPrint | ElegooSlicer | PrusaSlicer |
|---|---|---|---|---|---|
| `filament_flow_ratio` | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: both sides absent |
| `filament_max_volumetric_speed` | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: project direct, Preset not inspected as equivalent |
| `nozzle_temperature` | `UNRESOLVED`: project direct, Preset direct but slot unresolved | `DIRECT`: selected slot 1 or 4 is `230`, Preset is `230` | `DIRECT`: `230` vs `230` | `DIRECT`: `230` vs `230` | `MAPPED`: project `temperature=230`, Preset `temperature=230`, after filename-stem slot selection |
| `nozzle_temperature_initial_layer` | `UNRESOLVED`: project direct, Preset direct but slot unresolved | `DIRECT`: selected slot 1 or 4 is `230`, Preset is `230` | `DIRECT`: `230` vs `230` | `DIRECT`: `230` vs `230` | `MAPPED`: project `first_layer_temperature=230`, Preset `first_layer_temperature=230`, after filename-stem slot selection |
| `fan_min_speed` | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: project direct, Preset missing | `DIRECT`: `100` vs `100` | `MAPPED`: project `min_fan_speed=100`, Preset `min_fan_speed=100`, after filename-stem slot selection |
| `fan_max_speed` | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: project direct, Preset missing | `MAPPED`: project `max_fan_speed=100`, Preset `max_fan_speed=100`, after filename-stem slot selection |
| `fan_cooling_layer_time` | `UNRESOLVED`: project direct, Preset direct but slot unresolved | `DIRECT`: selected slot 1 or 4 is `50`, Preset is `50` | `DIRECT`: `50` vs `50` | `DIRECT`: `40` vs `40` | `MAPPED`: project `fan_below_layer_time=50`, Preset `fan_below_layer_time=50`, after filename-stem slot selection |
| `slow_down_layer_time` | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: project direct, Preset missing | `UNRESOLVED`: project direct, Preset missing | `MAPPED`: project `slowdown_below_layer_time=9`, Preset `slowdown_below_layer_time=9`, after filename-stem slot selection |

## Filament identity findings

- Orca: four slots; exact Preset identity `L2002CF @BBL P2S` matches slot 1 and slot 4. Under the agreed rule, select either matching slot (implementation should choose the lowest slot deterministically); all eight target values are equal between slots 1 and 4 in this fixture.
- Snapmaker: project has four slots and slot 1 is `pla_test`; the updated root Preset now gives `UNIQUE` identity. The existing validator still reports array ambiguity because it compares the full four-element project arrays instead of first selecting slot 1.
- CrealityPrint: one slot, exact `pla_test` match, `filament_ids=01001`; identity is `UNIQUE` for stored correspondence.
- ElegooSlicer: one slot, exact `pla_test` match, `filament_ids=EPLAB00`; identity is `UNIQUE` for stored correspondence.
- PrusaSlicer: supplied Preset has empty `filament_settings_id`, but filename stem `pla_test` exactly matches only project slot 1. Identity is `UNIQUE_BY_FILENAME` for this fixture; the filename is not a universal identity unless the project-side exact-match and uniqueness checks pass.

These classifications establish stored identity correspondence only. They do not establish that the selected slot is the runtime-effective filament configuration after inheritance, plate assignment, object assignment, or slicing.

## Compatibility classification

| Slicer | Classification | Reason |
|---|---|---|
| OrcaSlicer | `REUSE_WITH_ADAPTER` | Project JSON paths and keys are reusable, but identity and multi-slot selection need an adapter and a corrected pair |
| SnapmakerOrcaSlicer | `REUSE_WITH_ADAPTER` | Real pair now proves shared project JSON extraction and unique slot identity; slot-aware comparison and fork-specific provenance remain required |
| CrealityPrint | `REUSE_WITH_ADAPTER` | Existing Bambu project extraction reads the real project and exact slot identity; native Preset mapping/report source still needs slicer label and tests |
| ElegooSlicer | `REUSE_WITH_ADAPTER` | Existing Bambu project extraction reads the real project and exact slot identity; version/header and Preset semantics need adapter tests |
| PrusaSlicer | `SEPARATE_PARSER_REQUIRED` | Different project member and INI representation; Bambu parser cannot read it |

No classification above authorizes production Preview routing. P9-D1 must add adapter-level acceptance tests first.
