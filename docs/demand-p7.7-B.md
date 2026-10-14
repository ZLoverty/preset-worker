# P7.7-B — Snapmaker OrcaSlicer Processor + Evidence-Based Shared Core

## 0. Goal

Implement production support for the Snapmaker-distributed OrcaSlicer variant using the real-artifact and GUI evidence established by P7.7-A.

Validated environment:

```text
Snapmaker OrcaSlicer 2.4.0
```

P7.7-A classification:

```text
READY_FOR_PROCESSOR
```

Implementation relationship:

```text
SHARED_CORE_WITH_DISTINCT_PROCESSOR_FACADES_POSSIBLE
```

The objective is therefore:

```text
shared Orca-compatible processing core
        ↑                     ↑
OrcaSlicerProcessor    SnapmakerOrcaSlicerProcessor
        │                     │
distinct slicer_id      distinct slicer_id
        │                     │
distinct preset_key namespace
```

Do not collapse the two business identities.

---

# 1. Evidence From P7.7-A

Treat committed P7.7-A fixtures and reports as authoritative.

Established Snapmaker OrcaSlicer 2.4.0 behavior:

```text
baseline
    imports successfully
    existing preset produces overwrite prompt

name
    changing name alone creates a new preset
    controls visible identity

filament_settings_id
    modified value survives import/re-export
    not proven necessary to change with name

inherits
    "Snapmaker PLA" preserved

material/temperature parameters
    preserved

pm_method_version
    accepted on import
    removed during re-export

upstream Orca → Snapmaker
    import/export succeeds
    semantic content preserved

Snapmaker → upstream Orca
    import/export succeeds
    semantic content preserved

Artifact
    sufficient

UnifiedDiff
    sufficient
```

This is behavioral evidence for a shared implementation core.

---

# 2. Critical Architectural Distinction

Freeze this distinction:

```text
format/processing compatibility
        ≠
business identity
```

The two slicers may share processing implementation.

They must NOT share application identity.

---

# 3. Required Production Identities

There must remain two distinct processor facades conceptually:

```python
OrcaSlicerProcessor
SnapmakerOrcaSlicerProcessor
```

Each must expose its own:

```text
slicer_id
registry identity
preset_key namespace
```

Do not alias Snapmaker directly to the upstream processor instance.

---

# 4. Exact Snapmaker `slicer_id`

Determine the exact production string from the existing application/UI naming convention.

Prefer the already established user-facing slicer name if one exists.

Document the final value explicitly in the completion report.

Do not reuse:

```text
OrcaSlicer
```

for Snapmaker.

---

# 5. Scope

Implement:

```text
SnapmakerOrcaSlicerProcessor
distinct registry entry
shared Orca-compatible core where justified
source validation
canonicalization
serialization
UnifiedDiff
real Snapmaker fixture tests
CREATE workflow integration
UPDATE workflow integration
business-identity isolation tests
upstream Orca regression tests
all existing cross-slicer regressions
```

Do NOT implement:

```text
business identity merging
preset history merging
cross-slicer preset conversion
automatic slicer detection
generic workflow changes
Artifact redesign
UnifiedDiff redesign
broad processor-family refactor
```

---

# 6. Refactor Scope Is Narrow

P7.7-B may refactor the existing upstream `OrcaSlicerProcessor` only as necessary to extract behavior proven equivalent by P7.7-A.

Do not turn this into a general processor refactor.

In particular, do NOT touch Bambu, Creality, Elegoo, or Prusa architecture merely to make the abstraction look cleaner.

---

# 7. Shared Core Requirement

Extract or introduce a shared Orca-compatible processing core only for responsibilities demonstrated equivalent by evidence.

Conceptually:

```python
class OrcaCompatibleCore:
    ...
```

The actual name is implementation-defined.

Possible shared responsibilities include:

```text
JSON parsing
supported filament-profile structural validation
canonical name mutation
pm_method_version injection
serialization
recursive semantic diff
field classification
canonical validation
```

Only share responsibilities actually shown equivalent.

---

# 8. Distinct Processor Facades

Conceptually:

```python
class OrcaSlicerProcessor:
    slicer_id = "OrcaSlicer"

    def ...:
        return shared_core...


class SnapmakerOrcaSlicerProcessor:
    slicer_id = "<distinct Snapmaker id>"

    def ...:
        return shared_core...
```

