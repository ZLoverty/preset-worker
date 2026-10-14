# P7.4-B — CrealityPrint Processor Implementation

## 0. Goal

Implement production `CrealityPrintProcessor` using the evidence established by P7.4-A.

P7.4-A is complete and classified:

```text
READY_FOR_PROCESSOR
```

The real-artifact investigation established that the current generic architecture is sufficient.

Therefore P7.4-B must implement CrealityPrint support **without modifying generic workflow architecture** unless an unexpected implementation blocker is discovered.

---

# 1. Evidence From P7.4-A

Treat the committed P7.4-A reports and fixtures as authoritative evidence for this implementation.

Established behavior:

```text
name
    confirmed visible-name / primary identity field
    changing name alone creates a new preset

filament_settings_id
    survives modification/import/re-export

base_id
    slicer-managed semantics observed
    manually modified value was reset by CrealityPrint to GFSA04

inherits
    preserved

material/printing parameters
    preserved

pm_method_version
    accepted on import
    removed by CrealityPrint during re-export

Artifact(content, filename, media_type)
    sufficient

architecture
    no generic change required
```

Do not re-litigate these findings based on assumptions from BambuStudio or OrcaSlicer.

---

# 2. Scope

Implement:

```text
CrealityPrintProcessor
registry integration
real-artifact-derived fixtures
processor contract tests
canonicalization tests
validation tests
UnifiedDiff tests
generic workflow integration tests
Bambu/Orca isolation regressions
```

Do NOT implement:

```text
ElegooSlicer
PrusaSlicer
OrcaSlicer (Snapmaker)
cross-slicer conversion
generic workflow redesign
Artifact redesign
universal preset schema
```

---

# 3. Processor Independence

Create a dedicated processor, conceptually:

```python
class CrealityPrintProcessor:
    slicer_id = "CrealityPrint"
```

Use the exact slicer ID convention already established by the project.

Do not subclass:

```text
BambuStudioProcessor
OrcaSlicerProcessor
```

even if the artifact structure is similar.

Small shared pure helpers are acceptable only when genuinely format-independent.

---

# 4. Processor Contract

Implement the existing `SlicerProcessor` contract.

Conceptually:

```python
class SlicerProcessor(Protocol):
    slicer_id: str

    def parse(...)
    def validate_source(...)
    def normalize(...)
    def apply_company_policy(...)
    def validate_canonical(...)
    def serialize(...)
    def diff(...)
```

Do not change the contract merely to accommodate CrealityPrint unless a concrete blocker is found.

P7.4-A already indicates that the existing contract should be sufficient.

---

# 5. Opaque Artifact Boundary

The generic workflow must continue treating the canonical artifact as opaque.

Use:

```python
Artifact(
    content=...,
    filename=...,
    media_type=...,
)
```

All CrealityPrint-specific parsing and serialization stays inside the processor.

Generic workflow must not inspect CrealityPrint fields.

---

# 6. Real Artifact as Basis

Use the real P7.4-A artifact as the basis for compatibility fixtures.

Do not return to synthetic assumptions now that real evidence exists.

Retain focused synthetic fixtures only where useful for isolated edge cases.

---

# 7. Source Validation

`validate_source()` must establish that the uploaded artifact is a valid supported CrealityPrint filament/material preset.

Validation rules must come from the actual artifact structure established in P7.4-A.

Reject clearly malformed or unsupported artifacts.

Do not reject unknown fields merely because the processor does not understand them.

---

# 8. Preset Type Validation

Ensure that the artifact represents the supported filament/material preset type.

Do not silently accept unrelated CrealityPrint artifact types if they can be distinguished reliably.

Return a clear validation error for unsupported preset types.

---

# 9. Canonical Name Rule

Apply the company naming policy:

```python
canonical_name = f"{context.pi_code} @{context.printer}"
```

Set the evidence-backed CrealityPrint display-name field:

```text
name
```

to that value.

This is mandatory.

---

# 10. `name` Is the Required Identity Mutation

P7.4-A demonstrated that changing `name` alone is sufficient to create a new preset.

