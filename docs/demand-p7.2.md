# P7.2 — Unified Slicer-Neutral Diff Model

## 0. Goal

Formalize the diff boundary introduced in P7.0/P7.1 into a stable, slicer-neutral contract.

After P7.2:

```text id="hytgx4"
base Artifact
candidate Artifact
        ↓
SlicerProcessor.diff()
        ↓
UnifiedDiff
        ↓
Workflow / Storage / Miaoda / Reviewer
```

Everything above the processor must understand only `UnifiedDiff`.

It must not know:

```text id="3a92fo"
JSON paths
BambuStudio field semantics
BambuStudio important-field lists
how artifacts are parsed
how values are compared
```

P7.2 supports BambuStudio only.

Do NOT add another slicer.

---

# 1. Core Principle

Each slicer processor owns:

```text id="lyrt66"
artifact interpretation
semantic comparison
field/path extraction
change classification
slicer-specific parameter knowledge
```

The generic application owns:

```text id="qtdgvz"
displaying changes
persisting diff result
grouping by generic category
counting changes
transporting diff between Worker and UI
```

Therefore:

> Processor decides what changed and what the change means structurally.

> UI decides how a generic change is presented.

---

# 2. Define UnifiedDiff

Introduce an explicit immutable model.

Conceptually:

```python id="0j29u6"
@dataclass(frozen=True)
class UnifiedDiff:
    changes: tuple[DiffChange, ...]
```

Adapt exact Python typing/style to the existing project.

Do not expose slicer-specific parsed objects.

---

# 3. Define DiffChange

Conceptually:

```python id="rw2n6d"
@dataclass(frozen=True)
class DiffChange:
    path: str
    change_type: ChangeType
    category: DiffCategory
    old_value: object | None
    new_value: object | None
```

The exact serialization representation may differ, but these semantics must exist.

---

# 4. ChangeType

Define a stable enum/value set:

```text id="gixq5u"
ADDED
REMOVED
MODIFIED
```

Do not use arbitrary free-form strings produced by each processor.

Meaning:

```text id="sgq8jp"
ADDED
old absent
new present

REMOVED
old present
new absent

MODIFIED
old present
new present
values differ
```

---

# 5. Distinguish Missing From Null

Do not infer existence solely from:

```python id="mce2kx"
old_value is None
```

because a slicer artifact may legitimately contain:

```json id="r2u4hl"
{
  "parameter": null
}
```

Processor/diff implementation must distinguish:

```text id="r0dy9k"
field absent
```

from:

```text id="fzszca"
field present with null value
```

Use an internal sentinel or explicit presence information where necessary.

Serialized UnifiedDiff does not need to expose the sentinel.

---

# 6. DiffCategory

Formalize the existing categories:

```text id="a89n50"
IMPORTANT_PARAMETER
OTHER_PARAMETER
SYSTEM_METADATA
```

These are UI/business categories, not Bambu field names.

Every change must belong to exactly one category.

---

# 7. Unknown Fields

Default rule:

```text id="i6k1md"
unknown changed field
→ OTHER_PARAMETER
```

Never silently omit a changed field because it is unknown.

This is mandatory.

Completeness is more important than perfect categorization.

---

# 8. Processor Owns Classification

Generic workflow must not contain logic such as:

```python id="hxbn3p"
if path in IMPORTANT_BAMBU_FIELDS:
    ...
```

BambuStudioProcessor or its Bambu-specific diff helper owns the mapping:

```text id="ukomc7"
Bambu field/path
→ generic DiffCategory
```

Future slicers will define their own mappings.

---

# 9. SYSTEM_METADATA

Preserve existing BambuStudio system-metadata classification behavior.

Examples may include existing metadata fields already treated this way.

Do not expand or redefine the list merely as part of P7.2.

The goal is behavioral preservation.

---

# 10. IMPORTANT_PARAMETER

Preserve the current approved BambuStudio important-parameter classification.

Do not use P7.2 to redesign which printing parameters are considered important.

That is a product decision outside this refactor.

---

# 11. OTHER_PARAMETER

All remaining changed fields that are neither:

```text id="g54ab4"
IMPORTANT_PARAMETER
SYSTEM_METADATA
```

must appear as:

```text id="2t0pvj"
OTHER_PARAMETER
```

---

# 12. Path Semantics

