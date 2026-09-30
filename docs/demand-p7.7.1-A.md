# P7.7.1-A — CREATE Initial Review Diff

## 0. Goal

Change CREATE candidate enrichment so a newly created preset produces a meaningful review `UnifiedDiff` instead of `UnifiedDiff.empty()`.

Current behavior:

```text
CREATE
    canonical artifact = complete initial snapshot
    diff               = empty UnifiedDiff
```

Target behavior:

```text
CREATE
    canonical artifact = complete initial snapshot
    diff               = initial review diff

initial review diff
    =
all canonical semantic fields represented as ADDED changes
```

This allows reviewers to inspect important parameters of a new preset using the same diff model used for UPDATE.

The canonical artifact remains the authoritative version snapshot.

The CREATE diff is derived review information.

---

# 1. Core Semantic Rule

Freeze the following model:

```text
CREATE:
    canonical artifact
        = authoritative initial snapshot

    UnifiedDiff
        = review projection of the initial snapshot

UPDATE:
    canonical artifact
        = authoritative new snapshot

    UnifiedDiff
        = review projection of base → candidate
```

Do not treat diff as authoritative version state.

---

# 2. CREATE Still Has No Base Version

This phase must NOT create or simulate a database base version.

For CREATE retain:

```text
operation = CREATE

base_version_id = ""
base_version_record_id = None
base_version_no_text = ""
```

No `PresetVersion v0` exists.

No empty artifact is persisted.

No synthetic base record is created.

---

# 3. `None` Base Semantics

At the processor diff boundary define:

```python
processor.diff(
    base=None,
    candidate=canonical_artifact,
)
```

to mean:

> Produce the initial review representation of this newly created canonical artifact.

It does NOT mean:

> A real empty preset existed before this preset.

This distinction must be documented.

---

# 4. Target CREATE Diff

For every semantic field in the canonical artifact, produce conceptually:

```text
type = ADDED
path = <processor-defined semantic path>
old = missing
new = <canonical value>
category = <processor classification>
```

Use the existing `UnifiedDiff` representation exactly.

Do not create a second CREATE-specific persisted diff schema.

---

# 5. Preserve UnifiedDiff v1

Persist using the existing canonical format:

```json
{
  "schema_version": 1,
  "changes": [...]
}
```

Do not change `schema_version`.

Do not reintroduce the legacy:

```json
{
  "added": [],
  "removed": [],
  "modified": []
}
```

format.

---

# 6. All Fields, Not Only Important Fields

Worker must generate the complete semantic CREATE diff.

Do NOT filter the persisted diff to only:

```text
IMPORTANT_PARAMETER
```

Preserve:

```text
IMPORTANT_PARAMETER
OTHER_PARAMETER
SYSTEM_METADATA
```

The frontend may later decide what to emphasize or collapse.

Worker must not destroy information for presentation convenience.

---

# 7. Why Full CREATE Diff

Desired future review UI:

```text
New Preset

Important Parameters
    nozzle temperature
    bed temperature
    flow ratio
    max volumetric speed
    ...

Other Parameters
    [collapsed]

System Metadata
    [collapsed]
```

The Worker should provide enough structured data for this without requiring the frontend to parse the canonical artifact.

---

# 8. Processor Owns Semantic Enumeration

Generic enrichment must NOT inspect the artifact to enumerate fields.

Do NOT add generic logic such as:

```python
json.loads(candidate.content)
```

or:

```python
configparser(...)
```

in enrichment.

The processor owns:

```text
artifact parsing
semantic paths
field enumeration
field classification
missing-value semantics
```

Generic workflow only calls:

```python
processor.diff(None, canonical_artifact)
```

---

# 9. Audit Before Enabling

Before changing generic CREATE enrichment, audit all production processors:

```text
BambuStudioProcessor
OrcaSlicerProcessor
SnapmakerOrcaSlicerProcessor
CrealityPrintProcessor
ElegooSlicerProcessor
PrusaSlicerProcessor
```

Also inspect the fake non-JSON processor used for architecture regression.

Determine current `base=None` behavior for each.

Do not assume all implementations already behave consistently.

---

# 10. Processor Contract

Update/document the processor diff contract so conceptually:

```python
def diff(
    base: Artifact | None,
    candidate: Artifact,
) -> UnifiedDiff:
    ...
```

means:

```text
base is Artifact
    → ordinary UPDATE semantic diff

base is None
    → CREATE initial review diff
```

If the existing type signature already permits this, do not redesign it unnecessarily.

---

# 11. BambuStudio

For CREATE:

```text
base=None
candidate=canonical Bambu artifact
```

produce ADDED changes for all canonical semantic fields.

Use existing Bambu semantic paths and classification rules.

Do not introduce generic JSON field classification.

---

