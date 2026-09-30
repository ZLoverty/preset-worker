# P7.0 — Slicer Processor Contract & BambuStudio Refactor

## 0. Goal

Refactor the existing slicer-specific processing logic into a stable, explicit **Slicer Processor Contract**.

P7.0 supports **BambuStudio only**.

Do NOT add OrcaSlicer, Cura, PrusaSlicer, or any other slicer in this phase.

The purpose is architectural:

```text id="o0zmtb"
Before:

Worker / Submission Service
    ├─ knows BambuStudio JSON
    ├─ knows Bambu-specific fields
    ├─ performs validation
    ├─ performs canonicalization
    └─ may contain slicer-specific branching


After:

Worker / Workflow Layer
        │
        ▼
SlicerProcessorRegistry
        │
        ▼
SlicerProcessor Contract
        │
        ▼
BambuStudioProcessor
        │
        ├─ parse
        ├─ validate source
        ├─ normalize
        ├─ apply company policy
        ├─ validate canonical
        ├─ serialize
        └─ diff
```

The existing BambuStudio business behavior must remain unchanged.

P7.0 is a refactor, not a feature expansion.

---

# 1. Architectural Principle

The Worker workflow/domain layer owns:

```text id="1tdcy5"
Submission state transitions
Preset identity resolution
CREATE / UPDATE determination
base_version
base_version_no_text
VERSION_CONFLICT
review state
version allocation
PresetVersion creation
publication
current_version projection
photo projection
```

The slicer processor owns:

```text id="2qrbuv"
artifact parsing
slicer-specific validation
slicer-specific normalization
slicer-specific canonicalization
company-required preset field injection
slicer-specific semantic diff
artifact serialization
```

These responsibilities must not leak across the boundary.

---

# 2. Critical Rule

Adding a future slicer should conceptually require only:

```text id="e7sp9c"
1. implement a new processor
2. add fixtures
3. pass processor contract tests
4. register processor
```

It should NOT require modification of:

```text id="t8kr39"
publication logic
version allocation
review workflow
Submission state machine
PresetVersion lifecycle
M1/M2/M3 workflow semantics
```

P7.0 should establish the architecture necessary to make this possible.

---

# 3. Define Processor Contract

Create an explicit processor interface / abstract base class / protocol appropriate for the current Python codebase.

Conceptually:

```python id="tynsf5"
class SlicerProcessor(Protocol):
    slicer_id: str

    def parse(self, artifact: bytes, context: ProcessingContext):
        ...

    def validate_source(self, source, context: ProcessingContext):
        ...

    def normalize(self, source, context: ProcessingContext):
        ...

    def apply_company_policy(self, normalized, context: ProcessingContext):
        ...

    def validate_canonical(self, canonical, context: ProcessingContext):
        ...

    def serialize(self, canonical, context: ProcessingContext) -> bytes:
        ...

    def diff(self, base_artifact, candidate_artifact, context: ProcessingContext):
        ...
```

Exact Python signatures may be adapted to the existing codebase.

Do not force artificial abstraction where the existing implementation has a better equivalent.

However, the responsibility boundary must remain explicit.

---

# 4. Processing Context

Introduce a typed processing context instead of passing arbitrary Submission records deep into slicer logic.

Conceptually:

```python id="dpwh8h"
@dataclass(frozen=True)
class ProcessingContext:
    pi_code: str
    printer: str
    slicer: str
    pm_method_version: str
```

Include only fields actually needed by slicer processing.

Do NOT pass the entire mutable Submission model into the processor merely for convenience.

The processor must not be able to mutate workflow state.

If additional slicer-processing inputs are already required by existing behavior, add them explicitly and document why.

---

# 5. Processor Result

Define an explicit processing result.

Conceptually:

```python id="z5a5tx"
@dataclass(frozen=True)
class ProcessedArtifact:
    canonical_artifact: bytes
    validation_result: ValidationResult
```

If existing architecture requires parsed/canonical intermediate representation, include it as an internal result where useful.

Do not expose unnecessary Bambu-specific implementation details to the workflow layer.

