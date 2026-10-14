# P7.3 — OrcaSlicer Processor Support

## 0. Goal

Add OrcaSlicer as the second production slicer supported by the Worker.

P7.3 is the first real validation of the architecture created in:

```text
P7.0 — Slicer Processor Contract
P7.1 — Opaque Artifact Boundary
P7.2 — Unified Diff Model
```

Target runtime architecture:

```text
                         Workflow
                            │
                  Submission.slicer
                            │
                            ▼
                 SlicerProcessorRegistry
                      │             │
                      ▼             ▼
             BambuStudio       OrcaSlicer
              Processor         Processor
                      │             │
                      └──────┬──────┘
                             ▼
                         Artifact
                       UnifiedDiff
                             │
                             ▼
                Existing workflow/review/
                    publication system
```

P7.3 must add OrcaSlicer without introducing Orca-specific logic into generic workflow, publication, review, or UI logic.

---

# 1. Success Criterion

The strongest architectural success criterion is:

> Adding OrcaSlicer should primarily consist of implementing and registering `OrcaSlicerProcessor`, adding Orca-specific fixtures/tests, and exposing the already-supported slicer option.

If significant changes are required in:

```text
enrichment workflow
publication
version allocation
review workflow
PresetVersion lifecycle
generic diff transport
```

stop and report the architectural blocker before implementing slicer-specific branches there.

Do not patch around a broken abstraction.

---

# 2. Supported Slicer Identifier

Use the exact existing canonical slicer identifier already used by Submission/UI for OrcaSlicer.

Do not introduce aliases casually such as:

```text
Orca
orca
orca-slicer
Orca Slicer
```

unless the existing system explicitly normalizes them.

There must be one authoritative runtime slicer ID.

---

# 3. Processor Registration

Register:

```text
OrcaSlicerProcessor
```

through the existing registry composition introduced in P7.1.

Conceptually:

```python
default_processor_registry():
    return SlicerProcessorRegistry([
        BambuStudioProcessor(),
        OrcaSlicerProcessor(),
    ])
```

Do not modify enrichment to special-case Orca.

---

# 4. Independent Processor Boundary

Implement OrcaSlicer as its own processor:

```text
OrcaSlicerProcessor
```

Do NOT implement:

```python
class OrcaSlicerProcessor(BambuStudioProcessor):
    ...
```

merely because the formats currently look similar.

BambuStudio and OrcaSlicer are separate supported slicers and may evolve independently.

---

# 5. Shared Helpers Are Allowed

If BambuStudio and OrcaSlicer genuinely share identical low-level behavior, extract small pure helpers where useful.

Examples might include:

```text
JSON decoding helper
deterministic JSON serialization
generic recursive JSON diff primitive
```

Only share behavior that is demonstrably format-independent.

Do NOT share:

```text
field allowlists
required-field rules
inheritance semantics
display-name assumptions
metadata classification
slicer identification
version compatibility rules
```

unless verified independently for both slicers.

---

# 6. No Bambu-as-Orca Assumption

Do not begin from:

```text
OrcaSlicer ≈ BambuStudio
therefore reuse all Bambu rules
```

Instead determine Orca behavior from:

```text
real OrcaSlicer exported presets
existing project requirements
actual import behavior
```

Similarity may reduce implementation work, but it is not evidence of semantic equivalence.

---

# 7. Real Orca Fixture Corpus First

Before finalizing validation/canonicalization rules, collect real OrcaSlicer exported filament/material preset files.

Create:

```text
tests/fixtures/slicers/orca_slicer/
├── valid/
├── invalid/
├── legacy/
└── edge_cases/
```

Use real exported files wherever possible.

Do not build the processor primarily around synthetic dictionaries.

---

# 8. Record Fixture Provenance

For each important real fixture, document at least:

```text
OrcaSlicer version
preset type
whether inherits is present
source: real export
expected import behavior
```

A small README or fixture metadata file is sufficient.

This will matter when OrcaSlicer changes its schema later.

---

# 9. Establish Actual Orca Export Structure

Before implementing rules, inspect representative OrcaSlicer exports and document:

