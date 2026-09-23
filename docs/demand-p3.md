# Preset Worker — P3: Publish Approved Submission

## 0. Goal

Implement the publication stage after review approval.

Previous phases already prepare a Submission for review.

When a reviewer approves a Submission, its status becomes:

```text id="4ss2hb"
APPROVING
```

P3 implements the Worker behavior that processes these `APPROVING` submissions and publishes them into:

```text id="wrqzj8"
Preset
PresetVersion
```

The successful workflow is:

```text id="wog3d3"
READY_FOR_REVIEW
        │
        │ reviewer approves
        ▼
    APPROVING
        │
        │ Worker P3
        ▼
create PresetVersion
        │
        ▼
update Preset.current_version
        │
        ▼
update Submission.published_version
        │
        ▼
     APPROVED
```

For CREATE submissions, the Preset record must first be created.

Do NOT implement the review UI itself.

Do NOT redesign the existing enrichment workflow.

---

# 1. Inspect Existing Code First

Before editing:

1. inspect the current repository;
2. run the existing test suite;
3. understand the current Submission model and statuses;
4. inspect the existing Feishu/Bitable adapters;
5. inspect existing Preset / PresetVersion repositories if present;
6. inspect existing field mappings/configuration;
7. inspect how attachment fields are currently read/written;
8. inspect how Submission relations are represented;
9. reuse existing repository/service abstractions where possible.

Make the smallest coherent change.

Do NOT perform unrelated refactoring.

Do NOT remove working legacy code unless it directly blocks P3.

---

# 2. P3 Entry Condition

P3 only processes Submissions whose status is:

```text id="c3j89e"
APPROVING
```

Implement a clear service-level operation equivalent to:

```python id="mlulhf"
publish_submission(submission_id)
```

The exact function/class name may follow existing project conventions.

The Worker may query Bitable for:

```text id="adn41a"
status == APPROVING
```

and call this operation for each matching Submission.

Keep polling/discovery separate from publication business logic where practical.

---

# 3. Important Terminology

Do NOT treat publication as moving/deleting the Submission.

The Submission remains permanently available as the audit/provenance record.

Publication means:

```text id="prlxbk"
Submission
      │
      ├── create immutable PresetVersion
      │
      └── update current Preset projection
```

The original Submission must remain intact.

---

# 4. Preset Identity

The system no longer uses meaningless IDs such as:

```text id="7c53gi"
P000001
```

The logical identity of a Preset is:

```text id="oqbjkc"
preset_key
```

Example:

```text id="gftdpy"
L2002CF|BBL P2S|BambuStudio
```

`preset_key` is the business identity.

Do NOT generate an additional sequential `preset_id`.

The Feishu `record_id` is only an implementation-level identifier used for Bitable relations.

Do not expose or treat Feishu `record_id` as the business identity.

---

# 5. Preset Table Design

P3 assumes/implements the following logical Preset fields:

```text id="u1c6is"
Preset
────────────────────────────────

preset_key              text / primary business identity

pi_code                 existing appropriate field/relation
printer                 existing appropriate field/relation
slicer                  existing appropriate field

current_version         relation → PresetVersion

process_photos          attachment, if present in current schema
```

If additional current published process-record fields already exist, preserve them.

Do NOT invent unrelated Preset fields.

## Important semantics

Preset represents:

> the current published projection of a logical preset.

It is NOT the immutable version history.

`preset_key` is written when the Preset is created and should be treated as stable identity.

Do not dynamically regenerate an existing Preset's key because a related display name later changes.

---

# 6. PresetVersion Table Design

P3 assumes/implements the following logical fields:

```text id="y9fajg"
PresetVersion
────────────────────────────────

version_id              text / primary
preset_key              text
version_no              integer

change_reason           text

canonical_json          ATTACHMENT

review_comment          text

source_submission       relation → Submission

submitted_by            person
submitted_at            datetime

reviewed_by             person
reviewed_at             datetime

created_at              datetime
```

Use existing project field names where equivalent fields already exist.

Do not create duplicate concepts merely because the names differ slightly.

---

# 7. PresetVersion Is Immutable

Once a PresetVersion has been successfully created and published, its business content is immutable.

In particular, do not later mutate:

```text id="5iv5ye"
version_id
preset_key
version_no
change_reason
canonical_json
review_comment
source_submission
submitted_by
submitted_at
reviewed_by
reviewed_at
```

A correction must eventually become another version.

