# Preset Worker — Phase 1.1: Complete Pre-Review Enrichment

## 0. Goal

Phase 1 basic Submission enrichment has already been implemented.

This task is a small incremental change.

Implement ONLY the remaining automatic processing required before a Submission enters review:

1. slicer-specific validation/canonicalization architecture;
2. BambuStudio canonical JSON generation;
3. `pm_method_version` handling;
4. automatic `operation` detection;
5. automatic `preset` / `preset_id` resolution;
6. automatic `base_version_id` assignment;
7. diff based on canonical JSON.

Do NOT implement review or publication.

Do NOT redesign working Phase 1 code unnecessarily.

---

# 1. Inspect Existing Implementation First

Before modifying code:

1. inspect the Phase 1 implementation;
2. understand the current `enrich_submission()` flow;
3. identify existing JSON validation/canonicalization functions;
4. identify existing Preset and PresetVersion lookup code;
5. identify existing diff implementation;
6. identify current Feishu field mappings and configuration;
7. run the existing tests.

Make the smallest changes necessary.

Preserve existing working behavior unless this instruction explicitly changes it.

---

# 2. Updated Submission Input

A Submission now has these user-provided inputs:

```text
pi_code
machine
slicer
pm_method_version
uploaded_json
```

`pm_method_version` is required.

The user selects it before Submission enrichment.

It represents the parameter-tuning-method version used to produce this preset.

It MUST later become part of `canonical_json`.

Do not infer `pm_method_version` from uploaded JSON.

The Submission field is authoritative.

---

# 3. Pre-Review Output

After successful enrichment, the Submission must contain enough frozen information to be reviewed later:

```text
preset_key
operation

preset / preset_id
base_version_id

canonical_json
validation
diff

status = READY_FOR_REVIEW
```

The exact physical Feishu field representation may follow the existing project schema.

Do not introduce duplicate fields if the existing schema already represents the same concept.

---

# 4. Slicer-Specific Processing

The project will support multiple slicers in the future.

Different slicers may require different:

```text
validation rules
canonicalization rules
```

Therefore validation/canonicalization must have a clear slicer-specific boundary.

Conceptually:

```text
uploaded_json
      │
      ▼
select processor by slicer
      │
      ▼
processor.validate()
      │
      ▼
processor.canonicalize()
      │
      ▼
canonical_json
```

Current implementation requirement:

```text
BambuStudio → supported
other slicers → unsupported
```

Do NOT implement OrcaSlicer, Cura, or any other slicer in this phase.

Do NOT create unnecessary placeholder implementations.

An unsupported slicer should produce a clear domain error/result such as:

```text
UnsupportedSlicerError
```

Use naming and class structure consistent with the existing repository.

Avoid a growing monolithic function such as:

```python
if slicer == "BambuStudio":
    ...
elif slicer == "Orca":
    ...
elif slicer == "Cura":
    ...
```

but also avoid building a large plugin framework.

Use the smallest abstraction that leaves a clean extension point.

---

# 5. Processing Order

The required order is:

```text
uploaded_json
      ↓
parse
      ↓
BambuStudio validation
      ↓
canonicalization
      ↓
canonical_json
      ↓
resolve preset/base
      ↓
diff
      ↓
READY_FOR_REVIEW
```

Validation MUST inspect the original uploaded JSON.

Do not canonicalize an invalid JSON first and then validate the modified result.

---

# 6. BambuStudio Validation

Only implement validation rules currently required by the project.

Reuse Phase 1 validation wherever possible.

At minimum:

```text
uploaded_json must parse successfully
top-level JSON structure must be valid
existing required BambuStudio fields/types must satisfy current project rules
```

Do NOT introduce speculative BambuStudio validation rules.

Do NOT reject unknown BambuStudio fields merely because the worker does not know them.

The worker is not rebuilding the preset from a whitelist.

---

# 7. BambuStudio Canonicalization

For BambuStudio, canonicalization currently has EXACTLY TWO semantic rules.

Do not add additional transformations.

## Rule 1 — name

Set:

```text
name = "{pi_code} @{printer}"
```

Example:

```text
pi_code = L2002CF
printer = BBL P2S
```

Result:

```json
"name": "L2002CF @BBL P2S"
```

If `name` already exists in uploaded JSON, overwrite it.

If it does not exist, insert it.

### Printer name source

Use the project's canonical printer/machine display value.

Do NOT invent a printer name from IDs.

If the current data model distinguishes:

```text
machine_id
machine code
printer/display name
```

use the canonical human-readable printer name that is intended to appear in preset `name`.

If this mapping is ambiguous in the existing repository, stop and report the ambiguity rather than silently choosing an arbitrary field.

---

## Rule 2 — pm_method_version

Set:

```text
canonical_json["pm_method_version"]
    = Submission.pm_method_version
```

Example:

```text
Submission.pm_method_version = "2.1"
```

Result:

```json
"pm_method_version": "2.1"
```

If uploaded JSON already contains `pm_method_version`, overwrite it.

If it does not exist, insert it.

The value from the Submission is authoritative.

Do NOT trust or infer this value from uploaded JSON.

---

# 8. Preserve All Other JSON Content

This is a critical requirement.

Apart from:

```text
name
pm_method_version
```

canonicalization MUST NOT intentionally modify other fields.

For example, do not currently modify:

```text
inherits
filament_settings_id
version
nozzle_temperature
flow_ratio
retraction
unknown slicer fields
```

The model is:

```text
canonical_json = deep copy of uploaded_json

canonical_json["name"] = ...
canonical_json["pm_method_version"] = ...
```

Everything else remains semantically unchanged.

Do not reconstruct JSON from selected Bitable columns.

---

# 9. Do Not Mutate uploaded_json

`uploaded_json` is the original engineer-provided payload.

It must remain unchanged.

Implementation should avoid accidental in-place mutation.

Conceptually:

```python
canonical = deepcopy(uploaded)
```

then apply canonicalization to `canonical`.

After processing:

```text
uploaded_json
    = exactly the original submitted content/data

canonical_json
    = normalized candidate
```

Add a test for this.

---

# 10. Preset Key

Generate/store the logical preset identity:

```text
preset_key
```

using the existing project convention.

Conceptually:

```text
{pi_code}|{machine}|{slicer}
```

Do not introduce a second incompatible preset-key format if Phase 1 already has one.

The purpose is to provide a stable identity used for exact Preset lookup.

---

# 11. Automatic Operation Detection

The user MUST NOT choose CREATE or UPDATE.

Determine it automatically by exact Preset lookup.

## No matching Preset

If no Preset exists for `preset_key`:

```text
operation = CREATE
preset = empty
base_version_id = empty
```

Do NOT create a Preset.

Do NOT create PresetVersion v1.

Those belong to the future publication phase.

---

## Existing Preset

If the Preset exists:

```text
operation = UPDATE
preset = existing Preset
base_version_id = existing Preset.current_version
```

The Submission should therefore capture which published version it was based on when enrichment occurred.

---

# 12. base_version_id Semantics

`base_version_id` identifies the exact published PresetVersion used as the comparison/review baseline.

Example:

```text
Preset P42
current_version → P42@v7
```

Submission enrichment should produce:

```text
operation = UPDATE
preset = P42
base_version_id = P42@v7
```

For CREATE:

```text
base_version_id = null
```

Do NOT calculate:

```text
next_version
target_version
v8
```

in this phase.

Version allocation belongs to future publication logic.

---

# 13. Freeze the Baseline

Once enrichment successfully reaches:

```text
READY_FOR_REVIEW
```

do not automatically change:

```text
operation
preset
preset_key
base_version_id
canonical_json
diff
```

just because the database changes later.

Example:

Submission S123 is enriched when:

```text
current version = v7
```

Therefore:

```text
S123.base_version_id = v7
```

If another Submission later publishes v8, S123 must still say:

```text
base_version_id = v7
```

Do NOT silently update it to v8.

Future publication logic will detect that the baseline became stale.

That functionality is OUT OF SCOPE for this phase.

---

# 14. Diff

Diff must compare the content that will actually be reviewed.

Therefore use:

```text
canonical_json
```

not:

```text
uploaded_json
```

as the candidate side.

## UPDATE

Load:

```text
base_version_id
      ↓
PresetVersion.canonical_json
```

and compare:

```text
base canonical JSON
        ↓
       diff
        ↑
candidate canonical JSON
```

Conceptually:

```text
diff(
    base_version.canonical_json,
    submission.canonical_json
)
```

Use the existing structured diff implementation where possible.

Do not replace working diff code without a concrete reason.

---

## CREATE

There is no base version.

Do not invent one.

Use the existing CREATE diff representation if Phase 1 already defines one.

Do not over-engineer CREATE diff presentation in this task.

---

# 15. Validation Result

Continue storing validation results on Submission.

Successful example:

```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

Failure example:

```json
{
  "valid": false,
  "errors": [
    {
      "code": "...",
      "message": "..."
    }
  ],
  "warnings": []
}
```

Exact representation may follow the existing implementation.

Do not redesign a working validation result format merely to match this example.

---

# 16. Successful Final State

For an existing preset:

```text
Submission S123

USER INPUT
────────────────────────
pi_code            L2002CF
machine            BBL P2S
slicer             BambuStudio
pm_method_version  2.1
uploaded_json      {...}