# 12. Upstream OrcaSlicer

For CREATE, use the existing Orca-compatible semantic diff logic.

Every canonical semantic field must appear as ADDED.

Preserve existing category classification.

---

# 13. Snapmaker OrcaSlicer

Snapmaker must support the same `base=None` contract.

Shared mechanics may live in:

```text
OrcaCompatibleCore
```

where appropriate.

Do not merge Snapmaker and upstream business identities.

---

# 14. CrealityPrint

For CREATE:

```text
base=None
```

must produce complete canonical semantic ADDED changes using Creality-specific classification.

Preserve unknown fields.

---

# 15. ElegooSlicer

Likewise produce complete initial ADDED changes using Elegoo-specific semantics.

Do not infer behavior merely from format similarity.

---

# 16. PrusaSlicer

Prusa requires special attention because semantic identity includes:

```text
Artifact.filename
```

For CREATE, initial review diff must include the canonical filename identity.

Conceptually:

```text
path = "$artifact.filename"
type = ADDED
old = missing
new = "<pi_code> @<printer>.ini"
category = SYSTEM_METADATA
```

The canonical INI semantic fields must also appear as ADDED changes.

Do not invent an internal `name`.

---

# 17. Filename Semantics Are Processor-Owned

Only processors for which filename is semantically meaningful should expose filename in their semantic diff.

Do not generically add:

```text
$artifact.filename
```

for every slicer merely because `Artifact` contains a filename.

Prusa already has evidence that filename is semantic.

Other processors retain their existing processor-specific behavior.

---

# 18. Missing vs Null

Use the existing `UnifiedDiff` missing-value representation.

CREATE:

```text
field absent
```

is not a change.

A canonical field whose value is explicitly:

```text
null
```

is an ADDED field with a null value if the processor's semantic model distinguishes this.

Do not collapse:

```text
missing
null
""
0
false
```

---

# 19. Nested Structures

For JSON-based processors, preserve existing semantic diff granularity.

If current UPDATE diff recursively emits leaf paths, CREATE must use the same path model.

Do not introduce a different CREATE-only path convention.

Example conceptually:

```text
foo.bar
foo.baz
```

rather than an arbitrary whole-object change if UPDATE already works at leaf level.

---

# 20. Arrays

Use the existing processor's UPDATE diff semantics for arrays.

CREATE must not invent a new array representation.

If an array is treated as one semantic value during UPDATE, treat it the same way during CREATE.

---

# 21. Empty Structures

Follow existing semantic diff behavior for:

```text
{}
[]
""
null
```

Document any case where an empty but explicitly present value does or does not generate an ADDED change.

Consistency with UPDATE semantics is more important than maximizing row count.

---

# 22. Classification

Every CREATE change must receive a valid:

```text
DiffCategory
```

using processor-specific rules.

Unknown fields must default to:

```text
OTHER_PARAMETER
```

unless an existing processor rule explicitly classifies them otherwise.

---

# 23. Important Parameters

Existing slicer-specific important-parameter classification remains authoritative.

Do not create a universal parameter ontology in this phase.

For example, if different slicers use different native paths for nozzle temperature, their processors remain responsible for classification.

---

# 24. System Metadata

Existing processor-specific metadata classification remains authoritative.

Typical examples may include:

```text
name
pm_method_version
native identity metadata
inheritance metadata
Prusa filename identity
```

Use actual existing classification rules.

Do not blindly classify all ID-like fields as metadata.

---

# 25. Candidate Enrichment Change

Current conceptual CREATE path:

```python
if operation == CREATE:
    diff = UnifiedDiff.empty()
```

must become conceptually:

```python
if operation == CREATE:
    diff = processor.diff(
        base=None,
        candidate=canonical_artifact,
    )
```

Use actual project interfaces/naming.

Do not duplicate processor parsing in enrichment.

---

# 26. UPDATE Must Remain Unchanged

Existing UPDATE behavior remains:

```text
resolve current version
load base canonical artifact
canonicalize candidate
processor.diff(base, candidate)
```

P7.7.1-A must not change UPDATE semantics.

---

# 27. Base Metadata Remains Empty for CREATE

Even though CREATE now has non-empty diff:

```text
base_version_id
base_version_record_id
base_version_no_text
```

must remain empty/None exactly as before.

A non-empty CREATE diff must not trick generic workflow into believing a base version exists.

---

# 28. Operation Remains CREATE

Do not infer operation from whether diff is empty.

This becomes especially important after this change.

Operation is determined from preset identity/existence exactly as before.

---

# 29. Empty CREATE Artifact Edge Case

A structurally valid artifact containing no semantic fields is probably impossible for supported production slicers.

Nevertheless:

```text
CREATE + empty UnifiedDiff
```

must not automatically change operation or fail solely because the diff is empty.