Do not implement correction workflows in P3.

---

# 8. Person Fields Are Snapshots, Not Lookups

`submitted_by` and `reviewed_by` should be real Feishu person fields if supported by the existing schema.

However, they are snapshot values copied at publication time.

Do NOT implement them as dynamic lookup chains such as:

```text id="ibjfn6"
PresetVersion
    ↓ source_submission
Submission
    ↓ lookup
submitter
```

Instead:

```text id="b0yuz7"
PresetVersion.submitted_by
    = Submission.submitter

PresetVersion.reviewed_by
    = Submission.reviewer
```

Similarly:

```text id="1t4jjm"
PresetVersion.submitted_at
    = Submission.submitted_at

PresetVersion.reviewed_at
    = Submission.reviewed_at

PresetVersion.review_comment
    = Submission.review_comment
```

These values represent what was true when this version was published.

Do not convert person identities to plain display-name strings unless required by an unavoidable API limitation.

---

# 9. source_submission Is a Relation

`source_submission` MUST identify the actual Submission record that produced the version.

Conceptually:

```text id="ulc43v"
PresetVersion
      │
      └── source_submission
                 ↓
             Submission S123
```

Use a Bitable relation field where supported by the current schema.

This relation is also the logical idempotency key for publication.

---

# 10. canonical_json Is an Attachment

This is critical.

`PresetVersion.canonical_json` is NOT a multiline-text field.

It is an attachment field.

The canonical JSON file produced/stored by the Submission workflow must be attached to the PresetVersion record.

Do NOT serialize the canonical JSON into a text field as part of P3.

Reuse the existing attachment representation and Feishu attachment handling.

If the Submission already contains the canonical JSON as an attachment, publication should preserve that artifact.

Prefer reusing/copying the attachment through the existing supported Feishu attachment mechanism.

Do NOT:

```text id="lhtp2k"
download JSON
parse JSON
reserialize JSON
create a semantically equivalent but different artifact
```

unless the existing implementation/API requires this.

The published PresetVersion should represent the exact canonical artifact that passed review.

If attachment token reuse across records is already supported and tested by the project, reuse it.

If not, use the project's existing safe attachment-copy/upload mechanism.

Do not invent temporary-URL persistence.

---

# 11. version_id Format

The version ID format is fixed:

```text id="4k6ofb"
{preset_key}@v{version_no}
```

Example:

```text id="d13h1a"
preset_key =
L2002CF|BBL P2S|BambuStudio

version_no =
8
```

Then:

```text id="scppd9"
version_id =
L2002CF|BBL P2S|BambuStudio@v8
```

For the first version:

```text id="6spxq1"
L2002CF|BBL P2S|BambuStudio@v1
```

Do NOT parse `version_no` back out of `version_id`.

`version_no` is an independent integer field and is authoritative for version sequencing.

`version_id` is derived from:

```text id="ksuifk"
preset_key + version_no
```

---

# 12. UPDATE Publication

Suppose Submission S123 contains:

```text id="u9gfc6"
status           = APPROVING
operation        = UPDATE

preset_key       = L2002CF|BBL P2S|BambuStudio

preset           → existing Preset
base_version     → version 7
```

Before publishing, reload the Preset.

Read:

```text id="l07w6h"
Preset.current_version
```

The Submission may only publish if:

```text id="dts3t4"
Submission.base_version
==
Preset.current_version
```

If the current version is v7:

```text id="7bawx9"
new version_no = 7 + 1 = 8
```

Then:

```text id="nryg3e"
version_id =
L2002CF|BBL P2S|BambuStudio@v8
```

Create the new PresetVersion using the approved Submission data.

After successful creation:

```text id="y4ex3k"
Preset.current_version
    → new PresetVersion v8
```

Then update the Submission:

```text id="mx98xw"
published_version
    → new PresetVersion v8

status
    = APPROVED
```

---

# 13. UPDATE Conflict

Example:

Submission was enriched/reviewed against:

```text id="j4fmlk"
base_version = v7
```

but at publication time:

```text id="fefqvs"
Preset.current_version = v8
```

Do NOT publish the Submission as v9.

Do NOT automatically rebase it.

Do NOT automatically recalculate the diff.

Do NOT silently update its base version.

Instead:

```text id="8j5s40"
status = VERSION_CONFLICT
```

and stop publication.

No PresetVersion should be created for this attempt.

---

# 14. CREATE Publication

Suppose:

```text id="m15n1n"
operation = CREATE

preset_key =
L2002CF|BBL P2S|BambuStudio

preset = null
base_version = null
```

At publication time, query the Preset table again by exact `preset_key`.

This re-check is mandatory.

## If Preset Still Does Not Exist

Create the Preset first:

```text id="hmhdhs"
Preset
────────────────────────────
preset_key
pi_code
printer
slicer

current_version = empty initially
```

Capture the Feishu `record_id` returned by the API.

Then:

```text id="flpxg3"
version_no = 1
```

and:

```text id="mll3wr"
version_id =
{preset_key}@v1
```

Create PresetVersion v1.

Then update:

```text id="sj4frn"
Preset.current_version
    → v1
```

Then update the Submission:

```text id="zbm5ba"
Submission.preset
    → newly created Preset

Submission.published_version
    → v1

Submission.status
    = APPROVED
```

The temporary state:

```text id="k7k87w"
Preset exists
current_version = null
```

is acceptable during publication.

---

# 15. CREATE Conflict

If the Submission says:

```text id="d0cvt3"
operation = CREATE
```

but a Preset with the same exact `preset_key` already exists at publication time:

```text id="h3kvqv"
status = VERSION_CONFLICT
```

Do NOT silently convert the Submission to UPDATE.

Do NOT create another Preset with the same business key.

Do NOT publish another version.

The reviewer approved a CREATE operation, so changing its meaning after review is forbidden.

---

# 16. Process Record Projection to Preset

Process records belong to Submission.

Submission remains the historical source of truth.

However, Preset may expose the process records from the latest published Submission for downstream consumers.

If the current schema contains:

```text id="iyx2f0"
Submission.process_photos
```

and:

```text id="v51oh3"
Preset.process_photos
```

then successful publication should project:

```text id="79qg46"
Submission.process_photos
        ↓
Preset.process_photos
```

The Preset field represents:

> process photos associated with the current published version.

Do NOT remove or mutate the original Submission attachments.

Historical process records remain accessible through:

```text id="cfrs0p"
PresetVersion
      ↓ source_submission
Submission
      ↓
process_photos
```

Only update the Preset projection as part of successful publication.

Do NOT project process records when the Submission is merely:

```text id="upwmoc"
READY_FOR_REVIEW
```

or:

```text id="o9whl5"
APPROVING
```

before publication has actually succeeded.

If additional process-record projection fields already exist in the schema, follow the same principle.

---

# 17. Publication Ordering

For UPDATE, the logical order is:

```text id="q20mpu"
1. load Submission
2. verify APPROVING
3. idempotency check
4. reload Preset
5. verify base_version == current_version
6. determine new version_no
7. determine version_id
8. create PresetVersion
9. update Preset.current_version
10. update Preset current process projection
11. update Submission.published_version
12. set Submission.status = APPROVED
```

For CREATE:

```text id="jv8irx"
1. load Submission
2. verify APPROVING
3. idempotency check
4. re-check preset_key uniqueness
5. create Preset
6. determine version_no = 1
7. determine version_id
8. create PresetVersion
9. update Preset.current_version
10. update Preset current process projection
11. update Submission.preset
12. update Submission.published_version
13. set Submission.status = APPROVED
```

Do not set:

```text id="g71y5j"
APPROVED
```

until the publication state has been successfully established.

---

# 18. Idempotency

This is mandatory.

Publication may fail halfway because Bitable does not provide a database transaction spanning all required writes.

Example:

```text id="t6f1y6"
create PresetVersion v8
        ↓
SUCCESS

update Preset.current_version
        ↓
network failure
```

The Worker later sees:

```text id="rww4bx"
Submission S123
status = APPROVING
```

and retries.

It MUST NOT create v9.

---

# 19. Idempotency Key

Use:

```text id="3ag5wg"
PresetVersion.source_submission
```

as the logical publication idempotency key.

Before creating any PresetVersion:

```text id="7tfbn1"
find PresetVersion
where source_submission == current Submission
```

If no version exists:

continue normal publication.

If a version already exists:

do NOT create another version.

Instead enter recovery/repair behavior.

---

# 20. Partial Publication Recovery

Suppose S123 already produced:

```text id="yrgh1m"
PresetVersion v8
source_submission → S123
```

but publication stopped before all references were updated.

A retry should use the existing v8 and repair the remaining state.

At minimum verify/repair:

```text id="47q3sp"
Preset.current_version
    → existing v8

Preset process projection
    = S123 process records

Submission.preset
    → correct Preset

Submission.published_version
    → existing v8

Submission.status
    = APPROVED
```

Do not create a new version during recovery.

Repeated calls:

```text id="l1k5i3"
publish_submission(S123)
publish_submission(S123)
publish_submission(S123)
```

must result in exactly one PresetVersion associated with S123.

---

# 21. Important Recovery Safety

Do not blindly overwrite a newer legitimate current version during recovery.

Example:

```text id="vvytbc"
S123 created v8

later:
S124 legitimately published v9
```

If an old retry of S123 occurs, it must NOT do:

```text id="q4lkyq"
Preset.current_version = v8
```

and roll the Preset backward.

When repairing an existing publication, inspect the current version state first.

The recovery logic must distinguish:

```text id="mgzwlg"
incomplete publication
```

from:

```text id="7dwh8a"
an older already-published Submission being retried later
```

If S123 is already fully `APPROVED`, publication should simply be treated as already complete.

Keep the implementation conservative.

Do not overwrite a newer version.

---

# 22. Concurrency Limitation

Do not assume Bitable provides:

```text id="k2nyon"
database transactions
UNIQUE constraints
compare-and-swap
row locks
```

unless the existing adapter has explicitly verified such capabilities.

Application-level:

```text id="f05keb"
check → create
```

is not inherently atomic.

For P3, prefer the simplest safe publication model compatible with the existing Worker.

If the Worker already processes publication serially, preserve that behavior.

Do NOT build a distributed locking framework in P3.

Document any remaining race window clearly.

Correctness is more important than publication throughput.

---

# 23. APPROVED Is a Final State

Once publication completes:

```text id="9i0hmw"
Submission.status = APPROVED
```

Treat the Submission's business/review content as immutable.

Do not allow publication logic to modify its candidate content after this point.

The same applies to published PresetVersion records.

Do not implement a new edit-after-approval workflow in P3.

---

# 24. Reject Is Out of Scope

P3 does not need to implement the reviewer interaction.

Assume the review layer already performs:

```text id="wnw3tf"
Approve:
READY_FOR_REVIEW → APPROVING
```

and:

```text id="cz7e52"
Reject:
READY_FOR_REVIEW → REJECTED
```

P3 only owns publication after `APPROVING`.

Do not add review UI or approval buttons.

---

# 25. Required Repository Capabilities

Adapt these names to the existing architecture.

The publication service conceptually needs operations equivalent to:

```text id="24w1jk"
SubmissionRepository
    get(submission_id)
    update(...)

PresetRepository
    find_by_key(preset_key)
    get(...)
    create(...)
    update(...)

PresetVersionRepository
    get(...)
    find_by_source_submission(submission)
    create(...)
```

Do not put raw Feishu HTTP calls directly into core publication business logic if the current project already has an adapter/repository boundary.

Tests should use fake/in-memory repositories where practical.

---

# 26. Required Tests

Keep tests focused on P3.

## P3-T1 — CREATE first version

Given:

```text id="dyx3gi"
Submission S1
operation = CREATE
status = APPROVING
preset_key = X
```

and no Preset X exists.

Expected:

```text id="khtl0s"
Preset X created

PresetVersion:
version_no = 1
version_id = X@v1
source_submission = S1

Preset.current_version → X@v1

Submission.preset → X
Submission.published_version → X@v1
Submission.status = APPROVED
```

---

## P3-T2 — UPDATE

Given:

```text id="avl3tz"
Preset X
current_version = X@v7

Submission S2
operation = UPDATE
base_version = X@v7
status = APPROVING
```

Expected:

```text id="brjdt0"
new version_no = 8
version_id = X@v8

Preset.current_version → X@v8
Submission.published_version → X@v8
Submission.status = APPROVED
```

---

## P3-T3 — Version metadata snapshot

Verify PresetVersion receives independent copied values for:

```text id="e7e1q9"
change_reason
submitted_by
submitted_at
reviewed_by
reviewed_at
review_comment
```

Changing the Submission afterward in the test fixture must not dynamically alter the PresetVersion values.

---

## P3-T4 — canonical_json attachment

Verify:

```text id="5nxqhj"
PresetVersion.canonical_json
```

is populated as an attachment.

Do not accept a text-field implementation.

Verify the published attachment represents the reviewed canonical artifact.

---

## P3-T5 — source_submission relation

Verify:

```text id="fsvh6c"
PresetVersion.source_submission
```

points to the actual source Submission.

---

## P3-T6 — UPDATE stale baseline

Given:

```text id="rucgm3"
Submission.base_version = v7
Preset.current_version = v8
```

Expected:

```text id="6uwaxp"
Submission.status = VERSION_CONFLICT
```

No new PresetVersion.

---

## P3-T7 — CREATE conflict

Given:

```text id="l80hlm"
Submission.operation = CREATE
```

but the same `preset_key` already exists at publication time.

Expected:

```text id="iqq00f"
VERSION_CONFLICT
```

No new PresetVersion.

Do not convert to UPDATE.

---

## P3-T8 — Duplicate publish

Call:

```text id="8ix5su"
publish_submission(S1)
publish_submission(S1)
```

Expected:

exactly one PresetVersion whose:

```text id="1ifrcw"
source_submission = S1
```

---

## P3-T9 — Partial failure recovery

Simulate:

```text id="v4dxsh"
PresetVersion creation succeeds
Preset.current_version update fails
```

Retry publication.

Expected:

reuse the existing PresetVersion.

Do NOT create the next version.

Repair remaining references and finish APPROVED.

---

## P3-T10 — Do not roll back newer version

Given:

```text id="6drkmw"
S1 → v8 already exists
Preset.current_version = v9
```

Retry S1.

Expected:

do NOT change current_version back to v8.

---

## P3-T11 — Process photo projection

Given S1 has process photos.

After successful publication:

```text id="1j6zml"
Preset.process_photos
```

represents the process photos from S1.

Original:

```text id="7nd2jl"
Submission.process_photos
```

remains intact.

---

## P3-T12 — PresetVersion immutable behavior

After publication, normal publication/service operations must not mutate the existing PresetVersion business fields.

---

# 27. Explicitly Out of Scope

Do NOT implement:

```text id="n32vua"
Miaoda review UI
review page
approval button
rejection button
editing approved submissions
version rollback
version deletion
version correction
automatic rebase
automatic merge
NO_CHANGE workflow
OrcaSlicer publication differences
Cura publication differences
Git
PR
distributed locking system
historical process-photo duplication into PresetVersion
```

Do not solve future phases prematurely.

---

# 28. Acceptance Scenario

Existing state:

```text id="cch7j4"
Preset
preset_key =
L2002CF|BBL P2S|BambuStudio

current_version →
L2002CF|BBL P2S|BambuStudio@v7
```

Submission:

```text id="osw5gg"
S123

status = APPROVING
operation = UPDATE

preset_key =
L2002CF|BBL P2S|BambuStudio

base_version =
L2002CF|BBL P2S|BambuStudio@v7

canonical_json =
[canonical JSON attachment]

change_reason =
"Improve high-speed extrusion"

submitter =
Engineer A

submitted_at =
...

reviewer =
Reviewer B

reviewed_at =
...

review_comment =
"Validated print quality"

process_photos =
[attachments]
```

After:

```python id="41jjlr"
publish_submission("S123")
```

expected:

```text id="54f8ka"
PresetVersion
────────────────────────────────
version_id
L2002CF|BBL P2S|BambuStudio@v8

preset_key
L2002CF|BBL P2S|BambuStudio

version_no
8

canonical_json
[canonical JSON attachment]

change_reason
"Improve high-speed extrusion"

source_submission
→ S123

submitted_by
Engineer A

submitted_at
[snapshot]

reviewed_by
Reviewer B

reviewed_at
[snapshot]

review_comment
"Validated print quality"

created_at
[publication time]
```

and:

```text id="ap89r4"
Preset.current_version
→ L2002CF|BBL P2S|BambuStudio@v8
```

and:

```text id="2x81en"
Preset.process_photos
← S123.process_photos
```

and:

```text id="uyb2yu"
Submission.published_version
→ L2002CF|BBL P2S|BambuStudio@v8

Submission.status
= APPROVED
```

---

# 29. Completion Report

After implementation, report only:

1. files changed;
2. Preset schema assumptions;
3. PresetVersion schema assumptions;
4. publication flow implemented;
5. version allocation implementation;
6. canonical JSON attachment handling;
7. person snapshot handling;
8. process-record projection handling;
9. idempotency/recovery behavior;
10. concurrency limitations;
11. tests added;
12. test results;
13. any ambiguity encountered.

Do not implement the next phase unless explicitly requested.
