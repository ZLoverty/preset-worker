# P9-D5 Cross-Slicer Preview Integration Audit

## Executive summary

The six validators are independently callable and produce compatible
`p9b2.consistency.v1` report shapes for the available fixtures. The current
Preview path, however, intentionally dispatches consistency validation only
for `BambuStudio` and has no stale-write protection.

Production enablement is therefore **NOT READY**.

The two critical P9-D6 blockers are:

1. Add an explicit six-slicer consistency dispatch while preserving the native
   Preset processor registry and the non-blocking boundary.
2. Prevent stale consistency results from being accepted as current. At
   minimum, re-read and compare the relevant input attachment identities and
   status immediately before writeback; an atomic conditional write should be
   used if the available Feishu API supports it.

A separate lifecycle defect must also be corrected: `_write_candidate_failure()`
does not clear `consistency_report`, and the field-size fallback omits the field
from the retry update. Both paths can leave a previous report visible.

## Evidence and implementation map

| Area | Evidence | Finding | Status |
|---|---|---|---|
| Worker polling | `src/preset_worker/runtime.py:WorkerRuntime.run_once/_discover/_dispatch` | Discovers `PREVIEW_REQUESTED`, dispatches serially in one process | VERIFIED |
| Preview orchestration | `src/preset_worker/services/preview.py:PreviewService.preview_submission` | Native candidate first, optional consistency second, one result PUT | VERIFIED |
| Native Preset processing | `src/preset_worker/services/enrichment.py:SubmissionEnrichment.process_candidate` | Uses `default_processor_registry()` and preserves `CandidateResult.source_artifact` | VERIFIED |
| Consistency boundary | `src/preset_worker/services/consistency_preview.py:build_consistency_report` | Exact `BambuStudio` gate; other slicers return empty text | VERIFIED |
| Six validators | `src/preset_worker/three_mf/consistency.py` and `__init__.py` | All six callable; only Bambu is Preview-connected | VERIFIED |
| Report storage | `src/preset_worker/services/preview.py:_write_preview_result` | Writes one multiline text field, with a size-error retry | VERIFIED |
| Stale-write guard | `preview.py`, `enrichment.py`, `runtime.py` | No revision, input recheck, request generation, or conditional update | VERIFIED ABSENCE |
| Miaoda implementation | Repository search and `docs/p9-B3-A*` | No frontend implementation is present | NOT_VERIFIED |

## Actual Preview call graph

```text
WorkerRuntime.run()
  -> run_once()
     -> _discover("PREVIEW_REQUESTED", action="preview")
        -> FeishuClient.list_preview_candidates()
           -> find_submission_candidates()
     -> _dispatch(..., action="preview")
        -> PreviewService.preview_submission(record=discovered_record)
           -> status must be PREVIEW_REQUESTED
           -> SubmissionEnrichment.process_candidate()
              -> download first preset data/uploaded_json attachment
              -> registry.get(fields.slicer)
              -> process_artifact(processor, artifact, context)
                 -> parse / validate / normalize / company policy / serialize
              -> find Preset and optional base version
              -> calculate UnifiedDiff
           -> build_consistency_report(client, record, candidate)
              -> currently only if slicer == BambuStudio
              -> download first preset 3mf attachment
              -> validate_bambu_consistency()
              -> serialize {status, generated_at, report} or ERROR envelope
           -> _write_preview_result()
              -> reuse/upload canonical_json attachment
              -> one Feishu update_submission PUT
              -> set status DRAFT
```

Consistency runs after native Preset validation/diff preparation and before the
single Preview result write. It is inside `build_consistency_report`'s broad
exception boundary, so a consistency exception does not prevent the native
Preview result from being written.

## Validator dispatch audit

Canonical processor identifiers are supplied by `slicer_id` and registered in
`src/preset_worker/slicers/registry.py`:

