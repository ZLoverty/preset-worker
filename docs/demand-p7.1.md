# P7.1 — Opaque Canonical Artifact Boundary

## 0. Goal

Complete the artifact abstraction started in P7.0.

After P7.1, the workflow/domain layer must treat slicer artifacts as **opaque data**.

The workflow may:

```text id="8bvgjx"
receive artifacts
store artifacts
pass artifacts to processors
persist processor results
attach artifacts to Feishu
publish artifacts
```

but must NOT:

```text id="uc3gk0"
parse artifact contents
assume JSON
inspect slicer-specific fields
derive filenames from artifact contents
depend on canonical artifact internal structure
```

P7.1 does NOT add a new slicer.

BambuStudio remains the only supported slicer.

---

# 1. Current Problems

P7.0 identified the following remaining runtime boundary leaks.

### 1.1 Workflow parses base canonical artifact

Current enrichment code directly performs behavior equivalent to:

```python id="4asqtn"
json.loads(base_artifact)
```

This assumes every slicer canonical artifact is JSON.

### 1.2 Workflow parses processor canonical output

Workflow currently parses the processor-produced canonical artifact.

Again, this assumes JSON.

### 1.3 Workflow reads Bambu-specific `name`

Current workflow contains behavior equivalent to:

```python id="hy37kr"
canonical.get("name")
```

to construct the attachment filename.

This leaks BambuStudio canonical structure into workflow.

### 1.4 CandidateResult exposes parsed JSON

Current:

```text id="7ytx5d"
CandidateResult.canonical_json: Any
```

causes workflow to carry a slicer-specific parsed representation.

### 1.5 Registry composition lives in enrichment

Current runtime construction directly instantiates:

```python id="9vltpb"
SlicerProcessorRegistry([
    BambuStudioProcessor()
])
```

inside workflow/service code.

This should become composition/configuration responsibility.

---

# 2. Core Architecture Rule

After P7.1:

```text id="o72j6l"
Workflow
   │
   │ opaque bytes + metadata
   ▼
Processor Contract
   │
   │ slicer-specific interpretation
   ▼
BambuStudioProcessor
```

The processor boundary is the only runtime layer allowed to interpret slicer artifact contents.

---

# 3. Introduce Opaque Artifact Model

Define a slicer-neutral artifact model.

Conceptually:

```python id="shp2b3"
@dataclass(frozen=True)
class Artifact:
    content: bytes
    filename: str
    media_type: str | None = None
```

Exact naming may follow current project conventions.

The important properties are:

```text id="szfpqs"
opaque bytes
filename
optional media/content type
```

Workflow may inspect metadata such as filename/media type.

Workflow must not inspect `content`.

---

# 4. Artifact Content Must Be Bytes

Canonical artifact content crossing the processor boundary must be serialized:

```text id="7awtn5"
bytes
```

not:

```text id="v8nzpc"
dict
Any
JSON object
processor-specific AST
```

For BambuStudio:

```text id="2w20cg"
dict
   ↓ processor serialize
JSON bytes
   ↓
Artifact.content
```

The parsed dictionary remains private to the BambuStudio processor.

---

# 5. Processor Output

Replace the workflow-facing parsed canonical representation with an artifact.

Conceptually:

```python id="ztcftf"
@dataclass(frozen=True)
class ProcessedArtifact:
    canonical_artifact: Artifact
    validation_result: ValidationResult
```

If other existing processor-neutral metadata is required, retain it explicitly.

Do not expose the Bambu parsed dictionary through this result.

---

# 6. CandidateResult

Refactor:

```text id="h5k3qz"
CandidateResult.canonical_json: Any
```

into a slicer-neutral artifact representation.

Prefer conceptually:

```python id="zrl9ai"
@dataclass(frozen=True)
class CandidateResult:
    canonical_artifact: Artifact
    ...
```

or equivalent.

There must be no workflow-facing field whose runtime contract means:

```text id="xk9c6f"
parsed canonical JSON
```

---

# 7. Preserve Feishu Schema

