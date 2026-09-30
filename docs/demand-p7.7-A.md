# P7.7-A — OrcaSlicer (Snapmaker) Real Artifact Reconnaissance

## 0. Goal

Characterize the real filament/material preset artifact and GUI behavior of the Snapmaker-distributed OrcaSlicer variant before implementing production support.

This phase must determine:

```text id="zn3jri"
artifact format
actual import/export unit
visible-name semantics
preset identity semantics
inheritance semantics
native-ID behavior
custom metadata behavior
round-trip behavior
compatibility with current Artifact abstraction
behavioral relationship to upstream OrcaSlicer
```

Do NOT implement or register the production Snapmaker processor during P7.7-A.

Final classification:

```text id="vwg9gj"
READY_FOR_PROCESSOR
ARCHITECTURE_CHANGE_REQUIRED
INSUFFICIENT_EVIDENCE
```

---

# 1. Naming

Use a distinct application slicer identity for the Snapmaker-distributed Orca variant.

Do not silently treat it as:

```text id="p1sfus"
OrcaSlicer
```

The exact production `slicer_id` will be frozen from existing project/UI naming during P7.7-B.

For reconnaissance files use:

```text id="jjb7qc"
orca_slicer_snapmaker
```

unless the repository already has a preferred naming convention.

---

# 2. Existing Architecture

Production processors currently include:

```text id="4zz3b9"
BambuStudioProcessor
OrcaSlicerProcessor
CrealityPrintProcessor
ElegooSlicerProcessor
PrusaSlicerProcessor
```

Generic artifact boundary:

```python id="dfgzt6"
Artifact(
    content: bytes,
    filename: str,
    media_type: str | None,
)
```

The generic workflow treats artifacts as opaque.

P7.7-A must determine whether Snapmaker Orca fits the same contract.

---

# 3. Critical Principle

Do NOT assume:

```text id="qfgp8n"
Snapmaker Orca == upstream OrcaSlicer
```

even if:

```text id="qpj1zj"
UI looks similar
JSON looks similar
field names match
source code shares ancestry
```

Behavioral equivalence must come from real artifact and GUI evidence.

---

# 4. Business Identity Must Remain Independent

Regardless of implementation similarity, Snapmaker Orca must remain a distinct application slicer identity.

Conceptually:

```text id="1e1yfd"
L2002CF|SnapmakerPrinter|OrcaSlicer
```

and:

```text id="3eb5t4"
L2002CF|SnapmakerPrinter|OrcaSlicerSnapmaker
```

must be capable of representing distinct logical Presets if those are the configured slicer identities.

P7.7-A may investigate implementation sharing.

It must NOT collapse business identity.

---

# 5. Required Human Input

Request:

```text id="bwsls7"
1. exact Snapmaker OrcaSlicer version/build
2. one real custom filament/material preset exported from that exact version
```

Prefer a preset that:

```text id="l2n3l9"
was created/edited in the Snapmaker-distributed slicer
contains recognizable material parameters
has normal inheritance if the slicer supports it
is known to import successfully back into the same application
```

Do not use an upstream Orca export as the primary Snapmaker fixture.

---

# 6. Stop If Real Artifact Is Missing

If the real Snapmaker artifact is unavailable, STOP and request exactly:

> Please provide one real custom filament/material preset exported from the Snapmaker OrcaSlicer version used in your workflow, together with the exact application version/build.

Do not generate a synthetic Snapmaker fixture from the upstream Orca fixture.

Do not implement production support.

---

# 7. Preserve Original Artifact

Store the original unchanged under:

```text id="vhcdvf"
tests/fixtures/slicers/orca_slicer_snapmaker/reconnaissance/
```

For example:

```text id="ch7i5l"
source_original.<actual_extension>
```

Record:

```text id="c77fy6"
application/version/build
original filename
extension
size
SHA-256
```

Never modify the original fixture in place.

---

# 8. Determine Actual Artifact Format

Inspect actual bytes.

Determine:

```text id="4kuygx"
plain JSON
structured text
archive
3MF-derived container
binary
multi-file package
other
```

Do not infer from extension alone.

---

# 9. Determine Actual Import Unit

Establish what the GUI actually imports as one filament preset.

Determine whether it is:

```text id="8wd1pp"
one file
one archive
one bundle
multiple files
another structure
```