| Slicer key | Native processor | Consistency entry point |
|---|---|---|
| `BambuStudio` | `BambuStudioProcessor` | `validate_bambu_consistency` |
| `CrealityPrint` | `CrealityPrintProcessor` | `validate_creality_consistency` |
| `ElegooSlicer` | `ElegooSlicerProcessor` | `validate_elegoo_consistency` |
| `OrcaSlicer` | `OrcaSlicerProcessor` | `validate_orca_consistency` |
| `SnapmakerOrcaSlicer` | `SnapmakerOrcaSlicerProcessor` | `validate_snapmaker_orca_consistency` |
| `PrusaSlicer` | `PrusaSlicerProcessor` | `validate_prusa_slicer_consistency` |

The existing processor registry is appropriate for native Preset processing,
but attaching consistency behavior directly to the processor protocol would
couple native CRUD processing to optional 3MF validation and create avoidable
circular-import risk. D6 should use a small explicit mapping keyed by these
canonical slicer IDs, located beside `consistency_preview.py` or in a small
consistency dispatch module. Unknown keys should return empty report text (or a
sanitized unsupported envelope if that policy is approved), never invoke a
different slicer's validator.

Recommended callable contract:

```python
validator(candidate.source_artifact, project_artifact, context=None)
```

The current validators accept the first two artifacts and optional context;
the dispatch should pass the record's canonical slicer identity and preserve
the current CandidateResult artifact reuse.

## Six-validator evidence

Reports were generated from the real supplied pairs. Bambu uses the real local
pair in `downloads/3mf-fixture/`; the other five use their P9-D0 fixture roots.

| Slicer | Selection | Summary | Report bytes | Runtime status |
|---|---|---|---:|---|
| BambuStudio | `UNIQUE`, slot 1 | `MATCH=2`, `MISSING_IN_PRESET=6` | 63,666 | `RESOLVED/UNRESOLVED` (Bambu-specific) |
| CrealityPrint | `UNIQUE`, slot 1 | `MATCH=3`, `MISSING_IN_PRESET=5` | 28,578 | `NOT_ESTABLISHED` |
| ElegooSlicer | `UNIQUE`, slot 1 | `MATCH=4`, `MISSING_IN_PRESET=4` | 33,702 | `NOT_ESTABLISHED` |
| OrcaSlicer | `[1,4]`, representative slot 1, `MULTIPLE_EQUIVALENT` | `MATCH=3`, `MISSING_IN_PRESET=5` | 33,803 | `NOT_ESTABLISHED` |
| SnapmakerOrcaSlicer | `UNIQUE`, slot 1 | `MATCH=3`, `MISSING_IN_PRESET=5` | 38,327 | `NOT_ESTABLISHED` |
| PrusaSlicer | filename stem, `UNIQUE`, slot 1 | `MATCH=6`, `UNRESOLVED=2` | 45,104 | `NOT_ESTABLISHED` |

All six generated reports use `p9b2.consistency.v1`, include the same required
top-level report sections, and serialize as strict UTF-8 JSON. Additive fields
are present for Prusa mapping evidence and filename identity.

Important distinctions that must remain visible:

- Orca `[1,4]` is duplicate-equivalent selection, not unique identity.
- Prusa slot 1 is filename-derived identity, not native `filament_settings_id`.
- Prusa's two unresolved parameters are not missing-value matches.
- `NOT_ESTABLISHED` is not runtime-effective equivalence.
- Bambu's runtime field remains a Bambu-specific resolution result and should
  not be generalized to the other five slicers.

No dedicated report fingerprint field exists. The report contains artifact and
canonical Preset SHA-256 values in `artifacts`; the generated envelope also has
time-varying `generated_at`. Repeated validation of unchanged artifacts is
deterministic at the inner report level, but the complete stored envelope is
not byte-identical because `generated_at` changes.

## Feishu storage and lifecycle audit

The current field contract is documented in
`docs/p9-B3-A_integration_design.md` and implemented in
`services/consistency_preview.py`:

- field: `consistency_report`;
- type assumed by code: multiline text;
- value: compact UTF-8 JSON envelope;
- envelope: `status`, UTC `generated_at`, and either `report` or sanitized
  `error`;
