# Preset Worker — P5: Current Projection Framework & Photo Projection

## 0. Goal

Implement a small, explicit **Current Projection framework** for publication.

The first real use case is process-photo projection:

```text id="lvy1zq"
Submission
    │
    │ successful publication
    ▼
Preset
```

`Submission` remains the historical source of truth for process records.

`Preset` exposes the process records associated with the **currently published version** for downstream consumers.

P5 must support:

```text id="qqr3kz"
1. explicitly named standard photo fields required by downstream consumers
2. one additional "other photos" attachment field for non-standard photos
3. full replacement semantics
4. attachment transfer between Submission and Preset
5. a small projection architecture that can later support non-photo process fields
```

P5 must NOT redesign P1–P4 business logic.

---

# 1. Core Data Semantics

The three tables have different responsibilities:

```text id="etmhq5"
Submission
────────────────────────
historical source record
raw/candidate data
process photos
review information


PresetVersion
────────────────────────
immutable published version
canonical_json
source_submission → Submission


Preset
────────────────────────
current published projection
current_version → PresetVersion
current process-record fields
```

Process photos remain historically owned by Submission.

Do NOT duplicate historical photos into PresetVersion.

Historical retrieval remains:

```text id="al1mg6"
PresetVersion
      ↓ source_submission
Submission
      ↓
process photos
```

Preset only contains the process records associated with its current published version.

---

# 2. Why Projection Exists

Downstream consumers require specific columns to exist directly in Preset.

Therefore downstream access must NOT require:

```text id="y97oqx"
Preset
  ↓ current_version
PresetVersion
  ↓ source_submission
Submission
  ↓ photo
```

Instead:

```text id="0umjhk"
Preset.standard_photo_field
Preset.other_photos
```

must directly expose the current published process photos.

These fields are a **materialized current projection**, not historical source data.

---

# 3. Inspect Existing Repository First

Before editing:

1. inspect the P4 package structure;
2. run the complete existing test suite;
3. inspect `publication` service;
4. inspect Submission/Preset/PresetVersion models;
5. inspect Feishu repositories/adapters;
6. inspect current attachment handling for `canonical_json`;
7. inspect actual Submission and Preset field mappings;
8. identify the real standard photo field names already required by downstream consumers;
9. identify the actual "other photos" field name;
10. inspect whether existing code already supports writing attachment fields.

Do not guess field names if they already exist in configuration/schema.

Use the actual current schema.

Record the baseline test result before modification.

---

# 4. Do Not Invent Photo Categories

P5 must use the actual configured Submission/Preset photo fields.

Conceptually they may look like:

```text id="9l8hke"
first_layer_photo
finished_print_photo
surface_photo
other_photos
```

but these names are examples only.

Do NOT create these example fields unless they match the actual schema.

The implementation should make the list of projected photo fields explicit and centralized.

---

# 5. Standard Photo Fields + Other Photos

The projection consists of:

```text id="m5tpm0"
standard named photo fields
+
other_photos
```

Standard fields exist because downstream consumers require specific columns.

`other_photos` exists because the fixed downstream schema cannot represent every useful process photo.

The semantic rule is:

> `other_photos` contains supplementary photos that do not belong to one of the standard photo categories.

Do not use `other_photos` as a substitute for a missing standard photo field.

For example, if:

```text id="yd2upq"
standard_photo_A = empty
```

but a photo that semantically belongs to category A is stored in:

```text id="57i0xq"
other_photos
```

P5 should NOT reinterpret or automatically move it into category A.

Projection copies fields according to their explicit schema.

---

# 6. Submission and Preset Field Mapping

Prefer same-name mapping when possible:

```text id="czm2d1"
Submission.first_layer_photo
        ↓
Preset.first_layer_photo

Submission.finished_print_photo
        ↓
Preset.finished_print_photo

Submission.other_photos
        ↓
Preset.other_photos
```

However, do not assume the actual existing table field names are identical.

If Submission and Preset use different names, support an explicit mapping:

```python id="st0kh5"
source_field -> target_field
```

Do NOT scatter field-name translation across publication code.

---

# 7. Centralized Projection Specification

Define projection fields in one clear location.

For example, conceptually:

```python id="1exqg6"
PHOTO_PROJECTIONS = [
    AttachmentProjection(
        source_field="...",
        target_field="...",
    ),
    AttachmentProjection(
        source_field="...",
        target_field="...",
    ),
]
```

The exact representation should follow the existing P4 architecture.

A simple dataclass/config object/list is sufficient.

Do NOT introduce a plugin framework.

Do NOT introduce runtime schema discovery unless the existing project already uses it.

The goal is:

> adding another projected field later should require a small, obvious schema/config change rather than modifying publication business logic.

---

# 8. Projection Framework

Introduce a small projection abstraction/service with semantics equivalent to:

```python id="6ew0r7"
project_current_state(
    submission,
    preset,
)
```

or:

```python id="bsfsod"
projection_service.project(
    submission,
    preset,
)
```

The exact naming should match the current code style.

The publication service should NOT contain individual photo-specific statements such as:

```python id="56gnt5"
copy_first_layer_photo(...)
copy_finished_photo(...)
copy_surface_photo(...)
```

Instead publication should invoke one projection operation.

Conceptually:

```text id="et0jqk"
PublicationService
        │
        ├── create/recover PresetVersion
        ├── update current_version
        ├── project current state
        │       ↓
        │   ProjectionService
        │       ↓
        │   attachment adapter
        │
        └── finalize Submission
```

---

# 9. Keep the Framework Small

Although this is called a projection framework, P5 only needs to implement attachment/photo projection.

Do NOT implement speculative projection types for:

```text id="8aqj1i"
temperature
humidity
notes
print duration
machine telemetry
operator data
```

unless such fields already exist and are explicitly part of the current photo/process requirement.

The architecture should make future extension easy, but P5 should only implement what is currently needed.

---

# 10. Full Replacement Semantics

Projection uses **full replacement semantics**.

Suppose current Preset contains:

```text id="2yb5u7"
standard_photo_A = A
standard_photo_B = B
other_photos = [C, D]
```

and the newly published Submission contains:

```text id="6qyn8r"
standard_photo_A = E
standard_photo_B = F
other_photos = [G]
```

After publication:

```text id="cij3wu"
Preset.standard_photo_A = E
Preset.standard_photo_B = F
Preset.other_photos = [G]
```

NOT:

```text id="f9v7wb"
Preset.other_photos = [C, D, G]
```

Preset represents the current published Submission's process record.

It is not an accumulating photo archive.

---

# 11. Empty Means Clear

An empty projected source field must clear the corresponding Preset field.

Example:

current Preset:

```text id="mjdvxf"
surface_photo = A
```

new published Submission:

```text id="w3swj7"
surface_photo = empty
```

after projection:

```text id="hmlygc"
Preset.surface_photo = empty
```

Do NOT retain A.

Otherwise Preset would falsely expose a historical photo as belonging to the new current version.

This applies to:

```text id="81nztc"
single-photo fields
multi-photo fields
other_photos
```

Projection therefore means:

```text id="b04e8g"
target := source
```

not:

```text id="iqwldl"
target := target + source
```

and not:

```text id="7gq2g4"
if source is empty:
    keep target
```

---

# 12. Projection Happens Only During Successful Publication

Do NOT project photos when Submission is:

```text id="ecapml"
VALIDATING
READY_FOR_REVIEW
```

Projection belongs to publication of an approved candidate.

The intended relationship is:

```text id="5tp73q"
Submission
status = APPROVING
        │
        │ publish
        ▼
PresetVersion created/recovered
        │
        ▼
Preset.current_version updated
        │
        ▼
current projection updated
        │
        ▼
Submission.status = APPROVED
```

Do not set `APPROVED` before the current projection has succeeded.

---

# 13. Projection Must Match current_version