```text
top-level structure
required fields
preset type identification
name behavior
inherits behavior
filament_settings_id behavior
version-related fields
printer compatibility fields
Orca-specific fields
unknown/additional fields
```

Do not assume Bambu semantics.

---

# 10. Validation

`OrcaSlicerProcessor.validate_source()` must determine whether the uploaded artifact is acceptable as an OrcaSlicer material/filament preset.

It must reject at minimum:

```text
malformed artifact
wrong top-level structure
clearly wrong preset type
missing fields that Orca actually requires for this workflow
```

Do not invent stricter validation than Orca itself requires without a business reason.

---

# 11. Wrong-Slicer Detection

Where reliably detectable, reject a clearly incompatible artifact uploaded under:

```text
Submission.slicer = OrcaSlicer
```

However:

> Do not claim certainty if BambuStudio and OrcaSlicer artifacts cannot always be reliably distinguished.

If an artifact is structurally valid for both, shared compatibility is acceptable.

Do not create fragile heuristics merely to distinguish brands.

---

# 12. Canonicalization

OrcaSlicer canonicalization must follow the same company-level business intent as BambuStudio:

```text
company identity
+
selected Submission metadata
+
otherwise preserve slicer-native preset semantics
```

But the exact field mapping must be determined from Orca behavior.

---

# 13. Canonical Name

The desired company display identity remains conceptually:

```text
{pi_code} @{printer}
```

Determine which OrcaSlicer field(s) actually need modification to achieve the intended imported/displayed preset name.

Do NOT blindly assume:

```python
canonical["name"] = ...
```

is sufficient solely because BambuStudio uses that rule.

Verify using real OrcaSlicer import behavior.

---

# 14. `pm_method_version`

The canonical Orca artifact must carry the company-required:

```text
pm_method_version
```

according to the existing business requirement.

Determine whether OrcaSlicer safely preserves unknown/custom fields.

If yes, use the existing field convention.

If not, report the compatibility issue before inventing an alternate encoding.

Do not silently drop `pm_method_version`.

---

# 15. Preserve Unrelated Fields

Canonicalization must preserve unrelated valid Orca fields.

The processor must not reduce an uploaded Orca preset to a small known schema.

Principle:

```text
input preset
+ explicitly required company modifications
=
canonical preset
```

not:

```text
known field allowlist
→ reconstruct preset
```

---

# 16. Unknown Field Preservation

Mandatory regression:

```text
uploaded Orca preset contains:
future_unknown_field = X
```

After canonicalization:

```text
future_unknown_field = X
```

must remain unless there is a documented Orca rule requiring removal.

---

# 17. Inheritance

Explicitly investigate OrcaSlicer inheritance semantics.

Determine:

```text
whether `inherits` exists
how it affects import
how it affects display name
whether inherited base must exist locally
whether export preserves inheritance
```

Do not flatten inheritance in P7.3 unless Orca itself requires it.

---

# 18. Preserve Slicer-Native Artifact

The canonical artifact should remain a valid OrcaSlicer-native preset.

Do not transform it into:

```text
universal JSON
expanded internal schema
BambuStudio-compatible JSON
```

just because the Worker can handle those more easily.

---

# 19. Artifact Output

`OrcaSlicerProcessor.process()` must return:

```text
ProcessedArtifact
└── canonical_artifact: Artifact
```

with:

```text
content = serialized Orca artifact bytes
filename = processor-owned filename
media_type = appropriate type
```

Workflow must remain opaque to its contents.

---

# 20. Filename

Use a deterministic Orca canonical filename consistent with the intended identity.

Prefer, if valid for Orca:

```text
{pi_code} @{printer}.json
```

but verify this against real Orca import behavior.

Filename generation belongs entirely to `OrcaSlicerProcessor`.

---

# 21. Serialization

If Orca preset artifact is JSON:

```text
OrcaSlicerProcessor
```

owns:

```text
json.loads
json.dumps
encoding
serialization details
```

Generic workflow must remain unaware that Orca happens to use JSON.

---

# 22. Determinism

Same:

```text
uploaded Artifact
+
ProcessingContext
```

must produce semantically identical canonical Orca artifact.

No timestamp/random/database-state injection.

---

# 23. Idempotency

Canonicalizing an already canonical Orca artifact using the same context must not introduce further semantic changes.