---

# 6. Validation Result

Create or preserve a structured validation result.

It should distinguish at least:

```text id="bd9chj"
valid
invalid user artifact
unsupported slicer/artifact
internal processing failure
```

Validation errors intended for engineers should be structured and human-readable.

Do not require workflow code to parse exception strings to determine normal validation failure.

---

# 7. Processing Pipeline

For BambuStudio, explicitly structure processing conceptually as:

```text id="kjv36s"
uploaded artifact
      ↓
parse
      ↓
validate_source
      ↓
normalize
      ↓
apply_company_policy
      ↓
validate_canonical
      ↓
serialize
      ↓
canonical artifact
```

Do not collapse all stages into a single opaque function if doing so prevents future slicer-specific implementations.

Internal helper functions are encouraged.

---

# 8. BambuStudio Parsing

Move existing BambuStudio JSON parsing behavior behind:

```text id="8gt9hz"
BambuStudioProcessor
```

The workflow layer must not directly call:

```text id="dqst3w"
json.loads(...)
```

for slicer artifact interpretation.

Malformed JSON must remain a normal validation failure according to existing workflow behavior.

---

# 9. Preserve Existing BambuStudio Canonicalization

P7.0 must preserve the currently approved BambuStudio canonicalization rules.

The only intended semantic transformations remain:

```text id="tcfkjp"
canonical["name"] =
    f"{pi_code} @{printer}"

canonical["pm_method_version"] =
    Submission.pm_method_version
```

Do NOT introduce additional BambuStudio semantic transformations during this refactor.

In particular, do NOT modify merely because of P7.0:

```text id="e6z9eq"
inherits
filament_settings_id
version
nozzle temperatures
flow ratio
max volumetric speed
retraction
fan settings
unknown fields
other slicer parameters
```

Unknown valid fields must remain preserved according to current behavior.

---

# 10. Normalization vs Company Policy

Separate conceptually:

```text id="ty8iqy"
normalization
```

from:

```text id="fzfhzt"
company policy
```

For example:

Normalization may deal with representation-level concerns.

Company policy currently includes:

```text id="q1bkj5"
name = PI Code @ Printer
pm_method_version = selected Submission value
```

Do not hide company-required field injection inside generic JSON parsing.

This distinction will matter when future slicers require different company-policy mappings.

---

# 11. No Mutation of Uploaded Artifact

Processor execution must never mutate the original uploaded artifact.

The original:

```text id="5a2c1p"
Submission.uploaded_json
```

remains exact preserved input evidence.

Processor produces a separate canonical artifact.

Add regression coverage for this.

---

# 12. Determinism

For identical:

```text id="z7r7ga"
input artifact
+
ProcessingContext
```

the processor must produce semantically identical canonical output.

No processor output may depend on:

```text id="lxysw1"
current timestamp
random UUID
current database state
Submission status
reviewer
Worker retry count
```

unless an existing documented canonical rule explicitly requires it.

Current BambuStudio behavior should be deterministic.

---

# 13. Idempotency

Processing the already-canonicalized artifact again with the same context should not introduce further semantic changes.

Conceptually:

```text id="8bbl03"
canonicalize(canonicalize(x)) == canonicalize(x)
```

at semantic artifact level.

Add a regression test.

---

# 14. Processor Registry

Introduce a central registry/factory.

Conceptually:

```python id="zrx1g3"
PROCESSORS = {
    "BambuStudio": BambuStudioProcessor(),
}
```

or equivalent dependency-injected structure.

Workflow code should use:

```python id="mkwukx"
processor = registry.get(submission.slicer)
```

Do not scatter:

```python id="u2gfp1"
if slicer == "BambuStudio":
```

across services.

---

# 15. Stable Slicer Identifier

Use the existing canonical slicer value stored in Submission.

Do not infer slicer from:

```text id="8u8c7q"
filename
JSON fields
file extension
printer
preset_key parsing
```

Submission's selected slicer is authoritative for processor selection.

The processor may still reject an artifact that is incompatible with that slicer.

---

