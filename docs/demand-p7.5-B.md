# P7.5-B — ElegooSlicer Processor Implementation

## 0. Goal

Implement production `ElegooSlicerProcessor` using the real-artifact and GUI evidence established by P7.5-A.

Validated environment:

```text id="hhn8mb"
ElegooSlicer 1.5.2.5
```

P7.5-A final classification:

```text id="0i69la"
READY_FOR_PROCESSOR
```

The current:

```text id="aijw80"
SlicerProcessor
Artifact
UnifiedDiff
generic workflow
```

architecture is sufficient.

Do not redesign generic architecture during this phase.

---

# 1. Evidence From P7.5-A

Treat the committed P7.5-A reports and fixtures as authoritative.

Established behavior:

```text id="9hdhmt"
baseline
    imports successfully
    existing preset produces overwrite warning

name
    changing name alone creates a new preset
    confirmed visible-name / primary identity behavior

filament_settings_id
    modification survives import/re-export
    not required to change when canonical name changes

inherits
    preserved

material/printing parameters
    preserved

pm_method_version
    accepted on import
    removed during ElegooSlicer re-export

Artifact(content, filename, media_type)
    sufficient
```

Do not override these findings based on Orca/Creality similarity.

---

# 2. Scope

Implement:

```text id="k8a3yn"
ElegooSlicerProcessor
registry integration
source validation
canonicalization
serialization
UnifiedDiff
real-fixture regression tests
CREATE workflow integration
UPDATE workflow integration
cross-slicer isolation tests
```

Do NOT implement:

```text id="e1r4i8"
PrusaSlicer
OrcaSlicer (Snapmaker)
cross-slicer conversion
generic schema
Artifact redesign
workflow redesign
```

---

# 3. Dedicated Processor

Create a dedicated processor conceptually:

```python id="53suxo"
class ElegooSlicerProcessor:
    slicer_id = "ElegooSlicer"
```

Use the exact project naming convention if the registered slicer string differs.

Do not subclass:

```text id="6x5qfw"
OrcaSlicerProcessor
CrealityPrintProcessor
BambuStudioProcessor
```

even if implementation is structurally similar.

Shared pure helpers are allowed only when they are genuinely format-independent.

---

# 4. Existing Processor Contract

Implement the existing `SlicerProcessor` contract without changing it.

Conceptually:

```python id="a1m6d2"
parse(...)
validate_source(...)
normalize(...)
apply_company_policy(...)
validate_canonical(...)
serialize(...)
diff(...)
```

All Elegoo-specific interpretation remains inside the processor.

---

# 5. Opaque Artifact Boundary

Generic workflow may:

```text id="8wepn3"
store
retrieve
route
publish
```

Elegoo artifacts.

Generic workflow must NOT parse or interpret them.

The processor owns all content semantics.

---

# 6. Real Fixtures Are Authoritative

Use the real ElegooSlicer 1.5.2.5 artifacts collected during P7.5-A.

Do not replace them with synthetic Orca-like fixtures.

Synthetic fixtures may be retained only for focused edge-case unit tests.

---

# 7. Source Validation

Validate that an uploaded artifact is a supported ElegooSlicer filament/material preset.

Validation should be derived from the actual P7.5-A structure.

Reject:

```text id="0m75c2"
malformed artifact
unsupported preset type
clearly unrelated artifact
missing required native structure
```

Unknown fields should normally be accepted and preserved.

---

# 8. Canonical Name

Apply:

```python id="0h7vp9"
canonical_name = f"{context.pi_code} @{context.printer}"
```

to the real Elegoo visible-name field established in P7.5-A:

```text id="9l6c6r"
name
```

This is mandatory.

---

# 9. `name` Is Sufficient

P7.5-A demonstrated:

```text id="o7j8qu"
change name only
→ successful import
→ new preset
→ no conflict
```

Therefore do NOT synchronize additional native identity fields merely because `name` changes.

---

# 10. Preserve `filament_settings_id`

Preserve:

```text id="aq2whg"
filament_settings_id
```

from the uploaded source.

Do not derive it from:

```text id="xj95zr"
name
pi_code
printer
preset_key
```

P7.5-A established that changing it can survive round-trip, but did NOT establish that changing it is required.

Therefore minimum-mutation policy wins.

---

# 11. Preserve `inherits`

Preserve:

```text id="ebphmu"
inherits
```

according to source semantics.