Therefore the default canonicalization strategy is:

```text
modify name
preserve slicer-native identity metadata
```

Do not mutate additional identity-looking fields without evidence.

---

# 11. Preserve `filament_settings_id`

Do NOT derive `filament_settings_id` from:

```text
name
pi_code
printer
preset_key
```

P7.4-A demonstrated that CrealityPrint preserves modifications to this field, but did not establish that Worker must synchronize it with the canonical name.

Therefore:

```text
preserve source filament_settings_id unchanged
```

unless existing source validation requires otherwise.

---

# 12. Preserve `base_id`

Do NOT generate or normalize `base_id`.

Do NOT force:

```text
GFSA04
```

simply because CrealityPrint reset an experimental mutation to that value.

That experiment demonstrates slicer-managed semantics, not a Worker business rule.

Default behavior:

```text
preserve source base_id unchanged
```

If absent, do not invent one unless real fixture evidence establishes it as mandatory.

---

# 13. Preserve `inherits`

Preserve:

```text
inherits
```

exactly according to the source artifact semantics.

Do not:

```text
flatten inheritance
rename parent
remove inheritance
rewrite inheritance based on canonical name
```

P7.4-A demonstrated successful preservation.

---

# 14. Inject `pm_method_version`

The Worker business rule remains:

```python
canonical["pm_method_version"] = context.pm_method_version
```

or the structurally equivalent representation required by the actual artifact format.

This value comes from:

```text
Submission.pm_method_version
```

not from the uploaded artifact.

---

# 15. `pm_method_version` Is Authoritative Worker Metadata

CrealityPrint removing `pm_method_version` during re-export is an accepted slicer limitation.

The lifecycle is:

```text
Submission.pm_method_version
        ↓
Worker canonicalization
        ↓
canonical artifact contains pm_method_version
        ↓
CrealityPrint import
        ↓
CrealityPrint re-export may remove it
        ↓
next Submission supplies authoritative pm_method_version again
        ↓
Worker reinjects it
```

Do not attempt to work around CrealityPrint by hiding this metadata in unrelated native fields.

---

# 16. Unknown Field Preservation

Preserve unknown/unrecognized fields.

Canonicalization must not reconstruct the preset from a whitelist of known fields.

Preferred conceptual behavior:

```python
canonical = deep_copy(source)
apply_only_required_mutations(canonical)
```

The exact implementation may differ, but semantic preservation is required.

---

# 17. Minimum Mutation Principle

The expected Worker mutation set should be minimal.

For a normal valid source artifact, canonicalization should principally change:

```text
name
pm_method_version
```

plus only unavoidable serialization normalization.

Unexpected mutation of slicer-native fields is a regression.

---

# 18. Parameter Preservation

Material and printing parameters must remain semantically unchanged unless an explicit company policy says otherwise.

Add regression coverage demonstrating preservation of representative parameters from the real fixture.

---

# 19. Serialization

Serialize the canonical artifact in a form accepted by CrealityPrint.

Use evidence from the real artifact.

Do not require byte-for-byte reproduction of the original formatting unless CrealityPrint requires it.

Semantic preservation is the requirement.

---

# 20. Canonical Filename

The processor owns its canonical filename.

Do not move filename generation back into generic workflow.

Use a deterministic filename compatible with CrealityPrint and consistent with existing project conventions.

Where the real slicer requires a particular extension, preserve/use that extension.

The generic workflow must not derive the filename from parsed Creality fields.

---

# 21. Canonical Validation

After company policy is applied, `validate_canonical()` must verify at minimum:

```text
artifact remains valid CrealityPrint preset
name == "{pi_code} @{printer}"
pm_method_version == context.pm_method_version
required native fields remain valid
```

Do not require CrealityPrint to preserve `pm_method_version` after external round-trip.

The validation applies to the Worker-produced canonical artifact.

---

# 22. UnifiedDiff

Implement CrealityPrint diff using the existing:

```text
UnifiedDiff
DiffChange
ChangeType
DiffCategory
```

contract.

Do not introduce a Creality-specific persisted diff format.

---