- code limit: 100,000 UTF-8 bytes;
- oversized reports are replaced by a small ERROR envelope, not truncated;
- no report attachment or additional Feishu field is used.

The six real report sizes are below the code limit, with Prusa currently the
largest at 45,104 bytes. The actual deployed Feishu field limit is not present
in the repository and was not verified against a live schema; mark that limit
NOT_VERIFIED. D6 must verify the field type and byte limit in a non-production
table or authoritative Feishu schema response.

The Feishu client retries token refresh and transient API failures in
`enrichment.py:FeishuClient._request_json`; the Preview result update itself is
one PUT, with no application-level idempotency key or compare-and-swap.

| Scenario | Current behavior | Assessment |
|---|---|---|
| Valid Preset + valid 3MF | Writes READY envelope and native result | VERIFIED |
| Valid Preset, no 3MF | Writes empty string, clearing prior value | VERIFIED |
| Unsupported slicer, valid native Preset | Native Preview fails before consistency and `_write_candidate_failure` omits consistency field | STALE-RISK |
| Invalid 3MF | Consistency catches exception and writes ERROR envelope; native result continues | VERIFIED |
| Invalid Preset | Writes validation failure/status but does not clear old consistency field | STALE-RISK |
| Validation exception | Consistency exception is isolated; native result writes if candidate succeeded | VERIFIED |
| Repeated Preview, unchanged inputs | Recomputes and replaces report; inner report deterministic, envelope timestamp changes | PARTIALLY_VERIFIED |
| Changed Preset | Valid candidate replaces report; invalid candidate can leave old field | STALE-RISK |
| Changed 3MF | Valid candidate replaces report; no attachment changes are rechecked before write | CONCURRENCY-RISK |
| Slicer changed | Valid non-Bambu path writes empty; invalid native path may leave old field | STALE-RISK |
| 3MF removed | Empty string clears old report if native candidate is valid | VERIFIED |
| Worker retry | Transient API retry is bounded, but duplicate workers can overwrite in completion order | NOT_SAFE |

The `_write_preview_result` fallback that removes `consistency_report` after a
field/size error is particularly risky: if the record already contains an old
report, omitting the field from the retry PUT does not clear it.

## Concurrency and stale-result risk

There is no submission revision, attachment-generation field, request ID,
input fingerprint recheck, status guard at write time, or conditional update in
the current path. `WorkerRuntime` is serial within one runtime, but this does
not protect against another Worker process or a user edit during downloads and
validation. The discovered record is passed directly to Preview, so Preview
does not re-read authoritative fields before writing.

The report's artifact hashes provide evidence after the fact; they are not
checked against current Submission inputs before the PUT and are not visible as
a write precondition.

| Strategy | Assessment |
|---|---|
| A. Pre-write input fingerprint recheck | Best minimal D6 safeguard; re-read status and relevant attachment tokens/URLs, recompute or compare the input identity, and skip write if changed. Best effort only; a user can edit immediately after the recheck. |
| B. Preview request generation ID | Useful for correlating retries and UI state, but needs a persisted generation field or an authoritative request token. Alone it does not prevent an old worker from writing. |
| C. Conditional write/CAS | Strongest option if Feishu supports revision/updated-time conditions; repository currently has no implementation or verified API capability. Must be verified before relying on it. |
| D. Existing state-machine guard | Insufficient. The initial status check is against the stale discovered record and there is no status condition on PUT. |

Recommendation: D6 should implement A, include a request/input fingerprint in
the report envelope for observability, and investigate C in a safe environment.
If C is unavailable, document the residual race window rather than claiming an
atomic guarantee. The stale field must be explicitly cleared on every failure
path that returns control to Miaoda.

## Failure isolation

Consistency validation is informational after native candidate processing. Its
exception boundary in `build_consistency_report` prevents a bad 3MF, parser
exception, or serialization failure from rejecting the canonical Preset or
changing the Preview status. Approval/publication code does not read the
consistency field in this repository.

Current gaps are lifecycle cleanliness rather than primary-result blocking:

