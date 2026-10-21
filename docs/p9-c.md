# P9-C — Multi-Slicer 3MF Compatibility Investigation

## Background

The Preset Management System currently supports multiple slicer-specific Preset processors:

- BambuStudio
- OrcaSlicer
- OrcaSlicer (Snapmaker)
- CrealityPrint
- ElegooSlicer
- PrusaSlicer

P9-B implemented a non-blocking consistency check between an uploaded Preset file and an uploaded 3MF project for BambuStudio.

The existing validator compares eight filament-related parameters and produces a `p9b2.consistency.v1` report, which is stored in the Feishu Submission field `consistency_report` and displayed by the Miaoda frontend.

**P9-C is an investigation phase, not an implementation phase.**

Its purpose is to determine how this functionality can be extended to the other supported slicers with minimal duplication and without compromising comparison correctness.

## Objectives

Investigate the actual implementation and available project-file fixtures to answer:

1. Which slicers produce 3MF projects containing usable filament configuration data?
2. Which slicers share compatible 3MF archive structures and parameter representations?
3. Which parts of the existing BambuStudio validator can be reused?
4. How can the uploaded Preset be reliably associated with the correct filament slot in the project?
5. Which parameters can be compared reliably, and which require slicer-specific mapping or normalization?
6. What is the smallest maintainable implementation plan for the remaining P9 work?

Do not assume compatibility solely because slicers share ancestry or use the `.3mf` extension.

---

## C1 — Audit the Existing P9 Implementation

Inspect the repository and identify:

- The BambuStudio 3MF parser.
- The P9-B2 consistency validator.
- The eight parameter definitions.
- The parameter normalization and comparison logic.
- The filament-slot selection logic.
- The existing `selection.status` and `runtime_effective_status` semantics.
- The Preview integration and slicer dispatch logic.
- Existing tests and 3MF fixtures.

Document the relevant source files, classes, functions, and dependencies.

Determine whether the current implementation separates:

1. 3MF archive reading.
2. Slicer-specific configuration extraction.
3. Preset parsing.
4. Filament identity and slot matching.
5. Parameter normalization.
6. Value comparison.
7. Report generation.

Identify tightly coupled components that could prevent reuse.

Do not refactor them in P9-C.

## C2 — Inventory Available Test Fixtures

Search the repository and existing test resources for real exported 3MF projects and corresponding Preset files.

For each slicer, record:

- Slicer name and version.
- Printer model, when known.
- Project file type and export method.
- Corresponding Preset file format.
- Whether the project contains one or multiple filament slots.
- Whether the fixture was produced by the slicer itself.
- Whether the source files are available for reproducible testing.

Distinguish these cases where relevant:

- Save Project / Save Project As.
- Export 3MF.
- Published or shareable 3MF.
- Sliced or print-ready 3MF.
- Geometry-only 3MF.

Do not assume these modes embed identical settings.

If a fixture is missing, mark it as `NOT_TESTED`.

Do not fabricate fixtures or claim compatibility without evidence.

Synthetic fixtures may be used for parser unit tests, but must not count as proof of slicer compatibility.

## C3 — Inspect 3MF Archive Structures

For each available real 3MF fixture:

1. Open the file as a ZIP archive.
2. List its members.
3. Identify configuration-bearing files.
4. Determine whether those files contain JSON, INI, XML, or another representation.
5. Identify where filament parameters are stored.
6. Identify where filament identity and slot assignments are stored.
7. Check whether parameter values are explicit, inherited, resolved, or overridden.

Investigate likely paths such as:

- `Metadata/project_settings.config`
- `Metadata/filament_settings_*.config`
- `Metadata/model_settings.config`
- `Metadata/slice_info.config`
- `Metadata/Slic3r_PE.config`

These paths are investigation candidates, not guaranteed requirements.

For each slicer, document the actual paths observed.

Pay special attention to PrusaSlicer, whose Preset format is INI-based, and to OrcaSlicer variants that may support different project-export modes.

Do not parse embedded G-code unless it is demonstrably necessary for the eight target parameters.

Do not confuse model metadata with effective filament configuration.

## C4 — Parameter Compatibility Matrix

Use the existing P9-B2 parameter set as the initial scope:

1. `filament_flow_ratio`
2. `filament_max_volumetric_speed`
3. `nozzle_temperature`
4. `nozzle_temperature_initial_layer`
5. `fan_min_speed`
6. `fan_max_speed`
7. `fan_cooling_layer_time`
8. `slow_down_layer_time`

For each slicer and parameter, determine:

- Preset-side parameter name.
- 3MF-side parameter name.
- Source file and configuration path.
- Data type.
- Unit, if applicable.
- Scalar or array representation.
- Whether it is filament-specific.
- Whether the value is directly stored or must be resolved.
- Whether a deterministic normalization is possible.
- Confidence level based on actual evidence.

Use these classifications:

- `DIRECT`: same semantics, directly comparable.
- `MAPPED`: different key or representation, deterministic mapping.
- `CONDITIONAL`: comparable only under documented conditions.
- `UNRESOLVED`: source or semantics not established.
- `UNSUPPORTED`: demonstrated incompatibility.

Do not classify missing evidence as unsupported.

Do not assume parameters with similar names have identical semantics.

Do not silently convert values when units or meaning are uncertain.

## C5 — Filament Identity and Slot Matching

Investigate how each slicer represents:

- Filament preset name.
- Filament preset identifier.
- Printer compatibility.
- Filament slot index.
- Filament assignment to objects or plates.
- Multiple materials or extruders.
- Project-local or embedded presets.