Test:

```text
canonicalize(canonicalize(x))
≈
canonicalize(x)
```

---

# 24. Diff

Implement:

```python
OrcaSlicerProcessor.diff(
    base: Artifact,
    candidate: Artifact,
    context: ProcessingContext,
) -> UnifiedDiff
```

It must return the P7.2 generic diff contract.

---

# 25. Orca Diff Semantics

Determine Orca-specific semantic comparison from real artifacts.

Do not automatically copy the Bambu field classification table.

For each changed Orca field:

```text
path
change_type
category
old_value
new_value
```

must be produced.

---

# 26. Diff Categories

Every Orca change must map to exactly one:

```text
IMPORTANT_PARAMETER
OTHER_PARAMETER
SYSTEM_METADATA
```

Start conservatively.

Only classify a field as:

```text
IMPORTANT_PARAMETER
```

when the project has a clear reason to treat it as an important printing/material parameter.

Unknown fields default to:

```text
OTHER_PARAMETER
```

---

# 27. Avoid False Importance Mapping

Do not classify fields as IMPORTANT merely because their names resemble Bambu fields.

If the meaning is uncertain:

```text
OTHER_PARAMETER
```

is safer.

The diff must remain complete.

---

# 28. System Metadata

Identify actual Orca metadata fields separately.

Do not automatically inherit the entire Bambu `SYSTEM_METADATA` list.

Shared fields may share classification only after verifying equivalent semantics.

---

# 29. Missing vs Null

Orca diff must satisfy the P7.2 contract:

```text
missing → null = change
null → missing = change
null → null = no change
```

---

# 30. Deterministic Diff

Same Orca base/candidate artifacts must produce byte-for-byte equivalent serialized UnifiedDiff.

Preserve stable path ordering.

---

# 31. CREATE Workflow

For:

```text
Submission.slicer = OrcaSlicer
```

with no matching Preset:

```text
operation = CREATE
base_version = null
base_version_no_text = empty
```

Do not fabricate a diff against an empty artifact.

Existing CREATE workflow remains unchanged.

---

# 32. UPDATE Workflow

For existing:

```text
preset_key = PI | Printer | OrcaSlicer
```

the normal UPDATE workflow must apply:

```text
resolve Preset
→ current_version
→ base_version
→ base_version_no_text
→ processor.diff(base, candidate)
→ READY_FOR_REVIEW
```

No Orca-specific workflow branch.

---

# 33. Preset Identity

OrcaSlicer must remain a distinct Preset identity dimension.

Conceptually:

```text
L2002CF | BBL P2S | BambuStudio

!=

L2002CF | BBL P2S | OrcaSlicer
```

Do not reuse Bambu PresetVersion history for Orca.

---

# 34. No Cross-Slicer Base

An Orca Submission must never resolve:

```text
BambuStudio PresetVersion
```

as its base merely because:

```text
PI Code
printer
```

match.

Slicer remains part of preset identity.

Add a regression test.

---

# 35. Preview

M1 Preview for Orca must use the existing generic flow:

```text
PREVIEW_REQUESTED
→ Worker
→ Orca processor
→ canonical Artifact
→ UnifiedDiff
→ DRAFT + preview
```

No Orca-specific Miaoda diff logic.

---

# 36. Formal Submission

Formal:

```text
DRAFT
→ VALIDATING
→ Worker
→ Orca processor
→ READY_FOR_REVIEW
```

must use the same authoritative recomputation semantics as Bambu.

---

# 37. Required Photos

Existing guided process-photo requirements remain unchanged unless the SOP explicitly defines slicer-specific differences.

Do not add Orca-specific photo rules in P7.3.

---

# 38. Test 3MF

Existing required test `.3mf` submission evidence remains unchanged.

P7.3 does NOT parse the 3MF.

Do not attempt to verify that the 3MF was generated by OrcaSlicer.

---

# 39. Reviewer Workspace

M3 must display Orca Submission using existing generic:

```text
identity
operation
base version
validation
UnifiedDiff
photos
test 3MF
change_reason
canonical artifact
raw uploaded artifact
```

No Orca-specific reviewer page.

---

# 40. Publication

