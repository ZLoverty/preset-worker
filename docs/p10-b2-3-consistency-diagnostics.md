# P10-B2.3 Consistency Coverage Audit, Diagnostic Reliability & Regression Verification

## 1. Repository and target

- Baseline revision: `f79c4d8` (`p10-b2.2 important parameter catalog`) — CONFIRMED.
- Scope: existing Native Preset to 3MF Consistency diagnostics for six registered slicers — CONFIRMED.
- No new slicer, target parameter, Native Diff rule, Feishu schema, or publication behavior was added — CONFIRMED.

## 2. Current Consistency architecture

The implemented pipeline is:

```text
Native Artifact
  -> Slicer processor parse/validate/normalize/policy
  -> Native consistency target extraction
  -> canonical target names and adapter mapping
  -> compare_parameter()
  -> comparison objects and flattened comparison_rows
  -> Preview/Submit envelope in services/consistency_preview.py
```

The independent project path is:

```text
3MF Artifact
  -> SafeZipReader and bambu_parser.py/prusa_parser.py
  -> project settings and FilamentSlot extraction
  -> select_slot() identity/cardinality resolution
  -> slot-aware project value selection
  -> numeric normalization and comparison
  -> comparison objects and report rows
```

Ownership is split between `three_mf/comparison_core.py`, the native adapter in
`three_mf/native_consistency.py`, the Prusa adapter in
`three_mf/prusa_consistency.py`, the format parsers, and the optional boundary
`services/consistency_preview.py`. Missing values are represented as
`MISSING_IN_PRESET` or `MISSING_IN_3MF`; unresolved identity/selection remains
`UNRESOLVED`; shape mismatch is `NOT_COMPARABLE`; invalid numeric values are
`UNRESOLVED`. These are intentionally not collapsed into `MATCH`.

## 3. Prusa regression

The failing assertion was reproduced. The comparison engine already returned
`MISSING_IN_PRESET` when the key was genuinely absent. The test mutation was
incorrect: `pla_test.ini` uses CRLF, while the test removed only the LF form,
so `max_fan_speed = 100` remained in the parsed Native Preset and correctly
produced `MATCH`. The smallest correction was to remove the CRLF line in
`tests/test_p9_d4.py`; production comparison semantics were not weakened.

Added invariant tests cover:

- Native missing / 3MF present -> `MISSING_IN_PRESET`;
- Native present / 3MF missing -> `MISSING_IN_3MF`;
- both missing -> existing non-`MATCH` behavior (`MISSING_IN_PRESET`);
- equal and unequal resolved values;
- invalid numeric values -> `UNRESOLVED`;
- scalar/array shape mismatch -> `NOT_COMPARABLE`.

The comparison helper now also emits optional parameter-level `diagnostic`
fields while preserving `schema_version` and all public comparison statuses.

## 4. Orca `UNRESOLVED: 8` diagnosis

The committed pair was reproduced:

```text
tests/fixtures/slicers/orca_slicer/valid/pla_test.json
tests/fixtures/slicers/orca_slicer/orca.3mf
```

Observed evidence:

- Native identity candidate: `pla_test` — CONFIRMED.
- 3MF slot identities: `L2002CF @BBL P2S`, `P7TEST_NAME_SETTINGS_ID`,
  `AliZ PLA @System`, and `L2002CF @BBL P2S` — CONFIRMED.
- Selection: `UNRESOLVED`, reason `no identity match` — CONFIRMED.
- Summary: `{"UNRESOLVED": 8}` — CONFIRMED.

This is an insufficient/mismatched fixture pair, not evidence of a parser or
selector defect. The existing selector requirement was preserved; no fixture
identity was hardcoded and no first-slot fallback was introduced. Because the
pair cannot establish a valid association, it is not a valid end-to-end
comparison fixture. A separate committed Orca pair already demonstrates a
resolvable comparison in `tests/test_comparison_core.py`, while this pair is
retained as the negative identity-resolution regression.

## 5. Diagnostic taxonomy

The report continues to use the existing public status vocabulary. Optional
diagnostics now separate:

| Layer | Values/evidence | Meaning |
|---|---|---|
| Coverage | `MAPPING_DECLARED`, `MAPPING_UNKNOWN` | Whether a target mapping is declared or explicitly unverified |
| Resolution | `RESOLVED`, `SOURCE_PARAMETER_MISSING`, `SOURCE_PARAMETER_INVALID`, `FILAMENT_IDENTITY_UNRESOLVED`, `SHAPE_NOT_COMPARABLE` | Where operand or identity resolution stopped |
| Comparison | Existing `MATCH`, `MISMATCH`, `MISSING_IN_PRESET`, `MISSING_IN_3MF`, `UNRESOLVED`, `AMBIGUOUS`, `NOT_COMPARABLE` | Public comparison result |

Diagnostics are included on comparison objects and flattened rows. They do not
contain raw artifacts or sensitive metadata, and the report schema version is
unchanged.

## 6. Runtime changes

- `comparison_core.compare_parameter()` now records diagnostic layer values.
- Native and Prusa adapters add identity and mapping diagnostics at the point
  where those conditions are known.
- Flattened `comparison_rows` preserve source paths and include the optional
  diagnostic object.
- No Consistency target was added; `REQUIRED_PARAMETERS` remains the original
  eight-parameter tuple.
- Native Diff and the P10-B2.2 catalog were not changed.

## 7. Parameter-level coverage assessment

The P10-B2.2 inventory was regenerated against the unchanged eight target names:
93 rows remain: 46 statically target-covered and 47 not targeted. The inventory
is static membership evidence only. It does not assert extraction, mapping,
identity resolution, normalization, or comparison.