# 23. Diff Semantics

For structured parameter fields, detect:

```text
ADDED
REMOVED
MODIFIED
```

Correctly distinguish:

```text
missing → null
null → missing
null → null
```

consistent with existing UnifiedDiff semantics.

---

# 24. Stable Diff Ordering

Diff output must be deterministic.

Sort changes using the existing project convention.

Repeated diff of the same artifacts must produce equivalent output ordering.

---

# 25. Diff Classification

CrealityPrint-specific classification belongs inside:

```text
CrealityPrintProcessor
```

or Creality-specific helper modules.

Generic workflow must not know which Creality fields are important.

Use:

```text
IMPORTANT_PARAMETER
OTHER_PARAMETER
SYSTEM_METADATA
```

Unknown fields must default to:

```text
OTHER_PARAMETER
```

unless there is evidence they are system metadata.

Never silently omit unknown changes.

---

# 26. System Metadata

Identity/infrastructure fields such as confirmed slicer metadata may be classified as:

```text
SYSTEM_METADATA
```

based on evidence.

Do not classify ordinary material/process parameters as system metadata merely because they are unfamiliar.

---

# 27. `pm_method_version` Diff Classification

Treat:

```text
pm_method_version
```

as:

```text
SYSTEM_METADATA
```

unless the existing project-wide convention explicitly specifies otherwise.

---

# 28. CREATE Behavior

For CREATE:

```text
source artifact
    ↓
CrealityPrintProcessor
    ↓
canonical artifact
```

must produce a valid canonical artifact without requiring a base artifact.

Do not manufacture a fake diff against an empty preset.

Follow existing CREATE semantics.

---

# 29. UPDATE Behavior

For UPDATE:

```text
uploaded source artifact
current canonical base artifact
        ↓
CrealityPrintProcessor
        ↓
canonical artifact + UnifiedDiff
```

The processor must be able to compare current and candidate artifacts using Creality-specific parsing.

The generic workflow only receives the resulting UnifiedDiff.

---

# 30. Base Artifact Remains Opaque Outside Processor

Generic workflow may retrieve and pass the base Artifact.

It must not parse:

```text
name
base_id
filament_settings_id
inherits
```

or any other Creality field.

---

# 31. Registry Integration

Register `CrealityPrintProcessor` in:

```text
default_processor_registry
```

using the project's existing registry composition.

Selection must remain strictly based on:

```text
Submission.slicer
```

Do not infer slicer from:

```text
filename
extension
JSON fields
printer
vendor
```

---

# 32. No Workflow Branching

After implementation, search production generic code for new logic resembling:

```python
if slicer == "CrealityPrint":
    ...
```

outside the registry/composition layer or explicitly slicer-owned modules.

There should be none.

If one is necessary, explain why in the completion report.

---

# 33. Real Fixture Tests

Add real-export-derived CrealityPrint fixtures from P7.4-A.

At minimum retain safe fixtures representing:

```text
source real export
canonical expected artifact
round-trip evidence where useful
```

Preserve provenance/version documentation.

---

# 34. Fixture Hygiene

Ensure committed fixtures contain no inappropriate:

```text
usernames
absolute local paths
tokens
account IDs
network credentials
private machine identifiers
```

Document any sanitization.

Do not sanitize fields whose semantics are under test without explicit documentation.

---

# 35. Canonicalization Golden Test

Using a real-export-derived fixture, verify:

```text
name rewritten correctly
pm_method_version injected correctly
filament_settings_id preserved
base_id preserved
inherits preserved
unknown fields preserved
representative material parameters preserved
representative printing parameters preserved
```

This is a mandatory test.

---

# 36. Minimal Mutation Test

Add a semantic comparison test asserting that the set of Worker-intended changes is limited to the approved canonical mutations.

Conceptually:

```text
source
vs
canonical
```

must not show unexpected changes outside:

```text
name
pm_method_version
```

except documented serialization effects.

---

# 37. `base_id` Regression Test

Add an explicit regression test preventing future developers from treating:

```text
GFSA04
```

as a Worker-generated universal value.

