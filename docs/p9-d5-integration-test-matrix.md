# P9-D5 Integration Test Matrix

Coverage status refers to the current repository, not the intended P9-D6
behavior.

| ID | Slicer/workflow | Scenario | Expected result | Existing coverage | Status | Severity | P9-D6 action |
|---|---|---|---|---|---|---|---|
| D5-01 | BambuStudio | Real Preset + real 3MF | READY report, Bambu source, compatible rows | `test_p9_b2.py`, `downloads/3mf-fixture` manual audit | PARTIAL | high | Add real-fixture contract test |
| D5-02 | CrealityPrint | Real pair | slot 1, 3 MATCH, 5 missing | `test_p9_d2.py` | PASS | high | Include in six-slicer dispatch test |
| D5-03 | ElegooSlicer | Real pair | slot 1, 4 MATCH, 4 missing | `test_p9_d2.py` | PASS | high | Include in six-slicer dispatch test |
| D5-04 | OrcaSlicer | Duplicate equivalent identity | slots `[1,4]`, select 1, reason `MULTIPLE_EQUIVALENT` | `test_p9_d3.py` | PASS | critical | Contract assertion and rollout gate |
| D5-05 | SnapmakerOrcaSlicer | Four-slot real pair | unique slot 1, 3 MATCH, no false ambiguity | `test_p9_d3.py` | PASS | critical | Contract assertion and rollout gate |
| D5-06 | PrusaSlicer | Filename-stem identity | `pla_test` uniquely selects slot 1 | `test_p9_d4.py` | PASS | critical | Contract assertion and UI evidence |
| D5-07 | All six | Report shape | same schema, keys, order, serializability | manual report generation in D5 | PARTIAL | critical | Add automated contract test |
| D5-08 | All six | Inner report fingerprint | unchanged input has stable artifact/report hash | artifact hashes exist; no formal test | MISSING | high | Define and test input fingerprint |
| D5-09 | All six | Runtime status | non-Bambu never claims runtime equivalence | D2/D3/D4 tests | PASS | high | Preserve in contract test |
| D5-10 | All six | Missing Preset parameters | missing, not mismatch | D2/D3/D4 tests | PASS | high | Preserve |
| D5-11 | All six | No 3MF | clear old consistency field | `test_p9_b3_a.py` Bambu path only | PARTIAL | critical | Test all slicers through dispatch |
| D5-12 | All six | Unsupported slicer | native policy plus cleared report | native failure tests; no stale-field test | MISSING | critical | Clear field on candidate failure |
| D5-13 | All six | Invalid 3MF | ERROR envelope, native Preview succeeds | `test_p9_b3_a.py` Bambu exception mock | PARTIAL | high | Parameterize dispatch |
| D5-14 | All six | Malformed Preset | primary validation failure; no stale report | processor tests | PARTIAL | critical | Clear consistency field in failure write |
| D5-15 | All six | Changed Preset after prior Preview | new report replaces old, or failure clears old | no lifecycle test | MISSING | critical | Add stale-clear/replacement test |
| D5-16 | All six | Changed 3MF after prior Preview | new report corresponds to current attachment | no recheck | MISSING | critical | Add pre-write input recheck test |
| D5-17 | All six | Changed slicer | old report cleared/replaced | valid path clears; failure path untested | PARTIAL | critical | Test valid and invalid transitions |
| D5-18 | All six | Removed 3MF | empty field clears old report | valid candidate path implemented | PARTIAL | high | Add PreviewService mock test |
| D5-19 | All six | Repeated unchanged Preview | deterministic inner report; envelope timestamp may change | no exact repeat test | MISSING | medium | Assert stable inner fingerprint |
| D5-20 | All six | Worker retry | no stale restoration | Feishu transient retry only | MISSING | critical | Add retry/idempotency tests |
| D5-21 | All six | Two workers same record | one current result, no stale overwrite | serial runtime test only | MISSING | critical | Add concurrency simulation and guard |
| D5-22 | All six | Feishu write failure | native error handling, no corrupt partial result | limited client tests | PARTIAL | high | Test consistency field failure and retry |
| D5-23 | All six | Report over field limit | sanitized ERROR or verified alternative | oversized serialization unit test | PASS | high | Verify deployed field limit |
| D5-24 | All six | Unknown additive report field | tolerant frontend/consumer | no frontend test | MISSING | medium | Add contract consumer fixture |
| D5-25 | Miaoda | Unified table with 3MF | one table with Preset/3MF/status/provenance | frontend unavailable | NOT_VERIFIED | critical | Inspect actual Miaoda implementation |
| D5-26 | Miaoda | No 3MF / empty report | Preset-only table, no stale consistency | frontend unavailable | NOT_VERIFIED | high | Validate view model and clear behavior |
| D5-27 | Miaoda | Ambiguous/unresolved identity | visible uncertainty, never MATCH | frontend unavailable | NOT_VERIFIED | critical | Add UI acceptance tests |
| D5-28 | All six | Full timing | download, parse, comparison, write latency | `profiling.py` stages/API logs | PARTIAL | medium | Add consistency stage/outcome metrics |

## Test layers

- Unit tests: parser, comparison core, status precedence, identity strategy.
- Adapter tests: real fixture reports and synthetic malformed/mismatch variants.
- Preview service tests: mocked Feishu client, lifecycle clearing, exceptions,
  serialization fallback, and write failure.
- Contract tests: all six validators, common schema/order/status/fingerprint.
- Integration tests: discovered record through Preview write using recorded
  attachments and a fake Feishu client.
- Safe-environment tests: Feishu field type/limit, conditional update support,
  and actual Miaoda consumer behavior.

## Blocking cases

D6 production enablement must not proceed while D5-12, D5-15, D5-16, D5-20,
D5-21, or D5-25–D5-27 remain unverified. The current adapter unit tests are
necessary but do not cover these lifecycle, concurrency, storage, and frontend
properties.