Publication must remain unchanged.

Expected:

```text
APPROVING
→ existing publication service
→ PresetVersion
→ Preset.current_version
→ APPROVED
```

Publication must not parse Orca artifact contents.

---

# 41. Version Allocation

Orca uses the exact same version semantics:

```text
CREATE → v1

UPDATE:
current vN
→ vN+1
```

No slicer-specific version numbering.

---

# 42. VERSION_CONFLICT

Existing conflict behavior applies unchanged.

Example:

```text
Orca Submission A based on v3
Orca Submission B based on v3

A publishes → v4
B attempts publication
→ VERSION_CONFLICT
```

Do not auto-rebase.

---

# 43. Current Artifact Download

For an existing Orca Preset:

```text
Preset.current_version
→ PresetVersion.canonical_json
→ stored Orca canonical artifact
```

must be directly downloadable.

Do not convert it to Bambu format.

Do not reconstruct it.

---

# 44. Download Filename

The downloaded current Orca artifact should retain/use the processor-generated canonical filename according to existing attachment behavior.

Do not derive it from artifact contents in workflow.

---

# 45. Bambu Regression

Adding Orca must not change existing Bambu behavior.

All Bambu tests from P7.0–P7.2 must remain green.

---

# 46. Processor Isolation Test

Add an explicit test proving:

```text
Bambu Submission
→ BambuStudioProcessor

Orca Submission
→ OrcaSlicerProcessor
```

and neither processor is invoked for the other slicer.

---

# 47. Cross-Slicer Identity Test

Create:

```text
same PI Code
same Printer
BambuStudio preset exists
```

Then submit:

```text
slicer = OrcaSlicer
```

Expected:

```text
does NOT resolve Bambu Preset
```

If no Orca Preset exists:

```text
operation = CREATE
```

---

# 48. Wrong Artifact Test

Upload a clearly incompatible artifact under OrcaSlicer where reliable detection is possible.

Expected:

```text
validation failure
```

Do not fall back to Bambu processor.

---

# 49. Real Orca Import Test

Mandatory manual test:

```text
real OrcaSlicer export
        ↓
Worker canonicalization
        ↓
download canonical artifact
        ↓
import into OrcaSlicer
```

Verify:

```text
import succeeds
preset appears
display name is correct
parameters remain correct
```

---

# 50. Real Orca CREATE End-to-End Test

Manually perform:

```text
Miaoda
→ new Orca Submission
→ Preview
→ Submit
→ READY_FOR_REVIEW
→ Reviewer Approve
→ APPROVING
→ Worker publish
→ APPROVED
→ Preset v1
```

Verify Bitable relationships and canonical attachment.

---

# 51. Real Orca UPDATE End-to-End Test

Then:

```text
download current Orca v1
→ import into OrcaSlicer
→ modify parameter
→ export
→ new Submission
→ Preview
→ diff
→ review
→ publish
→ v2
```

Verify:

```text
base_version = v1
base_version_no_text = "1"
published version = v2
diff reflects intended changes
```

---

# 52. Round-Trip Test

For representative real Orca fixtures:

```text
Orca export
→ processor
→ canonical artifact
→ Orca import
```

must succeed manually.

Automated tests should additionally verify:

```text
parse
→ canonicalize
→ serialize
→ parse
```

---

# 53. Golden Canonical Fixture

Create at least one golden Orca canonicalization regression.

Verify exact intended semantic changes.

At minimum:

```text
company display identity behavior
pm_method_version
unrelated field preservation
unknown field preservation
```

---

# 54. Golden Diff Fixture

Create representative Orca base/candidate fixtures.

Verify:

```text
IMPORTANT_PARAMETER
OTHER_PARAMETER
SYSTEM_METADATA
unknown field fallback
added
removed
modified
```

where actual fixtures support them.

---

# 55. Existing Processor Contract

`OrcaSlicerProcessor` must pass the reusable P7 processor contract tests.

At minimum:

```text
valid artifact accepted
invalid artifact rejected
input not mutated
deterministic canonicalization
idempotent canonicalization
unknown field preserved
Artifact returned
filename returned
serialized artifact parseable
diff returns UnifiedDiff
deterministic diff
empty semantic diff
added/removed/modified
unknown change preserved
```