# 16. Unsupported Slicer

If no registered processor exists:

```text id="o2r5zo"
registry.get(slicer)
```

must produce a clear controlled unsupported-slicer result/error.

Do not:

```text id="aqcnh1"
fall back to BambuStudio
try generic JSON
silently accept
```

Example engineer-facing meaning:

```text id="5eecno"
当前 Worker 尚不支持该切片器。
```

Exact wording may follow existing UI conventions.

---

# 17. Unified Diff Boundary

P7.0 should establish the processor ownership boundary for semantic diff.

Conceptually:

```text id="e92fn6"
processor.diff(
    base_canonical_artifact,
    candidate_canonical_artifact,
    context
)
```

The workflow layer must not contain Bambu-specific field comparison logic.

---

# 18. Unified Diff Model

Preserve the current M1/M3 diff behavior while formalizing a slicer-neutral result model.

Conceptually:

```python id="tdb6pj"
@dataclass(frozen=True)
class DiffChange:
    path: str
    old_value: object
    new_value: object
    change_type: str
    category: str
```

Supported `change_type` should cover existing semantics such as:

```text id="7v8ltz"
added
removed
modified
```

Preserve current categories:

```text id="a6w6km"
IMPORTANT_PARAMETER
OTHER_PARAMETER
SYSTEM_METADATA
```

Do not redesign the UI categorization in P7.0.

---

# 19. Unknown Diff Fields

Unknown BambuStudio fields must not disappear from diff.

If a changed field has no special classification:

```text id="9gj69c"
category = OTHER_PARAMETER
```

according to existing behavior.

Completeness is more important than trying to classify every field.

---

# 20. Empty Semantic Diff

If base and candidate are semantically identical according to the processor:

```text id="yccm1g"
changes = []
```

Preserve current workflow behavior regarding whether such a Submission may continue.

Do NOT introduce NO_CHANGE status in P7.0.

---

# 21. Workflow Integration

Refactor existing Preview/formal enrichment paths to obtain slicer processing through the registry.

Both paths should reuse the same processor implementation.

Conceptually:

```text id="qag3qq"
Preview
   ↓
processor pipeline
   ↓
temporary preview result


Formal enrichment
   ↓
processor pipeline
   ↓
authoritative candidate result
```

Do not duplicate BambuStudio processing logic between Preview and formal enrichment.

---

# 22. Preview Semantics Remain Unchanged

Preserve existing M1-B semantics:

```text id="59khgh"
PREVIEW_REQUESTED
→ Worker
→ DRAFT + preview result
```

Preview remains non-authoritative.

P7.0 must not change:

```text id="i3ohsm"
base-version freeze
formal validation semantics
photo behavior
test 3MF behavior
Submission lifecycle
```

---

# 23. Formal Enrichment Semantics Remain Unchanged

Preserve:

```text id="k6g29f"
DRAFT
→ VALIDATING
→ READY_FOR_REVIEW
```

or existing validation failure behavior.

Formal enrichment remains authoritative and recomputes candidate processing.

---

# 24. Processor Must Not Resolve Preset Identity

The slicer processor must NOT determine:

```text id="13h5re"
preset_key
CREATE / UPDATE
Preset relation
base_version
base_version_no_text
```

These remain workflow/domain responsibilities.

Processor receives the identity context it needs for canonicalization but does not query or mutate Preset records.

---

# 25. Processor Must Not Publish

Processor must NOT:

```text id="ch5dvm"
create Preset
create PresetVersion
allocate version_no
update current_version
write current_version_no_text
project photos
change publication status
```

Publication remains slicer-neutral.

---

# 26. Processor Must Not Own Review

Processor must NOT read or modify:

```text id="otg2if"
reviewer
review_comment
reviewed_at
APPROVING
APPROVED
REJECTED
```

Review workflow is completely outside slicer processing.

---

# 27. Repository Boundary

Avoid allowing processor implementations to directly depend on the Bitable repository unless absolutely required by an existing slicer-specific rule.

Preferred:

```text id="zzq32n"
Workflow retrieves inputs
        ↓
ProcessingContext
        ↓
Processor
```