`DiffChange.path` must be stable and processor-defined.

For BambuStudio JSON, preserve the existing path representation where practical.

Examples conceptually:

```text id="c3rpxu"
nozzle_temperature
filament_retraction_length
some_nested.field
```

Do not redesign paths merely for aesthetics.

---

# 13. Path Is an Opaque Identifier to Workflow

Workflow/UI may:

```text id="6w86gx"
display path
sort by path if required
use path as rendering key together with change identity
```

but must not interpret path semantics.

Do not write generic logic like:

```python id="vtmgk9"
if path.startswith("filament_"):
```

outside the processor.

---

# 14. Values Must Be Transport-Safe

`old_value` and `new_value` must be representable in the existing persisted/API diff format.

For BambuStudio this will generally include:

```text id="k82dmz"
string
number
boolean
null
list
dict/object
```

Do not leak arbitrary Python processor objects into UnifiedDiff.

---

# 15. Preserve Native Semantic Values

Where practical, preserve values as semantic values.

Example:

```text id="dhnhtd"
old_value = 0.95
new_value = 0.98
```

Prefer this over:

```text id="zggvnf"
old_value = "0.95"
new_value = "0.98"
```

if the parsed artifact actually represents them numerically.

Do not stringify everything merely for UI convenience.

---

# 16. No Display Formatting in Processor

Processor should not produce UI strings such as:

```text id="e6hzpy"
"0.95 → 0.98"
"Added: 20"
"Removed"
```

It should return structured data.

Formatting belongs to UI/presentation.

---

# 17. Deterministic Ordering

UnifiedDiff output ordering must be deterministic.

The same:

```text id="em72yx"
base Artifact
candidate Artifact
```

must produce changes in the same order every time.

For BambuStudio, use a stable deterministic ordering appropriate to the existing behavior.

If current behavior already defines ordering, preserve it.

Otherwise use a simple stable rule such as path ordering.

Document the rule.

---

# 18. Deterministic Diff

Given identical:

```text id="ewh8sh"
processor
base Artifact
candidate Artifact
ProcessingContext
```

the serialized UnifiedDiff must be identical.

No dependence on:

```text id="gve7xq"
timestamp
database order
set iteration
randomness
Worker retry
```

---

# 19. Empty Diff

Semantically identical artifacts must produce:

```python id="csygmg"
UnifiedDiff(changes=())
```

or equivalent empty representation.

Do not introduce:

```text id="4njd0x"
NO_CHANGE
```

workflow status.

Preserve existing Submission lifecycle behavior.

---

# 20. Added Field

For:

```text id="47rz9r"
base:
field absent

candidate:
field = X
```

produce exactly one:

```text id="ljc7xc"
ADDED
```

change.

---

# 21. Removed Field

For:

```text id="18fjw4"
base:
field = X

candidate:
field absent
```

produce exactly one:

```text id="9rlfmk"
REMOVED
```

change.

---

# 22. Modified Field

For:

```text id="kvtq4m"
base:
field = X

candidate:
field = Y
```

produce exactly one:

```text id="5oxr56"
MODIFIED
```

change where appropriate according to existing Bambu diff semantics.

---

# 23. Nested Structures

Preserve existing BambuStudio behavior for nested structures.

Do not arbitrarily change:

```text id="2grgyx"
whole-object comparison
vs
recursive leaf comparison
```

during P7.2.

First lock current behavior with tests.

If current behavior is inconsistent or clearly defective, report it rather than silently redesigning it.

---

# 24. Arrays / Lists

Likewise preserve existing semantics for lists/arrays.

Do not introduce complex:

```text id="kh6l0a"
LCS
move detection
set semantics
```

unless already implemented.

For P7.2 the goal is stable contract, not advanced diff algorithms.

---

# 25. Bambu-Specific Diff Implementation

Move/keep all Bambu-specific diff logic under the Bambu slicer implementation boundary.

Conceptually:

```text id="34h7b8"
slicers/
└── bambu_studio/
    └── diff
```

or equivalent current organization.

Generic services must not know Bambu field classifications.

---

# 26. Processor Contract

Formalize:

```python id="kmig5v"
def diff(
    self,
    base: Artifact,
    candidate: Artifact,
    context: ProcessingContext,
) -> UnifiedDiff:
    ...
```