Do NOT rename the existing Bitable fields:

```text id="kb6a7n"
Submission.uploaded_json
Submission.canonical_json
PresetVersion.canonical_json
```

in P7.1.

These are currently storage-schema names.

Treat them as legacy business/storage naming.

Internally:

```text id="a4eg4b"
canonical_json Bitable field
        ↑
Artifact
```

The application model does not need to inherit the storage field name.

---

# 8. Repository Translation Boundary

Repository/storage adapters may know that the Feishu field is called:

```text id="hnhy8o"
canonical_json
```

but services above that boundary should use:

```text id="pbf8zp"
canonical_artifact
```

where practical.

Do not perform a broad risky schema rename.

Translate between:

```text id="g38g6y"
domain/application name
↕
Feishu storage field name
```

at the repository boundary.

---

# 9. Uploaded Artifact

Apply the same architectural principle to processor input.

The processor should receive uploaded content as an opaque artifact/bytes representation.

Workflow may retrieve:

```text id="g0x8s3"
Submission.uploaded_json attachment
```

from storage.

But once loaded:

```text id="vnhstz"
uploaded artifact bytes
        ↓
processor
```

Workflow must not parse it.

---

# 10. Remove Workflow JSON Parsing

Remove all slicer-artifact parsing from enrichment/workflow.

Specifically eliminate runtime behavior equivalent to:

```python id="bbq0d8"
json.loads(base_artifact)
json.loads(candidate_artifact)
```

from enrichment.

After P7.1:

```text id="x0p30r"
base artifact bytes
candidate artifact bytes
        ↓
processor.diff(...)
```

The processor owns interpretation.

---

# 11. Base Artifact Diff

For UPDATE:

```text id="emqlcz"
PresetVersion.canonical_json
        ↓ repository
base Artifact
        ↓
processor.diff(base, candidate)
```

Workflow must not parse base artifact before calling the processor.

For BambuStudio:

```text id="95a1pz"
BambuStudioProcessor.diff(...)
```

may internally parse both JSON artifacts.

That is correct.

---

# 12. Candidate Artifact Diff

Likewise, workflow passes:

```text id="7qjcg3"
candidate.canonical_artifact
```

directly to:

```text id="i22m0v"
processor.diff(...)
```

No intermediate JSON conversion in workflow.

---

# 13. Processor Owns Serialization

For BambuStudio:

```text id="4rt2gm"
parse source JSON
validate
normalize
apply policy
validate canonical
serialize JSON
```

The result crossing back into workflow is already serialized.

Workflow must not call:

```text id="t6kq8i"
json.dumps(...)
```

on processor canonical data.

---

# 14. Processor Owns Deserialization

Similarly, when processor needs to inspect a stored canonical artifact:

```text id="jmrnpi"
Artifact.content
        ↓
BambuStudioProcessor
        ↓
json.loads(...)
```

is valid.

JSON parsing inside BambuStudio processor/helpers is expected.

JSON parsing in generic workflow/domain code is not.

---

# 15. Artifact Filename Ownership

Remove workflow behavior equivalent to:

```python id="5fylyb"
canonical.get("name")
```

for filename generation.

The processor must return the canonical artifact with an appropriate filename.

Example:

```python id="fyxg6c"
Artifact(
    content=...,
    filename="L2002CF @BBL P2S.json",
    media_type="application/json",
)
```

Exact filename convention must preserve current BambuStudio behavior.

---

# 16. Filename Is Metadata, Not Canonical Content

Workflow may read:

```text id="9oz9ce"
artifact.filename
```

because this is slicer-neutral artifact metadata.

Workflow must not reconstruct the filename by inspecting:

```text id="w95np9"
artifact.content
```

---

# 17. BambuStudio Filename

Move the existing Bambu filename rule into:

```text id="rvy1yi"
BambuStudioProcessor
```

or a Bambu-specific artifact builder/helper.

Preserve existing user-visible filename behavior exactly unless an existing bug requires correction.

Do not use P7.1 to redesign naming.

---