- candidate/native validation failures do not clear old consistency text;
- consistency field write fallback can preserve old text;
- unsupported slicer failures happen before the consistency helper and do not
  clear old text;
- no explicit log field records the validator/slicer/report outcome, although
  stage/API timing logs exist.

## Miaoda audit

No Miaoda source, schema, or connected frontend session is available in this
repository. Frontend behavior is therefore **NOT_VERIFIED**. Existing backend
evidence says Miaoda can parse `consistency_report.report.comparison_rows`
(`docs/p9-B3-A_integration_design.md`), but there is no proof that the current
UI does so or avoids showing a duplicate legacy `diff` table.

D6 must define one view model that handles the report envelope states and keeps
the following distinctions: missing, unresolved, ambiguous, mismatch,
filename-derived identity, duplicate-equivalent selection, and runtime
uncertainty. It must not display an empty report as a failed validation.

## Performance and operations

Timing is implemented in `profiling.py` and used by Preview stages and Feishu
API calls. The consistency helper's CPU time and JSON serialization are not a
dedicated timing stage; they appear in `other_ms`. There is no live timing
sample in this audit, so the prior conclusion that Feishu/attachment I/O
dominates latency is PARTIALLY_VERIFIED from instrumentation design only.

Enabling five additional slicers adds one 3MF download and one bounded metadata
parse per valid Preview. The Preset download is already performed by native
candidate processing and is reused through `CandidateResult.source_artifact`.
The parsers do not extract meshes or G-code. The main operational risks are
attachment/network latency, report field size, transient write retries, and
duplicate concurrent work—not comparison CPU.

D6 should add explicit consistency timing and validator outcome counters, then
collect median/P95 samples for each slicer before broad rollout.

## Production readiness

| Gate | Status | Blocking work |
|---|---|---|
| Validator readiness | PARTIALLY_VERIFIED | Real/negative unit tests pass; production dispatch absent |
| Report compatibility | PARTIALLY_VERIFIED | Six reports compatible in code; contract test and frontend confirmation needed |
| Lifecycle correctness | NOT_VERIFIED | Clear stale field on all failure paths and changed inputs |
| Stale-write protection | BLOCKED FOR RELEASE | Add recheck and investigate conditional write |
| Failure isolation | PARTIALLY_VERIFIED | Primary result isolated; stale-field behavior needs correction |
| Feishu compatibility | NOT_VERIFIED | Verify deployed field type and byte limit |
| UI compatibility | NOT_VERIFIED | Miaoda implementation/session unavailable |
| Regression safety | VERIFIED for current tests | Full suite retains only known Diff baseline failure |
| Operational readiness | PARTIALLY_VERIFIED | Add consistency timing/outcome metrics and rollout/rollback procedure |

The system must not be declared production-ready for all six slicers until the
critical stale-write, lifecycle, Feishu schema, and frontend gates are closed.

## Verification run

Environment: repository root `/Users/zhengyang/Documents/GitHub/preset-worker`,
`PYTHONPATH=.`, `.venv/bin/pytest`, Python virtual environment already present.
No live Feishu credentials or production records were used; the report audit
used local fixtures and the local Bambu pair under `downloads/3mf-fixture/`.

Commands executed:

```text
PYTHONPATH=. .venv/bin/pytest -q tests/test_p9_b2.py tests/test_three_mf.py
20 passed, 0 failed, 0 skipped

PYTHONPATH=. .venv/bin/pytest -q tests/test_comparison_core.py tests/test_p9_d2.py tests/test_p9_d3.py tests/test_p9_d4.py tests/test_prusa_slicer.py tests/test_creality_print.py tests/test_elegoo_slicer.py tests/test_orca_slicer.py tests/test_snapmaker_orca.py tests/test_p9_b3_a.py
93 passed, 0 failed, 0 skipped

PYTHONPATH=. .venv/bin/pytest -q
198 passed, 1 failed, 1 skipped
```

The full-suite failure remains the known unrelated
`tests/test_diff_contract.py` assertion (`temperature` expected
`IMPORTANT_PARAMETER`, actual `OTHER_PARAMETER`). No new failure was observed.
