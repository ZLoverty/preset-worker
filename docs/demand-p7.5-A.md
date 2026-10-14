# P7.5-A — ElegooSlicer Real Artifact Reconnaissance

## 0. Goal

Investigate the real filament/material preset artifact produced by the ElegooSlicer version used in the engineering workflow before implementing `ElegooSlicerProcessor`.

This phase must establish, from real artifacts and GUI behavior:

```text
artifact format
import/export unit
visible-name semantics
preset identity semantics
inheritance semantics
custom metadata behavior
round-trip behavior
Artifact-contract compatibility
```

Do NOT implement or register `ElegooSlicerProcessor` during P7.5-A.

Final outcome must be one of:

```text
READY_FOR_PROCESSOR
ARCHITECTURE_CHANGE_REQUIRED
INSUFFICIENT_EVIDENCE
```

---

# 1. Existing Architecture Is the Baseline

Current supported processors:

```text
BambuStudioProcessor
OrcaSlicerProcessor
CrealityPrintProcessor
```

Current generic boundary:

```python
Artifact(
    content: bytes,
    filename: str,
    media_type: str | None,
)
```

and:

```text
SlicerProcessor
UnifiedDiff
generic enrichment/publication/version workflow
```

P7.5-A must test ElegooSlicer against this architecture.

Do not redesign the architecture merely because ElegooSlicer resembles or differs from an existing slicer.

---

# 2. Core Principle

Treat ElegooSlicer as an independent slicer.

Do NOT assume behavior from:

```text
BambuStudio
OrcaSlicer
CrealityPrint
PrusaSlicer
```

even if:

```text
file structure looks similar
field names are identical
the slicers share ancestry
the profile appears Orca/Prusa-derived
```

Format similarity is evidence for code-sharing opportunities later, not evidence of identical semantics.

---

# 3. Required Human Input

Request one real custom filament/material preset exported from the ElegooSlicer installation actually used in the workflow.

The human should provide:

```text
1. exact ElegooSlicer version
2. original exported preset artifact
```

Prefer a simple custom filament preset derived from a normal built-in/base preset.

The human must NOT manually edit the artifact.

---

# 4. Required Stop Point When Artifact Is Missing

If no real ElegooSlicer export is available, STOP and request:

> Please provide one real custom filament/material preset exported from the ElegooSlicer version used in your workflow, together with the exact ElegooSlicer version.

Do not create a synthetic substitute.

Do not implement the processor.

---

# 5. Preserve Original Artifact

Once supplied, preserve the artifact unchanged.

Use an appropriate location such as:

```text
tests/fixtures/slicers/elegoo_slicer/reconnaissance/
    source_original.<extension>
```

Record:

```text
ElegooSlicer version
original filename
extension
file size
SHA-256
```

Never modify the original in place.

---

# 6. Detect the Real Artifact Format

Inspect actual bytes rather than trusting the extension.

Determine whether the import/export unit is:

```text
plain JSON
other structured text
ZIP/archive
3MF-derived archive
binary
multiple external files
other
```

If an archive is used, inspect its member structure.

Do not confuse:

```text
one archive containing many files
```

with:

```text
multiple external Artifacts
```

One archive can still be one opaque `Artifact`.

---

# 7. Determine the Actual Import Unit

Establish what ElegooSlicer expects the user to import:

```text
single preset file
archive
configuration bundle
project
directory/package
other
```

The future Worker canonical artifact should normally correspond to this real import unit.

---

# 8. Structural Analysis

Analyze the source artifact sufficiently to identify:

```text
preset/material type
visible-name candidate fields
internal identity candidate fields
inheritance/parent fields
vendor fields
printer compatibility
material type
version metadata
UUID/ID fields
unknown/custom metadata capability
material/printing parameters
```

Do not assign semantics solely from field names.

Mark uncertain fields as candidates.

---

# 9. Compare With Existing Slicers

After inspecting the artifact, compare its structure with:

```text
OrcaSlicer
CrealityPrint
BambuStudio
```

Report:

```text
shared fields
different fields
different types
different container structure
different identity candidates
different inheritance representation
```

This comparison is descriptive only.

Do not use it to skip GUI validation.

---

# 10. Generate Analysis Report

Create:

```text
elegoo_artifact_analysis.md
```

