# P9-B2 — Bambu Studio Preset–3MF Consistency Validator

## 1. Objective

Implement a standalone, evidence-driven consistency validator that compares a Bambu Studio Filament Preset JSON artifact against the corresponding filament configuration stored in a Bambu Studio 3MF project.

Build on the P9-B1.1 parser and resolver.

The validator must:

1. Parse the submitted Bambu Studio Filament Preset JSON.
2. Parse the submitted Bambu Studio 3MF.
3. Identify the appropriate project filament slot.
4. Resolve the eight required parameters on both sides.
5. Normalize values using parameter-specific rules.
6. Produce reliable MATCH or MISMATCH results only when comparison is justified.
7. Represent missing, unresolved, ambiguous, and unsupported cases explicitly.
8. Generate a versioned, serializable consistency report.
9. Provide a standalone diagnostic CLI.
10. Include automated tests and real-fixture verification.

**Correctness is more important than comparison coverage.**

Do not infer an effective value merely because a parameter with the same name exists in both artifacts.

## 2. Existing Architecture

The existing repository contains:

- `BambuStudioProcessor`
- `Artifact` abstraction
- `UnifiedDiff`
- P9-B1.1 Bambu Studio 3MF parser
- `parse_bambu_3mf()`
- `resolve_bambu_project()`
- Structured 3MF snapshots
- Provenance-bearing parameter models
- Safe ZIP reader
- Diagnostic CLI

Inspect the actual implementations and interfaces before making changes.

Reuse the existing BambuStudioProcessor for submitted JSON parsing and canonicalization where appropriate.

Do not duplicate slicer-specific canonicalization rules.

Do not modify the behavior of existing preset normalization or UnifiedDiff.

## 3. Scope

### In Scope

- Bambu Studio only.
- Submitted Filament Preset JSON versus 3MF project configuration.
- Eight specified parameters.
- Filament-slot matching.
- Parameter normalization.
- Comparison semantics.
- Structured reporting.
- Standalone CLI.
- Unit and integration tests.
- Documentation.

### Out of Scope

- Worker lifecycle integration.
- Feishu API calls.
- Feishu schema changes.
- Miaoda frontend changes.
- Blocking submissions or approvals.
- Automatic modification of JSON or 3MF.
- Complete Bambu Studio inheritance engine.
- Complete slicing engine emulation.
- Supporting other slicers.

Keep P9-B2 independent of production workflow state.

## 4. Required Parameters

Implement comparison support for exactly these eight parameters:

| Parameter ID | Meaning | Unit |
|---|---|---|
| `filament_flow_ratio` | Filament Flow Ratio | Dimensionless |
| `filament_max_volumetric_speed` | Maximum Volumetric Speed | mm³/s |
| `nozzle_temperature` | Nozzle Temperature | °C |
| `nozzle_temperature_initial_layer` | Initial Layer Nozzle Temperature | °C |
| `fan_min_speed` | Minimum Part-Cooling Fan Speed | % |
| `fan_max_speed` | Maximum Part-Cooling Fan Speed | % |
| `fan_cooling_layer_time` | Upper Cooling Layer-Time Threshold | s |
| `slow_down_layer_time` | Lower Cooling Layer-Time Threshold | s |

The two cooling layer-time parameters must remain independent.

Do not collapse them into one threshold.

Do not compare Pressure Advance, retraction, bed temperature, auxiliary fan, or process parameters in this phase.

## 5. First Acceptance Gate — Test Infrastructure

Before implementing comparison logic:

1. Inspect the repository's existing test configuration.
2. Ensure pytest can be installed using the project's supported development dependency mechanism.
3. Run `tests/test_three_mf.py`.
4. Run the relevant existing Worker tests.
5. Record the baseline test results.
6. Fix P9-B1.1 defects that directly prevent reliable comparison.

Do not silently skip tests because pytest is unavailable.

If dependency installation is impossible, document the blocker and do not claim the implementation is fully verified.

Do not change unrelated production behavior merely to make tests pass.

## 6. Preset JSON Preparation

Use the existing BambuStudioProcessor to parse the submitted native Preset JSON.

Where applicable, apply the existing canonicalization process.

The validator should compare against the same canonical parameter values that would be eligible for publication.

Preserve:

- Original JSON artifact SHA-256.
- Canonical JSON SHA-256, if canonicalization is applied.
- Original parameter values.
- Parameter JSON paths.
- Canonicalization policy version, if available.
- Preset identity metadata.
- Inheritance references.

Important:

Canonical JSON is not necessarily an effective, fully expanded preset.

Do not assume that omitted parameters can be reconstructed from the canonical JSON.

Do not silently load defaults from the validator's environment.

Do not invent missing parent preset values.

If