A single archive containing multiple members may still be one opaque `Artifact`.

---

# 10. Artifact Boundary

Explicitly classify:

```text id="bgvy5c"
Artifact(content, filename, media_type)
```

as:

```text id="drs72u"
SUFFICIENT
INSUFFICIENT
UNCERTAIN
```

Do not modify Artifact during reconnaissance.

---

# 11. Structural Analysis

Inspect the real Snapmaker artifact and identify where present:

```text id="5zcq6i"
name / display-name candidate
preset type
filament/material type
inherits / parent
filament_settings_id
native IDs
vendor metadata
printer compatibility
Snapmaker-specific metadata
version/build metadata
material parameters
printing parameters
unknown/custom metadata
```

Do not limit the search to fields already known from upstream Orca.

---

# 12. Snapmaker-Specific Fields

Explicitly identify fields that appear:

```text id="unqtbf"
Snapmaker-specific
vendor-specific
fork-specific
machine-ecosystem-specific
```

Do not delete them from fixtures.

Determine whether they survive round-trip.

These fields may become important evidence that the processors should remain implementation-independent.

---

# 13. Compare With Real Upstream Orca Fixture

Use the already validated real upstream Orca fixture from P7.3/P7.3.1 as the comparison source.

Compare structurally:

```text id="s7e6i2"
container format
top-level structure
required fields
name
inherits
filament_settings_id
type
material fields
compatibility fields
vendor fields
custom metadata capability
unknown fields
```

Produce descriptive findings only.

Similarity is not yet behavioral equivalence.

---

# 14. Structural Comparison Classification

For each relevant field/component classify:

```text id="m3n5bu"
IDENTICAL_STRUCTURE
SIMILAR_STRUCTURE
SNAPMAKER_ONLY
UPSTREAM_ONLY
SEMANTICS_UNKNOWN
```

Do not use this classification to decide processor sharing yet.

---

# 15. Artifact Analysis Report

Create:

```text id="8n4oqu"
snapmaker_orca_artifact_analysis.md
```

Include:

```text id="0tnmkr"
exact version/build
source provenance
container format
import unit
important fields
Snapmaker-specific fields
candidate visible-name semantics
candidate identity semantics
candidate inheritance semantics
custom metadata capability
Artifact assessment
structural comparison with upstream Orca
```

---

# 16. Baseline Variant

Create:

```text id="88wbbr"
00_baseline.<extension>
```

semantically identical to the real source.

The human must import baseline before any modified variants.

Record:

```text id="v4u5d9"
import success
visible preset name
new vs overwrite
duplicate/conflict warning
other behavior
```

---

# 17. Baseline Failure Rule

If baseline does not import correctly into the same Snapmaker Orca version:

STOP.

Resolve import/export semantics before generating further conclusions.

---

# 18. Dynamic Experiment Matrix

After structural analysis, generate approximately:

```text id="ug57f3"
3–6 minimal variants
```

based on actual fields.

Do not blindly copy the upstream Orca matrix.

Each variant must answer one semantic question.

---

# 19. Name-Only Experiment

If `name` is the strongest visible-name candidate, create:

```text id="k9ld2r"
name = P7SM_NAME_ONLY
```

while preserving all other fields.

Test:

```text id="prrzh4"
visible name
new preset vs overwrite
conflict behavior
```

If the actual artifact indicates another name mechanism, test that instead.

---

# 20. `filament_settings_id` Experiment

If present, generate an evidence-driven identity experiment.

Possible matrix:

```text id="71d5a6"
name changed only

name + filament_settings_id changed
```

Do not assume `filament_settings_id` controls display identity.

Determine whether it:

```text id="scq8vh"
affects creation/overwrite
survives re-export
is regenerated
must track name
```

---

# 21. Inheritance-Preserved Experiment

If `inherits` exists:

create a new-name variant while preserving:

```text id="e2g7dr"
inherits
```

unchanged.

Determine whether a custom Snapmaker preset can have:

```text id="k8a4ol"
new visible identity
+
original inheritance
```

without conflict.

---

# 22. Other Native Identity Fields

If structural analysis finds additional strong identity candidates, test only those supported by evidence.

Do not mutate every ID-like field.

Fields such as:

```text id="ktvfb2"
uuid
base_id
setting_id
vendor ID
parent ID
```

must remain untouched unless there is a concrete reason to test them.