Compare these identities against the uploaded Preset.

Determine whether the existing BambuStudio slot-selection logic can be reused.

A project containing one filament slot does not automatically prove that the slot corresponds to the uploaded Preset.

Preserve the distinction between:

- Stored parameter equality.
- Filament identity matching.
- Runtime-effective configuration equivalence.

If slot identity cannot be established, the proposed implementation must retain an explicit unresolved status rather than claiming verified runtime equivalence.

Document how zero-based and one-based slot indices are represented.

## C6 — Compatibility Experiments

Where real fixture pairs are available, run the existing BambuStudio extraction and comparison components against other slicers in an isolated test harness.

Do not route unsupported slicers through the production Preview path.

Record:

- Whether the 3MF archive can be read.
- Whether configuration data can be extracted.
- Whether the eight parameters can be found.
- Whether normalization succeeds.
- Whether filament identity can be resolved.
- Whether comparison results agree with manually inspected source values.
- Any errors, unsupported fields, or ambiguous results.

Do not interpret successful JSON parsing as full compatibility.

For each tested slicer, classify reuse potential as:

- `REUSE_AS_IS`
- `REUSE_WITH_ADAPTER`
- `SEPARATE_PARSER_REQUIRED`
- `INSUFFICIENT_EVIDENCE`

If feasible, test at least one intentionally mismatched parameter for each supported fixture pair.

## C7 — Proposed Architecture

Based on the findings, recommend the smallest architecture that supports additional slicers.

Prefer reusing the existing P9-B2 comparison engine and report semantics.

Introduce slicer-specific extraction or mapping only when required by demonstrated differences.

Consider an interface conceptually equivalent to:

```python
extract_project_filament_config(
    project_bytes: bytes,
    slicer: str,
) -> ProjectFilamentConfig
```

This is an illustrative interface, not a required API.

Do not implement it during P9-C.

Avoid unnecessary abstraction layers, generic plugin frameworks, or speculative future slicer support.

Identify which existing code can remain unchanged and which components need targeted extension.

Evaluate whether the current report schema can represent all supported slicers without losing important identity or provenance information.

Prefer preserving `p9b2.consistency.v1` when its semantics remain valid. If a schema change is genuinely required, explain the specific incompatibility and propose a migration strategy.

## C8 — Recommended Implementation Order

Recommend a slicer-by-slicer implementation sequence based on:

1. Proven format compatibility.
2. Availability of real test fixtures.
3. Reuse of existing BambuStudio code.
4. Complexity of parameter mapping.
5. Complexity of filament identity resolution.
6. Risk of producing misleading MATCH results.

Evaluate OrcaSlicer and OrcaSlicer (Snapmaker) separately.

Do not automatically classify Snapmaker as compatible with standard OrcaSlicer.

Evaluate CrealityPrint, ElegooSlicer, and PrusaSlicer independently.

Where evidence is insufficient, recommend the smallest additional fixture or experiment needed.

---

## Required Deliverables

Produce the following documentation in the repository's existing documentation structure.

### 1. P9-C Investigation Report

`p9-c-investigation.md`

Include:

- Existing implementation audit.
- Observed 3MF structures.
- Findings by slicer.
- Reusable components.
- Known incompatibilities.
- Open questions.
- Evidence and fixture references.

### 2. Slicer Compatibility Matrix

`p9-c-compatibility-matrix.md`

Include a slicer-level overview and an eight-parameter comparison matrix.

Clearly distinguish verified facts, hypotheses, and untested cases.

### 3. Proposed Implementation Plan

`p9-d-implementation-plan.md`

Include:

- Recommended slicer implementation order.
- Proposed minimal code changes.
- Reusable components.
- Required slicer-specific adapters.
- Required tests and fixtures.
- Acceptance criteria for each slicer.
- Explicitly deferred functionality.

### 4. Optional Read-Only Inspection Script

If useful, add a small script to inspect 3MF ZIP members and configuration structure.

The script must:

- Be read-only.
- Avoid extracting unnecessary large files.
- Handle malformed ZIP archives safely.
- Avoid logging full machine G-code or sensitive project content.
- Produce deterministic summaries.

Do not build a general-purpose 3MF framework.

---

## Constraints

- Do not modify the production Worker Preview workflow.
- Do not change existing BambuStudio validation behavior.
- Do not change Feishu fields.
- Do not change Miaoda.
- Do not add new production slicer dispatch branches.
- Do not implement new validators in this phase.
- Do not change approval or publication conditions.
- Do not add new runtime dependencies unless strictly necessary for investigation.
- Do not introduce caching or unrelated performance optimizations.
- Keep the existing non-blocking consistency-check principle.

## Acceptance Criteria

P9-C is complete when:

1. The actual BambuStudio P9 implementation has been audited.
2. All five remaining slicer variants have an explicit investigation status.
3. Available real 3MF fixtures have been inspected.
4. All eight parameters have documented compatibility findings for each slicer, including unknowns.
5. Filament identity and slot-matching limitations are documented.
6. Reuse potential is supported by evidence.
7. A minimal P9-D implementation sequence is proposed.
8. No existing Preview or publication behavior has changed.

## Final Agent Response

Summarize:

- Files inspected.
- Tests and experiments performed.
- Compatibility findings for each slicer.
- Missing fixtures or unresolved questions.
- Proposed P9-D implementation order.
- Documentation files created.

Do not begin P9-D implementation without approval.