# Preset Worker — P6.1: Draft Isolation & Actionable-State Correction

## 0. Purpose

P6.1 is a small corrective phase after P6.

The current Worker incorrectly treats:

```text id="iuxd7x"
DRAFT
```

Submission records as actionable enrichment work.

This causes incomplete engineer drafts to be repeatedly picked up by the polling Worker even when required inputs such as uploaded JSON are not yet present.

P6.1 changes the runtime boundary so that:

> DRAFT is an engineer-owned editing state and is never automatically processed by the Worker.

This phase must remain narrowly scoped.

Do NOT implement M1-B preview processing in P6.1.

---

# 1. Problem

Current behavior is effectively:

```text id="h6phmh"
Engineer creates Draft
        ↓
status = DRAFT
        ↓
Worker polls
        ↓
finds Draft
        ↓
attempts enrichment
        ↓
uploaded JSON missing
        ↓
enrichment fails
        ↓
future poll may try again
```

This behavior is incorrect.

A Draft may legitimately remain incomplete for an arbitrary amount of time.

Examples:

```text id="bczzq5"
identity only
identity + no JSON
JSON not uploaded yet
pm_method_version not selected yet
engineer continues tomorrow
engineer opens same Draft on another device
```

None of these are Worker failures.

They are normal Draft states.

---

# 2. Core Ownership Rule

Establish the following workflow ownership boundary:

```text id="8xck7z"
DRAFT
    ↓
Engineer / Miaoda owns the record

non-DRAFT actionable workflow state
    ↓
Worker may process the record
```

More explicitly:

```text id="shkb9n"
DRAFT
    = editable candidate
    = incomplete data allowed
    = no Worker processing
    = no enrichment attempt
    = no validation attempt
    = no canonicalization attempt
    = no diff attempt
```

---

# 3. Hard Requirement

After P6.1:

```text id="pkvjv9"
DRAFT ∉ Worker actionable states
```

The polling Worker must never discover a Submission solely because:

```text id="s4vx6z"
status == DRAFT
```

---

# 4. Scope

P6.1 includes only:

1. remove DRAFT from Worker actionable discovery;
2. ensure `run_once()` ignores DRAFT;
3. ensure manual/indirect enrichment cannot accidentally treat DRAFT as an actionable runtime state unless explicitly supported for an administrative/debug operation;
4. preserve existing formal workflow behavior;
5. add regression tests;
6. update documentation.

Do not expand scope beyond this.

---

# 5. Explicitly Out of Scope

Do NOT implement:

```text id="cyhwlh"
PREVIEW_REQUESTED
preview processing
preview diff
preview validation
Miaoda preview button
JSON upload UI
M1-B
new review workflow
new publication workflow
webhooks
queues
async runtime
multiple workers
distributed locks
automatic Draft completeness detection
automatic Draft promotion
```

P6.1 is only about Draft isolation.

---

# 6. Inspect Existing Implementation First

Before modifying code, identify:

1. where actionable Submission statuses are defined;
2. where polling queries enrichment candidates;
3. how `run_once()` dispatches enrichment;
4. whether the repository query filters server-side or retrieves records and filters locally;
5. whether `enrich_submission()` itself checks status;
6. how the manual CLI command:

```bash id="b5ik9l"
preset-worker enrich <submission_id>
```

behaves with DRAFT;
7. existing tests covering actionable-state discovery.

Report these findings after implementation.

Do not assume the current code matches earlier design documents.

Modify the actual implementation.

---

# 7. Worker Discovery Rule

The Worker must query only states that explicitly mean:

> background work has been requested.

For formal enrichment, use the existing actual formal-enrichment trigger state.

If the current implementation uses:

```text id="f63kux"
VALIDATING
```

as the formal enrichment trigger, then polling should conceptually be:

```python id="iw4xdh"
enrichment_states = {
    "VALIDATING",
}
```

NOT:

```python id="fm7nx6"
enrichment_states = {
    "DRAFT",
    "VALIDATING",
}
```

Do not invent a new formal state if the existing implementation already has an appropriate one.

---

# 8. Publication Discovery Remains Unchanged

Existing publication behavior must remain intact.

For example, if publication currently discovers:

```text id="rxafnu"
APPROVING
```

continue doing so.

P6.1 must not change P3 publication semantics.

Conceptually:

```text id="6q29u1"
VALIDATING
    ↓
enrichment

APPROVING
    ↓
publication
```

while:

```text id="7s6pfy"
DRAFT
    ↓
nothing
```

---

# 9. Server-Side Filtering Preferred

If the Feishu repository supports querying by Submission status, filter actionable states at the query level.

Preferred:

```text id="h31l4m"
query Submission
WHERE status IN actionable_states
```

Avoid:

```text id="s8i7a7"
load every Submission
↓
filter DRAFT in Python
```

The polling Worker should not repeatedly fetch inactive Drafts.

This is especially important as the Submission table grows.

---

# 10. `run_once()` Behavior

After P6.1:

```text id="nd8qk9"
run_once()
    │
    ├── discover formal enrichment candidates
    │       status = VALIDATING
    │
    ├── process them
    │
    ├── discover publication candidates
    │       status = APPROVING
    │
    ├── process them
    │
    └── return
```

DRAFT must not appear in either candidate set.

---

# 11. Draft Completeness Must Not Matter

Do NOT replace:

```text id="6kz4tv"
process all DRAFT
```

with:

```text id="rhz5bb"
process DRAFT if JSON exists
```

or:

```text id="4evu0n"
process DRAFT if required fields appear complete
```

That would preserve the architectural problem.

The rule is based on workflow intent, not data completeness.

Correct:

```text id="sm88n5"
DRAFT
→ never background-process
```

Incorrect:

```text id="n4j6w7"
DRAFT + JSON
→ process
```

The presence of JSON does not mean the engineer has requested processing.

---

# 12. No Automatic State Promotion

The Worker must NOT inspect a Draft and decide:

```text id="cqexuf"
"This looks complete"
```

then change:

```text id="qmt7za"
DRAFT → VALIDATING
```

Only an explicit future user/workflow action may request that transition.

P6.1 does not implement that action.

---

# 13. Enrichment Service Guard

Inspect the enrichment service's current status guard.

The normal runtime path should require the appropriate formal enrichment state.

If the production enrichment service currently accepts DRAFT because P6 used DRAFT as the trigger, correct that assumption.

The normal service behavior should conceptually be:

```python id="ejgplq"
submission = reload_submission(id)

if submission.status != FORMAL_ENRICHMENT_STATE:
    do_not_mutate()
```

This creates defense in depth:

```text id="kcck4a"
repository discovery
        +
service state guard
```

A bug in polling discovery should not be enough to process a Draft.

---

# 14. Manual CLI Semantics

Preserve:

```bash id="opvwp4"
preset-worker enrich <submission_id>
```

as a useful debug/operations command.

However, do not silently let it violate workflow invariants.

Preferred behavior:

```text id="b95i8e"
preset-worker enrich <DRAFT_ID>
```

should refuse with a clear message such as:

```text id="w8wtv3"
Submission is DRAFT and is not eligible for formal enrichment.
```

If there is an existing explicit force/debug mechanism, preserve its documented behavior.

Do NOT add a new `--force` option in P6.1 unless one already exists and is required for compatibility.

---

# 15. No Draft Error Mutation

Worker polling must not mutate an incomplete Draft into:

```text id="c5bjbg"
VALIDATION_FAILED
FAILED
ERROR
```

simply because required enrichment inputs are missing.

Example:

```text id="8r2vbm"
status = DRAFT
uploaded_json = empty
```

Expected after unlimited polling cycles:

```text id="y1nydx"
status = DRAFT
```

with no Worker-generated validation failure.

---

# 16. No Draft Derived Fields

While a Submission remains DRAFT, P6.1 Worker polling must not populate or modify enrichment-derived fields such as:

```text id="k2gy7r"
operation
preset
base_version
canonical_json
validation
diff
```

The exact actual field names should be discovered from the current schema/code.

The principle is:

> Worker polling does not enrich DRAFT records.

---

# 17. Logging

Normal existence of Drafts must not produce Worker warnings/errors.

Do not log messages such as:

```text id="t1j6s8"
failed to enrich Draft because uploaded_json missing
```

because the Worker should never attempt the operation.

Idle polling should remain quiet according to existing P6 logging rules.

Do not add per-Draft:

```text id="4jn3g5"
Skipping Draft...
```

INFO logs.

That would create unnecessary log noise.

---