rather than:

```text id="ts1s4y"
Processor
        ↓
Bitable repository
```

Processors should be close to pure transformations.

This makes them easy to test and prevents hidden workflow coupling.

---

# 28. Exceptions

Define processor-specific/domain exceptions instead of leaking low-level implementation exceptions.

Conceptually:

```text id="17f7wh"
ArtifactParseError
ArtifactValidationError
UnsupportedSlicerError
ProcessorInternalError
```

Exact names may follow current project conventions.

Do not expose raw:

```text id="j73e8x"
JSONDecodeError
KeyError
TypeError
```

directly as workflow semantics.

Preserve useful diagnostic information in logs.

---

# 29. Logging

At processor boundary, log enough structured information to diagnose failures.

Useful dimensions:

```text id="nmjm1a"
submission_id
slicer
processor
stage
success/failure
validation error code
duration
```

Do not log full uploaded preset contents by default.

Do not log attachment credentials/tokens.

---

# 30. Processor Contract Tests

Create a reusable contract-test suite that every registered slicer processor will eventually be required to pass.

For P7.0 run it against:

```text id="rbgbyv"
BambuStudioProcessor
```

The contract should verify at minimum:

```text id="l9lb5v"
valid artifact accepted
malformed artifact rejected
wrong/invalid artifact rejected where detectable

input artifact not mutated

canonicalization deterministic

canonicalization semantically idempotent

required company policy applied

unknown valid fields preserved

canonical artifact serializable

serialized artifact parseable again

diff deterministic

identical semantic artifacts produce empty diff

added field represented
removed field represented
modified field represented

unknown changed field remains visible in diff

processor does not modify workflow state

processor does not publish
```

---

# 31. Real BambuStudio Fixture Corpus

Create/organize:

```text id="1c3yyh"
tests/fixtures/slicers/bambu_studio/
├── valid/
├── invalid/
├── legacy/
└── edge_cases/
```

Reuse existing real preset fixtures where available.

Do not fabricate all tests from tiny inline dictionaries.

At least some fixtures must come from real BambuStudio exported presets already available in the project/test assets.

If no real fixture exists for a category, document that instead of pretending a synthetic fixture is real.

---

# 32. Fixture Coverage

Where existing samples permit, cover:

```text id="6yrv95"
normal valid preset
inherits present
unknown/additional fields
non-ASCII values
missing required field
malformed JSON
wrong JSON top-level type
legacy/older preset if available
```

Do not broaden validation rules merely to make fixture categories exist.

---

# 33. Golden Canonicalization Test

For at least one representative real BambuStudio fixture:

```text id="l7pyu1"
input fixture
+
known ProcessingContext
```

store/verify expected canonical semantic output.

Explicitly verify:

```text id="xkoyn2"
name changed correctly
pm_method_version changed correctly
all unrelated fields preserved
```

This is a regression lock against accidental future canonicalization changes.

---

# 34. Golden Diff Test

Provide representative base/candidate BambuStudio fixtures with known changes.

Verify:

```text id="trg5zt"
changed paths
old values
new values
change types
categories
```

against existing approved behavior.

The purpose is to ensure refactoring does not silently change what M1/M3 reviewers see.

---

# 35. Round-Trip Processor Test

For a valid BambuStudio fixture:

```text id="1u76n2"
parse
→ validate
→ normalize
→ policy
→ validate canonical
→ serialize
→ parse serialized artifact
```

must succeed.

This does not replace manual BambuStudio import testing.

---

# 36. Manual Real-Slicer Regression

After automated tests pass, manually perform:

```text id="uoxkvi"
real BambuStudio export
        ↓
Submission upload
        ↓
Worker Preview
        ↓
formal Submit
        ↓
Reviewer
        ↓
Approve
        ↓
PresetVersion canonical artifact
        ↓
download artifact
        ↓
import into BambuStudio
```

Verify the imported preset:

```text id="4tstxs"
is recognized
is findable
has expected display behavior
contains expected parameters
```