This invariant is important:

> Preset projected process records must correspond to Preset.current_version.

If:

```text id="shrm2a"
Preset.current_version = v8
```

and:

```text id="9z0ygg"
v8.source_submission = S123
```

then:

```text id="nxoqpa"
Preset projected photo fields
```

must represent:

```text id="bhwjpe"
S123 photo fields
```

Do not knowingly leave:

```text id="0v6n1i"
current_version = v8
photos from v7
```

as a successful final state.

---

# 14. Projection and Partial Failure

Bitable publication spans multiple writes and is not assumed transactional.

Example:

```text id="opmnkh"
create PresetVersion v8       SUCCESS
update current_version        SUCCESS
project photo A               SUCCESS
project photo B               FAILURE
```

The Submission must NOT be marked:

```text id="etb6sv"
APPROVED
```

at this point.

A later retry must be able to repair the projection.

P5 must integrate with the P3 idempotent publication/recovery behavior.

---

# 15. Recovery Behavior

P3 already uses:

```text id="48f0jf"
PresetVersion.source_submission
```

as the publication idempotency key.

If a PresetVersion already exists for the Submission because an earlier attempt partially succeeded, P5 must NOT skip projection repair.

Conceptually:

```text id="ed8d97"
existing PresetVersion found
        ↓
verify safe recovery
        ↓
repair current_version if appropriate
        ↓
re-run projection from source Submission
        ↓
repair published_version
        ↓
APPROVED
```

Because projection is full replacement:

```text id="d1fpcp"
project(source, target)
```

should itself be naturally idempotent.

Running it twice should result in the same Preset state.

---

# 16. Do Not Roll Back Newer Published State

Preserve the P3 recovery safety rule.

Suppose:

```text id="ij3jhv"
S123 → v8
S124 → v9

Preset.current_version = v9
```

A late retry of S123 must NOT:

```text id="jjqfdt"
set current_version back to v8
```

and must also NOT:

```text id="1ic3k8"
replace v9 photos with S123/v8 photos
```

This is critical.

Projection repair is only valid when the Submission being recovered corresponds to the Preset version that is supposed to be current.

Before projecting during recovery, verify the publication state.

At minimum:

```text id="dnp3w7"
Preset.current_version
```

must not represent a newer legitimate version.

Do not allow stale retries to roll back either:

```text id="vtd0z6"
current_version
```

or:

```text id="bn9uj8"
current projection fields
```

---

# 17. Attachment Transfer Must Be an Adapter Concern

The projection service decides:

```text id="jggvsy"
which source attachment field
maps to
which target attachment field
```

It should NOT own low-level Feishu file-transfer details.

Those belong in the Feishu adapter layer.

Conceptually:

```text id="uqub8r"
ProjectionService
        │
        ▼
AttachmentTransfer / Feishu adapter
        │
        ▼
Bitable attachment field
```

Keep business mapping separate from transport/storage mechanics.

---

# 18. Determine the Real Feishu Attachment Transfer Mechanism

Do not assume attachment tokens can be copied across records without verification.

P5 must determine and test the actual mechanism supported by the current Feishu/Bitable API and current Base permissions.

Prefer the simplest verified mechanism.

Candidate A:

```text id="rlweu7"
read source attachment file_token
        ↓
write same file_token to target attachment field
```

If this is verified to work reliably for the relevant Submission → Preset records, use it.

Candidate B:

```text id="8tmm6p"
read/download source attachment
        ↓
upload attachment for target context
        ↓
receive new file_token
        ↓
write new token to Preset
```

Use this if direct token reuse is unsupported or unreliable.

Do not select a mechanism based on assumption alone.

---

# 19. Add a Real Feishu Integration Test

P5 must include or provide a focused integration test against the configured development/test Bitable environment.

The test should verify the actual attachment behavior.

Minimum scenario:

```text id="m02pcu"
1. identify/create a Submission test record
2. ensure a source attachment exists
3. read the attachment through the Worker
4. project/copy it to a Preset test record
5. read the Preset record again
6. verify the target attachment field is populated
7. verify the target attachment is actually accessible/usable
```

If direct token reuse is tested:

```text id="5x47ha"
source token = A
target write token = A
```

verify that the resulting target attachment can actually be accessed.

Do not treat an HTTP 200 update alone as proof that the attachment projection is valid.

---

# 20. Integration Test Must Be Safe

Do not run destructive attachment experiments against arbitrary production Presets.

Use:

```text id="a46o1m"
dedicated test records
development/test Base
or explicitly configured integration-test records
```

according to the project's existing integration-test strategy.

Do not hard-code a personal production record ID into normal package code.

Test configuration may use environment variables or existing test configuration mechanisms.

---

# 21. Attachment Order

For multi-attachment fields such as:

```text id="at4vn2"
other_photos
```

preserve source attachment ordering where the Feishu API provides a meaningful order.

Do not arbitrarily sort attachments by:

```text id="km6pjr"
filename
file_token
upload timestamp
```

unless required by an existing business rule.

Projection should preserve the Submission representation as closely as practical.

---

# 22. Attachment Metadata

Do not attempt to reinterpret photo metadata during projection.

Preserve the attachment content and normal Feishu attachment identity/metadata as supported by the chosen transfer mechanism.

Do not rename files unless required by the API.

Do not generate semantic filenames in P5.

Do not compress or transform images.

P5 is projection, not image processing.

---

# 23. Projection Specification Should Support Cardinality

The centralized projection specification may record whether a field is expected to represent:

```text id="8z7p7e"
single attachment
multiple attachments
```

if this is useful for validation and the existing schema distinguishes these semantics.

However, do not invent cardinality enforcement if Feishu's attachment field itself is simply a list and current business rules do not require it.

Keep the specification minimal.

---

# 24. Do Not Add New Validation Rules Without Requirement

P5 must not suddenly reject Submissions because a standard photo is absent unless that requirement already exists in the SOP/current validation logic.

For example, do NOT add:

```python id="suzfn3"
if not first_layer_photo:
    validation_failed
```

merely because the downstream has a `first_layer_photo` column.

Projection and required-field validation are separate concerns.

If a source field is legitimately empty:

```text id="h29fkl"
project empty
→ clear target
```

---

# 25. Projection API

Design the projection operation so publication can invoke it without knowing individual fields.

Conceptually:

```python id="9tygzq"
projection_service.project_submission_to_preset(
    submission=submission,
    preset=preset,
)
```

or equivalent.

A useful internal model could be:

```python id="c8l10s"
ProjectionSpec(
    source_field=...,
    target_field=...,
    kind="attachment",
)
```

but this is only an example.

Use the simplest representation that fits the existing codebase.

---

# 26. Future Extension Boundary

The framework should allow a future phase to add mappings such as:

```text id="ov94px"
Submission.operator_note
        ↓
Preset.operator_note

Submission.drying_condition
        ↓
Preset.drying_condition
```

without changing publication orchestration.

However P5 must NOT implement those fields unless they are part of the current requirement.

A future extension should ideally require:

```text id="9c0d1m"
add ProjectionSpec
+
implement/reuse appropriate projector
```

rather than editing P3 publication rules.

---

# 27. Suggested Internal Structure

Adapt this to the actual P4 package.

Conceptually:

```text id="gbrup5"
src/preset_worker/
│
├── services/
│   ├── enrichment.py
│   ├── publication.py
│   └── projection.py
│
├── adapters/
│   └── feishu/
│       ├── ...
│       └── attachments.py
│
└── ...
```

Do not force this exact file layout if the existing P4 result has a better equivalent.

Important separation:

```text id="f2c3sq"
publication
    = when projection occurs

projection
    = what fields map where

Feishu attachment adapter
    = how attachment transfer works
```

---

# 28. Unit Tests

Add focused tests.

## P5-T1 — Standard photo projection

