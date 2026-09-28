# P1.2 — Worker-Owned `Submission.base_version_no_text`

## Goal

Make:

```text
Submission.base_version_no_text
```

a Worker-owned derived snapshot.

It represents the version number of:

```text
Submission.base_version
```

at the time the Worker performs authoritative formal enrichment.

Example:

```text
base_version         -> PresetVersion v7
base_version_no_text = "7"
```

The Worker is the only component responsible for populating this field.

---

# 1. Ownership

Define:

```text
Submission.base_version_no_text
```

as:

```text
system-managed
Worker-owned
derived
historical snapshot
```

Miaoda must NOT write this field.

The engineer must NOT edit this field.

The reviewer must NOT edit this field.

Do not implement it as a frontend-derived value.

---

# 2. Source of Truth

The value must come from:

```text
resolved base PresetVersion.version_no
```

Conceptually:

```python
base_version_no_text = str(base_version.version_no)
```

Do NOT derive it from:

```text
version_id
Preset.current_version_no_text
UI state
preview display text
filename
relation display label
```

`PresetVersion.version_no` is authoritative.

---

# 3. UPDATE Formal Enrichment

During authoritative formal enrichment:

```text
VALIDATING
```

the Worker already resolves:

```text
Preset
→ Preset.current_version
→ base_version
```

For UPDATE, after resolving the authoritative base PresetVersion:

```text
Submission.base_version
        =
resolved PresetVersion relation
```

and:

```text
Submission.base_version_no_text
        =
str(resolved PresetVersion.version_no)
```

These two fields must describe the same PresetVersion.

Example:

```text
Preset.current_version -> v8

Worker enrichment:

Submission.base_version -> v8
Submission.base_version_no_text = "8"
```

---

# 4. CREATE Semantics

For CREATE:

```text
Submission.base_version = null
Submission.base_version_no_text = null/empty
```

Do not write:

```text
"0"
"v0"
"CREATE"
"NEW"
```

CREATE has no base version.

---

# 5. Write Together

Where practical, write:

```text
base_version
base_version_no_text
```

in the same Worker Submission update operation.

Avoid intermediate persisted states such as:

```text
base_version -> v8
base_version_no_text = "7"
```

or:

```text
base_version -> v8
base_version_no_text empty
```

If Bitable cannot provide transactional semantics, structure the Worker so these fields are still treated as one logical enrichment result.

---

# 6. READY_FOR_REVIEW Freeze

Once enrichment succeeds and Submission reaches:

```text
READY_FOR_REVIEW
```

the pair:

```text
base_version
base_version_no_text
```

is frozen historical Submission state.

Example:

```text
Submission:
base_version -> v7
base_version_no_text = "7"
status = READY_FOR_REVIEW
```

Later:

```text
Preset.current_version:
v7 → v8
```

must NOT change the Submission snapshot.

It remains:

```text
base_version -> v7
base_version_no_text = "7"
```

---

# 7. Do Not Use Lookup

Do NOT implement:

```text
base_version_no_text
```

as a Feishu Lookup through:

```text
base_version → PresetVersion.version_no
```

The field is intentionally a copied historical snapshot.

Reason:

```text
Submission records the state used for that submission,
not a live projection of another table.
```

---

# 8. Preview Does Not Own the Field

`PREVIEW_REQUESTED` may resolve a temporary current/base version for preview purposes.

That must NOT make preview authoritative owner of:

```text
base_version_no_text
```

Do not persist/freeze this field merely because Preview was generated.

Formal:

```text
DRAFT
→ VALIDATING
```

must resolve the authoritative base again.

---

# 9. Miaoda Save Allowlist

Inspect all Draft-save/update paths.

Ensure:

```text
base_version_no_text
```

is NOT in any engineer-editable field allowlist.

A stale browser or manipulated request must not be able to write:

```text
base_version_no_text = "999"
```

---

# 10. Submit Action

The Miaoda:

```text
Submit for Review
```

action must NOT calculate or write `base_version_no_text`.

Its responsibility remains:

```text
validate submission completeness
DRAFT → VALIDATING
```

Then Worker enrichment owns base resolution.

---

# 11. Reviewer UI

Reviewer Workspace may read:

```text
Submission.base_version_no_text
```

directly.

For UPDATE:

```text
基于版本 v8
```

For CREATE:

do not show a base version.

Reviewer UI must not need to traverse the SingleLink solely to obtain the display version number.

---

# 12. M2 Historical Detail

M2 may also read this snapshot directly.

Example:

```text
提交类型：UPDATE
基于版本：v8
```

This remains correct historical presentation even after the Preset advances to v9, v10, etc.

---

# 13. VERSION_CONFLICT Presentation

The snapshot may be used for display:

```text
Submission.base_version_no_text = "8"
Preset.current_version_no_text = "9"
```

UI:

```text
提交基于：v8
当前版本：v9
```

However:

```text
base_version_no_text
```

must NOT participate in conflict correctness logic.

Existing authoritative conflict detection remains based on the actual:

```text
base_version
vs
Preset.current_version
```