If `context` is not required by Bambu diff today, retain it only if useful for stable future contract consistency.

Do not force workflow to parse artifacts before calling this method.

---

# 27. CREATE Semantics

CREATE has no base artifact.

Do not generate a fake diff such as:

```text id="4ak9hy"
empty document
→ candidate
```

Preserve current product behavior:

```text id="q5x1b2"
CREATE
→ candidate summary
→ canonical artifact
→ no fake base diff
```

`processor.diff()` need not be called for CREATE unless an existing internal reason requires it.

---

# 28. UPDATE Semantics

For UPDATE:

```text id="l9vixk"
base_version.canonical artifact
+
candidate canonical artifact
        ↓
processor.diff()
        ↓
UnifiedDiff
```

This is the authoritative diff shown in Preview/Review.

---

# 29. Preview

M1 Preview must consume serialized/persisted UnifiedDiff without Bambu-specific interpretation.

Preserve current groups:

```text id="8dnvhi"
Important Parameters
Other Parameters
System Metadata
```

Preserve existing expand/collapse behavior.

---

# 30. Reviewer Workspace

M3 must consume the same UnifiedDiff contract.

Do not maintain a separate reviewer-specific diff implementation.

The exact same change set produced by Worker must be reviewable in M3.

---

# 31. Single Authoritative Diff

Do not recompute semantic diff in Miaoda.

The Worker processor remains authoritative.

Flow:

```text id="jq7fup"
Worker
→ UnifiedDiff
→ persisted diff
→ M1/M3 rendering
```

Frontend may group/sort for presentation but must not determine what changed.

---

# 32. Persistence Format

Define an explicit serialized representation for UnifiedDiff.

Conceptually:

```json id="5pj4bf"
{
  "schema_version": 1,
  "changes": [
    {
      "path": "flow_ratio",
      "change_type": "MODIFIED",
      "category": "IMPORTANT_PARAMETER",
      "old_value": 0.95,
      "new_value": 0.98
    }
  ]
}
```

Use existing field/storage mechanism where possible.

Do not add a new Bitable field solely for P7.2 unless required.

---

# 33. Diff Schema Version

Add a small explicit:

```text id="sfqqm1"
schema_version
```

to the serialized UnifiedDiff representation if the current persisted diff format can safely accommodate it.

Start with:

```text id="2np72g"
1
```

This versions the **generic diff representation**, not the slicer.

Do NOT use:

```text id="94anqf"
Bambu version
processor version
pm_method_version
```

as the diff schema version.

If adding `schema_version` would break existing UI/storage compatibility, document the issue and preserve compatibility first.

---

# 34. Serialization Ownership

UnifiedDiff serialization should be generic infrastructure.

Do not make:

```text id="pc8qwy"
BambuStudioProcessor
```

responsible for producing the final JSON string stored in Submission.

Processor returns:

```text id="hjd9gj"
UnifiedDiff
```

Generic infrastructure serializes it.

This is different from canonical artifact serialization, which remains processor-owned.

---

# 35. Deserialization

Provide a generic deserializer if persisted diff is read back into application models.

It must validate:

```text id="6p3gl5"
schema structure
known change_type
known category
required fields
```

Do not silently accept arbitrary malformed diff structures.

---

# 36. Existing Historical Diff Compatibility

Inspect existing Submission diff data.

If historical records use the current format, do NOT require migration merely for P7.2 unless necessary.

Prefer:

```text id="0rw83x"
reader supports legacy representation
new writer emits v1 representation
```

if a compatibility layer is needed.

Do not rewrite historical Submission records unnecessarily.

---

# 37. UI Compatibility

Before changing persisted diff representation, inspect how Miaoda currently consumes it.

P7.2 must not accidentally break:

```text id="scc18a"
M1 Preview
M2 Submission detail
M3 Reviewer Workspace
```

If they consume raw JSON directly, preserve or deliberately adapt the API representation.

---

# 38. No UI Knowledge in Diff Model

UnifiedDiff must not contain fields like:

```text id="aj4td2"
expanded
collapsed
color
icon
display_order_css
reviewer_highlight
```

Those belong to presentation.

---

# 39. Optional Display Metadata

Do NOT add generic display labels in P7.2 unless already required by current UI.

For now:

```text id="k0x23z"
path
category
old/new
change_type
```

should remain the stable core.