Given:

```text id="poh82e"
Submission.standard_photo = A
Preset.standard_photo = old
```

after projection:

```text id="ch2zjr"
Preset.standard_photo = A
```

---

## P5-T2 — Other photos projection

Given:

```text id="pn6a8w"
Submission.other_photos = [A, B, C]
Preset.other_photos = [old1, old2]
```

after projection:

```text id="9t73s5"
Preset.other_photos = [A, B, C]
```

not an appended list.

---

## P5-T3 — Empty standard field clears target

Given:

```text id="dt09ca"
Submission.standard_photo = empty
Preset.standard_photo = old
```

after projection:

```text id="wx4wnz"
Preset.standard_photo = empty
```

---

## P5-T4 — Empty other_photos clears target

Given:

```text id="cqbfjd"
Submission.other_photos = []
Preset.other_photos = [A, B]
```

after projection:

```text id="w9g1in"
Preset.other_photos = []
```

---

## P5-T5 — Multiple mappings

Given multiple configured projection fields, verify every configured field is projected.

Publication logic should not require field-specific branches.

---

## P5-T6 — Idempotent projection

Run:

```text id="o76jtt"
project(S123, Preset X)
project(S123, Preset X)
```

Expected final Preset state is identical to running projection once.

No attachment accumulation.

---

## P5-T7 — Partial publication recovery

Simulate:

```text id="6hqh5i"
PresetVersion created
current_version updated
projection fails
```

Submission must not become APPROVED.

Retry publication.

Expected:

```text id="z4cf6g"
existing PresetVersion reused
projection repaired
Submission becomes APPROVED
```

No extra PresetVersion.

---

## P5-T8 — Stale retry cannot overwrite current photos

Given:

```text id="twhpns"
S123 → v8
S124 → v9

Preset.current_version = v9
Preset photos = S124 photos
```

retry S123.

Expected:

```text id="iqn4oz"
current_version remains v9
Preset photos remain S124 photos
```

---

## P5-T9 — Source Submission remains unchanged

Projection must not mutate or clear:

```text id="54y8gr"
Submission photo fields
```

---

## P5-T10 — PresetVersion remains unchanged

P5 must not add process-photo duplication to PresetVersion.

Historical access continues through:

```text id="sg6jz6"
PresetVersion.source_submission
```

---

# 29. Feishu Integration Tests

Add a focused integration test for the chosen attachment transfer strategy.

## P5-IT1 — Single attachment

Verify:

```text id="7py3p9"
Submission attachment
        ↓
Preset attachment
```

works against real Feishu/Bitable.

Verify the target attachment is actually accessible.

---

## P5-IT2 — Multiple attachments

Verify a multi-photo field such as:

```text id="8mdgo2"
other_photos
```

can be projected with multiple attachments.

Verify all expected attachments are present after re-reading the Preset.

---

## P5-IT3 — Clear attachment field

Start with target attachments present.

Source is empty.

Project.

Re-read Preset.

Verify target field is actually empty.

---

## P5-IT4 — Repeat projection

Project the same Submission twice.

Verify the target does not accumulate duplicate attachments.

---

# 30. Publication Ordering

Integrate P5 into the existing P3 publication flow conservatively.

For UPDATE, the effective sequence should remain conceptually:

```text id="ljgqsw"
1. load Submission
2. verify APPROVING
3. idempotency check
4. reload Preset
5. verify version safety
6. create/recover PresetVersion
7. update/verify Preset.current_version
8. project current process record
9. update Submission.published_version
10. set Submission.status = APPROVED
```

For CREATE:

```text id="0yqbfs"
1. load Submission
2. verify APPROVING
3. idempotency check
4. verify CREATE uniqueness
5. create/recover Preset
6. create/recover PresetVersion v1
7. update/verify Preset.current_version
8. project current process record
9. update Submission.preset
10. update Submission.published_version
11. set Submission.status = APPROVED
```

Do not mark APPROVED before projection succeeds.