The exact composition mechanism may differ.

Prefer composition or thin explicit facades over confusing inheritance chains.

---

# 9. Do Not Alias Registry Entries

Avoid:

```python
registry["OrcaSlicer"] = processor
registry["SnapmakerOrca"] = processor
```

where both entries point to the same processor object with one identity.

Each registered processor must have a coherent distinct `slicer_id`.

Shared internal stateless helpers/core are fine.

---

# 10. Do Not Subclass Merely for Identity

Avoid an implementation whose only distinction is accidental inheritance such as:

```python
class SnapmakerOrcaSlicerProcessor(OrcaSlicerProcessor):
    slicer_id = "..."
```

if that makes Snapmaker semantics implicitly depend on every future upstream-Orca change.

Prefer an explicit shared core used by two facades.

The purpose is to make future behavioral divergence easy to represent.

---

# 11. Future Divergence Must Be Cheap

The design should allow:

```text
future upstream Orca changes behavior
```

without automatically changing Snapmaker behavior.

Likewise:

```text
future Snapmaker fork diverges
```

must not require undoing a deeply coupled inheritance hierarchy.

This is a major reason for distinct facades.

---

# 12. Canonical Name

For Snapmaker Orca:

```python
canonical_name = f"{context.pi_code} @{context.printer}"
```

Apply to:

```text
name
```

P7.7-A proved that `name` alone controls visible identity.

---

# 13. Preserve `filament_settings_id`

Preserve source:

```text
filament_settings_id
```

Do not synchronize it with:

```text
name
pi_code
printer
preset_key
```

P7.7-A demonstrated that it survives modification, but did not establish that it must change with visible name.

Minimum mutation wins.

---

# 14. Preserve `inherits`

Preserve:

```text
inherits
```

including validated Snapmaker-native inheritance such as:

```text
Snapmaker PLA
```

Do not:

```text
rewrite
flatten
remove
translate to upstream Orca parent
```

Snapmaker-native inheritance is legitimate slicer content.

---

# 15. Do Not Normalize Snapmaker Parents to Upstream Parents

Even though cross-import succeeds, do NOT transform:

```text
Snapmaker PLA
```

into an upstream Orca equivalent.

Cross-compatibility is not a request for cross-slicer normalization.

---

# 16. `pm_method_version`

Always inject:

```python
canonical["pm_method_version"] = context.pm_method_version
```

Uploaded artifact values do not override context.

Test both missing and stale source values.

---

# 17. Accepted Metadata Limitation

Snapmaker OrcaSlicer 2.4.0 removes `pm_method_version` during re-export.

This is accepted.

Do not encode it into unrelated native fields.

Worker reinjects it during canonicalization.

---

# 18. Unknown Fields

Preserve unknown fields.

Do not reconstruct Snapmaker artifacts from a whitelist.

This applies equally to:

```text
Snapmaker-specific fields
future fork-specific fields
future Orca-compatible fields
```

---

# 19. Minimum Mutation Set

For a valid normal Snapmaker artifact, expected intentional semantic changes should be:

```text
name
pm_method_version
```

Everything else should remain semantically unchanged unless required by proven serialization behavior.

Add a regression test.

---

# 20. Snapmaker Source Validation

Validate that uploaded content is a supported Snapmaker Orca filament/material preset.

P7.7-A demonstrated strong format compatibility with upstream Orca, so common structural validation may be shared where evidence supports it.

However:

```text
Submission.slicer = Snapmaker...
```

remains authoritative.

Do not infer Snapmaker identity merely because an artifact contains Snapmaker-specific fields.

---

# 21. Cross-Compatible Input Is Allowed

P7.7-A demonstrated successful upstream → Snapmaker import/export.

Therefore Snapmaker processor validation should not artificially reject an otherwise valid compatible filament preset solely because it originated from upstream Orca.

Likewise, source provenance must not be guessed from content.

---

# 22. Processor Selection Is Explicit

Registry selection remains:

```text
Submission.slicer
        ↓
exact processor
```

Never:

```text
inspect JSON
→ guess Orca vs Snapmaker
```

This is especially important because P7.7-A proved the formats can be semantically cross-compatible.

---

# 23. Serialization

Serialize using the validated Orca-compatible JSON representation.

Preserve unknown fields.

Use deterministic serialization according to existing processor conventions.