---

# 23. `pm_method_version` Experiment

If safe for the real artifact format, inject:

```text id="4r6glv"
pm_method_version = P7SM_TEST
```

Determine:

```text id="9rxuxl"
import accepted?
visible behavior changed?
survives re-export?
removed?
rewritten?
```

---

# 24. Metadata Authority Principle

Regardless of external round-trip behavior:

```text id="trrsl3"
Submission.pm_method_version
```

remains authoritative.

If Snapmaker Orca strips the custom field on re-export, this may be an accepted limitation exactly as with other slicers.

Do not invent a workaround during P7.7-A.

---

# 25. Experiment Manifest

Create:

```text id="q03h8f"
experiment_manifest.md
```

For each variant record:

```text id="py4q73"
filename
SHA-256
exact fields/components changed
old value
new value
question being tested
```

---

# 26. GUI Results Sheet

Create:

```text id="yvn1dl"
GUI_TEST_RESULTS.md
```

with:

| Variant | Import succeeds? | Visible preset name | Created new preset? | Overwrote/replaced existing preset? | Duplicate/conflict warning? | Other visible behavior | Re-exported filename |
|---|---|---|---|---|---|---|---|

Do not guess or pre-fill GUI outcomes.

---

# 27. Required Human Stop

After producing:

```text id="u20k0s"
source analysis
baseline
experiment variants
manifest
GUI result sheet
```

STOP.

Ask the human to run the GUI experiments.

Do not proceed directly to production implementation.

---

# 28. Re-Export Informative Variants

After GUI results are supplied, request/reuse re-exported artifacts for the most informative successful cases:

```text id="m4w1e9"
baseline
name-only
identity variant
inheritance-preserved variant
pm_method_version variant
```

Avoid redundant re-exports.

---

# 29. Snapmaker Round-Trip Analysis

Compare each relevant:

```text id="z52qgl"
input variant
→ Snapmaker Orca import
→ Snapmaker Orca re-export
```

Separate:

```text id="h0u9qw"
semantic changes
slicer-generated metadata
identity normalization
inheritance changes
removed custom metadata
parameter changes
serialization-only changes
```

---

# 30. Parameter Preservation

Verify representative real parameters survive the tested workflow.

Use actual fields from the fixture, covering where available:

```text id="hiylyu"
nozzle temperature
bed temperature
flow ratio
maximum volumetric speed
cooling
retraction
density
diameter
other material parameters
```

Do not rely on field names copied from upstream Orca.

---

# 31. Final Visible-Name Semantics

Determine exactly what controls the Snapmaker GUI-visible preset name.

Classify:

```text id="klb3ps"
name alone sufficient
name + native ID required
another field required
filename involved
uncertain
```

---

# 32. Final Identity Semantics

Determine what causes:

```text id="a88dvb"
new preset
overwrite/replacement
duplicate/conflict
```

Do not equate "field survives round-trip" with "field controls identity."

---

# 33. `filament_settings_id` Classification

If present, classify as:

```text id="6x3q70"
PRESERVE
MUST_CHANGE_WITH_NAME
SLICER_MANAGED
IRRELEVANT_TO_WORKER
UNCERTAIN
```

Do not change it in production merely because upstream Orca contains the same field.

---

# 34. Inheritance Classification

Determine:

```text id="wspdrg"
whether inherits is preserved
whether new name can retain old inherits
whether slicer rewrites it
whether Worker should preserve it
```

Prefer preservation unless evidence requires mutation.

---

# 35. `pm_method_version` Classification

Use:

```text id="t3xehm"
PRESERVED
REMOVED_ON_REEXPORT
REWRITTEN
UNSUPPORTED
NOT_TESTED
```

Document exact behavior.

---

# 36. Cross-Import Experiment

Because an upstream Orca processor already exists, perform a limited compatibility experiment after native Snapmaker behavior is understood.

Test:

```text id="u6op4s"
real upstream Orca custom filament preset
        ↓
Snapmaker Orca import
```

and, if practical:

```text id="0ujaz6"
real Snapmaker Orca custom filament preset
        ↓
upstream Orca import
```

Record:

```text id="itvms2"
import success
visible name
parameter integrity
warnings
missing fields
rewritten fields
```

This is diagnostic only.

---

# 37. Cross-Import Does Not Merge Business Identity

