# P10-B2.2 Native Important Parameter Catalog

## 1. Repository and target

- Revision baseline: `089e6c0e41ca5908a87953ef885307fe67e6998f` — CONFIRMED
- Target: Native Preset Diff Important Parameter classification for the six registered slicers — CONFIRMED
- Scope: BambuStudio, OrcaSlicer, CrealityPrint, ElegooSlicer, SnapmakerOrcaSlicer, and PrusaSlicer.
- Explicit non-scope: 3MF extraction, consistency target sets, comparison statuses, Feishu schemas, and publication.

## 2. Fixtures and evidence

No fixture files were added or modified. Existing Native Diff fixture tests were reused. The five known classification defects in `tests/test_fixture_field_classification.py` now pass — CONFIRMED. Existing external Bambu 3MF fixture tests remain environment-dependent — NOT_VERIFIED.

## 3. Existing architecture reuse

- Native processors retain their existing parse, validation, normalization, serialization, and UnifiedDiff contracts — CONFIRMED.
- `src/preset_worker/slicers/parameter_catalog.py` is the new canonical catalog. Processor-local sets are derived from it, with Prusa's existing `ini.` compatibility view preserved — CONFIRMED.
- Shared alias canonicalization from P10-B2.1 is reused — CONFIRMED.
- `three_mf/consistency.py`, `three_mf/native_consistency.py`, `three_mf/prusa_consistency.py`, and `three_mf/comparison_core.py` were not changed — CONFIRMED.

## 4. Gap assessment and changes

| Capability | Existing reuse | Required action | Evidence |
|---|---|---|---|
| Canonical Important catalog | Six duplicated/local definitions | Added `ParameterDefinition` catalog with canonical IDs, native paths, aliases, targets, and notes | CONFIRMED by catalog tests |
| Classification | Existing `DiffCategory` and UnifiedDiff | Centralized exact/indexed path classification; metadata checked first; unknown paths remain `OTHER_PARAMETER` | CONFIRMED by focused tests |
| Slicer-specific paths | Existing Snapmaker, Elegoo, and Prusa exceptions | Moved into explicit per-slicer catalog entries; no cross-slicer leakage | CONFIRMED by isolation tests |
| Consistency inventory | Existing runtime target catalogs | Added read-only `build_coverage_inventory()`; no runtime dispatch or status changes | CONFIRMED by static/determinism tests |
| Skill guidance | Existing onboarding workflow | Documented catalog use, coverage meanings, and the Important-versus-3MF distinction | CONFIRMED by skill validation |

## 5. Parameter coverage

The inventory is static target-name membership only. With the six registered slicers and `three_mf.consistency.REQUIRED_PARAMETERS`, it produces 93 rows: 46 `Covered` and 47 `Not covered`. No row is evidence of successful extraction, slot/index resolution, mapping, normalization, or end-to-end comparison.

Covered target families include flow ratio, maximum volumetric speed, nozzle temperatures, fan limits/timing, and slowdown layer time. Not covered include pressure advance, retraction, chamber and plate temperatures, nozzle range low, Elegoo extruder variant, Snapmaker plate variants, and several Prusa material/cooling/extrusion fields. These are disclosed gaps, not converted into 3MF targets.

When no target catalog is supplied, the inventory emits `Unknown`. This avoids inferring support from missing evidence.

## 6. Classification and compatibility details

- Exact native paths and numeric indexed paths such as `nozzle_temperature[1]` classify as Important when catalogued.
- Malformed indexes such as `[abc]`, prefix collisions, and unknown paths remain Other.
- System metadata takes precedence over Important classification.
- Prusa keeps its public processor path contract without `ini.` while the catalog stores the native `ini.*` paths.
- `UnifiedDiff` shape, path representation, value handling, category names, and deterministic ordering were not changed.

## 7. Tests

Focused verification:

```text
PYTHONPATH=src python -m unittest tests.test_parameter_catalog tests.test_fixture_field_classification tests.test_registration_completeness tests.test_p9_b3_a tests.test_creality_print tests.test_elegoo_slicer tests.test_orca_slicer tests.test_snapmaker_orca tests.test_prusa_slicer -q
Ran 84 tests ... OK
```

Additional checks:

- `python -m compileall -q src tests` — passed.
- `git diff --check` — passed; Git emitted only existing line-ending/config warnings.
- `python .agents/skills/skill-creator/scripts/quick_validate.py .agents/skills/slicer-onboarding` — passed (`ok: true`).
- Full discovery: 258 tests, 1 pre-existing failure, 8 environment-dependent errors, 2 skips.

The remaining failure is `test_p9_d4.P9D4PrusaTests.test_missing_preset_parameter_stays_missing` (`MATCH` versus expected `MISSING_IN_PRESET`) and is unrelated to catalog classification. The eight errors require the absent external `downloads/3mf-fixture` Bambu files. The focused suite contains no new failures.

## 8. Capability declaration

| Capability | Declaration | Evidence | Limitations |
|---|---|---|---|
| Native Preset | Supported | Existing processor tests plus catalog migration tests | This change is classification-focused |
| Validation | Supported | Existing cross-slicer tests | No validation behavior changed |
| Diff | Supported | UnifiedDiff contract and fixture classification tests | Important membership does not imply 3MF comparison |
| 3MF Extraction | Partial | Existing code and unchanged tests | No new extraction evidence or fixtures |
| Consistency | Partial | Static coverage inventory and unchanged runtime target sets | 47 inventory rows are not covered; runtime mapping is not proven by the inventory |
| Inheritance Resolution | Preserve Only / existing behavior | No change in this task | No new effective-value claim |
| Multi-filament | Existing declaration unchanged | No new fixtures | Not expanded by this task |
| Multi-plate | Existing declaration unchanged | No new fixtures | Not expanded by this task |
| Publication | Not Verified | No publication path exercised | Out of scope |

## 9. Acceptance

- Final status: Partial — CONFIRMED.
- Known limitations: the existing Prusa consistency regression and missing external Bambu fixtures remain; static coverage cannot establish semantic equivalence or end-to-end comparison.
- Recommended follow-up: P10-B2.3 should use this catalog and inventory to review uncovered parameters and decide, with fixture evidence, which mappings belong in future 3MF consistency work.
