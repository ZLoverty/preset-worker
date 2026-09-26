# Preset Worker — P6.2: PREVIEW_REQUESTED Polling & Dispatch

## 0. Goal

Extend the existing P6/P6.1 polling Worker so that Submission records in:

```text id="f1ut7j"
PREVIEW_REQUESTED
```

are discovered and dispatched to the existing M1-B preview-processing service.

P6.2 is a runtime integration phase.

Do NOT redesign preview business logic.

---

# 1. Existing State Ownership

Preserve the current architecture:

```text id="p63fl1"
DRAFT
    → engineer-owned
    → Worker ignores

PREVIEW_REQUESTED
    → Worker-owned
    → preview processing

VALIDATING
    → Worker-owned
    → formal enrichment

READY_FOR_REVIEW
    → reviewer-owned

APPROVING
    → Worker-owned
    → publication
```

The key invariant remains:

> Worker processes explicit actionable workflow states, not records that merely look complete.

---

# 2. Required Worker Actionable States

After P6.2 the runtime must recognize three distinct classes of work:

```text id="y86b8e"
PREVIEW_REQUESTED
    → preview service

VALIDATING
    → formal enrichment service

APPROVING
    → publication service
```

`DRAFT` must remain excluded.

Do NOT regress P6.1.

---

# 3. Inspect Current Implementation First

Before modifying code, inspect and report:

1. current actionable-state definitions;
2. current repository discovery methods;
3. current `run_once()` structure;
4. current preview service entry point implemented for M1-B;
5. preview service's required Submission state;
6. preview success state;
7. preview failure state;
8. existing tests for preview processing.

Use the actual implementation.

Do not recreate a second preview implementation.

---

# 4. Repository Discovery

Add a repository query for preview candidates.

Conceptually:

```python id="45v40j"
list_preview_candidates(
    status="PREVIEW_REQUESTED",
    limit=batch_size,
)
```

or extend the existing repository abstraction cleanly.

Prefer server-side filtering:

```text id="5unpnf"
Submission.status == PREVIEW_REQUESTED
```

Do NOT fetch all Drafts/Submissions and filter them locally.

---

# 5. Do Not Mix Preview With Formal Enrichment Discovery

Avoid an ambiguous query such as:

```python id="r6g71e"
list_enrichment_candidates(
    statuses=[
        "PREVIEW_REQUESTED",
        "VALIDATING",
    ]
)
```

followed by business branching deep inside enrichment.

Prefer explicit dispatch semantics:

```text id="2t58yp"
PREVIEW_REQUESTED
        ↓
preview service

VALIDATING
        ↓
formal enrichment service
```

The computation may be shared internally, but the workflow operations are different.

---

# 6. `run_once()` Integration

Extend `run_once()` conceptually to:

```text id="u9vgjp"
run_once()
    │
    ├── discover preview candidates
    │       status = PREVIEW_REQUESTED
    │
    ├── dispatch each to preview service
    │
    ├── discover formal enrichment candidates
    │       status = VALIDATING
    │
    ├── dispatch each to enrichment service
    │
    ├── discover publication candidates
    │       status = APPROVING
    │
    ├── dispatch each to publication service
    │
    └── return
```

Keep processing serial.

Do not introduce threads or asyncio.

---

# 7. Preview Service Must Reload State

Before performing preview work, the preview service must reload the Submission.

It must verify:

```text id="4iuvhg"
current status == PREVIEW_REQUESTED
```

If not:

```text id="y3vbnz"
do not process
do not mutate
```

This is defense in depth.

Discovery alone is not the correctness boundary.

---

# 8. Preview Processing

P6.2 must call the existing M1-B preview path.

Conceptually:

```text id="7p8hlz"
PREVIEW_REQUESTED
        ↓
existing preview service
        ↓
validate
canonicalize
resolve Preset
resolve base
calculate diff
        ↓
write preview result
```

Do NOT duplicate:

```text id="bl3ppn"
JSON parsing
BambuStudio validation
canonicalization
preset_key generation
CREATE/UPDATE resolution
diff logic
```

inside the polling runtime.

---

# 9. Preview Success

Preserve the M1-B success semantics.

Expected:

```text id="g6cij9"
PREVIEW_REQUESTED
        ↓
Worker preview succeeds
        ↓
preview result written
        ↓
DRAFT
```

After returning to DRAFT:

```text id="qdmglq"
engineer regains edit ownership
```

The Worker must not immediately process the resulting DRAFT again.

P6.1 guarantees this.

---

# 10. Preview Failure

Preserve M1-B preview-failure semantics.

Expected:

```text id="i0fyq3"
PREVIEW_REQUESTED
        ↓
preview validation / processing failure
        ↓
preview error written
        ↓
DRAFT
```

Do NOT convert ordinary preview failure into:

```text id="f0vqg7"
VALIDATION_FAILED
```

Preview-time invalid input is engineer feedback, not formal workflow history.

---

# 11. Infrastructure Failure Is Different

Distinguish candidate/validation failure from transient infrastructure failure.