Given a valid source fixture with its legitimate `base_id`:

```text
canonical base_id == source base_id
```

The processor must not overwrite it merely because the GUI experiment observed CrealityPrint normalizing an intentionally modified value.

---

# 38. `filament_settings_id` Regression Test

Verify:

```text
canonical filament_settings_id
==
source filament_settings_id
```

unless future evidence changes the rule.

Do not synchronize it with canonical `name`.

---

# 39. `inherits` Regression Test

Verify:

```text
canonical inherits
==
source inherits
```

for the real fixture.

---

# 40. Unknown Field Regression

Add at least one unknown-field preservation test.

For example, insert a harmless unknown field into a test artifact and verify canonicalization preserves it.

This ensures future refactors do not accidentally switch to whitelist reconstruction.

---

# 41. `pm_method_version` Regression

Explicitly verify:

```text
source may lack pm_method_version
        ↓
canonicalization
        ↓
canonical contains context.pm_method_version
```

Also verify that an uploaded stale/different value does not override the Submission context.

For example:

```text
source pm_method_version = OLD
context.pm_method_version = NEW

canonical pm_method_version == NEW
```

---

# 42. Diff Tests

Add tests covering:

```text
parameter modified
parameter added
parameter removed
unknown parameter modified
system metadata modified
null/missing behavior
stable ordering
```

Use real Creality structure where practical.

---

# 43. Fake/Generic Architecture Regression

Retain the existing fake non-JSON processor tests.

CrealityPrint support must not weaken the guarantee that generic workflow works with opaque non-JSON artifacts.

---

# 44. Bambu Isolation Regression

Run all BambuStudio processor and workflow tests unchanged.

Creality implementation must not alter Bambu canonicalization or diff behavior.

---

# 45. Orca Isolation Regression

Run all OrcaSlicer tests unchanged.

Creality implementation must not modify Orca rules, including the accepted `pm_method_version` round-trip limitation.

---

# 46. End-to-End CREATE Test

Add a generic workflow integration test using:

```text
Submission.slicer = CrealityPrint
```

Verify:

```text
registry selects CrealityPrintProcessor
canonical artifact produced
expected name produced
pm_method_version injected
artifact remains opaque to workflow
CREATE path succeeds
```

Do not require GUI automation.

---

# 47. End-to-End UPDATE Test

Add an UPDATE integration test using a Creality current/base artifact and candidate artifact.

Verify:

```text
correct processor selected
base artifact passed to processor
canonical candidate produced
UnifiedDiff produced
generic workflow does not inspect Creality content
```

---

# 48. Publication Isolation

Do not change publication semantics.

A Creality canonical artifact should flow through the same:

```text
Submission
→ READY_FOR_REVIEW
→ APPROVING
→ PresetVersion
→ Preset.current_version
→ APPROVED
```

logic as every other slicer.

---

# 49. No Special Versioning

CrealityPrint must use the same application-level:

```text
preset_key
version_no
version_id
base_version
current_version
```

semantics.

Do not map Creality-native IDs onto application version identity.

---

# 50. Preset Key

CrealityPrint remains a distinct slicer namespace.

Conceptually:

```text
{pi_code}|{printer}|CrealityPrint
```

must not collide with:

```text
{pi_code}|{printer}|BambuStudio
{pi_code}|{printer}|OrcaSlicer
```

Use the existing preset-key implementation rather than introducing new formatting logic.

---

# 51. Do Not Parse `base_id` as Application Base Version

`base_id` is slicer-native metadata.

It has nothing to do with:

```text
Submission.base_version
Preset.current_version
PresetVersion.version_no
```

Never use it for application version resolution.

---

# 52. Error Messages

Validation errors should identify Creality-specific artifact problems clearly without leaking low-level exceptions unnecessarily.

Examples conceptually:

```text
Invalid CrealityPrint preset artifact
Unsupported CrealityPrint preset type
Missing required CrealityPrint field: ...
```

Follow existing project error conventions.

---

# 53. Unsupported Artifact Handling

If a user selects:

```text
slicer = CrealityPrint
```