# 18. Media Type

For BambuStudio canonical artifacts:

```text id="h30htm"
media_type = application/json
```

is appropriate if useful to the existing attachment/storage implementation.

Do not make workflow behavior depend on:

```text id="9r2n5v"
media_type == application/json
```

Media type is metadata, not a processing dispatch mechanism.

Processor selection remains based on:

```text id="n07s4v"
Submission.slicer
```

---

# 19. Processor Diff Contract

Refine the P7.0 processor contract so diff consumes opaque artifacts.

Conceptually:

```python id="u5okqw"
def diff(
    self,
    base: Artifact,
    candidate: Artifact,
    context: ProcessingContext,
) -> UnifiedDiff:
    ...
```

or equivalent.

Do not require workflow to convert artifacts into slicer-specific objects first.

---

# 20. Processor Processing Contract

Prefer a workflow-facing operation conceptually similar to:

```python id="y4qt85"
def process(
    self,
    uploaded: Artifact,
    context: ProcessingContext,
) -> ProcessedArtifact:
    ...
```

Internal staged methods from P7.0 may remain:

```text id="rcj9f2"
parse
validate_source
normalize
apply_company_policy
validate_canonical
serialize
```

but their intermediate types are processor-private.

---

# 21. Internal Processor Types

BambuStudioProcessor may internally use:

```python id="y1dx8b"
dict[str, Any]
```

for parsed JSON.

That is completely acceptable.

P7.1 does NOT attempt to remove JSON from BambuStudio.

The requirement is:

> JSON must not cross the slicer processor boundary as the workflow representation of the canonical artifact.

---

# 22. Registry Composition

Move default processor composition out of enrichment/service implementation.

Introduce a composition helper/module conceptually:

```python id="4a0kuc"
def default_processor_registry() -> SlicerProcessorRegistry:
    return SlicerProcessorRegistry([
        BambuStudioProcessor(),
    ])
```

Place it in an appropriate composition/bootstrap/registry module.

---

# 23. Dependency Injection

Prefer services to receive:

```text id="ohql6c"
SlicerProcessorRegistry
```

through construction/dependency injection.

For convenience, production/bootstrap code may call:

```text id="pmzn8u"
default_processor_registry()
```

Do not instantiate `BambuStudioProcessor` directly inside enrichment business logic.

---

# 24. Tests May Inject Registry

Tests should be able to provide:

```text id="9vl1t9"
fake processor
test processor
custom registry
```

without patching BambuStudio implementation internals.

This will be important for future slicers.

---

# 25. No Slicer Inference

Do not use:

```text id="vh0agq"
artifact filename
file extension
media type
JSON content
printer
```

to select processor.

Continue using the authoritative:

```text id="2wl6ev"
Submission.slicer
```

---

# 26. Preview Integration

Preview path becomes conceptually:

```text id="9gsc7j"
uploaded attachment
        ↓
opaque Artifact
        ↓
registry.get(slicer)
        ↓
processor.process(...)
        ↓
ProcessedArtifact.canonical_artifact
        ↓
store preview canonical attachment
```

If UPDATE:

```text id="54qk6c"
base canonical attachment
        ↓
opaque Artifact
        ↓
processor.diff(base, candidate)
```

No workflow JSON parsing.

---

# 27. Formal Enrichment Integration

Formal enrichment follows the same processor boundary.

Conceptually:

```text id="ahxyfr"
Submission.uploaded_json
        ↓
Artifact
        ↓
processor.process(...)
        ↓
canonical Artifact
        ↓
persist Submission.canonical_json
```

For UPDATE:

```text id="nn70vw"
base Artifact
+
candidate Artifact
        ↓
processor.diff(...)
        ↓
UnifiedDiff
```

No workflow parsing.

---

# 28. Publication Integration

Publication currently does not parse canonical content.

Preserve that property.

Publication should continue conceptually:

```text id="i0d2ug"
Submission canonical attachment
        ↓
PresetVersion canonical attachment
```

without caring whether the artifact is:

```text id="p6ttck"
JSON
INI
CFG
ZIP
binary
```

Do not introduce new publication parsing in P7.1.

---

# 29. Download Integration

Current-version download should use stored canonical artifact directly.

Conceptually:

```text id="w3omyp"
Preset.current_version
        ↓
PresetVersion.canonical_json attachment
        ↓
download
```

Do not parse/rebuild the artifact for download.

Preserve its processor-generated filename where storage allows.

---

# 30. Exact Artifact Preservation

Once the processor produces:

```text id="q71iqv"
canonical_artifact.content
```

workflow/storage should preserve that serialized artifact without semantic reconstruction.

Do not:

```text id="a7z2sc"
parse
pretty-print
reorder
re-serialize
inject fields
```

after the processor boundary.

---

# 31. Validation Result Remains Structured

Keep P7.0 structured validation/error behavior.

Artifact abstraction must not collapse validation into generic exceptions.

The workflow should still distinguish:

```text id="cpln0n"
user artifact invalid
unsupported slicer
internal processor failure
```

without inspecting artifact contents.

---

# 32. Artifact Integrity Tests

Add tests verifying that processor-produced canonical bytes survive:

```text id="9psm53"
processor
→ workflow
→ attachment persistence boundary
```

without semantic modification.

Where exact byte preservation is supported by current storage test doubles, assert byte equality.

At minimum verify semantic equality for BambuStudio if attachment infrastructure changes transport encoding.

---

# 33. No Parsed Candidate Leakage

Add a repository-wide/runtime-path check.

There should be no generic workflow access such as:

```python id="a64h2e"
candidate.canonical_json["..."]
candidate.canonical_json.get(...)
json.loads(candidate.canonical_artifact.content)
```

outside slicer implementation code.

Tests may parse artifacts to assert results.

Production workflow code may not.

---

# 34. No Base Artifact Leakage

Likewise, no generic workflow production code should parse:

```text id="hnn9bk"
PresetVersion canonical artifact
```

for diff or metadata.

Pass it to the selected processor.

---

# 35. Contract Test Update

Update P7.0 processor contract tests so the public processor boundary uses opaque artifacts.

Verify:

```text id="fs1syx"
processor accepts Artifact
processor returns Artifact
canonical content is bytes
filename is present
diff accepts Artifact
diff returns UnifiedDiff
```

---

# 36. Fake Non-JSON Processor Boundary Test

P7.1 must NOT implement another slicer.

However, add a **test-only fake processor** whose artifact is deliberately non-JSON.

Example content:

```text id="ypdrm6"
b"THIS IS NOT JSON"
```

The purpose is architectural.

Run it through the generic candidate/enrichment path far enough to prove that workflow does not call:

```text id="2dlgyb"
json.loads(...)
```

on the artifact.

This is a very important P7.1 test.

---

# 37. Fake Processor Requirements

The fake processor may:

```text id="v5wr11"
accept arbitrary bytes
return arbitrary canonical bytes
return a filename such as preset.fake
return a deterministic UnifiedDiff
```

It must exist only in tests.

Do not register it in production.

---

# 38. Non-JSON UPDATE Test

Using the fake processor, test:

```text id="rq5rsm"
base artifact = non-JSON bytes
candidate artifact = non-JSON bytes
        ↓
generic enrichment
        ↓
processor.diff(...)
```

Expected:

```text id="dhy9k1"
workflow succeeds through the processor boundary
workflow never parses artifact
```

This is stronger evidence than merely searching for `json.loads`.

---

# 39. Filename Test

Fake processor returns:

```text id="m6eb1q"
filename = "example.fake"
```

Expected workflow/storage uses:

```text id="szsl8c"
example.fake
```

without inspecting artifact contents.

This proves removal of:

```text id="uvqydt"
canonical["name"]
```

dependency.

---

# 40. Bambu Regression

Existing BambuStudio behavior must remain unchanged.

Verify at minimum:

```text id="5sxbr0"
canonical content semantics
canonical filename
Preview
formal enrichment
diff
CREATE
UPDATE
validation failure
publication
download
```