# 18. Polling Performance

After P6.1, a table containing:

```text id="8qq2kk"
1000 DRAFT
0 VALIDATING
0 APPROVING
```

should behave conceptually as:

```text id="xzw4so"
poll
→ no actionable records
→ wait
```

not:

```text id="8hx40w"
fetch 1000 Drafts
→ inspect each
→ skip 1000
→ wait
```

Use server-side actionable-state filtering wherever the Feishu API/repository abstraction permits it.

---

# 19. Preserve P1–P5 Semantics

Do not modify:

```text id="5n90sa"
BambuStudio validation rules
canonicalization rules
name generation
pm_method_version handling
preset_key semantics
CREATE / UPDATE resolution
base_version semantics
diff semantics
publication semantics
version conflict semantics
idempotency semantics
photo projection semantics
```

P6.1 changes WHEN enrichment is invoked.

It does not change WHAT enrichment computes.

---

# 20. Preserve P6 Runtime Architecture

Do not change the basic runtime:

```text id="lbyxjd"
run()
   ↓
run_once()
   ↓
poll Bitable
   ↓
dispatch existing services
   ↓
wait
```

Keep:

```text id="u0vbt5"
serial processing
single-worker production assumption
poll interval
batch size
graceful shutdown
per-record exception isolation
```

unless a tiny mechanical adjustment is required by the status filter.

---

# 21. Test P6.1-T1 — Empty Draft

Create:

```text id="z1d5oz"
Submission
status = DRAFT
uploaded_json = empty
```

Run:

```text id="xblwvo"
run_once()
```

Expected:

```text id="42sygu"
Submission not discovered as actionable
no enrichment call
status remains DRAFT
no derived fields changed
```

---

# 22. Test P6.1-T2 — Complete-Looking Draft

Create a Draft containing all fields that would otherwise be sufficient for enrichment:

```text id="01mxyf"
status = DRAFT
PI Code = valid
Printer = valid
Slicer = BambuStudio
uploaded_json = valid
pm_method_version = valid
```

Run:

```text id="tn1g88"
run_once()
```

Expected:

```text id="f4fjgr"
no enrichment
status remains DRAFT
```

This test is important.

It proves processing is triggered by workflow state, not apparent completeness.

---

# 23. Test P6.1-T3 — Many Drafts

Create multiple DRAFT records.

Run:

```text id="o6ub6h"
run_once()
```

Expected:

```text id="2ev8ca"
0 Drafts dispatched
```

Where possible, verify the repository query itself excludes DRAFT rather than loading and skipping them afterward.

---

# 24. Test P6.1-T4 — Formal Enrichment Still Works

Create a valid Submission in the existing formal enrichment trigger state, expected to be:

```text id="xswg9e"
VALIDATING
```

Run:

```text id="evhdd3"
run_once()
```

Expected:

```text id="6jv0zn"
Submission discovered
existing enrichment executes
existing P1 behavior preserved
```

Expected successful final state according to current implementation:

```text id="ucm95u"
READY_FOR_REVIEW
```

---

# 25. Test P6.1-T5 — Invalid Formal Submission

Create:

```text id="b5zd8p"
status = VALIDATING
required enrichment input invalid/missing
```

Run Worker.

Expected:

the existing formal validation-failure behavior remains unchanged.

Do not redefine failure semantics in P6.1.

This distinguishes:

```text id="8hqh0e"
DRAFT + incomplete
    = normal

VALIDATING + incomplete
    = actual workflow error
```

---

# 26. Test P6.1-T6 — Publication Regression

Create/use a valid:

```text id="u7yqgn"
APPROVING
```

Submission.

Run Worker.

Expected:

existing P3 publication path still executes correctly.

---

# 27. Test P6.1-T7 — Repeated Polling

Leave an incomplete Draft in Bitable.

Run:

```text id="f5f22d"
run_once()
run_once()
run_once()
```

or run the Worker for several polling intervals.

Expected:

```text id="wtp6eg"
Draft unchanged
no repeated validation errors
no repeated enrichment attempts
no error-log spam
```

---

# 28. Test P6.1-T8 — Manual Enrich Against Draft

Run:

```bash id="gvlix1"
preset-worker enrich <draft_submission_id>
```

Expected:

clear refusal because DRAFT is not eligible for formal enrichment.