but uploads an artifact that is clearly not a supported CrealityPrint filament/material preset:

reject it.

Do not fall back to:

```text
OrcaSlicerProcessor
BambuStudioProcessor
```

even if parsing happens to succeed.

---

# 54. No Format Inference

Registry selection remains explicit.

Do not implement:

```text
try Bambu
then Orca
then Creality
```

or content-based auto-detection.

---

# 55. Production UI

Processor support may be enabled in the application only after automated acceptance criteria pass.

Do not add unrelated UI redesign.

If slicer options are centrally configured, make only the minimum required addition for:

```text
CrealityPrint
```

if that belongs to this repository.

Otherwise report that UI enablement belongs elsewhere.

---

# 56. No GUI Round-Trip Requirement for P7.4-B Completion

P7.4-A already performed the real GUI reconnaissance.

P7.4-B does not need to repeat the entire experiment matrix.

However, after implementation, one final real-world smoke test is recommended:

```text
real source
→ actual CrealityPrintProcessor
→ Worker canonical artifact
→ CrealityPrint import
```

If convenient, record the result.

Do not block automated implementation work while waiting for this unless processor output differs materially from the P7.4-A validated mutation pattern.

---

# 57. Final Smoke Test

Preferred final manual check:

```text
Worker canonical artifact imports successfully
visible name == "{pi_code} @{printer}"
parameters preserved
inherits preserved
no unexpected overwrite/conflict
```

`pm_method_version` may again disappear after CrealityPrint re-export.

That is an accepted limitation, not a processor failure.

---

# 58. Acceptance Criteria

P7.4-B is complete when:

```text
[ ] dedicated CrealityPrintProcessor implemented

[ ] processor implements existing SlicerProcessor contract

[ ] registered in default processor registry

[ ] no generic workflow Creality branching introduced

[ ] real P7.4-A fixtures used

[ ] valid Creality filament/material artifact validation implemented

[ ] canonical name = "{pi_code} @{printer}"

[ ] pm_method_version injected from ProcessingContext

[ ] filament_settings_id preserved

[ ] base_id preserved

[ ] inherits preserved

[ ] unknown fields preserved

[ ] material/printing parameters preserved

[ ] processor owns parsing and serialization

[ ] processor owns canonical filename

[ ] UnifiedDiff implemented

[ ] unknown diff fields are not silently dropped

[ ] stable diff ordering verified

[ ] CREATE integration test passes

[ ] UPDATE integration test passes

[ ] fake non-JSON processor tests still pass

[ ] Bambu tests still pass

[ ] Orca tests still pass

[ ] full suite passes

[ ] no Artifact architecture change required
```

---

# 59. Completion Report

Report:

1. files added;
2. files modified;
3. exact `slicer_id`;
4. source validation rules;
5. canonicalization rules;
6. exact fields intentionally mutated;
7. `name` handling;
8. `filament_settings_id` handling;
9. `base_id` handling;
10. `inherits` handling;
11. `pm_method_version` handling;
12. unknown-field preservation strategy;
13. canonical filename rule;
14. serialization behavior;
15. diff implementation;
16. diff classification rules;
17. real fixtures used;
18. fixture sanitization;
19. canonicalization golden-test result;
20. minimal-mutation regression result;
21. `base_id` regression result;
22. `filament_settings_id` regression result;
23. `inherits` regression result;
24. `pm_method_version` regression result;
25. CREATE integration result;
26. UPDATE integration result;
27. Bambu regression result;
28. Orca regression result;
29. fake non-JSON regression result;
30. full test-suite result;
31. any generic workflow changes;
32. any `if slicer == "CrealityPrint"` leakage found;
33. final manual Worker-artifact import result, if performed;
34. known limitations;
35. final readiness classification.

Final readiness should be one of:

```text
READY_FOR_PRODUCTION
READY_WITH_ACCEPTED_LIMITATIONS
NOT_READY
```

Given the known CrealityPrint behavior, loss of `pm_method_version` during external CrealityPrint re-export may be classified as an accepted limitation provided the Worker reliably re-injects authoritative `Submission.pm_method_version`.