---

# 31. Failure Handling

If attachment projection fails:

```text id="emuvba"
do not mark APPROVED
```

Preserve enough state for P3/P5 idempotent recovery to retry safely.

Do not delete an already-created PresetVersion solely because projection failed.

Do not attempt manual rollback across multiple Bitable records unless the existing P3 architecture already supports it.

Prefer:

```text id="z3x1ur"
forward recovery
```

over fragile pseudo-transactions.

---

# 32. Logging

Add useful projection-level logging consistent with the P4 logging style.

At minimum make it possible to identify:

```text id="e5djg5"
submission
preset
projection field
success/failure
attachment count
```

Do not log:

```text id="y0fiyx"
access tokens
app_secret
temporary authenticated download URLs
credential-bearing headers
```

Avoid dumping unnecessary binary/file content.

---

# 33. CLI Behavior

Existing P4 commands must continue to work:

```bash id="6b41u7"
preset-worker enrich <submission_id>
preset-worker publish <submission_id>
```

`publish` should naturally execute P5 projection as part of successful publication.

Do NOT add a separate required production command such as:

```bash id="odg0j6"
preset-worker project ...
```

unless useful strictly as a test/debug helper.

Projection is part of publication semantics.

Do NOT implement:

```bash id="q8d0ca"
preset-worker run
```

in P5.

That remains P6.

---

# 34. Regression Requirements

Run the complete P1–P4 test suite.

All existing behavior must remain intact.

Pay particular attention to:

```text id="0azm88"
canonical_json attachment handling
CREATE publication
UPDATE publication
VERSION_CONFLICT
duplicate publish
partial publication recovery
do-not-roll-back-newer-version behavior
CLI publish
```

Do not modify existing expected behavior merely to make new code pass.

---

# 35. Explicitly Out of Scope

Do NOT implement:

```text id="m6jufn"
polling worker
preset-worker run
systemd service
webhooks
Miaoda changes
review UI changes
new review states
new photo validation requirements
image compression
image conversion
image renaming
image analysis
automatic photo classification
automatic movement from other_photos to standard fields
historical photo duplication into PresetVersion
non-photo process projections not currently required
Git integration
new slicer support
distributed locking
```

---

# 36. Acceptance Criteria

P5 is complete when all of the following are true:

```text id="7l05zs"
[ ] projection fields are centrally defined

[ ] actual downstream-required standard photo fields are represented

[ ] an other_photos field is represented

[ ] publication calls one projection abstraction rather than field-specific business logic

[ ] standard photo fields project Submission → Preset

[ ] other_photos projects Submission → Preset

[ ] projection uses full replacement semantics

[ ] empty source clears target

[ ] repeated projection is idempotent

[ ] Submission source photos remain unchanged

[ ] PresetVersion does not duplicate process photos

[ ] stale retries cannot overwrite newer current photos

[ ] partial publication failure can recover safely

[ ] real Feishu attachment transfer behavior has been integration-tested

[ ] chosen attachment-transfer strategy is documented

[ ] existing enrich CLI still works

[ ] existing publish CLI still works

[ ] all P1–P4 regression tests pass

[ ] all P5 unit tests pass

[ ] P5 Feishu integration tests pass in the configured integration environment

[ ] no polling worker has been implemented
```

---

# 37. Completion Report

After implementation, report:

1. actual Submission photo fields discovered;
2. actual Preset photo fields discovered;
3. projection specification introduced;
4. projection service/files introduced;
5. Feishu attachment adapter changes;
6. whether source and target attachment field names are identical or mapped;
7. attachment transfer mechanism tested;
8. whether direct `file_token` reuse works;
9. whether download/re-upload is required;
10. replacement/clear behavior;
11. recovery behavior;
12. stale-retry protection;
13. files changed;
14. tests added;
15. integration tests performed;
16. P1–P4 regression result;
17. P5 test result;
18. any remaining attachment/API limitations.

Do not implement P6 unless explicitly requested.