SYSTEM ENRICHMENT
────────────────────────
preset_key         L2002CF|BBL P2S|BambuStudio
operation          UPDATE
preset             P42
base_version_id    P42@v7

canonical_json     {...}
validation         PASS
diff               {...}

status             READY_FOR_REVIEW
```

Canonical JSON must contain:

```json
{
  "...": "...",
  "name": "L2002CF @BBL P2S",
  "pm_method_version": "2.1"
}
```

while preserving all unrelated uploaded fields.

---

# 17. CREATE Example

Assume:

```text
L2002CF|BBL P2S|BambuStudio
```

does not exist.

Expected:

```text
preset_key         L2002CF|BBL P2S|BambuStudio
operation          CREATE
preset             empty
base_version_id    empty

canonical_json     populated
validation         PASS
diff               populated according to existing CREATE behavior

status             READY_FOR_REVIEW
```

No Preset or PresetVersion is created.

---

# 18. Tests

Add focused tests only.

## T1 — BambuStudio name normalization

Input:

```json
{
  "name": "Generic PLA",
  "inherits": "Generic PLA"
}
```

Context:

```text
pi_code = L2002CF
printer = BBL P2S
```

Expected canonical JSON:

```json
{
  "name": "L2002CF @BBL P2S",
  "inherits": "Generic PLA"
}
```

---

## T2 — pm_method_version insertion

Uploaded JSON does not contain `pm_method_version`.

Submission:

```text
pm_method_version = 2.1
```

Expected:

```json
"pm_method_version": "2.1"
```

---

## T3 — pm_method_version overwrite

Uploaded JSON:

```json
"pm_method_version": "1.0"
```

Submission:

```text
pm_method_version = 2.1
```

Expected canonical:

```json
"pm_method_version": "2.1"
```

Uploaded JSON must still contain its original `"1.0"` value.

---

## T4 — Other fields preserved

Given arbitrary unrelated fields:

```text
inherits
filament_settings_id
custom field
nested field
```

Expected:

all remain semantically unchanged in canonical JSON.

---

## T5 — CREATE detection

No matching Preset.

Expected:

```text
operation = CREATE
preset = null
base_version_id = null
```

---

## T6 — UPDATE detection

Matching Preset P42 exists:

```text
current_version = P42@v7
```

Expected:

```text
operation = UPDATE
preset = P42
base_version_id = P42@v7
```

---

## T7 — UPDATE diff uses canonical JSON

Create a case where canonicalization changes `name` and/or `pm_method_version`.

Verify the candidate side of diff is `canonical_json`, not raw `uploaded_json`.

---

## T8 — uploaded_json remains unchanged

Run enrichment.

Verify the original uploaded JSON has not been mutated by canonicalization.

---

## T9 — unsupported slicer

Use a slicer other than currently supported BambuStudio.

Expected:

clear unsupported-slicer result/error.

Do not silently process it as BambuStudio.

---

## T10 — baseline remains fixed

Enrich S123 against v7.

Then simulate Preset.current_version changing to v8.

Verify:

```text
S123.base_version_id
```

remains:

```text
v7
```

Do not implement conflict handling; only verify the stored baseline is not automatically rewritten.

---

# 19. Explicitly Out of Scope

Do NOT implement:

```text
review
approve
reject
publish_submission
Preset creation
PresetVersion creation
next version allocation
VERSION_CONFLICT
locking
concurrency control
automatic rebase
automatic merge
NO_CHANGE workflow
Miaoda UI
Git
PR
notifications
OrcaSlicer processing
Cura processing
```

Do not add placeholder implementations for these features.

Leave them for later phases.

---

# 20. Acceptance Criteria

This phase is complete when:

```text
Submission
    │
    ├─ pi_code
    ├─ machine
    ├─ slicer
    ├─ pm_method_version
    └─ uploaded_json
          │
          ▼
   select BambuStudio processor
          │
          ▼
       validate
          │
          ▼
      canonicalize
          │
          ├─ name = "{pi_code} @{printer}"
          └─ pm_method_version = Submission value
          │
          ▼
     resolve preset_key
          │
          ├─ missing → CREATE
          │
          └─ exists  → UPDATE
                         +
                    preset_id
                         +
                   base_version_id
          │
          ▼
     canonical diff
          │
          ▼
   READY_FOR_REVIEW
```

No review or publication occurs.

No new Preset is created.

No new PresetVersion is created.

No next version number is assigned.

No Git operation occurs.

---

# 21. Completion Report

After implementation, report only:

1. files changed;
2. how BambuStudio processing was implemented;
3. exact canonicalization rules implemented;
4. how `operation` is determined;
5. how `base_version_id` is determined;
6. tests added;
7. test results;
8. ambiguities or assumptions encountered.

Do not propose or implement the next phase unless requested.
