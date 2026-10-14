# P7.6-A — PrusaSlicer Real Artifact Reconnaissance

## 0. Goal

Investigate the real filament/material preset artifact produced and consumed by the PrusaSlicer version used in the engineering workflow before implementing `PrusaSlicerProcessor`.

This phase must establish from real artifacts and GUI behavior:

```text id="7im5gw"
actual export/import unit
artifact/container format
visible-name semantics
preset identity semantics
inheritance semantics
custom metadata behavior
round-trip behavior
compatibility with current Artifact abstraction
```

Do NOT implement or register `PrusaSlicerProcessor` during P7.6-A.

Final classification:

```text id="ax2yhk"
READY_FOR_PROCESSOR
ARCHITECTURE_CHANGE_REQUIRED
INSUFFICIENT_EVIDENCE
```

---

# 1. Existing Architecture

Currently validated production processors:

```text id="d9x00h"
BambuStudioProcessor
OrcaSlicerProcessor
CrealityPrintProcessor
ElegooSlicerProcessor
```

Generic artifact boundary:

```python id="zgkjf5"
Artifact(
    content: bytes,
    filename: str,
    media_type: str | None,
)
```

Generic processing model:

```text id="ptk48r"
Submission.slicer
        ↓
ProcessorRegistry
        ↓
SlicerProcessor
        ↓
opaque canonical Artifact
        +
UnifiedDiff
        ↓
generic workflow
```

P7.6-A must determine whether a real PrusaSlicer filament preset fits this model.

Do not change the architecture during reconnaissance.

---

# 2. Core Principle

Treat PrusaSlicer as an independent slicer.

Do NOT infer behavior from:

```text id="65uqqr"
OrcaSlicer
ElegooSlicer
BambuStudio
CrealityPrint
```

even if fields or profile structures appear related.

Shared ancestry is not evidence of identical import/export semantics.

---

# 3. First Question: What Is the Real Artifact?

Before analyzing fields, determine what a PrusaSlicer user actually exports and imports for **one custom filament preset**.

Possible outcomes may include:

```text id="1q6iyt"
single JSON file
INI/config file
configuration bundle
ZIP/archive
3MF/project-derived container
multiple files
directory/package
another format
```

Do not assume JSON.

Do not convert the artifact to JSON for convenience.

---

# 4. Required Human Input

Request:

```text id="j3x5sc"
1. exact PrusaSlicer version
2. one real custom filament/material preset exported from that version
```

The preset should preferably:

```text id="o93d1m"
be user-created/custom
derive from a normal existing filament profile
contain recognizable material parameters
be known to import successfully back into the same PrusaSlicer installation
```

The human must not manually edit the source artifact.

---

# 5. Stop If No Real Artifact Exists

If no real artifact has been supplied, STOP and request exactly:

> Please provide one real custom filament/material preset exported from the PrusaSlicer version used in your workflow, together with the exact PrusaSlicer version.

Do not create a synthetic fixture.

Do not implement the processor.

---

# 6. Preserve Original

Store the original artifact unchanged under:

```text id="d1xt6f"
tests/fixtures/slicers/prusa_slicer/reconnaissance/
```

Use a meaningful filename such as:

```text id="p1exzj"
source_original.<actual_extension>
```

Record:

```text id="7itq44"
PrusaSlicer version
original filename
extension
size
SHA-256
```

Never edit the original in place.

---

# 7. Determine Container Format From Bytes

Inspect the actual artifact.

Determine:

```text id="l1ijhm"
file/container format
encoding
magic bytes where applicable
archive structure where applicable
number of logical profiles contained
```

Do not rely only on filename extension.

---

# 8. Determine the Actual Import Unit

This is a critical P7.6-A result.

Determine whether one logical filament preset corresponds to:

```text id="xnvfru"
one independently importable file

one archive containing multiple internal members

a larger configuration bundle containing multiple presets

multiple independently named files

another structure
```

Document what the PrusaSlicer GUI actually accepts.

---

# 9. Bundle Semantics