Future slicers may motivate:

```text id="70iz99"
display_name
unit
```

but do not predict that requirement prematurely.

---

# 40. Fake Processor Contract Test

Reuse the P7.1 fake non-JSON processor.

Make it return a deterministic UnifiedDiff.

Example conceptually:

```text id="2j2ovz"
path = "fake.parameter"
MODIFIED
OTHER_PARAMETER
old = "A"
new = "B"
```

Generic workflow must persist and transport this without knowing the artifact format.

---

# 41. Cross-Format Independence Test

Fake processor:

```text id="9jz8vo"
base = arbitrary non-JSON bytes
candidate = different arbitrary non-JSON bytes
```

returns UnifiedDiff.

Expected:

```text id="25y68s"
workflow stores generic diff
UI/API representation is slicer-neutral
no JSON artifact parsing occurs
```

---

# 42. Contract Tests

Extend reusable processor contract tests.

Every processor must demonstrate:

```text id="2onqce"
diff returns UnifiedDiff
changes use known ChangeType
changes use known DiffCategory
ordering deterministic
same input → same diff
identical semantic artifacts → empty diff
added change represented
removed change represented
modified change represented
unknown changed field not dropped
values are transport-safe
```

For P7.2, run against BambuStudioProcessor.

---

# 43. Golden Bambu Diff

Use representative real Bambu fixtures.

Lock current approved behavior for:

```text id="1hqtlw"
important parameter modification
other parameter modification
system metadata modification
unknown field modification
added field
removed field
```

Verify exact:

```text id="ciz2cp"
path
change_type
category
old_value
new_value
```

---

# 44. Unknown Field Regression

Mandatory:

```text id="tyxf2k"
base:
unknown_future_field = A

candidate:
unknown_future_field = B
```

Expected:

```text id="8eq1i8"
one MODIFIED change
category = OTHER_PARAMETER
```

The change must not disappear.

---

# 45. Null Regression

Mandatory:

Case A:

```text id="c10qpm"
absent → null
```

must be distinguishable from no change.

Case B:

```text id="dxr6km"
null → absent
```

must also be distinguishable.

Case C:

```text id="fsqkkz"
null → null
```

must produce no change.

---

# 46. Determinism Regression

Run the same diff multiple times.

Serialized result must be identical.

This includes change ordering.

---

# 47. Retry Stability

Worker retry of the same Submission/base/candidate must persist equivalent diff.

Retry must not reorder changes or change classifications.

---

# 48. No Workflow Field Classification

Search generic runtime code for:

```text id="s14gax"
IMPORTANT_PARAMETER
SYSTEM_METADATA
Bambu-specific parameter names
field classification tables
```

Generic code may know enum category values for storage/presentation.

It must not know which slicer field belongs to which category.

---

# 49. No Frontend Semantic Diff

Confirm Miaoda does not:

```text id="8fx9h0"
compare base/candidate itself
classify fields itself
drop unknown fields
reinterpret ADDED/REMOVED/MODIFIED
```

It renders Worker output.

---

# 50. Preserve Current Product Semantics

P7.2 must not change:

```text id="utff4z"
Submission status lifecycle
Preview lifecycle
CREATE/UPDATE resolution
base_version
base_version_no_text
VERSION_CONFLICT
review decisions
publication
version allocation
photo behavior
3MF behavior
canonical artifact behavior
download behavior
```

---

# 51. No New Slicer

Do NOT implement:

```text id="t3brm7"
OrcaSlicer
Cura
PrusaSlicer
```

in P7.2.

---

# 52. No Advanced Semantic Mapping

Do not attempt to map:

```text id="aq8w3u"
Bambu flow_ratio
↔
Cura flow
↔
Prusa extrusion multiplier
```

into a universal parameter vocabulary.

UnifiedDiff is a common **change representation**, not a universal preset ontology.

---

# 53. No Risk Scoring

Do not add:

```text id="ifpj34"
risk score
importance score
AI severity
automatic approval recommendation
```

Categories remain descriptive grouping only.

---

# 54. No Diff Suppression

Do not introduce broad ignore rules merely to reduce noise.

If existing Bambu behavior ignores specific fields intentionally, preserve and document those exact existing rules.

Otherwise, changed fields must remain visible.

---

# 55. Architecture After P7.2

Target:

```text id="9s0ux5"
                   Slicer Processor
                         │
                         │
                 base/candidate
                    Artifacts
                         │
                         ▼
                    UnifiedDiff
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
     Preview            M2             Reviewer
        │                │                │
        └──────── generic rendering ──────┘
```

No consumer above this boundary should need to know how the slicer represented the original parameters.

---

# Mandatory Automated Tests

At minimum:

```text id="f73wqj"
[ ] UnifiedDiff model exists

[ ] DiffChange model exists

[ ] ChangeType is constrained

[ ] DiffCategory is constrained

[ ] Bambu diff returns UnifiedDiff

[ ] identical artifacts produce empty diff

[ ] added field produces ADDED

[ ] removed field produces REMOVED

[ ] modified field produces MODIFIED

[ ] absent → null is represented

[ ] null → absent is represented

[ ] null → null produces no change

[ ] important Bambu field classification preserved

[ ] other Bambu field classification preserved

[ ] system metadata classification preserved

[ ] unknown changed field → OTHER_PARAMETER

[ ] unknown changed field is never dropped

[ ] deterministic ordering

[ ] repeated diff produces identical serialized result

[ ] fake non-JSON processor returns UnifiedDiff

[ ] generic workflow persists fake UnifiedDiff

[ ] Preview consumes generic diff

[ ] M2 consumes generic diff

[ ] M3 consumes generic diff

[ ] CREATE does not fabricate empty-base diff

[ ] UPDATE uses processor.diff(base Artifact, candidate Artifact)

[ ] workflow contains no slicer-specific field classification

[ ] frontend does not recompute semantic diff

[ ] historical diff compatibility preserved or explicitly handled
```

---

# Manual Acceptance

Use one real BambuStudio UPDATE containing changes in all three categories:

```text id="cf2b3z"
IMPORTANT_PARAMETER
OTHER_PARAMETER
SYSTEM_METADATA
```

plus at least one unknown field if practical.

Verify in M1 Preview:

```text id="43hdkj"
all expected changes visible
correct grouping
old/new values correct
no unexpected missing field
```

Submit and inspect the exact same Submission in M3.

Verify:

```text id="jsn9x4"
same changes
same values
same categories
same completeness
```

M1 and M3 must not disagree about the candidate.

---

# Out of Scope

Do NOT implement:

```text id="xazp65"
new slicers
universal parameter ontology
cross-slicer diff
cross-slicer conversion
risk scoring
AI classification
new diff UI design
advanced array diff
move detection
automatic conflict merge
new workflow statuses
Feishu artifact field rename
migration-script cleanup
```

---

# Acceptance Criteria

P7.2 is complete when:

```text id="n1ylm5"
[ ] processor diff boundary returns UnifiedDiff

[ ] workflow is slicer-neutral with respect to diff semantics

[ ] Bambu-specific classification lives inside Bambu implementation

[ ] unknown changes cannot silently disappear

[ ] missing and null are correctly distinguished

[ ] diff output is deterministic

[ ] persisted diff has a defined stable representation

[ ] M1/M2/M3 consume the same generic diff

[ ] Bambu existing behavior is preserved

[ ] fake non-JSON processor proves diff transport is artifact-format agnostic

[ ] CREATE behavior remains unchanged

[ ] UPDATE behavior remains unchanged

[ ] no new slicer support is introduced
```

# Completion Report

Report:

1. final `UnifiedDiff` model;
2. final `DiffChange` model;
3. final `ChangeType`;
4. final `DiffCategory`;
5. serialized diff representation;
6. schema-version decision;
7. historical diff compatibility strategy;
8. deterministic ordering rule;
9. missing-vs-null implementation;
10. Bambu IMPORTANT classification location;
11. Bambu OTHER classification behavior;
12. Bambu SYSTEM_METADATA classification location;
13. unknown-field fallback behavior;
14. added-field test;
15. removed-field test;
16. modified-field test;
17. null/missing tests;
18. deterministic serialization test;
19. fake non-JSON processor diff test;
20. Preview integration result;
21. M2 integration result;
22. M3 integration result;
23. golden Bambu diff regression result;
24. CREATE regression result;
25. UPDATE regression result;
26. full test-suite result;
27. remaining slicer-specific diff assumptions outside processors;
28. any limitations discovered that should be resolved before P7.3 OrcaSlicer.