Even if both directions import perfectly:

do NOT conclude:

```text id="9ptvge"
Snapmaker Orca = OrcaSlicer
```

Cross-import compatibility establishes format compatibility, not application identity equivalence.

---

# 38. Behavioral Comparison With Upstream Orca

Create:

```text id="jvps6w"
upstream_orca_comparison.md
```

Compare:

| Behavior | Upstream Orca | Snapmaker Orca | Equivalent? |
|---|---|---|---|
| Artifact format | | | |
| Import unit | | | |
| Visible-name control | | | |
| New-preset identity | | | |
| `filament_settings_id` | | | |
| `inherits` | | | |
| Unknown fields | | | |
| `pm_method_version` | | | |
| Parameter preservation | | | |
| Cross-import | | | |

Use evidence, not source-code ancestry.

---

# 39. Implementation Relationship Classification

At the end of P7.7-A classify the implementation relationship as one of:

```text id="ek9l6o"
INDEPENDENT_IMPLEMENTATION_REQUIRED

SHARED_PURE_HELPERS_APPROPRIATE

SHARED_CORE_WITH_DISTINCT_PROCESSOR_FACADES_POSSIBLE

INSUFFICIENT_EVIDENCE
```

This classification is advisory for P7.7-B.

It must not collapse `slicer_id`.

---

# 40. Criteria for Shared Pure Helpers

Use:

```text id="pz0v4g"
SHARED_PURE_HELPERS_APPROPRIATE
```

when mechanics are identical but business rules may differ.

Examples:

```text id="as8o0g"
JSON loading
deterministic JSON serialization
recursive diff traversal
stable path sorting
```

Do not place slicer identity policy in these helpers.

---

# 41. Criteria for Shared Core

Only classify:

```text id="otgz9h"
SHARED_CORE_WITH_DISTINCT_PROCESSOR_FACADES_POSSIBLE
```

if real evidence shows equivalent behavior for all relevant processor responsibilities:

```text id="zv9c1a"
source validation
visible-name mutation
native identity preservation
inheritance behavior
company metadata injection
serialization
diff semantics
```

Structural similarity alone is insufficient.

---

# 42. No Refactor During P7.7-A

Even if shared-core eligibility looks obvious:

do NOT refactor `OrcaSlicerProcessor` during reconnaissance.

P7.7-A only produces evidence and recommendation.

---

# 43. Proposed P7.7-B Canonicalization

If ready, define minimum production mutation rules.

Likely shape may be:

```text id="3h61nf"
source Snapmaker artifact
+
canonical visible-name mutation
+
pm_method_version from ProcessingContext
```

but use the actual evidence.

Do not automatically copy upstream Orca's:

```text id="ngqss7"
name mutation
filament_settings_id behavior
inherits behavior
```

until validated.

---

# 44. Proposed Validation

Define how P7.7-B should distinguish:

```text id="m5vj80"
valid Snapmaker filament preset
malformed artifact
unsupported preset type
unrelated artifact
```

Unknown fields should normally remain accepted.

---

# 45. Proposed UnifiedDiff

Determine whether the current `UnifiedDiff` model is sufficient.

Expected classification:

```text id="35t4ke"
SUFFICIENT
```

unless real evidence proves otherwise.

Define slicer-specific classification rules from actual Snapmaker fields.

Unknown fields must ultimately map to:

```text id="q59ry5"
OTHER_PARAMETER
```

rather than disappear.

---

# 46. Fixture Hygiene

Inspect fixtures for:

```text id="q03e6l"
usernames
absolute paths
account IDs
tokens
network credentials
private machine identifiers
```

Sanitize where appropriate.

Document every sanitization that affects artifact content.

Do not silently sanitize fields under semantic investigation.

---

# 47. Evidence Priority

Use:

```text id="5qfnwb"
1. Snapmaker GUI import behavior
2. Snapmaker GUI re-export
3. original real Snapmaker export
4. cross-import experiments
5. upstream Orca GUI evidence
6. official source/docs if needed
7. structural similarity
```

Do not invert this hierarchy.

---

# 48. No Production Changes

P7.7-A must NOT:

```text id="lwp4g5"
implement Snapmaker production processor
register Snapmaker slicer
enable it in production UI
change preset_key
change Artifact
change UnifiedDiff
change generic workflow
refactor OrcaSlicerProcessor
```