No Submission fields should change.

---

# 29. Test P6.1-T9 — State Transition Makes Record Actionable

Start with:

```text id="4uvc1g"
status = DRAFT
```

Run Worker:

```text id="u7fc67"
→ ignored
```

Then externally perform the existing legitimate workflow transition:

```text id="u3fs6q"
DRAFT → VALIDATING
```

Run Worker again.

Expected:

```text id="buz5fv"
→ discovered
→ enrichment attempted
```

This proves the state transition, rather than record creation or completeness, is the work trigger.

---

# 30. Test P6.1-T10 — No Draft Mutation

Snapshot all relevant fields of a Draft before Worker execution.

Run multiple Worker cycles.

Compare after execution.

Expected:

```text id="uvibkn"
no Worker-owned field changed
```

Especially verify:

```text id="znx5ay"
status
operation
preset
base_version
canonical_json
validation
diff
```

---

# 31. Integration Test With Miaoda M1-A

Perform one real end-to-end test:

```text id="jfs2t8"
Miaoda
    ↓
create Submission
    ↓
status = DRAFT
    ↓
select PI Code / Printer / Slicer
    ↓
save Draft
```

Leave the Draft in Bitable.

Allow the production-style Worker to run for several polling intervals.

Then reopen the Draft from another machine/browser.

Expected:

```text id="2i8rri"
Draft still exists
status still DRAFT
identity fields preserved
Draft remains editable
no Worker validation error
no Worker canonicalization
no Worker diff
```

This test should pass before M1-B begins.

---

# 32. Future M1-B Extension Point

P6.1 must intentionally leave room for a future explicit preview trigger.

Expected future architecture may look like:

```text id="u88o5z"
DRAFT
   │
   │ user requests preview
   ▼
PREVIEW_REQUESTED
   │
   │ Worker
   ▼
DRAFT
```

and formal submission may later use:

```text id="zd6y8v"
DRAFT
   │
   │ user submits for review
   ▼
VALIDATING
   │
   │ Worker
   ▼
READY_FOR_REVIEW
```

Do NOT implement these new transitions in P6.1.

The only requirement is that the architecture does not prevent adding them later.

---

# 33. Architectural Invariant

After P6.1, document the following invariant:

> A Submission being present in Bitable does not imply that the Worker should process it.

Worker execution is requested by an explicit actionable workflow state.

In particular:

```text id="g2s9lc"
DRAFT
```

means:

> The engineer currently owns this mutable candidate. Background processing has not been requested.

This invariant should guide future M1-B and Worker development.

---

# 34. Acceptance Criteria

P6.1 is complete when:

```text id="lh5h8b"
[ ] DRAFT is removed from Worker actionable discovery

[ ] DRAFT is filtered out before dispatch

[ ] repository query excludes DRAFT where supported

[ ] incomplete DRAFT produces no enrichment attempt

[ ] complete-looking DRAFT also produces no enrichment attempt

[ ] repeated polling produces no Draft errors/log spam

[ ] Worker does not populate derived fields on DRAFT

[ ] formal enrichment state remains actionable

[ ] existing enrichment behavior is unchanged once legitimately triggered

[ ] APPROVING publication remains actionable

[ ] publication behavior remains unchanged

[ ] manual enrich against DRAFT does not silently violate state invariants

[ ] no automatic DRAFT → VALIDATING promotion exists

[ ] no completeness-based Draft processing exists

[ ] Miaoda M1-A Draft survives multiple Worker polling cycles unchanged

[ ] existing P1–P6 regression tests pass
```

---

# 35. Completion Report

After implementation, report:

1. where actionable enrichment states were previously defined;
2. why DRAFT was previously discovered;
3. the exact old actionable-state set;
4. the exact new actionable-state set;
5. the formal enrichment trigger state actually used by the current implementation;
6. whether filtering occurs server-side in the Feishu query;
7. whether the enrichment service also has a state guard;
8. behavior of `preset-worker enrich <DRAFT_ID>`;
9. result of incomplete-Draft test;
10. result of complete-looking-Draft test;
11. result of repeated-polling test;
12. result of DRAFT → formal-trigger-state test;
13. result of publication regression test;
14. result of real Miaoda Draft integration test;
15. confirmation that no preview functionality was implemented;
16. confirmation that no P1–P5 business semantics were changed.