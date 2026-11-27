# P10-B2.1 Registration Completeness

## Baseline

- Revision before implementation: `06724be021a81a08ff87f2338e00a4a37c888fb9`.
- Supported processor IDs: `BambuStudio`, `OrcaSlicer`, `CrealityPrint`, `ElegooSlicer`, `PrusaSlicer`, `SnapmakerOrcaSlicer`.
- Baseline command: `PYTHONPATH=src; python -m unittest discover -s tests -p 'test*.py'`.
- Baseline result: 240 tests, 6 failures, 8 errors, 2 skips. Existing failures are important-parameter classification and Prusa consistency assertions; errors depend on missing `downloads/3mf-fixture` files.

The current revision and P10-B1 Skill were inspected before implementation. No parameter catalogs, comparison algorithms, Feishu fields, publication schemas, or 3MF parsers were changed.

## Root cause and design

Native processors are composed by `slicers/registry.py`, while consistency validators are dispatched by `services/consistency_preview.py`. Previously, a processor could exist without a validator and `build_consistency_report()` returned an empty string for both unknown slicers and that partial-registration condition.

The minimal design is:

- `slicers/capabilities.py` contains the explicit `SUPPORTED`/`UNSUPPORTED` capability declaration and `check_registration_completeness()`.
- `SlicerProcessorRegistry.registered_ids` exposes deterministic processor IDs for inspection without exposing mutable internals.
- Alias canonicalization now lives in `slicers/contracts.py:canonical_slicer_id()` and is reused by the registry, consistency dispatch, and checker.
- `services/consistency_preview.py` checks capability at the dispatch boundary before looking for attachments or running a validator.

This is a guard, not a plugin framework or a new runtime feature matrix.

## Checker API and diagnostics

```python
check_registration_completeness(
    processor_registry,
    validators,
    capabilities,
) -> tuple[RegistrationIssue, ...]
```

`RegistrationIssue` contains `code`, canonical `slicer_id`, and deterministic `message`. Diagnostics include:

- `MISSING_CAPABILITY_DECLARATION`
- `MISSING_EXPECTED_VALIDATOR`
- `ORPHAN_VALIDATOR`
- `UNEXPECTED_VALIDATOR`
- `UNKNOWN_CAPABILITY_DECLARATION`
- `INVALID_CAPABILITY_DECLARATION`
- duplicate capability declarations where the input representation exposes them

The default production declaration marks the six current slicers `SUPPORTED`. The checker does not assume a fixed slicer count.

## Runtime behavior

- Unknown slicer: existing behavior remains an empty consistency result.
- Registered `UNSUPPORTED` capability: returns the existing envelope shape with outer status `UNSUPPORTED` and error code `CONSISTENCY_UNSUPPORTED`; Native Preset processing is unaffected.
- Registered `SUPPORTED` capability with missing validator: returns an `ERROR` envelope with `CONSISTENCY_VALIDATOR_NOT_REGISTERED` and the canonical slicer ID. It is checked before 3MF attachment handling, so it is not confused with missing 3MF.
- Registered supported validator: existing validation, error sanitization, report schema, and comparison statuses are unchanged.
- Missing 3MF for a registered validator: existing empty behavior remains unchanged.

No startup validation was added; the focused checker is exercised by tests and dispatch protection is localized to consistency reporting.

## Files changed

- `src/preset_worker/slicers/capabilities.py` — capability declarations, issue type, checker.
- `src/preset_worker/slicers/contracts.py` — shared alias canonicalization and registry ID view.
- `src/preset_worker/slicers/registry.py` — reuse shared canonicalization.
- `src/preset_worker/slicers/__init__.py` — exports guard API.
- `src/preset_worker/services/consistency_preview.py` — dispatch enforcement.
- `tests/test_registration_completeness.py` — synthetic and default-composition checker tests.
- `tests/test_p9_b3_a.py` — unsupported capability and missing-validator dispatch tests.
- `.agents/skills/slicer-onboarding/SKILL.md` and relevant references/checklist — capability/checker onboarding guidance.

## Tests and comparison

Focused command:

```text
PYTHONPATH=src; python -m unittest tests.test_registration_completeness tests.test_p9_b3_a tests.test_snapmaker_orca -v
```

Result: 31 tests passed.

Additional verification:

- `PYTHONPATH=src; python -m compileall -q src tests` — passed.
- Full unittest suite after implementation: 250 tests, 6 failures, 8 errors, 2 skips.
- Compared with baseline: +10 tests, with the same 6 failures, 8 errors, and 2 skips. No new failure or error was observed.

The full-suite errors remain environment/fixture-dependent because `downloads/3mf-fixture/PPS100CF10 H2D (1).json/.3mf` is absent. Existing classification and Prusa consistency failures remain pre-existing. No unrelated test was weakened.

## Compatibility and limitations

The consistency envelope gains an explicit outer `UNSUPPORTED` status for a declared Native-only slicer, while comparison schema `p9b2.consistency.v1` and comparison status meanings remain unchanged. Existing aliases, Preview/Submit paths, Native Preset processing, and publication code remain compatible.

The capability declaration is currently maintained beside the guard and must be updated when a processor is added. The checker is not automatically invoked at process startup; omission is detected by focused tests and a supported-missing-validator dispatch error. A future phase may consider startup enforcement if deployment semantics justify it.

## Recommended P10-B2.2

Add a formal capability/registration acceptance command or CI check without expanding runtime behavior. Keep parameter catalog consolidation and comparison coverage changes separate from this registration guard.