Examples:

### Candidate failure

```text id="95qfls"
malformed JSON
invalid BambuStudio preset
unsupported candidate
duplicate Preset
missing current_version
```

Expected:

```text id="aprlpx"
write preview error
return to DRAFT
```

### Infrastructure failure

```text id="j47e8a"
Feishu timeout
temporary attachment download failure
temporary API failure
```

Prefer leaving:

```text id="f8l2c7"
PREVIEW_REQUESTED
```

actionable for a later polling retry, according to existing service/error conventions.

Do not tell the engineer their preset is invalid merely because Feishu timed out.

---

# 12. Per-Record Exception Isolation

One broken preview request must not stop the Worker.

Example:

```text id="nmbg04"
S1 PREVIEW_REQUESTED → infrastructure exception
S2 PREVIEW_REQUESTED → valid
S3 VALIDATING        → valid
```

Expected:

```text id="g5ktmt"
S1 failure logged / remains recoverable
S2 processed
S3 processed
Worker continues running
```

Preserve P6 per-record exception isolation.

---

# 13. No Tight Retry Loop

If a preview request fails because of transient infrastructure:

do not retry repeatedly inside the same dispatch operation.

Let the next polling cycle retry it.

This preserves the existing P6 model:

```text id="91azyp"
poll
→ attempt
→ transient failure
→ continue
→ wait
→ next poll
```

---

# 14. Batch Size

Preview discovery must respect the existing Worker batch-size configuration.

Do not create an independent hard-coded preview batch size unless the current architecture explicitly requires separate configuration.

Use the existing simple Worker runtime model.

---

# 15. Ordering

If the repository supports stable ordering, process preview requests oldest-first.

This is desirable but not a correctness requirement.

Do not introduce complex scheduling.

---

# 16. Logging

Log useful lifecycle events such as:

```text id="0d4mte"
processing preview request <submission>
preview completed
preview candidate invalid
preview infrastructure failure
```

Do not log full uploaded JSON or canonical JSON by default.

Avoid leaking potentially large artifacts into logs.

Normal DRAFT records should still produce no Worker log noise.

---

# 17. `run_once()` Return/Statistics

If `run_once()` currently reports processing counts, extend them consistently to include preview work.

For example, if appropriate:

```text id="ouq5m8"
preview_processed
enrichment_processed
publication_processed
```

Do not redesign the return type unnecessarily if no such reporting currently exists.

---

# 18. Manual Preview Command

If M1-B already introduced a manual preview service/CLI command, preserve it.

If no manual command exists, adding one is optional and NOT required for P6.2.

Do not expand scope solely to add CLI features.

The required integration is:

```text id="rm0g4e"
polling Worker
→ PREVIEW_REQUESTED
→ existing preview service
```

---

# 19. No Publication Side Effects

Processing PREVIEW_REQUESTED must never:

```text id="3z3uvl"
create Preset
create PresetVersion
update Preset.current_version
set published_version
set APPROVED
project current photos to Preset
```

Verify this with integration tests.

---

# 20. Do Not Trust Preview for Formal Enrichment

P6.2 must not change formal submission behavior.

Later:

```text id="wcd55s"
DRAFT
→ VALIDATING
```

must still cause formal enrichment to recompute the candidate.

Do not optimize by reusing preview output as authoritative formal output.

---

# 21. Test P6.2-T1 — DRAFT Still Ignored

Create:

```text id="x0kdo4"
status = DRAFT
valid uploaded_json
```

Run:

```text id="85yq6c"
run_once()
```

Expected:

```text id="1ftfyj"
no preview
no enrichment
record unchanged
```

This is the primary P6.1 regression test.

---

# 22. Test P6.2-T2 — Preview Request Discovered

Create:

```text id="0zzd2u"
status = PREVIEW_REQUESTED
valid preview inputs
```

Run:

```text id="7whknx"
run_once()
```

Expected:

```text id="fd2fgb"
record discovered
preview service called exactly once
```

---

# 23. Test P6.2-T3 — Successful Preview

Given valid CREATE candidate:

```text id="em8hdb"
PREVIEW_REQUESTED
```

run Worker.

Expected:

```text id="8eh7jq"
preview generated
status → DRAFT
```

Verify preview result exists.

Verify:

```text id="3e24yx"
no Preset created
no PresetVersion created
```

---

# 24. Test P6.2-T4 — UPDATE Preview

Given:

```text id="lylcuv"
unique existing Preset
current_version = v7
valid changed candidate
```

request preview.

Expected:

```text id="9xq97g"
PREVIEW_REQUESTED
→ Worker
→ DRAFT
```

with:

```text id="13ozak"
operation preview = UPDATE
base = v7
correct diff
```

---

# 25. Test P6.2-T5 — Candidate Failure

Use malformed/invalid JSON.

Expected:

```text id="p7lm4o"
PREVIEW_REQUESTED
→ preview service
→ preview error recorded
→ DRAFT
```

No formal:

```text id="6jyd2g"
VALIDATION_FAILED
```