| Slicer | Target membership | Mapping evidence | Resolution evidence | Comparison evidence | Highest supported level |
|---|---:|---|---|---|---|
| BambuStudio | 8 target families | Native adapter paths are present | `tests/fixtures/slicers/bambu_studio/PETG-CF A2L.*` resolves | P9-D6 Preview/Submit fixture dispatch passes | `COMPARISON_VERIFIED` for exercised target rows |
| OrcaSlicer | 8 target families | Direct target paths are present | Valid pair: verified; `pla_test` pair: identity unresolved | Valid committed pair comparison tests pass; negative identity pair is unresolved | `COMPARISON_VERIFIED` for valid pair; `UNVERIFIED` for `pla_test` pair |
| CrealityPrint | 8 target families | Native adapter uses shared target names | Committed single-slot fixture resolves | `tests/test_p9_d2.py` asserts comparison summaries | `COMPARISON_VERIFIED` for tested target rows |
| ElegooSlicer | 8 target families | Native adapter uses shared target names | Committed single-slot fixture resolves | `tests/test_p9_d2.py` asserts comparison summaries | `COMPARISON_VERIFIED` for tested target rows |
| SnapmakerOrcaSlicer | 8 target families | Native adapter uses shared target names | Committed fixture resolves | `tests/test_p9_d3.py` asserts comparison summaries | `COMPARISON_VERIFIED` for tested target rows |
| PrusaSlicer | 8 target families | Six native mappings exercised; two mappings explicitly unverified | Filename identity resolves in `prusa.3mf` | `tests/test_p9_d4.py` asserts six matches and two unresolved mappings | `COMPARISON_VERIFIED` for six mappings; `UNVERIFIED` for flow/max-volume mappings |

For every cataloged important parameter outside the eight targets, the highest
level is `NOT_TARGETED`; it is not silently removed. For target rows without a
fixture-level assertion, the highest level is `STATIC_TARGET_ONLY` or
`UNVERIFIED`, never `COMPARISON_VERIFIED`. The exact native aliases remain
available from `build_coverage_inventory()` in
`src/preset_worker/slicers/parameter_catalog.py`.

## 8. Fixtures and provenance

| Fixture | Use | Evidence |
|---|---|---|
| `tests/fixtures/slicers/prusa_slicer/pla_test.ini` + `prusa.3mf` | Prusa positive, mismatch, missing, malformed, unsafe archive cases | CONFIRMED |
| `tests/fixtures/slicers/orca_slicer/L2002CF @BBL P2S.json` + `orca.3mf` | Orca resolvable comparison | CONFIRMED |
| `tests/fixtures/slicers/orca_slicer/valid/pla_test.json` + `orca.3mf` | Orca identity-resolution negative case | CONFIRMED |
| `tests/fixtures/slicers/creality_print/*` | Creality comparison regression | CONFIRMED |
| `tests/fixtures/slicers/elegoo_slicer/*` | Elegoo comparison regression | CONFIRMED |
| `tests/fixtures/slicers/orca_slicer_snapmaker/*` | Snapmaker comparison regression | CONFIRMED |
| `tests/fixtures/slicers/bambu_studio/PETG-CF A2L.json` + `.3mf` | Bambu Preview/Submit integration | CONFIRMED; supplied fixture pair |

No fixture bytes were modified or added.

## 9. Tests

Focused command:

```text
PYTHONPATH=src python -m unittest tests.test_p10_b2_3 tests.test_p9_d4 tests.test_p9_b2 tests.test_p9_d3 tests.test_comparison_core tests.test_registration_completeness tests.test_p9_b3_a tests.test_parameter_catalog -q
Ran 69 tests ... OK
```

Additional checks:

- `PYTHONPATH=src python -m unittest discover -s tests -q`: 263 tests passed,
  2 skips, no errors or assertion failures.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- Skill validation: passed (`Skill is valid!`).

Historical comparison: P10-B2.2 reported 258 tests, 1 Prusa assertion failure,
8 missing-external-fixture errors, and 2 skips. P10-B2.3 fixes the Prusa
assertion, adds five focused tests, and updates P9-D6 to use the supplied
repository Bambu fixture; the former eight fixture errors are now resolved.

## 10. Capability declaration

| Capability | Declaration | Evidence | Limitation |
|---|---|---|---|
| Native Preset | Supported | Existing processors and unchanged catalog tests | Not expanded here |
| Validation | Supported | Existing processor/consistency tests | No validation contract change |
| Diff | Supported | P10-B2.2 tests and unchanged UnifiedDiff behavior | Out of this phase's runtime scope |
| 3MF Extraction | Supported | Committed parser fixtures and safe archive tests, including Bambu | Parameter breadth remains limited to existing targets |
| Consistency | Partial | Six adapters, diagnostics, positive/negative fixtures, full suite | 47 catalog records remain not targeted; some mappings unverified |
| Inheritance Resolution | Preserve Only | Existing behavior unchanged | No effective inherited-value claim |
| Multi-filament | Partial | Slot selection fixtures | Identity ambiguity remains explicit |
| Multi-plate | Partial | Existing project extraction only | No new plate semantics added |
| Publication | Not Verified | Not exercised | Out of scope |

## 11. Acceptance and follow-up

- Final status: Partial — CONFIRMED.
- No bulk target expansion was performed.
- Remaining limitations: invalid Orca `pla_test` identity pairing and two
  explicitly unverified Prusa mappings.
- Future work should expand Consistency targets only after each parameter has
  source-path, identity/slot, normalization, and end-to-end fixture evidence.
- Human confirmation is required before treating any of the 47 `NOT_TARGETED`
  records as comparable 3MF parameters.