Do not:

```text id="n2ff9g"
flatten it
rename it
rewrite it
remove it
derive it from canonical name
```

---

# 12. Preserve Other Native Identity Metadata

Any additional native identity-looking fields present in the real artifact should be preserved unless P7.5-A explicitly demonstrated that Worker must change them.

Do not synthesize new slicer-native IDs.

---

# 13. Inject `pm_method_version`

Always apply authoritative application metadata:

```python id="k4kbn2"
canonical["pm_method_version"] = context.pm_method_version
```

or the structurally equivalent operation appropriate to the artifact.

Uploaded values must NOT override the Submission context.

---

# 14. Authoritative Metadata Rule

Test:

```text id="n70ar5"
source has no pm_method_version
context = NEW
→ canonical = NEW
```

and:

```text id="zmq0jq"
source pm_method_version = OLD
context = NEW
→ canonical = NEW
```

`ProcessingContext.pm_method_version` is authoritative.

---

# 15. Accepted Round-Trip Limitation

ElegooSlicer 1.5.2.5 removes `pm_method_version` during re-export.

This is accepted.

Do not:

```text id="qunhjq"
encode it into unrelated native fields
rename it to trick Elegoo
modify native IDs to preserve it
```

The Worker restores it during the next canonicalization.

---

# 16. Preserve Unknown Fields

Canonicalization must preserve unknown fields.

Do not reconstruct artifacts from a whitelist.

Conceptually prefer:

```python id="2xdjzr"
canonical = deep_copy(source)
apply_required_company_mutations(canonical)
```

The implementation may differ, but semantics must match.

---

# 17. Minimum Mutation Set

For a normal valid source artifact, expected intentional semantic changes should be limited to:

```text id="1iy6jn"
name
pm_method_version
```

unless P7.5-A documented another mandatory change.

Add regression coverage for this.

---

# 18. Preserve Material/Printing Parameters

All unrelated material and printing parameters must remain semantically unchanged.

Use representative real fields from the P7.5-A fixture in regression tests.

---

# 19. Serialization

Serialize into an artifact accepted by ElegooSlicer.

Use the real P7.5-A format.

Do not require byte-for-byte formatting identity unless the slicer requires it.

Semantic preservation is required.

---

# 20. Processor-Owned Filename

The processor owns the canonical filename.

Use a deterministic Elegoo-compatible filename and extension.

Do not let generic workflow parse the artifact to determine its filename.

---

# 21. Canonical Validation

After canonicalization verify at minimum:

```text id="wvn9pb"
supported Elegoo preset structure remains valid

name == f"{context.pi_code} @{context.printer}"

pm_method_version == context.pm_method_version

required native fields remain valid
```

Do not require external Elegoo re-export to preserve `pm_method_version`.

---

# 22. UnifiedDiff

Implement:

```text id="xd27mc"
UnifiedDiff
DiffChange
ChangeType
DiffCategory
```

using the existing generic contract.

Do not introduce an Elegoo-specific persisted diff schema.

---

# 23. Diff Change Types

Correctly represent:

```text id="yixvmm"
ADDED
REMOVED
MODIFIED
```

including:

```text id="al4djf"
missing → null
null → missing
null → null
```

according to existing project semantics.

---

# 24. Stable Ordering

Diff output must be deterministic.

Repeated diff of the same two artifacts must return changes in stable order.

---

# 25. Diff Classification

Elegoo-specific classification belongs inside the Elegoo processor/helper layer.

Use existing categories:

```text id="y2k70u"
IMPORTANT_PARAMETER
OTHER_PARAMETER
SYSTEM_METADATA
```

Unknown fields default to:

```text id="5eh46x"
OTHER_PARAMETER
```

Never silently drop unknown changes.

---

# 26. Metadata Classification

Fields such as:

```text id="92wmqr"
name
filament_settings_id
inherits
pm_method_version
```

may be classified according to the project's established slicer-specific conventions.

`pm_method_version` should normally be:

```text id="cvx6wa"
SYSTEM_METADATA
```

Keep ordinary material parameters out of SYSTEM_METADATA.

---

# 27. CREATE

For CREATE:

```text id="m5frfk"
real Elegoo source
    ↓
ElegooSlicerProcessor
    ↓
canonical Artifact
```

must work without a base artifact.

Do not generate a fake diff against an empty document.

---

# 28. UPDATE

For UPDATE:

```text id="57mv06"
current canonical Artifact
candidate uploaded Artifact
        ↓
ElegooSlicerProcessor
        ↓
canonical candidate
UnifiedDiff
```

Generic workflow must not inspect Elegoo content.

---

# 29. Registry Integration

Register the processor in:

```text id="hdxjym"
default_processor_registry
```

Selection must be based strictly on:

```text id="oxqu68"
Submission.slicer
```

Do not infer slicer from content or filename.

---

# 30. No Fallback Parsing

Do not implement behavior such as:

```python id="plm7vk"
try:
    OrcaSlicerProcessor(...)
except:
    ElegooSlicerProcessor(...)
```

or vice versa.

Each slicer has explicit identity.

---

# 31. No Generic Slicer Branch

After implementation, search generic production code for:

```python id="mkvsxz"
if slicer == "ElegooSlicer":
```

There should be no new slicer-specific branch outside registry/composition or slicer-owned code.

Report any exception.

---

# 32. Preset Namespace

ElegooSlicer must occupy its own preset namespace through the existing `preset_key` mechanism.

Conceptually:

```text id="4sppmu"
{pi_code}|{printer}|ElegooSlicer
```

must remain distinct from:

```text id="2xikf7"
{pi_code}|{printer}|OrcaSlicer

{pi_code}|{printer}|CrealityPrint

{pi_code}|{printer}|BambuStudio
```

Do not introduce a new preset-key implementation.

---

# 33. Real-Fixture Golden Test

Using a real P7.5-A-derived fixture, verify:

```text id="9nuj80"
name rewritten
pm_method_version injected
filament_settings_id preserved
inherits preserved
unknown fields preserved
material parameters preserved
printing parameters preserved
```

Mandatory.

---

# 34. Minimal Mutation Regression

Compare source vs canonical semantically.

Expected intentional mutation set:

```text id="b2vag5"
name
pm_method_version
```

Unexpected mutation = test failure unless explicitly documented.

---

# 35. `filament_settings_id` Regression

Assert:

```text id="2cdl8s"
canonical["filament_settings_id"]
==
source["filament_settings_id"]
```

for the real fixture.

Do not synchronize it with canonical name.

---

# 36. `inherits` Regression

Assert preservation of the real fixture's inheritance semantics.

If represented as a direct field:

```text id="mhj3ki"
canonical["inherits"] == source["inherits"]
```

---

# 37. Unknown Field Regression

Add an unknown-field preservation test.

A harmless extra field must survive canonicalization unchanged.

This protects against future whitelist reconstruction.

---

# 38. `pm_method_version` Regression

Test both:

```text id="yzps9d"
missing source value
→ injected from context
```

and:

```text id="hcgf8x"
stale source value
→ replaced by context value
```

---

# 39. Parameter Preservation Regression

Choose representative real material/printing fields and assert they remain semantically identical.

Do not limit this test to identity metadata.

---

# 40. Diff Tests

At minimum cover:

```text id="2n4oym"
modified material parameter
added field
removed field
unknown field
system metadata field
null/missing distinction
stable ordering
```

---

# 41. CREATE Workflow Integration Test

Run the real/fidelity fixture through generic CREATE workflow with:

```text id="ixxaj5"
Submission.slicer = ElegooSlicer
```

Verify:

```text id="77q2r1"
correct processor selected
canonical artifact produced
canonical name correct
pm_method_version injected
generic workflow treats artifact as opaque
```

---

# 42. UPDATE Workflow Integration Test

Test:

```text id="1pbdyf"
existing Elegoo base Artifact
+
candidate Elegoo Artifact
```

Verify:

```text id="2i0opj"
correct processor selected
base passed opaquely
canonical candidate produced
UnifiedDiff produced
generic workflow does not parse Elegoo content
```

---

# 43. Cross-Slicer Isolation

Run unchanged tests for:

```text id="2htr3b"
BambuStudioProcessor
OrcaSlicerProcessor
CrealityPrintProcessor
fake non-JSON processor
```

Adding Elegoo support must not change their behavior.

---

# 44. Do Not Generalize Prematurely

Elegoo may turn out to share substantial code with Orca.

Do NOT use P7.5-B as an excuse to introduce:

```text id="haj6n3"
BaseOrcaLikeProcessor
PrusaFamilyProcessor
UniversalJsonProcessor
```

unless duplication is both substantial and semantically identical.