---

# 24. Processor-Owned Filename

The processor/shared core may generate the canonical artifact filename according to existing Orca-compatible behavior.

Generic workflow must not parse content to determine filename.

If upstream and Snapmaker filename rules are identical, sharing the pure filename-generation mechanic is acceptable.

---

# 25. Canonical Validation

Validate at minimum:

```text
supported filament preset structure

name ==
    f"{context.pi_code} @{context.printer}"

pm_method_version ==
    context.pm_method_version

required native fields remain valid
```

Do not require:

```text
filament_settings_id == name
```

or any equivalent unsupported coupling.

---

# 26. UnifiedDiff

Use existing:

```text
UnifiedDiff
DiffChange
ChangeType
DiffCategory
```

No new persisted schema.

If P7.7-A showed the relevant semantic structure is equivalent to upstream Orca, shared diff mechanics are appropriate.

---

# 27. Diff Semantics

Support:

```text
ADDED
REMOVED
MODIFIED
```

including existing:

```text
missing → null
null → missing
null → null
```

semantics.

Ordering must remain deterministic.

---

# 28. Diff Classification

Use:

```text
IMPORTANT_PARAMETER
OTHER_PARAMETER
SYSTEM_METADATA
```

Unknown fields default to:

```text
OTHER_PARAMETER
```

Never silently discard unknown changes.

---

# 29. Shared Classification Rules

If P7.7-A evidence establishes equivalent field semantics, upstream Orca and Snapmaker may share classification mechanics.

Do not generalize those rules to:

```text
Bambu
Creality
Elegoo
Prusa
```

during P7.7-B.

---

# 30. Snapmaker-Specific Fields

If the real fixture contains Snapmaker-specific fields not present upstream:

```text
preserve them
diff them
classify unknown ones as OTHER_PARAMETER unless clearly metadata
```

Do not silently ignore them because the shared core originated from upstream Orca.

---

# 31. CREATE

Support:

```text
real Snapmaker Artifact
        ↓
SnapmakerOrcaSlicerProcessor
        ↓
canonical Artifact
```

without a base artifact.

Do not generate fake empty-document diff.

---

# 32. UPDATE

Support:

```text
current Snapmaker canonical Artifact
+
candidate Snapmaker Artifact
        ↓
SnapmakerOrcaSlicerProcessor
        ↓
canonical candidate
UnifiedDiff
```

Generic workflow remains content-agnostic.

---

# 33. Distinct Preset Namespace

Mandatory regression:

Given identical:

```text
pi_code
printer
```

these must remain distinct:

```text
PI|Printer|OrcaSlicer
PI|Printer|<Snapmaker slicer id>
```

They must be able to have independently:

```text
Preset rows
current_version
version_no
PresetVersion history
Submission history
```

---

# 34. No Cross-Slicer Version History

Do not attempt to detect:

```text
Snapmaker artifact semantically equals upstream Orca artifact
```

and then reuse:

```text
Preset
PresetVersion
base_version
current_version
```

Cross-format equivalence does not merge histories.

---

# 35. Real Snapmaker Golden Test

Using the real P7.7-A fixture verify:

```text
name rewritten
pm_method_version injected
filament_settings_id preserved
inherits preserved
Snapmaker-specific fields preserved
unknown fields preserved
material parameters preserved
temperature parameters preserved
```

Mandatory.

---

# 36. Minimal Mutation Regression

Semantic comparison:

```text
source
→ canonical
```

Expected intentional mutation set:

```text
name
pm_method_version
```

Unexpected semantic mutation = test failure unless documented.

---

# 37. `filament_settings_id` Regression

Assert:

```text
canonical["filament_settings_id"]
==
source["filament_settings_id"]
```

where present.

Do not synchronize with canonical name.

---

# 38. `inherits` Regression

Assert preservation of:

```text
inherits = Snapmaker PLA
```

for the validated real fixture.

This is particularly important because a future shared-core refactor must not replace fork-native inheritance.

---

# 39. Unknown-Field Regression

Add a harmless unknown field and verify it survives canonicalization unchanged.

---

# 40. `pm_method_version` Regression

Test:

```text
missing source
+ context NEW
→ NEW
```

and:

```text
source OLD
+ context NEW
→ NEW
```

---

# 41. Parameter Preservation Regression

Use actual real fixture fields to verify representative material/temperature/process values remain semantically identical.

