# Flash Studio Slicer Support Plan

> Status: IMPLEMENTED. The implementation evidence and remaining limitations are
> recorded in `docs/flash-studio-onboarding-report.md`.

## 1. Discovery scope

- Mode: `DISCOVERY` → `IMPLEMENTATION` → `VERIFICATION`; the original discovery
  plan is retained as the decision record.
- Repository revision inspected: `ad0e230cde6ce2591d215dada07620669f156f3c`.
- Official slicer name: `Flash Studio` — CONFIRMED by user.
- Canonical Worker ID: `FlashStudio` — CONFIRMED for the plan.
- Fixture directory: `tests/fixtures/slicers/flash_studio/`.
- Current registered slicers: BambuStudio, CrealityPrint, ElegooSlicer, OrcaSlicer, PrusaSlicer, and SnapmakerOrcaSlicer.

## 2. Fixture inventory

| Fixture | Size | SHA-256 | Evidence |
|---|---:|---|---|
| `pla ff creator 5.json` | 829 bytes | `906ccb48079f2277771117cc50cd957bd2606dd79681c57197f7dec68546ff4e` | Native JSON, UTF-8/CRLF, directly inspected — CONFIRMED |
| `pla ff creator 5.3mf` | 14,871 bytes | `47bf7233a4ae110766ae180f5e0892af652685ac919ed323fae17c4ca08fd296` | Safe ZIP inspection, 12 members — CONFIRMED |

Native JSON identity and metadata:

```text
name: pla ff creator 5
filament_settings_id: ["pla ff creator 5"]
inherits: Generic PLA @FF C5
version: 2.4.0.10
```

3MF observations:

- `3D/3dmodel.model` reports `BambuStudio-02.06.00.51` and `OrcaSlicer 2.4.2` — CONFIRMED.
- `Metadata/slice_info.config` repeats Bambu/Orca version markers — CONFIRMED.
- `Metadata/project_settings.config` is JSON-shaped Bambu/Orca-family settings — CONFIRMED.
- Printer context is `Flashforge Creator 5`, printer profile `Flashforge Creator 5 0.4 nozzle` — CONFIRMED.
- Four slots all use `pla ff creator 5`, PLA, and `GFL99` — CONFIRMED.
- One plate is present in `Metadata/model_settings.config` — CONFIRMED.
- No multi-plate or ambiguous-identity evidence is supplied — NOT_VERIFIED.

The archive was inspected in memory without extraction or execution. Original fixture bytes were not modified.

## 3. Current compatibility evidence

The existing `BambuStudioProcessor` parses and validates the Native JSON shape. The existing `parse_bambu_3mf()` extracts the Flashforge printer context, four filament slots, and all relevant target arrays. Running the existing `validate_bambu_consistency()` against this pair produced:

```text
selection: UNIQUE
matching_slot_ids: [1, 2, 3, 4]
summary: {"MATCH": 8}
```

This proves parser/shape compatibility with the current Bambu-family implementation — CONFIRMED. It does not prove that Flash Studio is semantically identical to BambuStudio, nor that the 3MF was exported by Flash Studio — NOT_VERIFIED.

## 4. Native parameter inventory

The Native fixture contains these relevant fields:

| Native field | Current catalog/target relationship | Proposed plan status |
|---|---|---|
| `filament_flow_ratio` | Existing Bambu-family important field and consistency target | Reuse after Flash-specific classification test |
| `filament_max_volumetric_speed` | Existing target | Reuse after classification test |
| `nozzle_temperature` | Existing target | Reuse after classification test |
| `nozzle_temperature_initial_layer` | Existing target | Reuse after classification test |
| `fan_min_speed`, `fan_max_speed` | Existing targets | Reuse after classification test |
| `fan_cooling_layer_time`, `slow_down_layer_time` | Existing targets | Reuse after classification test |
| `filament_density` | Important in the fixture but not a current JSON consistency target | Keep Native Diff decision separate; do not add a 3MF target yet |
| `filament_extruder_variant` | Catalogued only for ElegooSlicer today | Add Flash-specific catalog entry only after semantic confirmation |
| `pressure_advance` | Catalogued as Important for JSON families, not a current consistency target | Native Diff candidate; 3MF comparison remains out of scope |
| `textured_plate_temp` / `hot_plate_temp` | Plate-temperature fields; `hot_plate_temp` is not currently catalogued for BambuStudio | Verify semantics and exact Flash paths before catalog change |
| `nozzle_temperature_range_low` | Existing catalog path for JSON families | Verify Flash classification with a fixture mutation |

