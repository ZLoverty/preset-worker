---
name: slicer-onboarding
description: Onboard or assess a new 3D-printing slicer in preset-worker using Native Preset and 3MF fixtures; use for processor reuse, parsing, validation, diff, extraction, consistency, registration, tests, and acceptance—not unrelated Worker changes.
metadata:
  short-description: Fixture-driven slicer onboarding
---

# Slicer onboarding

Use this skill when adding or assessing slicer support in `preset-worker`. It is fixture-driven and must distinguish proven behavior from inference. It does not apply to unrelated Worker changes.

## Inputs

For full onboarding, require the slicer name, version, repository, and at least one real Native Preset. Claim 3MF support only with a real 3MF, its relationship to the Native Preset, and expected values or an explicit characterization step. Parent presets, multi-filament/plate fixtures, printer/material identity, aliases, Feishu labels, and version metadata are conditional inputs.

## Modes

- **DISCOVERY** (default): inspect current code and fixtures, produce an assessment and plan, and make no production changes.
- **IMPLEMENTATION**: after semantic questions are resolved and the user authorizes implementation, add only approved adapters, registrations, fixtures, and tests.
- **VERIFICATION**: run acceptance and regression checks, then produce capability and compatibility reports.

Always complete discovery and semantic verification before implementation. A blocked capability may remain partial while independent capabilities proceed.

## Workflow

1. Read the current repository and the relevant P10-A reports; prefer current code when they differ.
2. Record revision, test environment, processor registry, aliases, consistency dispatch, contracts, lifecycle services, fixtures, and baseline failures.
3. Characterize supplied files without modifying originals: format, encoding, ZIP entries, keys, identities, inheritance, arrays, slots, plates, objects, and version metadata.
4. Identify reusable format-family components and build a capability-gap assessment.
5. Propose native and 3MF mappings with source paths and evidence; ask only unresolved semantic questions.
6. In IMPLEMENTATION, change only the missing processor/adapter, capability registration, fixtures, and targeted tests. Shared Native Diff catalogs may be changed only when the task explicitly requires catalog consolidation; preserve the diff contract and do not change 3MF runtime behavior as a side effect.
7. For Native Diff classification, use `src/preset_worker/slicers/parameter_catalog.py` as the canonical Important Parameter Catalog. Add aliases and slicer-specific native paths there, keep system metadata precedence explicit, and verify exact/indexed paths. Do not treat catalog membership as proof of 3MF comparability.
8. In VERIFICATION, run `python -m unittest tests.test_registration_completeness tests.test_p9_b3_a tests.test_parameter_catalog` (with `PYTHONPATH=src` when needed), then registration checks, parameter coverage checks, cross-slicer regressions, Preview/Submit integration, and publication only when claimed.
9. For consistency audits, trace Native parsing/extraction, identity and slot selection, 3MF extraction, normalization, comparison, row generation, and Preview/Submit propagation. Test missing, invalid, ambiguous, unresolved, equal, and unequal operands; add a real-fixture comparison and negative mismatch test whenever committed evidence permits.
10. Complete `templates/onboarding-report.md` and `templates/compatibility-matrix.md` with `CONFIRMED`, `INFERRED`, or `NOT_VERIFIED` evidence labels.

## Non-negotiable guardrails

Do not guess parameter semantics, assume JSON slicers are Orca-compatible, assume 3MF structures are equivalent, select a slot without evidence, flatten arrays without confirmed indexing, treat missing or unsupported values as matches, claim inherited values are resolved when they are only preserved, claim complete consistency from a few comparisons, change unrelated slicers to pass tests, alter shared comparison contracts silently, or claim runtime-effective values without evidence.

Use bounded ZIP inspection and treat fixtures as untrusted. Do not execute embedded content, extract archives to arbitrary paths, modify originals, or commit proprietary fixtures without authorization.

## Required declarations

Every onboarding attempt must declare: Native Preset, Validation, Diff (Supported/Unsupported); 3MF Extraction and Consistency (Supported/Partial/Unsupported); Inheritance Resolution (Supported/Preserve Only/Unsupported); Multi-filament and Multi-plate (Supported/Partial/Unsupported); Publication (Verified/Not Verified). Each declaration needs evidence, fixtures, tests, and limitations. Never infer Supported from a parser that merely does not raise.

Consistency diagnostics must keep three layers separate: coverage (`TARGET_NOT_DECLARED`, `MAPPING_NOT_IMPLEMENTED`, `MAPPING_DECLARED`, or `MAPPING_UNKNOWN`), runtime resolution (identity, slot, source-value, and normalization outcomes), and public comparison status. Do not add comparison statuses for internal causes. A missing or unresolved operand must never be emitted as `MATCH`; use existing status semantics and the optional parameter-level diagnostic fields already present in the report contract.

Read the references as needed:

- [architecture.md](references/architecture.md) for current modules and lifecycle boundaries.
- [contracts.md](references/contracts.md) for artifact, diff, validation, 3MF, consistency, and status contracts.
- [fixture-guide.md](references/fixture-guide.md) for intake, characterization, safety, and semantic checkpoints.
- [acceptance-checklist.md](references/acceptance-checklist.md) before claiming completion.

Use the templates for reports; do not create a new report schema. Stop before implementation or acceptance when the conditions in the acceptance checklist are unmet.

## Important Parameter Catalog

The catalog is the source of truth for Native Preset Diff `IMPORTANT_PARAMETER`
classification across BambuStudio, OrcaSlicer, CrealityPrint, ElegooSlicer,
SnapmakerOrcaSlicer, and PrusaSlicer. Each definition records a canonical
parameter ID, slicer-specific native paths, optional consistency target names,
and semantic notes. Processors must derive their local important-path sets from
this catalog; compatibility-facing processor attributes may remain available.

Use `classify_native_path()` for classification. It supports exact paths and
numeric array suffixes such as `field[0]`, while malformed or non-numeric
suffixes remain `OTHER_PARAMETER`. System metadata is checked before important
parameters. Unknown paths remain `OTHER_PARAMETER`.

Use `build_coverage_inventory()` only as a read-only static inventory. Its
coverage values mean:

- `Covered`: the catalog definition names a supplied consistency target;
- `Not covered`: no supplied target is named;
- `Unknown`: no consistency target catalog was supplied.

These labels do not prove extraction, identity/slot resolution, mapping,
normalization, or end-to-end comparison. In particular, an Important Native
Diff parameter is not automatically a 3MF comparable parameter. Every report
must disclose uncovered and uncertain mappings and keep 3MF runtime target
sets/statuses unchanged unless separately authorized.

For consistency coverage evidence, distinguish `STATIC_TARGET_ONLY`,
`MAPPING_VERIFIED`, `RESOLUTION_VERIFIED`, `COMPARISON_VERIFIED`,
`UNVERIFIED`, and `NOT_TARGETED`. These are audit evidence levels, not runtime
comparison statuses. If a fixture cannot establish identity or slot selection,
preserve `UNRESOLVED` and document the fixture limitation rather than weakening
selection requirements.
