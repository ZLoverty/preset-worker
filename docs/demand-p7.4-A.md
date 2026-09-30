# P7.4-A — CrealityPrint Artifact Reconnaissance

## 0. Purpose

Before implementing `CrealityPrintProcessor`, determine the actual artifact format and preset semantics used by the CrealityPrint version deployed in the real engineering workflow.

Do NOT implement production CrealityPrint support in this phase.

P7.4-A answers:

```text
What does CrealityPrint actually export?

What artifact must the Worker accept?

What artifact must the Worker produce?

How is preset identity represented?

How is the visible preset name determined?

Is inheritance used?

Can unknown/custom fields survive?

Can pm_method_version survive import/export?

Does the existing Artifact abstraction support the format?
```

The output of P7.4-A will define P7.4-B.

---

# 1. Architecture Context

Current processor architecture:

```text
Submission
    │
    ▼
SlicerProcessorRegistry
    │
    ▼
SlicerProcessor
    │
    ├── Artifact
    │     content: bytes
    │     filename: str
    │     media_type: str | None
    │
    └── UnifiedDiff
```

Existing production processors:

```text
BambuStudioProcessor
OrcaSlicerProcessor
```

CrealityPrint must eventually fit this architecture without leaking slicer-specific behavior into workflow.

But P7.4-A must first determine whether the existing `Artifact` contract is sufficient.

---

# 2. Do Not Assume JSON

Do NOT assume CrealityPrint exports:

```text
JSON
single file
Bambu-compatible profile
Orca-compatible profile
```

even if internal implementation or documentation suggests similarities.

Inspect the real exported artifact first.

---

# 3. Do Not Assume Orca Semantics

Do NOT infer CrealityPrint behavior from:

```text
BambuStudio
OrcaSlicer
PrusaSlicer
```

Field names may look familiar while having different import/identity semantics.

Treat CrealityPrint as an independent slicer.

---

# 4. Required Human Input

Request exactly one real custom filament/material preset exported from the CrealityPrint installation actually used by the engineering workflow.

Prefer:

```text
a simple custom filament preset
derived from a normal built-in/base preset
known to work in CrealityPrint
with a clearly identifiable visible name
```

Do not ask the human to edit the artifact.

---

# 5. Record CrealityPrint Version

Record the exact CrealityPrint version used to create the source artifact.

This must accompany the fixture.

Do not describe compatibility generically as:

```text
CrealityPrint compatible
```

without the tested version.

---

# 6. Preserve Original Artifact

Store the original export unchanged.

Conceptually:

```text
tests/fixtures/slicers/creality_print/reconnaissance/
    source_original.<actual extension>
```

Compute and record:

```text
filename
file size
SHA-256
```

Never modify the original in place.

---

# 7. Determine Artifact Container Type

Inspect the artifact safely.

Determine whether it is:

```text
plain JSON
plain text
ZIP/archive
3MF-derived archive
binary
multiple files
directory/package
other
```

Do not rely only on file extension.

Inspect magic bytes/container structure where appropriate.

---

# 8. If Artifact Is an Archive

If it is an archive:

inspect:

```text
member paths
member file types
manifest files
preset/profile files
metadata
```

Do not extract and then treat only one internal file as the artifact unless CrealityPrint itself accepts that internal file independently.

The external import/export unit is what matters to the Worker contract.

---

# 9. If Artifact Is JSON

If plain JSON, inspect:

```text
top-level type
keys
nested structure
identity fields
preset-type fields
inheritance fields
version fields
printer compatibility fields
material fields
metadata fields
```

Do not implement a processor yet.

---

# 10. If Artifact Is Not JSON

This is especially valuable.

Determine whether:

```text
Artifact(content: bytes, filename, media_type)
```

can represent it unchanged.

If yes, report:

```text
existing opaque Artifact abstraction is sufficient
```

If not, explain exactly why.

Do NOT immediately redesign Artifact.

---

# 11. Single-Artifact Question

Determine whether one exported preset corresponds to one self-contained artifact.

Possible outcomes:

```text
A. one file, self-contained

B. one archive containing multiple internal files

C. multiple external files required together

D. external dependencies required
```