relations/identities.

The text field is presentation data only.

---

# 14. Idempotent Enrichment

Reprocessing the same formal enrichment result must produce the same pair:

```text
base_version -> v8
base_version_no_text = "8"
```

If enrichment retries before READY_FOR_REVIEW and authoritative resolution remains v8, writing `"8"` again is harmless.

Do not append or increment the text field.

---

# 15. Repair Inconsistent Pair Before Freeze

If a retry encounters an in-progress Submission where:

```text
base_version -> v8
base_version_no_text missing
```

and the authoritative enrichment result still resolves v8:

repair:

```text
base_version_no_text = "8"
```

before READY_FOR_REVIEW.

Likewise, do not allow enrichment success to leave a mismatched pair.

---

# 16. Historical Backfill

Provide an explicit idempotent backfill/repair path for existing historical UPDATE Submissions where:

```text
base_version != null
base_version_no_text is empty
```

For each such record:

1. resolve `Submission.base_version`;
2. read the linked `PresetVersion.version_no`;
3. write:

```text
base_version_no_text = str(version_no)
```

Do not parse `version_id`.

Do not recompute the base from current Preset.

This distinction is critical.

For an old Submission:

```text
base_version -> v7
current Preset -> v10
```

backfill must write:

```text
"7"
```

not:

```text
"10"
```

---

# 17. Backfill Safety

The backfill must NOT modify:

```text
status
operation
base_version
preset
canonical_json
diff
validation
review fields
published_version
```

Only repair:

```text
base_version_no_text
```

from the already-linked historical `base_version`.

---

# 18. CREATE Backfill

For historical CREATE Submission:

```text
base_version = null
```

leave:

```text
base_version_no_text
```

empty.

Do not infer v1 from its published version.

A CREATE Submission had no base.

---

# 19. Tests — UPDATE

Prepare:

```text
Preset.current_version -> v7
v7.version_no = 7
```

Run formal enrichment.

Expected:

```text
Submission.operation = UPDATE
Submission.base_version -> v7
Submission.base_version_no_text = "7"
```

---

# 20. Tests — CREATE

No matching Preset.

Run formal enrichment.

Expected:

```text
operation = CREATE
base_version = null
base_version_no_text empty
```

---

# 21. Test — Preset Advances After Enrichment

Formal enrichment produces:

```text
base_version -> v7
base_version_no_text = "7"
READY_FOR_REVIEW
```

Then publish another Submission so:

```text
Preset.current_version -> v8
```

Expected original Submission remains:

```text
base_version -> v7
base_version_no_text = "7"
```

---

# 22. Test — Backfill

Historical Submission:

```text
base_version -> v6
base_version_no_text empty
current Preset -> v9
```

Run backfill.

Expected:

```text
base_version_no_text = "6"
```

Mandatory regression test.

---

# 23. Test — Manipulated UI Request

Attempt to write from Miaoda:

```text
base_version_no_text = "999"
```

through Draft save/update request.

Expected:

```text
field ignored/rejected according to existing mutation policy
```

Worker remains sole owner.

---

# 24. Test — Reviewer Display

Submission:

```text
operation = UPDATE
base_version_no_text = "8"
```

Reviewer Workspace must show:

```text
基于版本 v8
```

without requiring a live relation lookup.

---

# 25. Out of Scope

Do NOT change:

```text
base_version conflict semantics
VERSION_CONFLICT rules
version allocation
Preset.current_version
Preset.current_version_no_text
PresetVersion.version_no
publication logic
working-base/download semantics
```

Do not introduce:

```text
working_base_version
```

as part of this patch.

That is a separate architectural decision.

---

# Acceptance Criteria

Complete when:

```text
[ ] Worker owns base_version_no_text

[ ] Miaoda cannot write base_version_no_text

[ ] UPDATE enrichment writes it from base PresetVersion.version_no

[ ] base_version and base_version_no_text describe the same version

[ ] CREATE leaves it empty

[ ] Preview does not freeze it

[ ] formal enrichment recomputes it

[ ] READY_FOR_REVIEW freezes it

[ ] later Preset publication does not change it

[ ] conflict logic does not depend on the text field

[ ] Reviewer Workspace can display it directly

[ ] M2 historical detail can display it directly

[ ] historical backfill uses linked base_version, not current Preset

[ ] version_id is never parsed

[ ] existing workflow/publication semantics remain unchanged
```

# Completion Report

Report:

1. Worker code path that owns `base_version_no_text`;
2. exact source used for the value;
3. UPDATE behavior;
4. CREATE behavior;
5. fields written together with `base_version`;
6. Draft mutation allowlist result;
7. Preview behavior;
8. READY_FOR_REVIEW freeze behavior;
9. historical backfill implementation;
10. number of historical records repaired;
11. UPDATE test result;
12. CREATE test result;
13. Preset-advance-after-enrichment test result;
14. historical v6/current-v9 backfill test result;
15. manipulated UI write test result;
16. Reviewer display test result;
17. confirmation that conflict logic still uses actual version relations, not `base_version_no_text`.