If PrusaSlicer exports a configuration bundle rather than a standalone filament profile, determine:

```text id="4ps2ub"
whether the bundle may contain multiple presets
whether unrelated printer/print/filament presets are included
whether one target filament preset can be isolated
whether PrusaSlicer can import the isolated unit
whether Worker would need to preserve the whole bundle
```

Do NOT immediately redesign `Artifact`.

First characterize the real behavior.

---

# 10. Artifact Boundary Question

Explicitly answer:

> Can one logical PresetVersion in our system still be represented by one `Artifact(content, filename, media_type)`?

A single archive or bundle can still be one Artifact.

The important distinction is whether one application-level preset requires multiple separately named external resources.

---

# 11. Structural Analysis

After establishing the import unit, inspect its structure.

Identify where possible:

```text id="gz5fmv"
preset name
preset type
material type
vendor
inheritance / parent profile
native IDs
UUIDs
compatibility rules
printer/nozzle constraints
version metadata
material parameters
printing parameters
custom/unknown metadata
```

Mark uncertain semantics explicitly.

---

# 12. Do Not Assume Existing Field Names

Do not search only for:

```text id="4p90qf"
name
filament_settings_id
inherits
base_id
```

because those happened to matter for other slicers.

PrusaSlicer may represent these concepts differently.

Start from the actual artifact.

---

# 13. Configuration-Section Semantics

If the artifact uses sections such as INI/config sections, determine whether the preset's visible identity is represented by:

```text id="42xfbs"
section name
property inside section
both
another mechanism
```

Treat section names/paths as semantic data if PrusaSlicer uses them as identity.

Do not treat them as mere serialization formatting.

---

# 14. Initial Comparison With Existing Slicers

Create a descriptive comparison against:

```text id="udbd8k"
BambuStudio
OrcaSlicer
CrealityPrint
ElegooSlicer
```

Focus on:

```text id="w9ym87"
container format
import unit
name representation
identity representation
inheritance representation
custom metadata capability
```

Do not infer behavior from similarity.

---

# 15. Artifact Analysis Report

Create:

```text id="58g3vc"
prusa_artifact_analysis.md
```

Include:

```text id="k89iub"
tested PrusaSlicer version
source provenance
container format
actual import unit
bundle semantics if applicable
profile structure
candidate visible-name mechanism
candidate identity mechanism
candidate inheritance mechanism
custom metadata capability
initial Artifact assessment
comparison with existing processors
```

---

# 16. Baseline

Create an untouched or semantically identical baseline:

```text id="yaf70j"
00_baseline.<appropriate_extension>
```

If the artifact is a bundle, preserve its valid container structure.

The human must import baseline first.

Record:

```text id="4gjctf"
Import succeeds?
Visible preset name?
Created new preset?
Overwrite/replacement warning?
Duplicate/conflict warning?
Other behavior?
```

---

# 17. Baseline Failure Rule

If baseline cannot be imported back into the same PrusaSlicer version:

STOP.

Investigate export/import semantics before generating identity experiments.

Do not interpret variant failures until baseline behavior is understood.

---

# 18. Dynamic Experiment Matrix

After structural analysis, generate the smallest useful experiment matrix based on **actual Prusa fields/sections**.

Target approximately:

```text id="6mrxp5"
3–6 variants
```

Do not mechanically reproduce Orca/Elegoo/Creality experiments.

Each variant must answer one specific semantic question.

---

# 19. Visible-Name Experiment

Identify the strongest visible-name candidate.

Create a variant changing only that identity representation.

Use an unmistakable test value:

```text id="2fnfx7"
P7PS_NAME_ONLY
```

If name is represented by a section name/path rather than a property, modify the appropriate structural identity.

Question:

> Is changing only the apparent display-name identity sufficient to create a distinct PrusaSlicer filament preset?

---

# 20. Native Identity Experiments

If separate native identity fields exist, test only the strongest candidates.

Examples conceptually:

```text id="4z50a9"
display name only

display name + native ID A

display name + native ID B
```

Do not mutate every ID-looking field.

Determine whether each candidate:

```text id="9zwhv7"
affects new-vs-overwrite behavior
survives round-trip
is regenerated by PrusaSlicer
affects visible name
```

---

# 21. Inheritance Experiment

If PrusaSlicer exposes parent/inheritance semantics, generate a variant that:

```text id="t36cwi"
changes intended custom preset identity
preserves parent/inheritance unchanged
```

Test whether the renamed custom preset can continue using the original parent.

Do not flatten inheritance.

---

# 22. Custom Metadata Experiment

If the format safely allows unknown properties, add:

```text id="xxwnpl"
pm_method_version = P7PS_TEST
```

in the structurally appropriate place.

Determine:

```text id="8at30b"
accepted on import?
preserved on re-export?
removed?
rewritten?
causes validation failure?
```

---

# 23. Important `pm_method_version` Principle

`Submission.pm_method_version` remains authoritative.

Therefore:

```text id="2g6im9"
PrusaSlicer removes unknown metadata on re-export
```

is potentially acceptable.

Do not redesign the system merely to force third-party persistence.

---

# 24. Bundle Mutation Discipline

If experiments operate on a bundle containing multiple profiles:

modify only the target filament preset and the minimum container metadata necessary.

Do not alter unrelated presets.

Record every modified section/member.

---

# 25. Experiment Manifest

Create:

```text id="ntuzmx"
experiment_manifest.md
```

For each variant record:

```text id="0trc6x"
filename
SHA-256
exact structural elements changed
old value
new value
semantic question
```

For section-based formats, include section names.

For archives, include member paths.

---

# 26. GUI Test Sheet

Create:

```text id="c1uwkz"
GUI_TEST_RESULTS.md
```

with:

| Variant | Import succeeds? | Visible preset name | Created new preset? | Overwrote/replaced existing preset? | Duplicate/conflict warning? | Other visible behavior | Re-exported filename |
|---|---|---|---|---|---|---|---|

Do not pre-fill experimental results.

---

# 27. Required Human Stop

After generating:

```text id="g4vkiu"
artifact analysis
baseline
experiment variants
experiment manifest
GUI test sheet
```

STOP.

Ask the human to perform the GUI tests.

Do not implement `PrusaSlicerProcessor`.

Do not infer GUI behavior.

---

# 28. Human Test Order

Test:

```text id="6d13oz"
1. baseline
2. name/identity-only variant
3. additional identity variants
4. inheritance variant
5. custom metadata variant
```

Use unique test identities where needed to prevent one experiment from contaminating another.

---

# 29. Re-Export Selected Variants

Request re-export of the most informative successful variants.

Prefer:

```text id="6nfhmw"
baseline
name-only
meaningful identity variant(s)
inheritance-preserved variant
pm_method_version variant
```

Skip redundant cases.

---

# 30. Round-Trip Analysis

Compare:

```text id="r7e34p"
variant imported into PrusaSlicer
        ↓
PrusaSlicer re-export
        ↓
semantic comparison against variant input
```

Separate:

```text id="0hjyw8"
identity changes
inheritance changes
slicer-generated metadata
removed unknown metadata
material parameter changes
printing parameter changes
formatting/order-only changes
```

---

# 31. Section/Ordering Normalization

If PrusaSlicer rewrites:

```text id="c7p7kh"
property order
section order
whitespace
numeric formatting
escaping
```

do not automatically treat these as semantic changes.

The round-trip analyzer should distinguish semantic content from serialization noise where practical.

---

# 32. Visible-Name Conclusion

Determine:

```text id="n1jij4"
what actually controls the GUI-visible preset name
whether one change is sufficient
whether a second native ID must be synchronized
whether the identity resides in a field, section name, filename, or combination
```

---

# 33. New-vs-Overwrite Semantics

Determine what causes PrusaSlicer to:

```text id="x3x1z4"
create a new preset
overwrite/replace an existing preset
reject as duplicate
warn
merge
```

This is more important than guessing what an ID field “means.”

---

# 34. Inheritance Conclusion

Determine:

```text id="9hvck6"
whether inheritance exists
how it is represented
whether it survives rename/import/re-export
whether Worker should preserve it
```

Prefer preservation unless evidence requires otherwise.

---

# 35. Native ID Conclusion

For each important native ID/identity component classify it as:

```text id="8p7itc"
PRESERVE
MUST_CHANGE_WITH_CANONICAL_NAME
SLICER_MANAGED
IRRELEVANT_TO_WORKER
UNCERTAIN
```

Do not synthesize native IDs without evidence.

---

# 36. Parameter Preservation

Confirm whether identity modifications preserve representative:

```text id="u9mvsk"
temperature
flow/extrusion
cooling
retraction
material properties
other filament parameters
```

using whatever fields actually exist in the real artifact.

Unexpected semantic mutations must be documented.

---

# 37. `pm_method_version` Classification

Classify:

```text id="5i92c0"
PRESERVED
REMOVED_ON_REEXPORT
REWRITTEN
UNSUPPORTED
NOT_TESTED
```

If accepted on import but removed on re-export, Worker reinjection remains a valid strategy.

---

# 38. Artifact Sufficiency Classification

Classify the existing:

```python id="ctcmtf"
Artifact(content, filename, media_type)
```

as:

```text id="5epakl"
SUFFICIENT
INSUFFICIENT
UNCERTAIN
```

Do not extend `Artifact` merely because a single archive/bundle contains multiple internal objects.

---

# 39. Architecture Escalation

Only recommend architecture changes when real PrusaSlicer semantics cannot be represented by one opaque Artifact.

Examples of actual blockers:

```text id="3tqlr6"
multiple independently named external files are mandatory
directory identity is mandatory
external resource relationships cannot be embedded
one PresetVersion cannot correspond to the import/export unit
```

If such a blocker exists:

```text id="lqufgo"
ARCHITECTURE_CHANGE_REQUIRED
```

and stop before processor implementation.

---

# 40. Proposed P7.6-B Canonicalization

If architecture is sufficient, propose the minimum canonicalization rules.

General preference:

```text id="v2w0if"
real source artifact
+
minimum identity mutation required for canonical display name
+
pm_method_version if safely supported
```

Preserve everything else unless evidence says otherwise.

---

# 41. Canonical Naming Target

Application-level desired visible name remains:

```python id="ph5l33"
f"{context.pi_code} @{context.printer}"
```

P7.6-A must determine **how this maps into PrusaSlicer artifact semantics**.

Do not assume a `name` JSON field exists.

---

# 42. Proposed Validation Rules

Define evidence-based rules for distinguishing:

```text id="fnc5zi"
valid supported Prusa filament preset
malformed artifact
unsupported Prusa preset type
unrelated artifact
```

Do not reject unknown parameters merely because Worker does not recognize them.

---

# 43. Proposed UnifiedDiff Strategy

Determine whether semantic content can map cleanly into:

```text id="5mtgze"
UnifiedDiff
DiffChange
ChangeType
DiffCategory
```

If sections are involved, define stable semantic paths conceptually, for example:

```text id="k01un8"
filament.temperature
filament.retraction
metadata.parent
```

Use actual structure rather than these example names.

Unknown parameters should ultimately remain visible as:

```text id="h95wtx"
OTHER_PARAMETER
```

not disappear.

---

# 44. No Production Code

During P7.6-A do NOT:

```text id="b6tmtv"
create production PrusaSlicerProcessor
register PrusaSlicer
enable Prusa in UI
modify generic enrichment
modify publication
modify versioning
modify Artifact
modify UnifiedDiff
```

Experimental analysis scripts are allowed.

---

# 45. No Premature Prusa-Family Abstraction

Do not introduce:

```text id="tb2h2n"
PrusaFamilyProcessor
OrcaLikeProcessor
BasePrusaProcessor
```

during reconnaissance.

Even if the artifact looks extremely similar to Orca/Elegoo, collect real behavioral evidence first.

---

# 46. Fixture Hygiene

Inspect real artifacts for:

```text id="5tz8w5"
usernames
absolute local paths
account identifiers
tokens
network credentials
private machine identifiers
```