unless the actual M1-B design explicitly uses another documented preview-error mechanism.

---

# 26. Test P6.2-T6 — Infrastructure Failure

Simulate a transient repository/API/attachment failure.

Expected:

```text id="fmw0l9"
Worker does not crash
other records continue
request remains recoverable/actionable
```

Verify the exact retry behavior follows current service conventions.

---

# 27. Test P6.2-T7 — State Changed Before Dispatch

Discovery returns Submission S as:

```text id="xew59b"
PREVIEW_REQUESTED
```

Before preview service processes it, change current authoritative state to:

```text id="m1xovw"
DRAFT
```

Expected:

```text id="cnj6ax"
service reloads state
refuses processing
no preview fields mutated
```

---

# 28. Test P6.2-T8 — Mixed Workload

Prepare:

```text id="y8zj25"
S1 = DRAFT
S2 = PREVIEW_REQUESTED
S3 = VALIDATING
S4 = APPROVING
```

Run:

```text id="y7d6a4"
run_once()
```

Expected:

```text id="1t8m80"
S1 ignored
S2 preview processed
S3 formal enrichment processed
S4 publication processed
```

Each must be dispatched to the correct service.

---

# 29. Test P6.2-T9 — Multiple Preview Requests

Prepare several:

```text id="g9gjnr"
PREVIEW_REQUESTED
```

records.

Run Worker.

Expected:

```text id="p9udv5"
processed serially
batch-size respected
one failure does not block later records
```

---

# 30. Test P6.2-T10 — Polling Integration

Run:

```bash id="pnm6ft"
preset-worker run
```

Then use the real Miaoda M1-B UI:

```text id="tdjnf2"
open Draft
upload valid JSON
select pm_method_version
click 生成预览
```

Expected:

```text id="ey5wlu"
DRAFT
→ PREVIEW_REQUESTED
→ Worker discovers it
→ preview generated
→ DRAFT
→ Miaoda displays preview
```

No manual Worker command should be necessary.

This is the main end-to-end acceptance test.

---

# 31. Test P6.2-T11 — Repeated Polling After Success

After successful preview:

```text id="dv83nj"
status = DRAFT
```

allow Worker to run several more polling cycles.

Expected:

```text id="ggz03c"
no additional preview processing
```

This verifies P6.1 + P6.2 compose correctly.

---

# 32. Test P6.2-T12 — Preview Has No Publication Side Effects

Snapshot:

```text id="ahxx1h"
Preset count
PresetVersion count
Preset.current_version
```

Run one or multiple previews.

Expected:

```text id="opks9p"
Preset count unchanged
PresetVersion count unchanged
current_version unchanged
```

---

# 33. Architecture After P6.2

The intended runtime is:

```text id="xx3i7v"
                    Submission
                        │
          ┌─────────────┼─────────────┐
          │             │             │
        DRAFT     PREVIEW_REQUESTED VALIDATING
          │             │             │
          │             ▼             ▼
       ignore       PreviewService EnrichmentService
                        │             │
                        ▼             ▼
                      DRAFT     READY_FOR_REVIEW


                   APPROVING
                        │
                        ▼
                PublicationService
                        │
                        ▼
                    APPROVED
```

Do not collapse these workflow responsibilities.

---

# 34. Acceptance Criteria

P6.2 is complete when:

```text id="9eim3n"
[ ] PREVIEW_REQUESTED is Worker-actionable

[ ] PREVIEW_REQUESTED is discovered server-side where supported

[ ] PREVIEW_REQUESTED dispatches to the existing preview service

[ ] DRAFT remains non-actionable

[ ] VALIDATING still dispatches to formal enrichment

[ ] APPROVING still dispatches to publication

[ ] preview service reloads and verifies current state

[ ] successful preview returns to DRAFT

[ ] preview candidate failure returns to DRAFT with feedback

[ ] transient infrastructure failure remains recoverable

[ ] one preview failure does not stop the Worker

[ ] no tight retry loop exists

[ ] preview does not create Preset

[ ] preview does not create PresetVersion

[ ] preview does not update Preset.current_version

[ ] repeated polling after preview success does nothing

[ ] real Miaoda → Worker preview flow works without manual intervention

[ ] existing P1–P6.1 tests continue to pass
```

---

# 35. Completion Report

After implementation report:

1. previous Worker actionable states;
2. new Worker actionable states;
3. repository method used to discover PREVIEW_REQUESTED;
4. whether filtering happens server-side;
5. preview service entry point called by Worker;
6. where the PREVIEW_REQUESTED state guard is enforced;
7. preview success transition;
8. candidate-failure transition;
9. transient-infrastructure-failure behavior;
10. `run_once()` dispatch order;
11. result of DRAFT regression test;
12. result of successful CREATE preview;
13. result of UPDATE preview;
14. result of invalid candidate preview;
15. result of mixed-workload test;
16. result of real Miaoda end-to-end test;
17. confirmation that preview creates no publication artifacts;
18. confirmation that no preview business logic was duplicated in Worker runtime.