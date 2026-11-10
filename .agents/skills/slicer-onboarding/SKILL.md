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
6. In IMPLEMENTATION, change only the missing processor/adapter, capability registration, fixtures, and targeted tests. Do not refactor shared catalogs or runtime behavior.
7. In VERIFICATION, run `python -m unittest tests.test_registration_completeness tests.test_p9_b3_a` (with `PYTHONPATH=src` when needed), then registration checks, parameter coverage checks, cross-slicer regressions, Preview/Submit integration, and publication only when claimed.
8. Complete `templates/onboarding-report.md` and `templates/compatibility-matrix.md` with `CONFIRMED`, `INFERRED`, or `NOT_VERIFIED` evidence labels.

## Non-negotiable guardrails

Do not guess parameter semantics, assume JSON slicers are Orca-compatible, assume 3MF structures are equivalent, select a slot without evidence, flatten arrays without confirmed indexing, treat missing or unsupported values as matches, claim inherited values are resolved when they are only preserved, claim complete consistency from a few comparisons, change unrelated slicers to pass tests, alter shared comparison contracts silently, or claim runtime-effective values without evidence.

Use bounded ZIP inspection and treat fixtures as untrusted. Do not execute embedded content, extract archives to arbitrary paths, modify originals, or commit proprietary fixtures without authorization.

## Required declarations

Every onboarding attempt must declare: Native Preset, Validation, Diff (Supported/Unsupported); 3MF Extraction and Consistency (Supported/Partial/Unsupported); Inheritance Resolution (Supported/Preserve Only/Unsupported); Multi-filament and Multi-plate (Supported/Partial/Unsupported); Publication (Verified/Not Verified). Each declaration needs evidence, fixtures, tests, and limitations. Never infer Supported from a parser that merely does not raise.

Read the references as needed:

- [architecture.md](references/architecture.md) for current modules and lifecycle boundaries.
- [contracts.md](references/contracts.md) for artifact, diff, validation, 3MF, consistency, and status contracts.
- [fixture-guide.md](references/fixture-guide.md) for intake, characterization, safety, and semantic checkpoints.
- [acceptance-checklist.md](references/acceptance-checklist.md) before claiming completion.

Use the templates for reports; do not create a new report schema. Stop before implementation or acceptance when the conditions in the acceptance checklist are unmet.