Experimental scripts and fixtures are allowed.

---

# 49. Acceptance Criteria

P7.7-A is complete when:

```text id="ty2f17"
[ ] exact Snapmaker Orca version/build recorded
[ ] real custom Snapmaker filament artifact obtained
[ ] original artifact preserved
[ ] SHA-256 recorded
[ ] actual artifact format established
[ ] actual import unit established
[ ] Snapmaker-specific fields identified
[ ] real upstream Orca structural comparison completed
[ ] baseline GUI import succeeds
[ ] minimal evidence-driven variants generated
[ ] GUI results recorded
[ ] informative variants re-exported
[ ] round-trip analysis completed
[ ] visible-name semantics established
[ ] new-vs-overwrite semantics established
[ ] filament_settings_id behavior classified if present
[ ] inheritance behavior established
[ ] pm_method_version behavior classified
[ ] material/printing parameters checked
[ ] cross-import tested where practical
[ ] upstream-vs-Snapmaker behavioral comparison completed
[ ] Artifact abstraction assessed
[ ] UnifiedDiff suitability assessed
[ ] implementation relationship classified
[ ] P7.7-B canonicalization rules proposed
[ ] P7.7-B validation rules proposed
[ ] no production processor implemented
[ ] no upstream Orca refactor performed
[ ] final readiness classification produced
```

---

# 50. Completion Report

Create:

```text id="zdxyjg"
p7.7-A_completion_report.md
```

Report:

1. exact application name;
2. exact version/build;
3. source artifact provenance;
4. original filename;
5. original size;
6. SHA-256;
7. actual artifact format;
8. actual import unit;
9. important structural fields;
10. Snapmaker-specific fields;
11. upstream-Orca structural differences;
12. candidate visible-name semantics;
13. candidate identity fields;
14. inheritance representation;
15. baseline result;
16. generated experiment matrix;
17. name-only result;
18. native-ID experiment results;
19. new-vs-overwrite behavior;
20. inheritance result;
21. `pm_method_version` result;
22. selected re-export results;
23. round-trip semantic mutations;
24. serialization-only changes;
25. material/printing parameter preservation;
26. final visible-name semantics;
27. final preset identity semantics;
28. `filament_settings_id` classification;
29. final inheritance semantics;
30. custom metadata classification;
31. upstream Orca → Snapmaker import result;
32. Snapmaker → upstream Orca import result;
33. cross-import limitations;
34. final upstream-vs-Snapmaker behavioral comparison;
35. Artifact sufficiency classification;
36. UnifiedDiff suitability;
37. proposed P7.7-B canonicalization;
38. proposed P7.7-B source validation;
39. proposed P7.7-B diff strategy;
40. implementation relationship classification;
41. whether shared helpers are justified;
42. whether shared core is justified;
43. business-identity separation confirmation;
44. fixture sanitization;
45. known limitations;
46. final readiness classification.

---

# 51. Final Classification

Use exactly one:

```text id="45wl2n"
READY_FOR_PROCESSOR
ARCHITECTURE_CHANGE_REQUIRED
INSUFFICIENT_EVIDENCE
```

Separately report implementation relationship as:

```text id="n3k7h1"
INDEPENDENT_IMPLEMENTATION_REQUIRED

SHARED_PURE_HELPERS_APPROPRIATE

SHARED_CORE_WITH_DISTINCT_PROCESSOR_FACADES_POSSIBLE

INSUFFICIENT_EVIDENCE
```

These are two different conclusions.

---

# 52. Expected First Agent Response

If no real Snapmaker artifact/version has yet been provided, the Agent should NOT begin implementation.

Its next response should be:

> Please provide one real custom filament/material preset exported from the Snapmaker OrcaSlicer version used in your workflow, together with the exact application version/build.

---

# 53. Expected Successful End State

A successful P7.7-A ends conceptually as:

```text id="7thz30"
P7.7-A complete.

Snapmaker OrcaSlicer <version/build> real filament-preset
semantics have been characterized through native GUI testing,
round-trip analysis, and controlled comparison with upstream OrcaSlicer.

Artifact:
SUFFICIENT

Processor readiness:
READY_FOR_PROCESSOR

Implementation relationship:
<one classification>

Business identity:
DISTINCT

Production Snapmaker Orca support has NOT been implemented.
```