Artifact validation remains processor-owned.

---

# 30. Persistence

Persist the CREATE UnifiedDiff through the existing serialization path.

Expected shape:

```json
{
  "schema_version": 1,
  "changes": [
    ...
  ]
}
```

No special CREATE wrapper is required.

Operation remains available separately on Submission.

---

# 31. No New Diff Schema

Do NOT add:

```text
create_changes
initial_fields
initial_diff
snapshot_diff
```

or another persisted field.

Use existing:

```text
Submission.diff
```

and existing UnifiedDiff.

---

# 32. Historical Rows

Do not rewrite historical CREATE submissions that already contain:

```json
{
  "schema_version": 1,
  "changes": []
}
```

unless an explicit migration is separately requested.

Old CREATE rows may remain empty.

Newly processed CREATE submissions use initial review diff.

Document this compatibility behavior.

---

# 33. Reprocessing / Idempotency

If a DRAFT/PREVIEW candidate is processed repeatedly without source/context changes, CREATE diff output must remain deterministic.

Same canonical artifact must produce semantically identical UnifiedDiff and stable ordering.

---

# 34. READY_FOR_REVIEW Freeze

Existing freeze semantics remain unchanged.

Once the candidate reaches:

```text
READY_FOR_REVIEW
```

the persisted CREATE diff is part of the frozen review candidate.

Do not recompute it from a later slicer state.

---

# 35. Publication

Publication must not depend on CREATE diff content.

CREATE publication continues using:

```text
canonical artifact
preset identity
review state
publication guards
```

Diff remains review metadata.

Do not reconstruct the published artifact from diff.

---

# 36. Version Snapshot

For the first published version:

```text
PresetVersion v1
```

the canonical artifact remains the authoritative initial state.

The CREATE diff is not required to reconstruct v1.

---

# 37. Fake Non-JSON Processor

Update the fake non-JSON processor contract/test if necessary so:

```text
base=None
```

also produces a meaningful initial diff.

This protects the architectural principle that CREATE diff generation is processor-driven and not JSON-driven.

Do not make the fake processor parse JSON merely to satisfy the new test.

---

# 38. Required Generic CREATE Test

Update the existing CREATE workflow test that currently expects empty diff.

Instead assert:

```text
operation == CREATE

base_version_id == ""
base_version_record_id is None
base_version_no_text == ""

diff is non-empty
all expected initial semantic changes are ADDED
```

Use a representative production processor fixture.

---

# 39. Required Generic UPDATE Regression

Existing UPDATE test must continue proving:

```text
operation == UPDATE
base resolved
processor.diff(base, candidate) used
normal MODIFIED/ADDED/REMOVED behavior preserved
```

---

# 40. Required Bambu CREATE Test

Using a real/fidelity Bambu canonical artifact:

verify representative canonical fields become:

```text
ADDED
```

with correct categories.

Also verify unknown fields are represented rather than silently dropped.

---

# 41. Required Orca CREATE Test

Verify:

```text
name
pm_method_version
important material fields
unknown fields
```

appear in the initial review diff with correct semantics/categories.

---

# 42. Required Snapmaker CREATE Test

Verify at minimum:

```text
name
pm_method_version
inherits = Snapmaker PLA
representative material parameters
unknown field
```

are represented.

Business identity remains Snapmaker-specific.

---

# 43. Required Creality CREATE Test

Verify representative:

```text
name
pm_method_version
filament_settings_id
base_id if present
inherits
material parameters
unknown field
```

are represented according to existing classification rules.

Do not mutate those fields merely for diff generation.

---

# 44. Required Elegoo CREATE Test

Verify representative identity, metadata, material parameters and unknown fields are represented as ADDED according to existing semantics.

---

# 45. Required Prusa CREATE Test

Mandatory.

Verify CREATE initial diff contains:

```text
$artifact.filename
```

as ADDED with the canonical filename.

Also verify representative INI semantic fields appear as ADDED.

Assert no synthetic internal:

```text
name
```

is introduced.

---

# 46. Missing / Null / Empty Tests

Add focused regression coverage for the processor models where applicable:

```text
explicit null
empty string
false
0
empty array
empty object
```

Ensure CREATE semantics remain consistent with each processor's UPDATE diff behavior.

Do not create artificial cases unsupported by the actual artifact format.

---

# 47. Stable Ordering Test

For each shared diff implementation at minimum, verify:

```text
processor.diff(None, candidate)
```

produces deterministic ordering.

Repeated calls must serialize identically.

---

# 48. Category Coverage Test

At least one CREATE fixture should demonstrate all available categories where naturally present:

```text
IMPORTANT_PARAMETER
OTHER_PARAMETER
SYSTEM_METADATA
```

Do not fabricate meaningless fields solely to force category coverage.

