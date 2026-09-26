# P6.2b — Implement Worker PreviewService

## 0. Problem

P6.2 successfully discovers and dispatches:

```text
PREVIEW_REQUESTED
```

but runtime currently falls back to:

```python
_preview_service_unavailable()
```

and raises:

```text
RuntimeError:
PREVIEW_REQUESTED discovered but no M1-B preview service is configured
```

The polling/dispatch integration is working.

The missing component is the actual Worker-side preview-processing service.

Implement it now.

Do NOT redesign runtime polling.

---

# 1. Goal

Implement a real service with semantics equivalent to:

```python
preview_submission(submission_id)
```

and wire it into the existing runtime preview dispatch.

Expected end-to-end flow:

```text
Miaoda
   ↓
DRAFT → PREVIEW_REQUESTED
   ↓
Worker discovers record
   ↓
PreviewService
   ↓
validate
canonicalize
resolve Preset
resolve base
calculate diff
   ↓
write preview result
   ↓
DRAFT
```

---

# 2. Inspect Existing Enrichment Implementation First

Before writing PreviewService, inspect the current formal enrichment implementation.

Identify exactly where the following logic currently lives:

```text
load Submission
load uploaded JSON attachment
parse JSON
validate slicer input
canonicalize
resolve preset_key
resolve Preset
resolve CREATE / UPDATE
resolve base_version
load base canonical_json
calculate diff
write canonical_json
write validation result
write operation
write preset
write base_version
transition status
```

Do not duplicate this logic blindly.

Report the current service/module/function structure after implementation.

---

# 3. Separate Computation From Workflow Side Effects

The formal enrichment implementation likely combines:

```text
candidate computation
+
Submission workflow mutation
```

Preview needs the first part but not the second.

Refactor only as much as necessary to obtain a reusable candidate-processing core.

Conceptually:

```python
result = process_candidate(submission)
```

where the result contains the computed candidate information without performing workflow transitions.

For example:

```python
CandidateResult(
    operation=...,
    preset=...,
    base_version=...,
    canonical_json=...,
    validation=...,
    diff=...,
)
```

Use actual project types and conventions.

Do not introduce unnecessary abstractions.

---

# 4. Shared Candidate Processing

Both:

```text
PreviewService
```

and:

```text
formal EnrichmentService
```

must use the same candidate-processing implementation.

Desired architecture:

```text
                    process_candidate()
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ▼                           ▼
      PreviewService              EnrichmentService
             │                           │
      temporary result             formal snapshot
             │                           │
             ▼                           ▼
           DRAFT                 READY_FOR_REVIEW
```

There must not be two implementations of:

```text
BambuStudio validation
canonicalization
preset resolution
base resolution
diff
```

---

# 5. Preserve Existing Canonicalization Exactly

Do not change P1 semantics.

For BambuStudio, canonicalization remains exactly:

```python
canonical_json["name"] = f"{pi_code} @{printer}"
canonical_json["pm_method_version"] = submission.pm_method_version
```

Do not add additional semantic transformations.

The raw uploaded JSON must remain unchanged.

---

# 6. Preview State Guard

`preview_submission(submission_id)` must reload the authoritative Submission.

Require:

```text
status == PREVIEW_REQUESTED
```

If not:

```text
do not process
do not mutate preview fields
do not change status
```

Do not trust the state observed earlier by runtime discovery.

---

# 7. Preview Success Semantics

On successful candidate processing, PreviewService must write the preview result required by the current M1-B Miaoda implementation.

First inspect which fields Miaoda currently expects.

Do not invent incompatible field names.

The preview result should represent at least:

```text
operation
base version when UPDATE
validation success/result
canonical candidate
diff
preview metadata/revision/fingerprint if already implemented
```

Then transition:

```text
PREVIEW_REQUESTED
→ DRAFT
```

Only after the preview result has been written successfully.

---

# 8. Do Not Create Publication Artifacts

PreviewService must NEVER:

```text
create Preset
create PresetVersion
update Preset.current_version
set published_version
set APPROVED
project photos
```

Preview is read/compute/write-back only.

---

# 9. CREATE Preview

If no matching Preset exists:

```text
operation = CREATE
preset = null
base_version = null
```

Generate the canonical candidate.

Do not create the Preset.

Do not manufacture a fake base version.

---

# 10. UPDATE Preview

If exactly one matching Preset exists and has a valid:

```text
current_version
```

then:

```text
operation = UPDATE
preset = existing Preset
base_version = Preset.current_version
```

Load:

```text
base_version.canonical_json
```

and calculate diff against the newly generated canonical candidate.

---

# 11. Invalid Preset Resolution

Preserve existing formal enrichment rules.

### Duplicate Preset

If multiple Presets match the exact identity:

```text
preview failure
```

Do not select one arbitrarily.

### Missing current_version

If exactly one matching Preset exists but:

```text
current_version = empty
```

treat preview as invalid.

Do not infer the latest version from PresetVersion history.

---

# 12. Candidate Failure

Candidate/data errors include cases such as:

```text
malformed JSON
invalid slicer JSON
missing required input
duplicate Preset
invalid matching Preset
missing current_version
unsupported slicer
```

These are preview feedback, not Worker infrastructure failures.

Expected:

```text
PREVIEW_REQUESTED
        ↓
candidate processing fails
        ↓
write preview error
        ↓
DRAFT
```

The engineer regains ownership and can correct the Draft.

Do NOT transition to:

```text
VALIDATION_FAILED
```

for preview-time candidate errors.

---

# 13. Infrastructure Failure

Infrastructure failures are different:

```text
Feishu API unavailable
attachment download timeout
repository timeout
temporary network failure
unexpected storage error
```

Do not convert these into "invalid preset" feedback.

Prefer leaving the Submission:

```text
PREVIEW_REQUESTED
```

so a later Worker polling cycle can retry.

Raise/log the infrastructure exception according to existing runtime conventions.

---

# 14. Write Result Before Returning to DRAFT

Avoid:

```text
PREVIEW_REQUESTED
→ DRAFT
→ write preview fields
```

because Miaoda could regain edit ownership before the preview result is complete.

Preferred order:

```text
PREVIEW_REQUESTED
        ↓
compute
        ↓
write preview result
        ↓
verify write if repository convention requires
        ↓
status → DRAFT
```

The status transition is the ownership handoff.

---

# 15. Failure Result Ordering

For candidate failure:

```text
PREVIEW_REQUESTED
        ↓
write preview error
        ↓
status → DRAFT
```

Again, do not return ownership before feedback is persisted.

---

# 16. Preview Fields Must Match Miaoda Contract

Inspect the current M1-B Miaoda implementation/schema and identify exactly what it reads after preview completes.

Examples may include:

```text
canonical_json
diff
validation
operation
base_version
preview_error
preview_revision
```

Use the actual fields.

Do not create parallel fields that Miaoda does not read.

Document the contract in code/tests.

---

# 17. Preview Revision / Fingerprint

If M1-B already implemented:

```text
draft_revision
preview_revision
```

or an equivalent fingerprint mechanism, PreviewService must preserve that contract.

The preview result must identify which Draft input revision it processed.

Do not invent a second staleness mechanism.

If no revision/fingerprint exists yet, report this explicitly rather than silently designing an unrelated mechanism.

---

# 18. Formal Enrichment Must Still Recompute

After this refactor, formal:

```text
VALIDATING
```

must still independently call shared candidate processing.

Do NOT implement:

```text
if preview exists:
    copy preview into formal result
```

Formal enrichment must recompute against the current database state.

This protects against:

```text
preview base = v7
another publication creates v8
formal submit occurs later
```

Formal enrichment must resolve v8.

---

# 19. Preserve Formal Enrichment Behavior

Refactoring candidate computation must not change existing P1 behavior.

Run regression tests for:

```text
CREATE enrichment
UPDATE enrichment
canonicalization
diff
duplicate Preset
missing current_version
validation failure
READY_FOR_REVIEW transition
```

P6.2b is not an opportunity to redesign formal enrichment.

---

# 20. Runtime Wiring

Replace the current fallback:

```python
_preview_service_unavailable
```

with the actual PreviewService dependency.

The runtime should conceptually contain:

```text
preview action
    → preview_submission

enrich action
    → enrich_submission

publish action
    → publish_submission
```

Do not put preview business logic directly inside `runtime.py`.

`runtime.py` remains dispatcher/orchestration code.

---

# 21. Test — Runtime Wiring

Given:

```text
status = PREVIEW_REQUESTED
```

run:

```text
run_once()
```

Expected:

```text
preview_submission(id)
```

is invoked.

The error:

```text
PREVIEW_REQUESTED discovered but no M1-B preview service is configured
```

must no longer occur in normal configured runtime.

---

# 22. Test — CREATE Preview

Given:

```text
unique new preset identity
valid BambuStudio JSON
status = PREVIEW_REQUESTED
```

run Worker.

Expected:

```text
operation = CREATE
canonical candidate generated
no base_version
preview result persisted
status = DRAFT
```

And:

```text
Preset count unchanged
PresetVersion count unchanged
```

---

# 23. Test — UPDATE Preview

Given:

```text
existing Preset
current_version = v7
valid changed JSON
status = PREVIEW_REQUESTED
```

Expected:

```text
operation = UPDATE
base_version = v7
canonical candidate generated
diff calculated against v7
status = DRAFT
```

No publication artifacts created.

---

# 24. Test — Canonicalization Reuse

Verify PreviewService and EnrichmentService produce identical canonical candidate JSON for identical Submission inputs and identical database state.

This test is mandatory.

It proves canonicalization was not duplicated.

---

# 25. Test — Diff Reuse

For the same UPDATE candidate and same base:

```text
PreviewService diff
==
EnrichmentService diff
```

subject to the actual diff representation.

This test is mandatory.

---

# 26. Test — Candidate Error

Use malformed JSON.

Expected:

```text
preview error persisted
status returns to DRAFT
```

Worker continues running.

No:

```text
VALIDATION_FAILED
```

unless existing M1-B schema explicitly defines an equivalent preview-only result.

---

# 27. Test — Infrastructure Error

Simulate attachment/repository transient failure.

Expected:

```text
status remains PREVIEW_REQUESTED
exception propagates to runtime isolation layer
Worker logs failure
later records continue
```

---

# 28. Test — Stale State

Runtime discovers:

```text
PREVIEW_REQUESTED
```

but before service execution authoritative state becomes:

```text
DRAFT
```

Expected:

```text
PreviewService refuses processing
no preview fields changed
```

---

# 29. Test — Formal Recompute After Preview

Generate preview against:

```text
base = v7
```

Then legitimately advance:

```text
Preset.current_version = v8
```

Then formally submit:

```text
DRAFT → VALIDATING
```

Expected:

```text
formal enrichment base = v8
```

Do not reuse preview's v7 result.

---

# 30. Test — End-to-End Miaoda Flow

Use the real UI:

```text
Miaoda Draft
    ↓
upload JSON
    ↓
生成预览
    ↓
PREVIEW_REQUESTED
    ↓
preset-worker run
    ↓
PreviewService
    ↓
DRAFT
    ↓
Miaoda displays preview
```

No CLI/manual intervention should be necessary.

---

# 31. Acceptance Criteria

P6.2b is complete when:

```text
[ ] real PreviewService exists

[ ] runtime no longer uses _preview_service_unavailable in normal configuration

[ ] PREVIEW_REQUESTED dispatch reaches PreviewService

[ ] PreviewService has authoritative state guard

[ ] preview reuses formal candidate-processing logic

[ ] validation logic is not duplicated

[ ] canonicalization logic is not duplicated

[ ] Preset resolution logic is not duplicated

[ ] diff logic is not duplicated

[ ] CREATE preview works

[ ] UPDATE preview works

[ ] candidate errors return to DRAFT with feedback

[ ] infrastructure errors remain retryable

[ ] preview result is persisted before returning to DRAFT

[ ] preview never creates Preset

[ ] preview never creates PresetVersion

[ ] preview never changes Preset.current_version

[ ] formal enrichment still recomputes

[ ] existing formal enrichment regression tests pass

[ ] real Miaoda → Worker → Miaoda preview flow passes
```

---

# 32. Completion Report

After implementation report:

1. why `_preview_service_unavailable` existed;
2. where the new PreviewService lives;
3. its public entry point;
4. what candidate-processing code was extracted/reused;
5. whether formal enrichment required refactoring;
6. exact preview fields written;
7. exact success state transition;
8. exact candidate-error behavior;
9. exact infrastructure-error behavior;
10. how preview revision/fingerprint is handled;
11. result of CREATE preview test;
12. result of UPDATE preview test;
13. result of canonicalization-equivalence test;
14. result of diff-equivalence test;
15. result of formal-recompute-after-preview test;
16. result of real Miaoda end-to-end test;
17. confirmation that preview produces no publication artifacts.