---

# 42. Snapmaker Diff Tests

At minimum cover:

```text
modified important parameter
added field
removed field
unknown field
system metadata
null/missing distinction
stable ordering
```

Use real field names from the fixture.

---

# 43. CREATE Workflow Integration

Run generic CREATE with:

```text
Submission.slicer = <Snapmaker slicer id>
```

Verify:

```text
Snapmaker processor selected
canonical artifact produced
canonical name correct
pm_method_version injected
generic workflow remains opaque
```

---

# 44. UPDATE Workflow Integration

Run generic UPDATE with:

```text
Snapmaker base Artifact
+
Snapmaker candidate Artifact
```

Verify:

```text
correct processor selected
base remains opaque to workflow
candidate canonicalized
UnifiedDiff generated
```

---

# 45. Upstream Orca Regression

This is mandatory because P7.7-B may refactor its implementation.

All existing upstream Orca tests must pass unchanged.

In particular verify existing P7.3/P7.3.1 behavior remains:

```text
name controls canonical visible identity
filament_settings_id not unnecessarily changed
inherits preserved
unknown fields preserved
pm_method_version injected
UnifiedDiff behavior unchanged
```

---

# 46. Golden Output Stability for Upstream Orca

Where practical, compare upstream Orca canonical output before/after shared-core extraction.

There must be no unintended semantic change.

If serialization formatting changes but semantics do not, document it.

Prefer avoiding unnecessary fixture churn.

---

# 47. Cross-Processor Equivalence Test

Using semantically equivalent compatible fixtures, verify that the two facades apply equivalent shared rules where intended:

```text
canonical name policy
pm_method_version policy
unknown-field preservation
diff mechanics
```

This test proves shared-core behavior.

It must NOT assert equal:

```text
slicer_id
preset_key
application identity
```

---

# 48. Processor Identity Test

Explicitly assert:

```text
OrcaSlicerProcessor.slicer_id
!=
SnapmakerOrcaSlicerProcessor.slicer_id
```

or the equivalent runtime property.

Mandatory.

---

# 49. Registry Identity Test

Verify registry lookup for:

```text
OrcaSlicer
```

returns the upstream facade.

Verify lookup for the Snapmaker slicer ID returns the Snapmaker facade.

They must not resolve to the same business processor identity.

---

# 50. Future Divergence Testability

Structure tests so a future Snapmaker-specific rule can be added without modifying upstream behavior.

Do not write tests that permanently assert:

```text
every Snapmaker rule must always equal upstream Orca
```

Only assert currently validated shared behavior.

---

# 51. Cross-Slicer Regressions

Run unchanged tests for:

```text
BambuStudioProcessor
CrealityPrintProcessor
ElegooSlicerProcessor
PrusaSlicerProcessor
fake non-JSON processor
```

No behavior changes are allowed.

---

# 52. No Generic Snapmaker Branch

Search generic production code for new logic equivalent to:

```python
if slicer == "Snapmaker...":
    ...
```

There should be no new slicer-specific branch outside:

```text
registry/composition
Snapmaker processor facade
shared Orca-compatible implementation
```

Report any exception.

---

# 53. No Automatic Orca/Snapmaker Detection

Do not implement content-based distinction.

P7.7-A explicitly demonstrated bidirectional format compatibility.

Therefore content inspection may be fundamentally unable to determine user-intended slicer identity.

The explicit Submission.slicer value is authoritative.

---

# 54. Publication and Versioning

Do not modify:

```text
Preset
PresetVersion
base_version
current_version
version_no
APPROVING
APPROVED
VERSION_CONFLICT
publication idempotency
```

Snapmaker uses the existing lifecycle.

---

# 55. UI Enablement

If slicer choices are configured in this repository, add the distinct Snapmaker slicer option after processor tests pass.

Do not alias its UI value to:

```text
OrcaSlicer
```

If UI configuration lives elsewhere, report the required follow-up.

---

# 56. Manual Production Smoke Test

After implementation, preferably generate one canonical artifact through the real production Snapmaker processor.

Import into:

```text
Snapmaker OrcaSlicer 2.4.0
```

Verify:

```text
import succeeds
visible name = "{pi_code} @{printer}"
new/custom preset behavior is correct
inherits remains appropriate
material parameters remain correct
no unexpected conflict
```

