# Preset Worker — Phase 1: Enrich Submission

## 0. Scope

Implement ONLY the first stage of the new preset submission workflow:

> Enrich a newly created Submission record.

Do NOT implement review or publication in this phase.

The final architecture will later support:

```text
Submission
    ↓
review
    ↓
publish
    ↓
PresetVersion
```

but this task stops at:

```text
new Submission
    ↓
resolve preset
    ↓
read uploaded JSON
    ↓
validate
    ↓
normalize
    ↓
calculate diff
    ↓
write results back to Submission
```

Keep future extension points clean, but DO NOT implement future functionality now.

---

# 1. First inspect the existing code

Before editing:

1. inspect the current repository;
2. identify the existing Feishu/Bitable adapter;
3. identify the current Submission-related code;
4. identify reusable JSON validation / normalization code;
5. identify existing tests.

Prefer the smallest modification that fits the current architecture.

Do NOT perform unrelated refactoring.

Do NOT remove legacy Git code in this phase unless it directly blocks this implementation.

Do NOT redesign the whole project.

---

# 2. Input

A Submission record already exists in Feishu Bitable.

The Submission contains, at minimum:

```text
submission_id
pi_code
machine
slicer
uploaded_json
```

The exact Feishu field names MUST come from the existing configuration/schema where possible.

Do not hard-code guessed field IDs if the project already has a field mapping mechanism.

`uploaded_json` contains the complete JSON exported from the slicer.

The engineer does NOT edit individual preset parameters in Bitable.

---

# 3. Required output

After processing a valid Submission, populate these logical fields:

```text
preset
operation
base_version

canonical_json
diff
validation

status
```

Expected successful state:

```text
status = READY_FOR_REVIEW
```

Expected validation failure state:

```text
status = VALIDATION_FAILED
```

This phase MUST NOT create or modify any PresetVersion.

---

# 4. Main entry point

Implement one clear service-level operation equivalent to:

```python
enrich_submission(submission_id)
```

The exact name may follow existing project conventions.

This function is the only main workflow required by this phase.

Its logical behavior is:

```text
load Submission
      ↓
validate required Submission metadata
      ↓
build preset_key
      ↓
find existing Preset
      ↓
determine CREATE / UPDATE
      ↓
parse uploaded_json
      ↓
validate JSON
      ↓
normalize JSON
      ↓
calculate diff
      ↓
update Submission
```

Do not add review or publish behavior to this function.

---

# 5. Resolve Preset

Build the logical preset identity from:

```text
pi_code
machine
slicer
```

Use the project's existing naming/normalization rules if they exist.

Conceptually:

```text
preset_key = pi_code | machine | slicer
```

Search the Preset table for an exact matching logical preset.

## If Preset does not exist

Set:

```text
operation = CREATE
preset = empty
base_version = empty
```

Do NOT create the Preset yet.

Preset creation belongs to the future publication phase.

## If Preset exists

Set:

```text
operation = UPDATE
preset = existing Preset
base_version = existing Preset.current_version
```

`base_version` is a snapshot of the current version at submission-processing time.

Do not allocate a new version number.

---

# 6. Parse uploaded JSON

Parse `uploaded_json`.

If parsing fails:

```text
status = VALIDATION_FAILED
```

Store a useful validation error.

Stop processing this Submission.

Do not attempt normalization or diff.

The original `uploaded_json` MUST remain unchanged.

---

# 7. Validation

Keep validation deliberately small in this phase.

Reuse existing validation logic if available.

At minimum check:

```text
JSON can be parsed
top-level structure is valid
required fields currently defined by the project exist
required field types are valid
```

Do NOT invent a large new validation framework.

Do NOT add speculative slicer-specific rules.

The purpose of this phase is workflow completion, not exhaustive preset validation.

Store the result in the Submission `validation` field.

A simple structured result is sufficient, for example:

```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

or the closest representation that fits the existing storage layer.

If invalid:

```text
status = VALIDATION_FAILED
```

and stop.

---

# 8. Normalization

After validation succeeds, normalize the uploaded JSON.

Reuse existing normalization logic where possible.

Only normalize fields whose rules are already clearly defined by the project.

Do NOT rebuild the JSON from Bitable parameter columns.

The model is:

```text
complete uploaded JSON
        ↓
small controlled transformations
        ↓