The current BambuStudio static inventory has 15 catalog rows: 8 target-covered and 7 not targeted. This is a planning observation, not a request to expand `REQUIRED_PARAMETERS`.

## 5. Recommended architecture

### User-confirmed decisions

1. Official display name is `Flash Studio`; use `FlashStudio` as the canonical Worker ID — CONFIRMED.
2. Flash Studio is probably Orca-derived, but the exact upstream fork and version are not known — INFERRED / NOT_VERIFIED.
3. `textured_plate_temp` is provisionally treated as a Native Preset stored setting, while `hot_plate_temp` is provisionally treated as a slicer-computed plate-specific firmware input — INFERRED / NOT_VERIFIED.
4. Four equal filament slots may be resolved as one equivalent selection when the existing duplicate-equivalence proof passes — CONFIRMED.

### Phase A — identity and semantic confirmation

Before implementation, confirm:

1. Flash Studio version, upstream repository/fork, and the exact Orca-derived baseline remain to be confirmed.
2. Whether the Native JSON is exported by Flash Studio itself or by an Orca-derived compatibility mode.
3. Whether `pla ff creator 5.json` and `pla ff creator 5.3mf` are a guaranteed pair from the same export.
4. Whether the 3MF `BambuStudio`/`OrcaSlicer` metadata is expected Flash Studio behavior or an inherited upstream marker.
5. Whether the provisional `textured_plate_temp` (stored preset setting) versus `hot_plate_temp` (computed plate-specific firmware input) distinction is confirmed by Flash Studio behavior or source code.
6. Whether duplicate-equivalent slot selection should always use the lowest matching slot; the supplied fixture permits this, but a multi-material/non-equivalent fixture is still required.

### Phase B — Native Preset support

Implement a thin Flash Studio JSON processor reusing the existing JSON parsing, validation, normalization, policy, serialization, and diff mechanics. Because the fixture carries Orca metadata, first compare behavior with `orca_compatible_core.py`; reuse that core only where the fixture and tests prove compatibility. Prefer a shared JSON core or explicit delegation over copying BambuStudio/Orca code.

Required work:

- Add a canonical `FlashStudio` processor registration and only explicit aliases approved for the `Flash Studio` label.
- Derive `important_parameter_paths` and classification from `parameter_catalog.py`; do not reuse BambuStudio's hard-coded classifier implicitly.
- Add Flash-specific system metadata paths only when fixture or processor evidence establishes them.
- Preserve unknown fields, array shape, native paths, deterministic ordering, and `UnifiedDiff` serialization.
- Add malformed JSON, missing version, invalid identity, round-trip, and unknown-field tests.
- Add field mutation tests for all candidate Important fields, including indexed paths and metadata precedence.

Initial Native capability proposal: `Supported` for parse/validation/diff only after Phase B tests pass — INFERRED.

### Phase C — 3MF extraction and Consistency

Reuse `bambu_parser.py`, `comparison_core.py`, and `native_consistency.py` only if the confirmed Flash Studio export contract remains compatible.

Required work:

- Add a Flash-specific validator entry point so reports identify `FlashStudio`, rather than silently reporting `BambuStudio`.
- Register the validator and capability only after a dedicated Flash fixture test passes registration completeness.
- Assert the exact identity path, four-slot cardinality, duplicate-equivalence selection, source paths, and all eight existing comparison rows.
- Add a deliberate Native or 3MF value mutation proving `MISMATCH`.
- Add missing Native, missing 3MF, invalid numeric, and unresolved identity cases.
- Preserve `UNRESOLVED` if a future Flash fixture has unmatched identity; do not add a first-slot fallback.
- Do not add `filament_density`, pressure advance, plate temperatures, or other uncovered fields to the target set in the first onboarding phase.

Initial Consistency capability proposal: `Partial` / not yet declared `SUPPORTED` until Flash-specific provenance and validator tests are complete — INFERRED.

### Phase D — lifecycle integration

After Native and Consistency evidence is complete:

- Add Preview dispatch coverage.
- Add formal Submit coverage.
- Verify unsupported/missing-validator behavior through the P10-B2.1 registration guard.
- Verify canonical slicer ID propagation in errors and reports.
- Leave Feishu field mappings and publication behavior unchanged unless separately approved.

## 6. Planned files

Likely implementation files, subject to Phase A confirmation:

```text
src/preset_worker/slicers/flash_studio.py          # new thin processor/facade
src/preset_worker/slicers/registry.py              # registration
src/preset_worker/slicers/contracts.py             # explicit aliases only if needed
src/preset_worker/slicers/capabilities.py          # capability declaration
src/preset_worker/slicers/parameter_catalog.py     # only confirmed Flash paths
src/preset_worker/three_mf/consistency.py          # dedicated validator entry point if supported
src/preset_worker/services/consistency_preview.py  # dispatch registration if supported
tests/test_flash_studio.py                         # Native contract and diff tests
tests/test_flash_studio_consistency.py             # fixture-based consistency tests
tests/test_registration_completeness.py            # registration assertions
```

Do not change `REQUIRED_PARAMETERS`, comparison statuses, slot-selection algorithms, or Native Diff schema as part of the initial onboarding.

## 7. Acceptance test plan

### Native Preset

- Valid fixture parses and validates.
- Missing `version`, malformed JSON, non-object JSON, and invalid filename behavior are asserted.
- Canonical naming and `pm_method_version` remain context-authoritative.
- Unknown fields survive round-trip.
- Important, ordinary, metadata, unknown, and indexed fields classify correctly.
- Diff path, change type, values, category, ordering, and serialization remain compatible.

### 3MF and Consistency

- Safe ZIP member inspection and malformed archive behavior.
- Exact `Metadata/project_settings.config` and Flash printer context.
- Four equal identity slots select as `UNIQUE` only because target arrays are equivalent.
- Eight existing targets compare to `MATCH` for the supplied pair.
- A controlled changed value produces `MISMATCH`.
- Missing operands never produce `MATCH`.
- Identity mismatch produces `UNRESOLVED`, not a guessed slot.

### Integration

- Registration completeness passes.
- Preview and Submit report `schema_version = p9b2.consistency.v1`.
- Native-only processing remains available if Consistency is temporarily `UNSUPPORTED`.
- No external `downloads/` fixture dependency is introduced; use the supplied repository fixture path.

## 8. Capability matrix for the plan

| Capability | Current evidence | Planned declaration | Limitation |
|---|---|---|---|
| Native Preset | JSON shape parses through Bambu processor | Supported after Flash-specific processor tests | Official identity and policy semantics unconfirmed |
| Validation | Existing JSON validation is reusable | Supported after required-field tests | No Flash-specific validation rules established |
| Diff | Existing Bambu-family diff can classify fixture fields | Supported after catalog/path tests | Flash-specific metadata and bed aliases unresolved |
| 3MF Extraction | Existing parser extracts fixture successfully | Partial initially | Export provenance and Flash-specific semantics unconfirmed |
| Consistency | Existing Bambu validator gives `MATCH: 8` | Partial initially; Supported only after dedicated validator | Current result is Bambu-labeled evidence |
| Inheritance | Native `inherits` and 3MF `inherits_group` are present | Preserve Only | No effective parent merge should be claimed |
| Multi-filament | Four identical slots are present | Partial | Only duplicate-equivalent selection evidenced |
| Multi-plate | One plate observed | Not Verified | No multi-plate fixture |
| Publication | No Flash-specific publication test | Not Verified | Out of scope for discovery |

## 9. Exit criteria and open decisions

The implementation milestone is complete. Native Preset support and fixture-backed
Diff tests are implemented; Consistency uses a dedicated FlashStudio validator
entry point and is covered by fixture-backed tests. This does not establish Flash
Studio's official upstream identity or runtime semantics beyond the supplied
artifacts.

Open decisions requiring confirmation:

- Canonical slicer ID and accepted display aliases.
- Whether Flash Studio should initially declare Consistency `UNSUPPORTED` or receive a dedicated `SUPPORTED` validator after Phase C.
- Whether the provisional `hot_plate_temp` / `textured_plate_temp` storage-versus-computed distinction is confirmed.
- Whether Flash Studio's 3MF metadata intentionally identifies as BambuStudio/OrcaSlicer.
- Flash Studio version and upstream repository/fork.