---

# 56. Do Not Weaken Contract Tests

If Orca fails an existing contract test:

1. determine whether Orca legitimately violates an assumption in the generic contract;
2. if yes, report the contract design issue;
3. change the generic contract only if the abstraction is actually wrong.

Do NOT simply special-case Orca in the test suite to get green tests.

This is one of the primary purposes of P7.3.

---

# 57. Detect Architectural Friction

During implementation, explicitly record every place where adding Orca required modifying code outside:

```text
Orca processor
processor registry/composition
Orca fixtures/tests
minimal UI supported-slicer configuration
```

Classify each modification as:

```text
expected generic extension
architecture leak
UI configuration
bug fix
```

This is required in the completion report.

---

# 58. Stop Condition for Architecture Leak

If Orca requires adding logic conceptually like:

```python
if slicer == "OrcaSlicer":
```

inside:

```text
enrichment
publication
review
version allocation
generic diff serialization
```

do not continue by default.

Report why the processor contract cannot express the requirement.

Fix the abstraction rather than spreading slicer branching.

---

# 59. UI Slicer Selection

If Miaoda already offers OrcaSlicer as a slicer choice, enable it only after Worker support is deployed.

If not, add it through the existing slicer-option configuration.

Do not build a separate Orca submission form.

---

# 60. Capability Consistency

The UI must not allow a slicer that the deployed Worker registry does not support.

Where practical, keep supported slicer identifiers in one authoritative configuration source or ensure they are explicitly synchronized.

Do not introduce a complex capability-discovery service in P7.3.

---

# 61. Validation Error Presentation

Orca validation failures should use the existing generic validation-result pipeline.

Miaoda should display meaningful errors without understanding Orca internals.

Example:

```text
上传的文件不是有效的 OrcaSlicer 耗材预设
```

Exact wording should follow existing application conventions.

---

# 62. Logging

Processor logging should identify:

```text
submission_id
slicer = OrcaSlicer
processor = OrcaSlicerProcessor
stage
success/failure
duration
```

Do not log complete preset contents.

---

# 63. Migration Scripts

Do NOT refactor historical migration scripts merely to support runtime Orca processing.

If existing migration assumptions conflict with new production data creation, report the conflict separately.

---

# 64. Storage Schema

Continue using existing Feishu fields:

```text
uploaded_json
canonical_json
```

for Orca if Orca's canonical artifact is JSON.

Do not rename schema in P7.3.

The application-layer artifact abstraction already prevents this legacy naming from leaking into processor architecture.

---

# 65. No Bambu-to-Orca Conversion

Do not offer:

```text
existing Bambu preset
→ automatically generate Orca preset
```

P7.3 requires a real Orca artifact submission.

---

# 66. No Shared Version History

Do not attempt:

```text
Bambu v7
→ Orca v8
```

Each slicer-specific preset identity owns its own history.

---

# 67. No Universal Parameter Model

Do not introduce a universal model to reconcile Bambu and Orca fields.

P7.3 is testing processor isolation, not cross-slicer normalization.

---

# 68. No Automatic Inheritance Repair

If an uploaded Orca preset references an inheritance base unavailable in the target Orca installation, do not silently rewrite it unless this is already an explicit canonicalization requirement.

Detect/report the issue if reliably possible.

---

# 69. No Slicer-Version Compatibility Matrix Yet

Do not build a large compatibility engine for every Orca release.

Record fixture versions and implement only validation needed for currently supported real exports.

If material format differences across Orca versions are discovered, report them explicitly.

---

# 70. Mandatory Automated Tests

At minimum:

```text
[ ] Orca processor registered

[ ] correct processor selected for Orca

[ ] Bambu still selects Bambu processor

[ ] valid real Orca fixture accepted

[ ] malformed Orca artifact rejected

[ ] wrong top-level artifact rejected

[ ] wrong preset type rejected where detectable

[ ] Orca canonical Artifact returned

[ ] Orca filename deterministic

[ ] Orca canonicalization deterministic

[ ] Orca canonicalization idempotent

[ ] pm_method_version applied

[ ] intended display identity applied

[ ] unrelated fields preserved

[ ] unknown fields preserved

[ ] Orca diff returns UnifiedDiff

[ ] identical Orca artifacts → empty diff

[ ] added field → ADDED

[ ] removed field → REMOVED

[ ] modified field → MODIFIED

[ ] missing/null semantics preserved

[ ] unknown changed field → OTHER_PARAMETER

[ ] diff ordering deterministic

[ ] same PI/printer Bambu preset does not become Orca base

[ ] Orca CREATE resolves correctly

[ ] Orca UPDATE resolves correctly

[ ] Orca base_version correct

[ ] Orca base_version_no_text correct

[ ] Preview works

[ ] formal enrichment works

[ ] publication works

[ ] current-version download works

[ ] Bambu regression suite remains green

[ ] generic processor contract passes for Orca
```

---

# 71. Mandatory Manual Tests

Perform:

### A. Import Compatibility

```text
real Orca export
→ Worker
→ canonical artifact
→ Orca import
```

### B. CREATE

```text
Submission
→ Preview
→ Review
→ Publish
→ v1
```

### C. UPDATE

```text
download v1
→ edit in Orca
→ export
→ Submission
→ Preview diff
→ Review
→ Publish
→ v2
```

### D. Bambu Isolation

Verify existing Bambu workflow still behaves normally after Orca registration.

---

# 72. Out of Scope

Do NOT implement:

```text
Cura
PrusaSlicer
other slicers

Bambu → Orca conversion
Orca → Bambu conversion

universal parameter schema
cross-slicer diff
shared cross-slicer version history

3MF parsing
3MF parameter extraction

advanced inheritance resolution
automatic inheritance repair

new publication workflow
new review workflow
new conflict semantics

risk scoring
AI review
```

---

# Acceptance Criteria

P7.3 is complete when:

```text
[ ] OrcaSlicerProcessor exists as an independent processor

[ ] Orca is registered through existing processor registry

[ ] real Orca exports are used as fixtures

[ ] actual Orca artifact semantics were investigated rather than assumed from Bambu

[ ] Orca canonical artifact imports successfully into OrcaSlicer

[ ] company naming requirement works in real OrcaSlicer

[ ] pm_method_version survives correctly

[ ] unrelated and unknown fields survive canonicalization

[ ] Orca diff satisfies UnifiedDiff contract

[ ] Orca CREATE works end-to-end

[ ] Orca UPDATE works end-to-end

[ ] Orca has independent Preset/version history from Bambu

[ ] Reviewer Workspace requires no Orca-specific implementation

[ ] publication requires no Orca-specific implementation

[ ] version allocation requires no Orca-specific implementation

[ ] existing Bambu behavior remains unchanged

[ ] no slicer-specific branching leaked into generic workflow

[ ] reusable processor contract passes
```

# Completion Report

Report:

1. exact Orca slicer identifier;
2. Orca fixture versions and provenance;
3. observed Orca export structure;
4. differences discovered between Orca and Bambu artifacts;
5. Orca validation rules;
6. how Orca preset type is identified;
7. whether Bambu/Orca files can reliably be distinguished;
8. Orca inheritance findings;
9. actual Orca display-name behavior;
10. exact canonicalization rules;
11. `pm_method_version` behavior;
12. unknown-field preservation result;
13. final canonical filename rule;
14. Orca diff implementation;
15. IMPORTANT_PARAMETER mapping strategy;
16. SYSTEM_METADATA mapping strategy;
17. unknown-field diff behavior;
18. processor contract test result;
19. golden canonicalization result;
20. golden diff result;
21. Orca CREATE automated result;
22. Orca UPDATE automated result;
23. cross-slicer identity isolation result;
24. Preview result;
25. formal enrichment result;
26. publication result;
27. current-version download result;
28. real Orca import compatibility result;
29. real CREATE end-to-end result;
30. real UPDATE v1 → v2 end-to-end result;
31. Bambu regression result;
32. full test-suite result;
33. every code change required outside Orca processor/registry/fixtures/tests/UI configuration, classified as expected extension / architecture leak / UI configuration / bug fix;
34. any generic architecture limitation discovered while adding the second real slicer;
35. recommendation on whether the architecture is ready for the third slicer.