---

# 41. JSON Imports

Do not mechanically ban:

```python id="5yns6j"
import json
```

from the entire services package if JSON is used for unrelated workflow data such as serialized diff or API payloads.

The rule is narrower and more important:

> Generic workflow must not parse or serialize slicer artifact contents.

Review remaining `json.loads/json.dumps` usages by purpose.

Document legitimate non-artifact JSON usages.

---

# 42. Storage Adapter May Handle Transport

Repository/storage adapters may need to:

```text id="olbxj9"
upload bytes
download bytes
construct attachment metadata
```

This is allowed.

They must not interpret slicer semantics.

---

# 43. Migration Scripts

Do NOT refactor:

```text id="d78y5m"
scripts/migrate_to_submission.py
```

in P7.1.

Its existing:

```text id="36my0k"
printer → slicer inference
Bambu printer mappings
legacy default slicer versions
```

are historical migration concerns, not runtime processing.

Document them as intentional legacy/migration-layer assumptions.

They must not be used as examples for new runtime code.

---

# 44. No Feishu Schema Migration

Do NOT rename:

```text id="mv0b9p"
uploaded_json
canonical_json
```

in Bitable during P7.1.

Do not create duplicate:

```text id="4utuz3"
uploaded_artifact
canonical_artifact
```

columns merely for naming purity.

The abstraction belongs in application code first.

---

# 45. No Universal Artifact Schema

Do not introduce:

```text id="z2svcv"
UniversalPreset
UniversalSlicerDocument
UniversalPresetJSON
```

P7.1 treats content as opaque.

That is the abstraction.

---

# 46. No Format Conversion

Do not convert:

```text id="61mx6n"
INI → JSON
CFG → JSON
binary → JSON
```

to satisfy the existing workflow.

Future processors should be free to emit their natural canonical artifact format.

---

# 47. No Artifact-Type Branching in Workflow

Avoid future-hostile logic such as:

```python id="8gsxf9"
if artifact.media_type == "application/json":
    ...
elif artifact.media_type == "...":
    ...
```

in enrichment.

Format-specific behavior belongs in processors.

---

# 48. No New Slicer

Do NOT implement:

```text id="bdj8af"
OrcaSlicerProcessor
CuraProcessor
PrusaSlicerProcessor
```

in P7.1.

The fake non-JSON processor is test-only.

---

# 49. Desired Runtime Boundary After P7.1

The final runtime flow should resemble:

```text id="dm9bkh"
                    WORKFLOW
                       │
                       │ Submission.slicer
                       ▼
                ProcessorRegistry
                       │
                       ▼
                  Processor
                       │
uploaded Artifact ─────┤
                       │
                       ▼
              canonical Artifact
              ┌────────────────┐
              │ bytes          │
              │ filename       │
              │ media_type     │
              └────────────────┘
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
          storage          processor.diff()
                               ▲
                               │
                         base Artifact
```

At no point does generic workflow need to know what is inside `bytes`.

---

# 50. Architecture Verification

After implementation, search runtime production code for artifact-content assumptions.

Specifically inspect:

```text id="ffl1n8"
json.loads
json.dumps
["name"]
.get("name")
canonical_json
dict[str, Any]
BambuStudioProcessor(
```

Do not blindly remove all matches.

Classify each remaining occurrence as:

```text id="70pyb5"
processor implementation
storage schema mapping
unrelated JSON
legacy migration
test
runtime boundary leak
```

There must be no remaining runtime boundary leak in generic workflow.

---

# Mandatory Tests

At minimum add/update automated tests for:

```text id="8c8y5i"
[ ] Bambu processor accepts opaque uploaded Artifact

[ ] Bambu processor returns canonical Artifact

[ ] canonical Artifact.content is bytes

[ ] canonical Artifact.filename matches existing behavior

[ ] workflow does not parse candidate artifact

[ ] workflow does not parse base artifact

[ ] workflow does not read canonical["name"]

[ ] UPDATE diff receives opaque base/candidate artifacts

[ ] fake non-JSON CREATE candidate passes generic processing boundary

[ ] fake non-JSON UPDATE passes generic diff boundary

[ ] fake processor filename is used unchanged

[ ] unsupported slicer behavior unchanged

[ ] Bambu Preview unchanged

[ ] Bambu formal enrichment unchanged

[ ] Bambu CREATE unchanged

[ ] Bambu UPDATE unchanged

[ ] Bambu validation failure unchanged

[ ] Bambu diff unchanged

[ ] Bambu publication unchanged

[ ] Bambu current-version download unchanged

[ ] processor-produced canonical artifact survives persistence without semantic reconstruction

[ ] default registry is composed outside enrichment business logic

[ ] custom registry can be injected in tests
```

---

# Manual Acceptance

Perform one real BambuStudio end-to-end regression:

```text id="i2tltq"
real exported JSON
        ↓
Miaoda Draft
        ↓
Preview
        ↓
Submit
        ↓
READY_FOR_REVIEW
        ↓
Approve
        ↓
PresetVersion
        ↓
Download current JSON
        ↓
Import into BambuStudio
```

Verify:

```text id="l5hlz6"
preset imports successfully
display behavior unchanged
expected parameters unchanged
filename behavior unchanged
```

No new manual test for another slicer is required in P7.1.

---

# Out of Scope

Do NOT implement:

```text id="u6k7xl"
OrcaSlicer
Cura
PrusaSlicer

Feishu uploaded_json rename
Feishu canonical_json rename

migration script cleanup

cross-slicer conversion

universal preset schema

artifact format conversion

new diff UI

new review workflow

new publication semantics

new version conflict semantics

working_base_version

3MF semantic parsing
```

---

# Acceptance Criteria

P7.1 is complete when:

```text id="7u9rcy"
[ ] workflow treats slicer artifacts as opaque

[ ] canonical artifact crosses processor boundary as bytes

[ ] CandidateResult no longer exposes parsed canonical JSON

[ ] workflow no longer parses base canonical artifact

[ ] workflow no longer parses candidate canonical artifact

[ ] workflow no longer reads canonical["name"]

[ ] processor owns canonical artifact filename

[ ] processor owns serialization/deserialization

[ ] processor.diff accepts opaque artifacts

[ ] existing UnifiedDiff remains slicer-neutral

[ ] registry composition is outside enrichment business logic

[ ] registry remains injectable

[ ] fake non-JSON processor proves generic workflow is format-agnostic

[ ] existing Bambu behavior remains unchanged

[ ] existing Feishu schema remains unchanged

[ ] migration legacy assumptions remain isolated

[ ] publication remains artifact-content agnostic

[ ] current-version download does not reconstruct artifact

[ ] no new slicer support is introduced
```

# Completion Report

Report:

1. final `Artifact` model;
2. final `ProcessedArtifact` model;
3. final `CandidateResult` model;
4. processor public method signatures;
5. how uploaded attachment becomes an Artifact;
6. how canonical Artifact is persisted to `canonical_json`;
7. how base canonical attachment becomes an Artifact;
8. how UPDATE diff now works without workflow parsing;
9. where Bambu JSON parsing now lives;
10. where Bambu JSON serialization now lives;
11. where canonical filename is generated;
12. confirmation that workflow no longer reads `canonical["name"]`;
13. registry composition implementation;
14. dependency-injection behavior;
15. fake non-JSON CREATE test result;
16. fake non-JSON UPDATE/diff test result;
17. fake filename propagation test result;
18. Bambu Preview regression result;
19. Bambu formal enrichment regression result;
20. Bambu CREATE/UPDATE regression result;
21. Bambu diff regression result;
22. Bambu publication regression result;
23. Bambu download regression result;
24. real BambuStudio end-to-end manual regression result;
25. remaining `json.loads/json.dumps` occurrences and classification;
26. remaining `canonical_json` occurrences and classification;
27. remaining Bambu-specific assumptions outside slicer processor code;
28. full test-suite result.