including:

```text
tested version
artifact provenance
container format
import unit
structural summary
identity candidates
inheritance candidates
custom metadata capability
comparison with existing slicers
initial Artifact-contract assessment
```

---

# 11. Baseline Variant

Generate:

```text
00_baseline.<actual extension>
```

semantically identical to the original.

The human must import this first.

Record:

```text
import succeeds?
visible name?
new preset?
existing preset overwritten?
duplicate/conflict warning?
other behavior?
```

If baseline fails, STOP.

Do not interpret later experiments until baseline import is understood.

---

# 12. Dynamic Experiment Generation

After inspecting the real artifact, the Agent must generate a **minimal evidence-driven experiment matrix**.

Do NOT blindly reuse Orca or Creality field names.

Experiments must be based on fields actually present in the real Elegoo artifact.

Target approximately:

```text
3–6 variants
```

unless the artifact genuinely requires more.

Avoid combinatorial testing.

---

# 13. Name-Only Experiment

If a plausible visible-name field exists, create a variant modifying only that field.

Use an unmistakable name such as:

```text
P7ES_NAME_ONLY
```

Question:

> Is this field alone sufficient to control the visible name and create a distinct preset?

No other semantic field may change.

---

# 14. Identity Experiments

Identify the strongest plausible internal identity fields.

For each useful candidate, generate a controlled experiment such as:

```text
name + identity candidate A
name + identity candidate B
```

Only include candidates supported by the actual artifact.

Questions include:

```text
Does the field survive import/re-export?
Does changing it affect new-vs-overwrite behavior?
Does it affect visible name?
Does ElegooSlicer regenerate it?
```

---

# 15. Inheritance Experiment

If the source contains inheritance/parent semantics, generate a variant that:

```text
changes only the intended visible identity
preserves inheritance exactly
```

Determine whether the renamed custom preset can continue inheriting from the same base.

Do NOT initially invent a broken/nonexistent parent.

---

# 16. Do Not Mutate Native Base IDs Without Purpose

If fields resembling:

```text
base_id
parent_id
setting_id
filament_id
filament_settings_id
uuid
```

exist, do not automatically rewrite all of them.

Test only the strongest candidates needed to understand identity behavior.

The goal is eventually to discover the **minimum necessary Worker mutation set**.

---

# 17. Custom Metadata Experiment

If the artifact format safely permits unknown/custom fields, generate a controlled variant containing:

```text
pm_method_version = "P7ES_TEST"
```

or the structurally appropriate equivalent.

Test:

```text
import acceptance
re-export preservation
removal
rewriting
```

Do not force the field into a format that clearly does not support arbitrary metadata.

---

# 18. Existing `pm_method_version` Rule

Remember that application semantics are:

```text
Submission.pm_method_version
    = authoritative
```

The future Worker can re-inject it during canonicalization.

Therefore:

```text
ElegooSlicer removes it on re-export
```

does NOT automatically make Elegoo unsupported.

Record the behavior objectively.

---

# 19. Generate Experiment Manifest

Create:

```text
experiment_manifest.md
```

For each variant record:

```text
filename
source SHA-256
variant SHA-256
fields/components intentionally changed
old value
new value
question being tested
```

For archives, identify modified member paths.

---

# 20. Generate GUI Test Sheet

Create:

```text
GUI_TEST_RESULTS.md
```

using:

| Variant | Import succeeds? | Visible preset name | Created new preset? | Overwrote/replaced existing preset? | Duplicate/conflict warning? | Other visible behavior | Re-exported filename |
|---|---|---|---|---|---|---|---|

Pre-fill only the variant names.

---

# 21. Stop for Human GUI Validation

After generating:

```text
artifact analysis
baseline
experiment variants
experiment manifest
GUI test sheet
```

STOP.

Do not guess GUI results.

Ask the human to:

```text
1. test baseline first
2. import each variant
3. record observable behavior
4. re-export selected successful variants
```

---

# 22. Avoid Cross-Test Contamination

Because identity experiments may overwrite each other, use unique names/IDs where appropriate.

The human should record whether a variant:

```text
creates
duplicates
merges
overwrites
```

an existing preset.

Overwrite behavior is important evidence.

---

# 23. Round-Trip Inputs