No new full reconnaissance matrix is required.

Re-export removal of `pm_method_version` is expected.

---

# 57. Do Not Perform Broad P7.8 Refactor Yet

P7.7-B may perform the narrow Orca/Snapmaker shared-core extraction required by this implementation.

Do NOT yet consolidate:

```text
all JSON processors
all diff implementations
all validation logic
all filename logic
all processor base classes
```

That belongs to a separate architecture consolidation phase after P7.7-B.

---

# 58. Acceptance Criteria

P7.7-B is complete when:

```text
[ ] independent Snapmaker processor facade implemented
[ ] distinct Snapmaker slicer_id established
[ ] distinct registry entry established
[ ] upstream Orca business identity unchanged
[ ] Snapmaker business identity distinct
[ ] shared core extracted only where P7.7-A supports equivalence
[ ] future behavioral divergence remains possible
[ ] real Snapmaker 2.4.0 fixture used
[ ] source validation implemented
[ ] canonical name = "{pi_code} @{printer}"
[ ] pm_method_version injected from context
[ ] filament_settings_id preserved
[ ] inherits preserved
[ ] Snapmaker-specific fields preserved
[ ] unknown fields preserved
[ ] material/temperature parameters preserved
[ ] deterministic UnifiedDiff implemented/reused
[ ] CREATE workflow passes
[ ] UPDATE workflow passes
[ ] upstream Orca regression passes
[ ] upstream Orca canonical semantics unchanged
[ ] processor identity isolation test passes
[ ] preset namespace isolation test passes
[ ] Bambu regression passes
[ ] Creality regression passes
[ ] Elegoo regression passes
[ ] Prusa regression passes
[ ] fake non-JSON regression passes
[ ] no generic Snapmaker-specific branch introduced
[ ] no content-based Orca/Snapmaker detection introduced
[ ] Artifact unchanged
[ ] UnifiedDiff unchanged
[ ] generic workflow unchanged
[ ] full test suite passes
```

---

# 59. Completion Report

Create:

```text
p7.7-B_completion_report.md
```

Report:

1. files added;
2. files modified;
3. exact Snapmaker processor class;
4. exact Snapmaker `slicer_id`;
5. tested Snapmaker OrcaSlicer version;
6. shared-core design;
7. why shared core is evidence-supported;
8. processor-facade separation;
9. registry separation;
10. preset namespace separation;
11. source validation rules;
12. canonicalization rules;
13. exact intentional mutation set;
14. `name` behavior;
15. `filament_settings_id` behavior;
16. `inherits` behavior;
17. Snapmaker-specific field handling;
18. `pm_method_version` behavior;
19. unknown-field preservation;
20. material/temperature parameter preservation;
21. serialization behavior;
22. canonical filename behavior;
23. UnifiedDiff implementation;
24. diff classification;
25. real fixtures used;
26. fixture sanitization;
27. Snapmaker golden-test result;
28. minimal-mutation result;
29. identity-preservation regressions;
30. `pm_method_version` regressions;
31. CREATE workflow result;
32. UPDATE workflow result;
33. upstream Orca regression result;
34. upstream Orca canonical-output compatibility result;
35. cross-processor shared-behavior result;
36. processor identity isolation result;
37. preset namespace isolation result;
38. Bambu regression result;
39. Creality regression result;
40. Elegoo regression result;
41. Prusa regression result;
42. fake non-JSON regression result;
43. full test-suite result;
44. generic workflow changes, if any;
45. slicer-specific leakage found, if any;
46. manual GUI smoke-test result, if performed;
47. known limitations;
48. future divergence strategy;
49. deferred refactoring opportunities for P7.8;
50. final readiness classification.

Use:

```text
READY_FOR_PRODUCTION
READY_WITH_ACCEPTED_LIMITATIONS
NOT_READY
```

---

# 60. Expected End State

A successful implementation should look conceptually like:

```text
                    shared Orca-compatible core
                    /                         \
                   /                           \
      OrcaSlicerProcessor          SnapmakerOrcaSlicerProcessor
              │                               │
      slicer_id=OrcaSlicer          slicer_id=<Snapmaker>
              │                               │
              └──────── distinct ─────────────┘
                     business identity
```

The shared core represents **validated processing equivalence**.

The two facades represent **distinct product/business identity**.

Neither concept should be sacrificed for the other.