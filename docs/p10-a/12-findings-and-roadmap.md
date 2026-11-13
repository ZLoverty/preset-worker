# Findings and Roadmap

## Ranked findings

1. **BLOCKER — inconsistent important-parameter catalogs.** Evidence: processor sets, `three_mf/consistency.py:20-29`, `comparison_core.py:13-22`, and failing `test_fixture_field_classification.py`. Impact: parameters can be extracted and diffed but omitted from consistency. Minimal correction: define a versioned canonical catalog with per-slicer native aliases and explicit unsupported reasons; do not change rules during P10-A.
2. **BLOCKER — incomplete consistency registration contract.** Evidence: separate processor registry and validator map (`registry.py:28-36`, `consistency_preview.py:30-37`), plus wrappers documented as not registered. Impact: partial onboarding can silently yield empty report. Minimal correction: capability/completeness check in tests or composition.
3. **HIGH_VALUE — missing committed Bambu integration fixtures.** Evidence: tests reference `downloads/3mf-fixture`, absent from repository. Impact: 8 errors and no reproducible Bambu lifecycle baseline. Minimal correction: commit sanitized paired fixtures or make tests explicitly skip with a documented acquisition step.
4. **HIGH_VALUE — inheritance is preserved, not resolved.** Evidence: all `normalize()` implementations are copies and no parent resolver exists. Impact: new slicers cannot claim effective inherited values. Minimal correction: document preserve-only behavior; implement resolver only after fixture semantics are approved.
5. **HIGH_VALUE — generic outer consistency error loses diagnostic class.** Evidence: `consistency_preview.py:97-104`. Impact: persisted report cannot distinguish malformed data, mapping gap and implementation defect. Minimal correction: preserve report issue codes/reason categories in the envelope.
6. **OPTIONAL — duplicated Snapmaker aliases.** Evidence: `contracts.py:98-113` versus `registry.py:19-25`. Minimal correction: one alias table.
7. **NOT_RECOMMENDED — introduce a plugin framework.** Existing processor composition and protocol are sufficient for the current six slicers.

## Roadmap

- P10-B: build the onboarding skill from this evidence; add registry/completeness and fixture-inventory procedures.
- P10-C: apply the skill to one new slicer with approved fixtures, then implement only missing adapters and tests.
- Before either phase, decide whether “consistency coverage” means the current eight stored parameters or the broader processor important sets; current code does not make that contract explicit.

No production code, tests or configuration were changed by this audit.