Correctness and slicer independence take priority.

Refactoring can happen later with four validated implementations as evidence.

---

# 45. Shared Helpers

Small shared pure functions are acceptable for truly generic mechanics such as:

```text id="5iw4ln"
deterministic JSON serialization
generic recursive diff traversal
stable path sorting
```

provided they do not encode slicer-specific identity semantics.

Do not move:

```text id="8lz9yc"
name rules
inheritance rules
native ID rules
validation rules
```

into generic workflow.

---

# 46. Publication and Versioning

Do not modify:

```text id="n73x0s"
READY_FOR_REVIEW
APPROVING
APPROVED
VERSION_CONFLICT

PresetVersion
current_version
version_no
base_version
publication idempotency
```

Elegoo uses the same generic lifecycle.

---

# 47. Application Identity vs Slicer Identity

Never use Elegoo native IDs as application version identity.

Application identity remains:

```text id="uqgs2v"
preset_key
PresetVersion
base_version
current_version
```

Native fields remain opaque slicer metadata.

---

# 48. UI Enablement

If slicer options are configured in this repository, make only the minimal addition needed to expose:

```text id="hvcqlw"
ElegooSlicer
```

after tests pass.

If UI configuration belongs elsewhere, do not modify it; report the required follow-up.

---

# 49. Final Manual Smoke Test

After processor implementation, preferably generate one actual Worker canonical artifact from the real source fixture.

Human validation:

```text id="6ysp6i"
import into ElegooSlicer 1.5.2.5

verify:
- import succeeds
- visible name is expected
- parameters preserved
- inherits preserved
- no unexpected overwrite/conflict
```

This is a smoke test, not another full reconnaissance matrix.

If re-exported, loss of `pm_method_version` is expected and accepted.

---

# 50. Acceptance Criteria

P7.5-B is complete when:

```text id="oaqx2m"
[ ] dedicated ElegooSlicerProcessor implemented
[ ] existing SlicerProcessor contract unchanged
[ ] registered in default registry
[ ] real P7.5-A fixtures used
[ ] source validation implemented
[ ] canonical name = "{pi_code} @{printer}"
[ ] pm_method_version always comes from context
[ ] filament_settings_id preserved
[ ] inherits preserved
[ ] other native IDs preserved unless evidence says otherwise
[ ] unknown fields preserved
[ ] material/printing parameters preserved
[ ] processor owns parsing
[ ] processor owns serialization
[ ] processor owns filename
[ ] deterministic UnifiedDiff implemented
[ ] unknown diff fields preserved as changes
[ ] CREATE workflow test passes
[ ] UPDATE workflow test passes
[ ] Bambu regressions pass
[ ] Orca regressions pass
[ ] Creality regressions pass
[ ] fake non-JSON regressions pass
[ ] no generic Elegoo-specific branch introduced
[ ] Artifact abstraction unchanged
[ ] full test suite passes
```

---

# 51. Completion Report

Create:

```text id="kekul8"
p7.5-B_completion_report.md
```

Report:

1. files added;
2. files modified;
3. exact `slicer_id`;
4. supported/tested ElegooSlicer version;
5. source validation rules;
6. canonicalization rules;
7. exact intentional mutation set;
8. `name` behavior;
9. `filament_settings_id` behavior;
10. `inherits` behavior;
11. other native-ID behavior;
12. `pm_method_version` behavior;
13. unknown-field preservation;
14. material/printing parameter preservation;
15. serialization behavior;
16. canonical filename rule;
17. diff implementation;
18. diff classifications;
19. real fixtures used;
20. fixture sanitization;
21. golden-test result;
22. minimal-mutation result;
23. identity-preservation regressions;
24. `pm_method_version` regressions;
25. CREATE workflow result;
26. UPDATE workflow result;
27. Bambu regression result;
28. Orca regression result;
29. Creality regression result;
30. fake non-JSON regression result;
31. full test-suite result;
32. generic workflow changes, if any;
33. slicer-specific leakage found, if any;
34. manual Worker-artifact smoke-test result, if performed;
35. known limitations;
36. final readiness classification.

Use:

```text id="o0d1qs"
READY_FOR_PRODUCTION
READY_WITH_ACCEPTED_LIMITATIONS
NOT_READY
```

Given P7.5-A evidence, ElegooSlicer removing `pm_method_version` during re-export is an accepted limitation provided Worker canonicalization always restores the authoritative context value.