This directly affects P7.4-B architecture.

---

# 12. Import Unit

Determine what CrealityPrint actually expects the user to import:

```text
individual preset file
archive
configuration bundle
project file
other
```

The Worker canonical artifact should normally correspond to the slicer's actual import unit.

---

# 13. Source Inspection Report

Generate:

```text
creality_artifact_analysis.md
```

containing:

```text
CrealityPrint version
source filename
size
checksum
container type
internal structure
apparent preset type
identity-related fields
inheritance-related fields
version-related fields
custom/unknown field candidates
initial architecture observations
```

---

# 14. Identify Candidate Identity Fields

Based on the real artifact, identify fields that appear potentially related to:

```text
visible preset name
internal preset ID
material ID
settings ID
profile ID
UUID
inheritance
parent profile
vendor
printer
```

Do not conclude semantics from names alone.

Mark them as:

```text
candidate identity field
```

until GUI experiments confirm behavior.

---

# 15. Establish Baseline Import

Generate an untouched baseline copy:

```text
00_baseline.<extension>
```

The human imports it back into the same CrealityPrint installation.

Record:

```text
import succeeds?
visible preset name
new preset?
existing preset overwritten?
warning/conflict?
other behavior?
```

If baseline fails, STOP.

Do not interpret identity experiments until the baseline workflow is valid.

---

# 16. Controlled Mutation Strategy

After inspecting the real artifact, generate a minimal experiment matrix based on fields that actually exist.

Do NOT blindly copy the Orca experiment filenames/fields.

The Agent must derive experiments from the Creality artifact.

---

# 17. Name-Only Experiment

If a clear candidate visible-name field exists, generate a variant changing only that field.

Use a unique value such as:

```text
P7CP_NAME_ONLY
```

Question:

> Is changing this field sufficient to create/display a distinct custom preset?

---

# 18. Identity-ID Experiments

For each credible identity field found in the artifact, consider a controlled experiment:

```text
name + identity field A
name + identity field B
...
```

Only generate useful experiments.

Do not create a combinatorial explosion.

---

# 19. Minimum Useful Matrix

Prefer approximately:

```text
baseline
name only
name + strongest ID candidate
name + second ID candidate, if justified
all plausible identity fields, if justified
```

Usually 3–6 files are enough.

Do not generate dozens of variants.

---

# 20. Inheritance Experiment

If the source artifact uses inheritance/parent references:

first test:

```text
change intended visible identity
preserve inheritance exactly
```

Do NOT initially mutate the inheritance target.

Question:

> Can a custom renamed preset remain inherited from the same base?

---

# 21. Unknown Custom Field Experiment

Determine whether it is safe to add an unknown field to the artifact.

If the artifact format allows this without invalidating schema/container integrity, generate a controlled custom field such as:

```text
pm_method_version = "P7CP_TEST"
```

The exact representation depends on the real artifact.

Do not inject it blindly if the format is not extensible.

---

# 22. `pm_method_version` Question

Determine whether CrealityPrint:

```text
accepts the custom metadata
preserves it internally
preserves it on re-export
removes it
rejects the artifact
rewrites it
```

This is important, but remember:

`Submission.pm_method_version` remains authoritative.

Loss during slicer re-export may be acceptable if Worker can safely re-inject it during every canonicalization, as with validated Orca behavior.

---

# 23. Experiment Manifest

Generate:

```text
experiment_manifest.md
```

For each variant record:

```text
filename
source checksum
variant checksum
fields/components changed
old value
new value
question being tested
```

For archive artifacts, include changed internal member paths.

---

# 24. GUI Test Sheet

Generate:

```text
GUI_TEST_RESULTS.md
```

with:

| Variant | Import succeeds? | Visible preset name | Created new preset? | Overwrote/replaced existing preset? | Duplicate/conflict warning? | Other visible behavior | Re-exported filename |
|---|---|---|---|---|---|---|---|

The human fills only observable results.

---

# 25. Human Test Procedure

The human should:

```text
1. Test baseline first.
2. Import each generated variant.
3. Record visible behavior.
4. Do not manually edit variants.
5. Re-export selected successful presets.
```

---

# 26. Avoid Experiment Contamination

If importing one variant can affect the next:

```text
remove the experimental preset
restore known state
or use unique identity values
```

Record overwrite behavior carefully.

An overwrite is evidence about identity semantics.

---

# 27. Re-export Selected Variants

Re-export at minimum:

```text
baseline
name-only successful variant
most informative identity variant
custom-metadata variant
```

where possible.

Keep input and re-export files separate.

---

# 28. Round-Trip Analysis

For every re-exported artifact compare:

```text
experiment input
        vs
CrealityPrint re-export
```

For structured artifacts, produce semantic differences.

For archives, compare:

```text
archive members
added/removed members
changed members
semantic changes inside structured members
```

Ignore formatting differences only after explicitly identifying them as formatting.

---

# 29. Determine Display-Name Semantics

Conclude from evidence:

```text
which field controls visible name?
is that field sufficient?
does another ID need synchronization?
does inheritance override it?
does CrealityPrint rewrite it?
```

---

# 30. Determine Preset Identity Semantics

Use:

```text
new preset behavior
overwrite behavior
duplicate behavior
round-trip output
```

to infer which field(s) participate in logical identity.

Do not use visible name alone.

---

# 31. Determine Inheritance Semantics

If inheritance exists, determine:

```text
whether parent reference survives import
whether it survives re-export
whether renamed custom preset can retain parent
whether parent must exist locally
```

Do not flatten inheritance unless evidence requires it.

---

# 32. Determine Custom Metadata Behavior

Conclude whether `pm_method_version`:

```text
survives
is stripped
must be stored elsewhere
or cannot safely exist in the native artifact
```

Do not redesign company metadata storage during reconnaissance.

---

# 33. Parameter Preservation

For successful variants verify that changing identity metadata did not unexpectedly modify material/process parameters.

Round-trip analysis should distinguish:

```text
identity changes
Creality-generated metadata changes
printing/material parameter changes
```

Unexpected parameter changes must be reported.

---

# 34. Test Current Artifact Abstraction

Explicitly answer:

> Can the current `Artifact(content: bytes, filename, media_type)` represent the complete CrealityPrint import/export unit without loss?

Possible conclusions:

```text
YES

YES, because the entire package/archive can remain opaque bytes

NO, because multiple independently named external artifacts are required

UNCERTAIN
```

---

# 35. Do Not Confuse Archive With Multi-Artifact

If CrealityPrint exports one ZIP-like file containing many internal files:

```text
one archive
```

is still one opaque Artifact.

Do NOT introduce package abstraction merely because the artifact contains multiple internal members.

---

# 36. Architecture Escalation Condition

Only propose extending `Artifact` if CrealityPrint genuinely requires something the existing model cannot represent.

For example:

```text
multiple external files required as one logical preset
directory semantics that cannot be serialized safely
external references that must accompany the artifact
```

Provide concrete evidence.

---

# 37. No Processor Yet

Do NOT add:

```text
CrealityPrintProcessor
```

to the production registry during P7.4-A.

Do not enable CrealityPrint in production UI.

---

# 38. Experimental Parsing Is Allowed

Reconnaissance scripts may parse or unpack Creality artifacts.

These scripts are exploratory tooling.

They must not be wired into production workflow.

---

# 39. Do Not Modify Generic Workflow

No changes should be made to:

```text
enrichment
publication
review
version allocation
Preset identity
Artifact contract
UnifiedDiff contract
```

unless reconnaissance discovers a concrete architecture incompatibility.

If so, report it instead of immediately changing production code.

---

# 40. No Synthetic Production Rules

Do not produce final validation rules from documentation alone.

Documentation may support analysis, but real exported artifacts and real import behavior are authoritative for this phase.

---

# 41. Version Scope

Do not attempt to characterize every historical CrealityPrint version.

Validate the version actually used by the engineering workflow.

Record any obvious version markers found in the artifact.

Future compatibility can be expanded later.

---

# 42. Security / Fixture Hygiene