After GUI testing, request re-exported artifacts for the most informative successful cases.

Prefer:

```text
baseline
name-only
important identity-field variant(s)
inheritance-preserved variant
pm_method_version/custom-metadata variant
```

Do not require redundant re-exports if two experiments clearly test the same behavior.

---

# 24. Automated Round-Trip Analysis

Compare:

```text
experiment input
vs
ElegooSlicer re-export
```

For structured artifacts, perform semantic comparison.

For archives, compare:

```text
members added
members removed
members changed
structured semantic changes
```

Distinguish:

```text
identity changes
slicer-generated metadata
material/printing parameter changes
formatting-only changes
unknown changes
```

---

# 25. Visible-Name Conclusion

Determine from actual GUI evidence:

```text
which field controls visible name
whether changing it alone is sufficient
whether another field must be synchronized
whether inheritance affects it
whether Elegoo rewrites it
```

---

# 26. Identity Conclusion

Determine sufficiently for Worker implementation:

```text
which fields influence new-vs-overwrite behavior
which IDs should be preserved
which IDs must change
which IDs are slicer-managed
which fields should never be synthesized by Worker
```

Do not claim more certainty than the experiments establish.

---

# 27. Inheritance Conclusion

If inheritance exists, determine:

```text
whether it survives import
whether it survives re-export
whether renamed custom preset can retain it
whether referenced base must exist locally
```

Default future design preference is preservation rather than flattening.

---

# 28. Parameter Preservation

Verify that successful identity experiments do not unexpectedly alter material/printing parameters.

Unexpected parameter rewriting must be explicitly reported.

Do not silently classify it as harmless.

---

# 29. `pm_method_version` Conclusion

Classify behavior as one of:

```text
PRESERVED
REMOVED_ON_REEXPORT
REWRITTEN
UNSUPPORTED
NOT_TESTED
```

If removed on re-export but accepted on import, explicitly note that Worker reinjection remains possible.

---

# 30. Artifact Contract Assessment

Explicitly answer:

> Can the complete ElegooSlicer preset import/export unit be represented losslessly enough by the current `Artifact(content, filename, media_type)` abstraction?

Classify:

```text
SUFFICIENT
INSUFFICIENT
UNCERTAIN
```

A single archive containing multiple internal members still counts as one Artifact.

---

# 31. Architecture Escalation Rule

Do NOT change `Artifact` during reconnaissance.

If the current abstraction is insufficient, document the exact concrete failure mode.

Examples:

```text
multiple separately named external files required
directory semantics required
external companion resource required
```

Then classify:

```text
ARCHITECTURE_CHANGE_REQUIRED
```

---

# 32. Proposed Canonicalization Rules

If evidence is sufficient, propose P7.5-B rules.

Prefer:

```text
preserve original artifact
        +
minimum company-required mutations
```

Expected company policy normally includes:

```text
canonical display name
pm_method_version
```

but do not assume the exact native field mapping before experiments establish it.

---

# 33. Minimum Mutation Principle

For every native Elegoo field, ask:

> Is changing this field required to produce the intended canonical preset?

If no evidence says yes:

```text
preserve it
```

Do not synchronize native IDs merely because they look related to `name`.

---

# 34. Proposed Source Validation

Based on the real artifact, define what P7.5-B should validate to distinguish:

```text
valid supported Elegoo filament/material preset
malformed artifact
unsupported Elegoo preset type
unrelated artifact
```

Unknown fields should normally be tolerated.

---

# 35. Proposed Diff Strategy

Determine whether P7.5-B can implement semantic diff using the existing:

```text
UnifiedDiff
DiffChange
ChangeType
DiffCategory
```

model.

Identify likely:

```text
SYSTEM_METADATA
IMPORTANT_PARAMETER
OTHER_PARAMETER
```

fields.

Unknown fields should eventually default to:

```text
OTHER_PARAMETER
```

rather than being dropped.

Do NOT implement production diff in P7.5-A.

---

# 36. No Generic Workflow Changes

P7.5-A must not modify:

```text
enrichment
publication
review
version allocation
preset_key semantics
Artifact contract
UnifiedDiff contract
```

If evidence suggests a required change, report it instead.

---

# 37. No Production Registration

Do NOT add:

```text
ElegooSlicer
```