This is mandatory P7.0 manual acceptance.

---

# 37. Existing Test Preservation

All existing relevant tests for:

```text id="wxm7pz"
M1
M2
M3
P1 enrichment
P3 publication
P5 projection
P6 polling
```

must continue to pass.

Update tests only where architecture changed.

Do not weaken assertions merely to make the refactor pass.

---

# 38. No Database Schema Expansion Unless Necessary

P7.0 should not require new Bitable business fields.

Do not introduce:

```text id="56m2gv"
processor_name
processor_version
artifact_type
schema_version
```

into Bitable merely because they may be useful later.

If implementation metadata is useful internally, keep it in code/logging unless there is a demonstrated persistence requirement.

---

# 39. Preserve Existing `canonical_json`

Do NOT rename the Bitable field:

```text id="7ks0xl"
canonical_json
```

in P7.0.

Artifact abstraction will be handled separately in P7.1.

However, new processor/workflow interfaces should avoid unnecessary assumptions that every future canonical artifact must always be JSON.

For BambuStudio in P7.0:

```text id="brm7mg"
canonical artifact = JSON bytes/file
```

---

# 40. Preserve Existing `uploaded_json`

Likewise, do NOT rename:

```text id="u9b5kt"
uploaded_json
```

in P7.0.

P7.1 may address generalized artifact naming.

Avoid unnecessary schema migration now.

---

# 41. No New Slicer-Specific UI

Miaoda remains BambuStudio-only from the processor capability perspective during P7.0.

Do not add placeholder:

```text id="6z6qkb"
Orca
Cura
Prusa
```

processing behavior.

If the UI already contains slicer options for future use, unsupported values must fail cleanly through the unsupported-processor path.

---

# 42. Code Organization

Prefer a structure conceptually similar to:

```text id="cx0h5n"
material_worker/
├── slicers/
│   ├── __init__.py
│   ├── base.py
│   ├── registry.py
│   ├── models.py
│   └── bambu_studio/
│       ├── __init__.py
│       ├── processor.py
│       ├── validation.py
│       ├── canonicalization.py
│       └── diff.py
```

Adapt to the repository's existing package structure.

Do not split trivial code into unnecessary files purely to match this example.

The important boundary is:

```text id="wod7sl"
workflow/domain
≠
slicer implementation
```

---

# 43. Dependency Direction

Desired dependency direction:

```text id="0rjj6d"
Workflow
   ↓
Processor Contract
   ↑
BambuStudio implementation
```

Avoid:

```text id="wn04an"
BambuStudio implementation
   ↓
SubmissionService internals
   ↓
PublicationService
```

Slicer code should not depend upward on workflow implementation details.

---

# 44. Compatibility Layer

If the existing code exposes public helper functions used extensively by tests/services, a temporary compatibility wrapper is acceptable.

Example conceptually:

```python id="m00e50"
def canonicalize_bambu_preset(...):
    return registry.get("BambuStudio").process(...)
```

But:

- new workflow code must use the processor abstraction;
- mark compatibility wrappers clearly;
- do not create two independent implementations.

There must be one source of processing behavior.

---

# 45. Do Not Over-Abstract

P7.0 must not attempt to predict every future slicer.

Avoid abstractions such as:

```text id="56s6le"
UniversalPreset
UniversalFilamentSchema
UniversalPrinterSchema
UniversalSlicerAST
```

unless already demonstrably required.

The contract should abstract **operations**, not invent a universal preset data model.

---

# 46. No Cross-Slicer Conversion

P7.0 does NOT support:

```text id="h0vgom"
BambuStudio → OrcaSlicer
BambuStudio → Cura
generic preset conversion
```

A processor handles artifacts belonging to its own slicer.

---

# 47. No Fully Expanded Universal Preset

Do not expand BambuStudio inheritance into a universal flattened preset as part of this refactor.

Preserve current canonical artifact semantics.

---

# 48. Performance

Processor abstraction should not introduce unnecessary repeated parsing.

Where reasonable:

```text id="bd0dxm"
parse once
operate on parsed representation
serialize once
```