complete canonical JSON
```

Preserve unrelated JSON fields.

Store the result as:

```text
Submission.canonical_json
```

The original:

```text
Submission.uploaded_json
```

must remain untouched.

---

# 9. Diff

## UPDATE

If the Submission is an UPDATE:

read:

```text
base_version.canonical_json
```

and compare it with:

```text
Submission.canonical_json
```

Generate a structured diff.

At minimum distinguish:

```text
added
removed
modified
```

Example:

```json
{
  "added": [],
  "removed": [],
  "modified": [
    {
      "path": "filament_max_volumetric_speed",
      "old": ["18"],
      "new": ["20"]
    }
  ]
}
```

The exact representation may follow existing project conventions.

Prefer semantic JSON comparison over raw text comparison.

## CREATE

For CREATE there is no old JSON.

Generate a sensible CREATE diff representation.

Do not invent a fake base version.

For example, treating all candidate fields as additions is acceptable if it fits the existing diff implementation.

---

# 10. Successful result

After all processing succeeds, update the Submission with:

```text
preset
operation
base_version
canonical_json
diff
validation
status = READY_FOR_REVIEW
```

The operation should now stop.

Nothing else happens.

---

# 11. Explicitly out of scope

DO NOT implement any of the following in this phase:

```text
review UI
approve
reject
publish_submission
Preset creation
PresetVersion creation
version number allocation
current_version update
published_version
VERSION_CONFLICT handling
concurrency locking
Git operations
Git PR
automatic merge
Miaoda UI
notifications
```

Do not create placeholder implementations for these.

It is enough that the current design does not prevent adding them later.

---

# 12. Future extension point

The expected future workflow is:

```text
enrich_submission()
        ↓
READY_FOR_REVIEW
        ↓
[FUTURE]
review
        ↓
publish_submission()
```

Therefore, after this phase a successful Submission must contain enough information for future publication:

```text
preset
operation
base_version
canonical_json
diff
validation
```

But no publication behavior should exist yet.

---

# 13. Error handling

Keep error handling simple.

Distinguish at least:

### Expected validation failure

Example:

```text
invalid JSON
missing required JSON field
wrong field type
```

Result:

```text
status = VALIDATION_FAILED
validation = error details
```

### Infrastructure/programming failure

Example:

```text
Feishu API unavailable
unexpected response
internal bug
```

Do NOT incorrectly convert these into:

```text
VALIDATION_FAILED
```

Let existing infrastructure error handling/retry/logging handle them.

---

# 14. Idempotency for this phase

`enrich_submission(submission_id)` should be safe to run again.

At minimum:

```text
same Submission
same uploaded_json
same database state
```

should produce the same enrichment result.

Do not create any additional Preset or PresetVersion records, so rerunning should not have external side effects beyond updating the same Submission.

Avoid implementing a complex idempotency system in this phase.

---

# 15. Tests

Keep the test set focused.

Required tests:

## T1 — New preset

No matching Preset exists.

Expected:

```text
operation = CREATE
preset = empty
base_version = empty
canonical_json populated
diff populated
status = READY_FOR_REVIEW
```

---

## T2 — Existing preset

Matching Preset exists with current version v7.

Expected:

```text
operation = UPDATE
preset = existing preset
base_version = v7
canonical_json populated
diff against v7
status = READY_FOR_REVIEW
```

---

## T3 — Invalid JSON

Expected:

```text
status = VALIDATION_FAILED
canonical_json not published/used
validation contains error
```

---

## T4 — Validation failure

JSON parses but fails an existing required validation rule.

Expected:

```text
status = VALIDATION_FAILED
```

---

## T5 — Normalization

Input JSON contains a field that has an existing defined normalization rule.

Expected:

```text
uploaded_json unchanged
canonical_json normalized
```

---

## T6 — UPDATE diff

Existing canonical JSON differs from uploaded/normalized JSON.

Expected:

```text
diff correctly reports the changed field(s)
```

---

## T7 — Re-run

Call:

```text
enrich_submission(S123)
enrich_submission(S123)
```

Expected:

no new Preset;
no new PresetVersion;
same final Submission result.

---

# 16. Acceptance scenario

The following scenario must work:

Existing database:

```text
Preset:
    P42
    pi_code = L2002CF
    machine = BBL P2S
    slicer = BambuStudio
    current_version = P42@v7

PresetVersion:
    P42@v7
    canonical_json = {...}
```

New Submission:

```text
S123

pi_code = L2002CF
machine = BBL P2S
slicer = BambuStudio

uploaded_json = {...new complete JSON...}
```

Run:

```python
enrich_submission("S123")
```

Expected Submission:

```text
S123

preset = P42
operation = UPDATE
base_version = P42@v7

uploaded_json = original JSON
canonical_json = normalized new JSON

validation = PASS
diff = v7 → candidate changes

status = READY_FOR_REVIEW
```

No Preset is created.

No PresetVersion is created.

No version number is allocated.

No review occurs.

No Git operation occurs.

---

# 17. Implementation discipline

This phase should be SMALL.

Prefer:

```text
one workflow
few functions
few repository additions
focused tests
```

over a generalized framework.

Do not solve future phases prematurely.

If an architectural decision is only needed for review/publication later, leave it for later.

At completion report only:

1. files changed;
2. behavior implemented;
3. tests added;
4. test results;
5. assumptions made;
6. anything intentionally deferred to the next phase.