to `default_processor_registry`.

Do not enable it in production UI.

That belongs to P7.5-B.

---

# 38. Fixture Hygiene

Before committing real-export-derived artifacts, inspect for:

```text
usernames
absolute paths
account information
tokens
network addresses
private machine identifiers
```

Sanitize where necessary.

Document every sanitization affecting fixture content.

Do not sanitize fields whose semantics are being tested without recording the change.

---

# 39. Reconnaissance Automation

It is acceptable and encouraged to create reusable tooling for:

```text
artifact inspection
variant generation
checksum generation
semantic round-trip comparison
```

But do not turn exploratory code into generic production abstraction prematurely.

---

# 40. Reuse Existing Reconnaissance Helpers Carefully

If P7.4-A produced useful experiment/round-trip helpers, reuse them when genuinely slicer-independent.

Do not copy Creality-specific field assumptions into Elegoo reconnaissance.

---

# 41. Evidence Hierarchy

Use this priority:

```text
1. real GUI import behavior
2. real GUI re-export artifact
3. original real exported artifact
4. official slicer documentation/source where useful
5. structural similarity with another slicer
```

Similarity alone must never override contradictory real behavior.

---

# 42. P7.5-B Readiness

At completion classify:

### READY_FOR_PROCESSOR

Use when:

```text
artifact format understood
baseline works
display-name semantics understood
identity behavior sufficiently understood
inheritance sufficiently understood where applicable
canonicalization rules can be specified
Artifact abstraction is sufficient
```

### ARCHITECTURE_CHANGE_REQUIRED

Use only when real Elegoo behavior cannot fit the current processor/artifact architecture.

### INSUFFICIENT_EVIDENCE

Use when important behavior remains unresolved.

---

# 43. Acceptance Criteria

P7.5-A is complete when:

```text
[ ] exact ElegooSlicer version recorded
[ ] real exported artifact preserved
[ ] checksum recorded
[ ] real container format identified
[ ] actual import unit identified
[ ] structural analysis completed
[ ] baseline import succeeds
[ ] minimal dynamic experiment matrix generated
[ ] GUI observations recorded
[ ] selected successful variants re-exported
[ ] round-trip analysis completed
[ ] visible-name semantics established
[ ] preset identity behavior sufficiently established
[ ] inheritance behavior established where applicable
[ ] pm_method_version behavior classified
[ ] material/printing parameter preservation checked
[ ] Artifact abstraction assessed
[ ] P7.5-B canonicalization rules proposed
[ ] P7.5-B validation rules proposed
[ ] P7.5-B diff approach proposed
[ ] no production processor added
[ ] readiness classification produced
```

---

# 44. Completion Report

Create:

```text
p7.5-A_completion_report.md
```

Report:

1. exact ElegooSlicer version;
2. source artifact provenance;
3. source filename, size and SHA-256;
4. actual artifact/container format;
5. import unit;
6. preset type;
7. important structural fields;
8. comparison with BambuStudio;
9. comparison with OrcaSlicer;
10. comparison with CrealityPrint;
11. visible-name candidate(s);
12. identity candidate(s);
13. inheritance representation;
14. baseline GUI result;
15. experiment matrix;
16. name-only result;
17. identity experiment results;
18. new/overwrite/duplicate behavior;
19. inheritance experiment result;
20. `pm_method_version` result;
21. re-export results;
22. all meaningful round-trip mutations;
23. material/printing parameter preservation result;
24. final visible-name semantics;
25. final preset identity semantics;
26. final inheritance semantics;
27. native fields that Worker should preserve;
28. native fields that Worker should modify;
29. native fields that Worker should never synthesize;
30. proposed P7.5-B canonicalization rules;
31. proposed source-validation rules;
32. proposed UnifiedDiff strategy;
33. Artifact abstraction assessment;
34. any generic architecture problem discovered;
35. fixture sanitization performed;
36. readiness classification.

---

# 45. End State

Do not finish P7.5-A by saying:

```text
ElegooSlicer is supported.
```

The correct outcome is reconnaissance readiness, for example:

```text
P7.5-A complete.

ElegooSlicer real-artifact behavior has been characterized.

Readiness:
READY_FOR_PROCESSOR

Production ElegooSlicer support has NOT yet been implemented.
```