Do not repeatedly:

```text id="0f3aap"
bytes → JSON → bytes → JSON
```

between every internal stage merely for architectural purity.

---

# 49. P7.0 Mandatory Regression Scenarios

At minimum automate these scenarios:

### Scenario A — Existing valid UPDATE

```text id="qz4x0v"
BambuStudio upload
→ Preview
→ formal enrichment
→ READY_FOR_REVIEW
```

Candidate canonical JSON and diff must match pre-refactor behavior.

### Scenario B — Existing valid CREATE

Same expected behavior as before.

### Scenario C — Malformed JSON

Must follow existing validation-failure behavior.

### Scenario D — Unknown field

Unknown valid field survives canonicalization and appears in diff if changed.

### Scenario E — Retry

Repeated processing of same Submission/context produces equivalent result.

### Scenario F — Unsupported slicer

Controlled unsupported-slicer failure.

No Bambu fallback.

### Scenario G — Publication

Existing BambuStudio Submission:

```text id="nbv0mb"
APPROVING
→ Worker
→ APPROVED
```

must publish exactly as before.

Processor refactor must not alter publication semantics.

---

# 50. Out of Scope

Do NOT implement in P7.0:

```text id="efktg7"
OrcaSlicer support
Cura support
PrusaSlicer support
multi-format Bitable schema migration
canonical_json rename
uploaded_json rename
cross-slicer conversion
universal preset schema
inheritance expansion
3MF parsing
3MF semantic validation
new review workflow
new publication workflow
working_base_version
new version conflict semantics
new diff UI
new Bitable fields solely for processor metadata
```

---

# Acceptance Criteria

P7.0 is complete when:

```text id="0tdxwg"
[ ] explicit SlicerProcessor contract exists

[ ] typed ProcessingContext exists

[ ] processor result / validation boundary is explicit

[ ] BambuStudio processing implements the contract

[ ] workflow obtains processors through one registry

[ ] unsupported slicer fails explicitly

[ ] workflow contains no Bambu-specific parsing logic

[ ] processor does not own Preset resolution

[ ] processor does not own workflow state

[ ] processor does not own review

[ ] processor does not own publication

[ ] Bambu canonicalization behavior is unchanged

[ ] name rule is unchanged

[ ] pm_method_version rule is unchanged

[ ] unrelated/unknown valid fields are preserved

[ ] original uploaded artifact is unchanged

[ ] processing is deterministic

[ ] processing is semantically idempotent

[ ] diff is processor-owned

[ ] diff result is slicer-neutral

[ ] current M1/M3 diff categories are preserved

[ ] unknown changed fields remain visible

[ ] real Bambu fixtures exist and are used

[ ] reusable processor contract tests exist

[ ] golden canonicalization regression passes

[ ] golden diff regression passes

[ ] round-trip processing regression passes

[ ] existing M1/M2/M3/P1/P3/P5/P6 tests pass

[ ] real BambuStudio export → publish → download → import manual regression passes

[ ] no new slicer is added

[ ] no unnecessary Bitable schema migration is introduced
```

# Completion Report

Report:

1. final processor interface;
2. final `ProcessingContext`;
3. processor result and validation models;
4. registry implementation;
5. BambuStudio processor code organization;
6. old Bambu-specific workflow logic removed/moved;
7. compatibility wrappers retained, if any;
8. exact Bambu canonicalization rules after refactor;
9. diff abstraction/result model;
10. unsupported-slicer behavior;
11. exception hierarchy;
12. fixture corpus added/reused;
13. processor contract test count/results;
14. golden canonicalization result;
15. golden diff result;
16. determinism/idempotency result;
17. unknown-field preservation result;
18. Preview regression result;
19. formal enrichment regression result;
20. CREATE/UPDATE regression result;
21. publication regression result;
22. full existing test-suite result;
23. manual BambuStudio export → publish → download → import result;
24. confirmation that no new slicer support was added;
25. confirmation that no publication/version/review semantics were changed;
26. any remaining Bambu-specific assumptions outside the processor layer that should be addressed in P7.1.