Sanitize if necessary.

Document sanitization.

Do not silently sanitize fields whose semantics are being investigated.

---

# 47. Reuse Reconnaissance Tooling

Reusable P7.4/P7.5 tooling may be used for:

```text id="46pbh3"
checksums
variant generation
semantic comparison
manifest generation
```

only if it is format-independent.

Do not force Prusa artifacts through JSON-specific helpers if the real format is not JSON.

---

# 48. Evidence Priority

Use:

```text id="o5ey7l"
1. actual GUI import behavior
2. actual GUI re-export
3. original real export
4. official Prusa behavior/documentation if needed
5. similarity to other slicers
```

Real behavior overrides assumptions from shared ancestry.

---

# 49. Acceptance Criteria

P7.6-A is complete when:

```text id="xlcc3q"
[ ] exact PrusaSlicer version recorded
[ ] real custom filament preset obtained
[ ] original artifact preserved
[ ] SHA-256 recorded
[ ] actual container format established
[ ] actual import unit established
[ ] bundle semantics established if applicable
[ ] baseline import succeeds
[ ] minimal dynamic experiment matrix generated
[ ] GUI results recorded
[ ] selected successful variants re-exported
[ ] semantic round-trip analysis completed
[ ] visible-name semantics established
[ ] new-vs-overwrite semantics sufficiently established
[ ] native identity behavior sufficiently established
[ ] inheritance behavior established where applicable
[ ] parameter preservation checked
[ ] pm_method_version behavior classified
[ ] Artifact abstraction assessed
[ ] P7.6-B canonicalization rules proposed
[ ] P7.6-B validation rules proposed
[ ] P7.6-B UnifiedDiff approach proposed
[ ] no production processor implemented
[ ] final readiness classification produced
```

---

# 50. Completion Report

Create:

```text id="h8qxnl"
p7.6-A_completion_report.md
```

Report:

1. exact PrusaSlicer version;
2. source artifact provenance;
3. original filename, size and SHA-256;
4. actual file/container format;
5. actual import unit;
6. whether the artifact contains one or multiple profiles;
7. bundle semantics, if applicable;
8. supported preset type;
9. important structural elements;
10. comparison with BambuStudio;
11. comparison with OrcaSlicer;
12. comparison with CrealityPrint;
13. comparison with ElegooSlicer;
14. visible-name candidate mechanism;
15. identity candidates;
16. inheritance representation;
17. baseline GUI result;
18. generated experiment matrix;
19. name-only result;
20. native-ID experiment results;
21. new-vs-overwrite behavior;
22. inheritance experiment result;
23. `pm_method_version` result;
24. selected re-export results;
25. semantic round-trip mutations;
26. serialization-only round-trip changes;
27. material/printing parameter preservation;
28. final visible-name semantics;
29. final preset identity semantics;
30. final inheritance semantics;
31. native identity fields/components Worker should preserve;
32. native identity fields/components Worker must modify;
33. native identity fields/components Worker must not synthesize;
34. proposed P7.6-B canonicalization rules;
35. proposed source-validation rules;
36. proposed UnifiedDiff strategy;
37. Artifact sufficiency classification;
38. any generic architecture incompatibility;
39. fixture sanitization;
40. final readiness classification.

---

# 51. Final Classification

Use exactly one:

```text id="qfvjtr"
READY_FOR_PROCESSOR
ARCHITECTURE_CHANGE_REQUIRED
INSUFFICIENT_EVIDENCE
```

`READY_FOR_PROCESSOR` requires enough real evidence to implement `PrusaSlicerProcessor` without guessing about identity or Artifact semantics.

---

# 52. Required End State

A successful P7.6-A ends conceptually as:

```text id="qsg6b5"
P7.6-A complete.

PrusaSlicer <version> real filament-preset artifact semantics
have been characterized through export/import/round-trip testing.

Artifact:
SUFFICIENT

Processor readiness:
READY_FOR_PROCESSOR

Production PrusaSlicer support has NOT been implemented.
```