Before committing real-export-derived fixtures, inspect them for:

```text
usernames
local paths
machine names
account identifiers
tokens
network addresses
private metadata
```

Sanitize where necessary.

Do not alter fields relevant to the compatibility experiment without documenting the transformation.

---

# 43. Reconnaissance Tests

Automated exploratory tests/scripts should be able to verify:

```text
original artifact readable
variant mutations limited to intended fields/components
checksums generated
baseline preserved
round-trip comparison deterministic
```

These are not yet `SlicerProcessor` contract tests.

---

# 44. Required Stop Point #1

If no real CrealityPrint artifact has been supplied:

STOP and request:

> Please provide one real custom filament/material preset exported from the CrealityPrint version used in your workflow.

Do not create synthetic substitute data.

---

# 45. Required Stop Point #2

After analyzing the real artifact and generating controlled variants:

STOP.

Return:

```text
artifact analysis
experiment variants
experiment manifest
GUI test sheet
```

Ask the human to perform the import tests.

Do not implement `CrealityPrintProcessor` yet.

---

# 46. Resume After GUI Results

After GUI observations and available re-exported artifacts are returned:

perform:

```text
round-trip analysis
identity conclusions
inheritance conclusions
custom metadata conclusions
Artifact-contract assessment
```

Then produce the P7.4-A completion report.

Still do NOT implement the production processor unless explicitly continuing into P7.4-B.

---

# 47. P7.4-B Readiness

At the end classify reconnaissance as:

```text
READY_FOR_PROCESSOR
ARCHITECTURE_CHANGE_REQUIRED
INSUFFICIENT_EVIDENCE
```

### READY_FOR_PROCESSOR

Artifact format, identity behavior and canonicalization requirements are sufficiently understood.

### ARCHITECTURE_CHANGE_REQUIRED

Real Creality behavior cannot be represented correctly by the current processor/artifact architecture.

### INSUFFICIENT_EVIDENCE

Important import/export semantics remain unresolved.

---

# Acceptance Criteria

P7.4-A is complete when:

```text
[ ] exact tested CrealityPrint version recorded

[ ] real exported preset preserved

[ ] actual artifact/container format identified

[ ] import unit identified

[ ] baseline re-import verified

[ ] identity candidate fields identified

[ ] controlled variants generated from real artifact

[ ] GUI results recorded

[ ] selected successful variants re-exported where possible

[ ] round-trip analysis completed

[ ] visible-name semantics established

[ ] preset identity behavior established sufficiently for processor design

[ ] inheritance behavior established where applicable

[ ] pm_method_version/custom metadata behavior tested where safely possible

[ ] printing/material parameters remain understood/preserved

[ ] current Artifact abstraction explicitly assessed

[ ] no production processor was prematurely implemented

[ ] P7.4-B readiness classification produced
```

# Completion Report

Report:

1. exact CrealityPrint version;
2. source artifact provenance;
3. filename/extension/size/checksum;
4. actual container/file format;
5. internal structure if applicable;
6. actual import unit;
7. source preset type;
8. candidate visible-name field(s);
9. candidate identity field(s);
10. inheritance representation;
11. version/compatibility metadata;
12. baseline import result;
13. generated experiment matrix;
14. name-only result;
15. identity-field experiment results;
16. overwrite/duplicate behavior;
17. inheritance-preserved result;
18. custom `pm_method_version` experiment result;
19. round-trip changes;
20. final visible-name semantics conclusion;
21. final identity semantics conclusion;
22. final inheritance conclusion;
23. custom-field preservation conclusion;
24. parameter-preservation conclusion;
25. whether one opaque Artifact is sufficient;
26. any architecture limitation discovered;
27. differences from BambuStudio;
28. differences from OrcaSlicer;
29. proposed evidence-backed canonicalization rules for P7.4-B;
30. proposed validation rules for P7.4-B;
31. proposed diff approach for P7.4-B;
32. fixture sanitization performed;
33. readiness: `READY_FOR_PROCESSOR`, `ARCHITECTURE_CHANGE_REQUIRED`, or `INSUFFICIENT_EVIDENCE`.