---

# 49. No Generic Artifact Parsing Regression

Add or retain an architectural regression proving generic enrichment does not:

```text
JSON.parse
json.loads
INI parse
inspect filename semantics
enumerate artifact fields
classify parameter paths
```

CREATE must remain as opaque as UPDATE.

---

# 50. No Slicer-Specific Generic Branches

Search generic workflow/enrichment code for new branches equivalent to:

```python
if slicer == "PrusaSlicer":
    ...
elif slicer == "OrcaSlicer":
    ...
```

There should be none.

Processor dispatch remains registry-based.

---

# 51. No Frontend Changes

P7.7.1-A does NOT modify Miaoda/client rendering.

The frontend currently has a known compatibility bug with UnifiedDiff v1.

That is intentionally handled in:

```text
P7.7.1-B
```

Do not mix frontend rendering changes into this Worker phase.

---

# 52. Important Transitional Warning

After P7.7.1-A, new CREATE submissions may persist non-empty:

```json
{
  "schema_version": 1,
  "changes": [...]
}
```

while the current frontend may still incorrectly render them as empty.

Therefore P7.7.1-A and P7.7.1-B should be deployed together, or frontend compatibility must land before the Worker CREATE behavior is enabled in production.

Document this deployment dependency prominently.

---

# 53. Acceptance Criteria

P7.7.1-A is complete when:

```text
[ ] processor diff contract documents base=None semantics
[ ] all six production processors audited
[ ] all six support CREATE initial review diff
[ ] fake non-JSON processor remains compatible
[ ] generic CREATE calls processor.diff(None, canonical)
[ ] CREATE no longer intentionally uses UnifiedDiff.empty()
[ ] CREATE operation detection unchanged
[ ] CREATE base_version fields remain empty
[ ] canonical artifact remains authoritative snapshot
[ ] all canonical semantic fields are available to CREATE diff
[ ] changes use ADDED semantics
[ ] existing categories are preserved
[ ] unknown fields are not silently dropped
[ ] Prusa filename identity is represented
[ ] Prusa synthetic name is not introduced
[ ] UPDATE behavior unchanged
[ ] diff persistence remains UnifiedDiff schema_version=1
[ ] historical rows require no migration
[ ] repeated CREATE diff is deterministic
[ ] generic workflow remains artifact-opaque
[ ] no slicer-specific generic branch added
[ ] publication behavior unchanged
[ ] full Worker test suite passes
```

---

# 54. Completion Report

Create:

```text
p7.7.1-A_create_initial_review_diff_report.md
```

Report:

1. previous CREATE diff behavior;
2. new CREATE diff semantics;
3. authoritative snapshot vs derived diff distinction;
4. processor contract change/documentation;
5. Bambu `base=None` audit result;
6. upstream Orca audit result;
7. Snapmaker Orca audit result;
8. Creality audit result;
9. Elegoo audit result;
10. Prusa audit result;
11. fake non-JSON audit result;
12. generic enrichment change;
13. base-version behavior;
14. operation behavior;
15. persisted schema;
16. ADDED semantics;
17. missing/null/empty semantics;
18. category behavior;
19. unknown-field behavior;
20. Bambu CREATE test result;
21. Orca CREATE test result;
22. Snapmaker CREATE test result;
23. Creality CREATE test result;
24. Elegoo CREATE test result;
25. Prusa CREATE test result;
26. Prusa filename result;
27. fake non-JSON regression result;
28. generic CREATE integration result;
29. generic UPDATE regression result;
30. stable-ordering result;
31. generic opacity regression result;
32. slicer-specific leakage check;
33. historical-data compatibility;
34. publication regression result;
35. full Worker test-suite result;
36. files changed;
37. deployment dependency on P7.7.1-B;
38. known limitations;
39. final status.

Final status:

```text
READY_FOR_FRONTEND_INTEGRATION
PARTIALLY_COMPLETE
NOT_READY
```

---

# 55. Expected End State

```text
CREATE
    │
    ├─ canonical artifact
    │      authoritative initial snapshot
    │
    ├─ base version
    │      NONE
    │
    └─ UnifiedDiff
           processor.diff(None, canonical)
                    │
                    ├─ ADDED / IMPORTANT_PARAMETER
                    ├─ ADDED / OTHER_PARAMETER
                    └─ ADDED / SYSTEM_METADATA


UPDATE
    │
    ├─ canonical artifact
    │      authoritative new snapshot
    │
    ├─ base version
    │      current version
    │
    └─ UnifiedDiff
           processor.diff(base, canonical)
                    │
                    ├─ ADDED
                    ├─ REMOVED
                    └─ MODIFIED
```

The generic workflow remains unaware of JSON, INI, filenames, parameter names, and slicer-specific review semantics.