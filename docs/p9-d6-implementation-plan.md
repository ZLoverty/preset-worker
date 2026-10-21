# P9-D6 Cross-Slicer Preview Enablement Plan

P9-D6 must implement production integration only after the D5 critical gates
are addressed. This plan deliberately does not claim an atomic stale-write
guarantee until the Feishu capability is verified.

## D6.1 — Dispatch and report-contract stabilization

### Objective

Connect all six independently tested validators to the existing consistency
boundary without changing the native Preset processor registry or report
schema.

### Code areas

- `src/preset_worker/services/consistency_preview.py`
- `src/preset_worker/three_mf/consistency.py`
- new small dispatch mapping module if needed
- `tests/test_p9_d5_contract.py` (new)

### Required changes

1. Map exact canonical slicer IDs to validator entry points.
2. Pass the existing `CandidateResult.source_artifact` and downloaded 3MF
   artifact to the selected validator.
3. Preserve `p9b2.consistency.v1`, outer envelope, and current error
   sanitization.
4. Keep unsupported IDs and missing project attachments explicit and clear.
5. Add a common contract assertion for required keys, parameter order, status
   values, source identity, and serializability.

### Tests and acceptance

- Six real fixture validators execute through the dispatch mapping.
- Bambu output remains semantically compatible.
- Orca `[1,4]`, Snapmaker slot 1, and Prusa filename identity remain visible.
- No new slicer-specific frontend branch is required by the report.

### Dependencies and rollback

Depends on D5 contract review. Roll back by restoring the Bambu-only mapping;
native Preset processing remains independent.

## D6.2 — Lifecycle and stale-result safeguards

### Objective

Ensure that an old consistency result cannot remain visible after a failed
Preview and reduce the stale-input write window.

### Code areas

- `src/preset_worker/services/preview.py`
- `src/preset_worker/services/consistency_preview.py`
- `src/preset_worker/services/enrichment.py`
- Feishu client capability wrapper if conditional update is verified
- lifecycle/concurrency tests

### Required changes

1. Include `consistency_report: ""` in every Preview candidate failure write.
2. On consistency field size/write fallback, explicitly clear or replace the
   field rather than omitting it and preserving stale text.
3. Re-read the authoritative Submission immediately before writeback.
4. Compare current status, Preset attachment token/name, 3MF attachment
   token/name, and slicer against the input record.
5. If inputs changed, skip the stale write and leave the record eligible for a
   fresh request according to the chosen state policy.
6. Add an input fingerprint/generation value to the envelope for observability,
   not as a substitute for conditional write.
7. Verify whether Feishu supports an updated-time/revision conditional update;
   use it if available and test it in a safe environment.

### Tests and acceptance

- Invalid Preset, unsupported slicer, and native validation failure clear the
  old consistency report.
- Removed 3MF clears the old report.
- Changed Preset/3MF/slicer cannot result in a report whose artifact hashes
  describe the previous inputs.
- Two-worker simulation documents behavior; conditional write passes if
  supported.

### Dependencies and rollback

Depends on D6.1 and Feishu schema/API verification. Rollback can disable the
new dispatch while retaining stale-clear changes, which are independently safe.

## D6.3 — Preview integration and Feishu writeback

### Objective

Enable the five additional validators in the actual Preview path while keeping
consistency informational and preserving the one-result write.

### Code areas

- `services/consistency_preview.py`
- `services/preview.py`
- `tests/test_p9_d6_preview.py`

### Required changes

1. Keep native candidate processing first and unchanged.
2. Download one 3MF attachment only when present.
3. Run the validator in an isolated boundary for every canonical slicer.
4. Write READY/ERROR/empty consistency text in the same Preview update where
   possible.
5. Preserve primary Preview result on consistency exceptions.
6. Verify the actual deployed multiline field type and byte limit.
7. Add consistency timing and validator outcome logs without logging report
   contents or tokens.

### Tests and acceptance

- All lifecycle rows D5-11 through D5-23 that are backend-owned pass.
- Feishu write payload remains within verified limits.
- Approval/publication behavior and canonical artifacts are unchanged.

### Dependencies and rollback

Depends on D6.1 and D6.2. Rollout behind a configuration flag or controlled
allowlist if available; otherwise deploy with a reversible Bambu-only mapping.

## D6.4 — Miaoda unified comparison view

### Objective

Render one cross-slicer comparison model without duplicating the legacy Diff
table or flattening uncertainty into MATCH/MISMATCH.

### Code areas

- Actual Miaoda frontend repository/session (not available in this Worker repo)
- frontend view-model/contract tests
- possibly no Worker code beyond documented envelope

### Required changes

1. Parse the `consistency_report` envelope and distinguish empty, READY, and
   ERROR.
2. With no 3MF, show native Preset comparison only.
3. With 3MF, render rows from `report.comparison_rows` with Preset, project,
   status, and provenance columns.
4. Display identity evidence, matching slot IDs, filename strategy, and runtime
   uncertainty.
5. Keep missing, unresolved, ambiguous, not-comparable, and mismatch distinct.
6. Confirm the legacy `diff` table is not rendered as a duplicate comparison
   table.

### Tests and acceptance

- Real reports from all six slicers render in one view model.
- Prusa unresolved mappings and Orca duplicate-equivalent selection are
  visible and not presented as successful runtime equivalence.
- Stale/empty/error states have explicit UI tests.

### Dependencies and rollback

Blocked until the actual Miaoda consumer is identified. Roll back by keeping
the existing Preset-only view and hiding the optional consistency card.

## D6.5 — End-to-end verification and controlled rollout

### Objective

Prove the complete Worker/Feishu/Miaoda behavior in a safe environment and
release incrementally.

### Code and environment areas

- full Worker test suite
- recorded/fake Feishu integration client
- non-production Feishu table/app
- actual Miaoda preview environment
- deployment configuration and rollback runbook

### Required changes and tests

1. Run the complete D5 matrix, including changed inputs and two workers.
2. Measure preview median/P95 by slicer and record report sizes.
3. Verify Feishu field write/read round trips for the largest report.
4. Verify retries, write failures, and stale-input rejection.
5. Start with Bambu plus one adapter, then expand by allowlist only after
   observed stability.
6. Preserve a quick rollback to Bambu-only dispatch.

### Acceptance

All critical D5 gates are closed, the known unrelated Diff baseline failure is
unchanged or separately resolved, and the rollout owner accepts the residual
race risk if Feishu lacks conditional writes.

## Approval decisions required before D6

1. Approve the explicit validator mapping keyed by canonical slicer IDs.
2. Confirm the deployed Feishu `consistency_report` field type and byte limit.
3. Confirm whether conditional update/revision support is available.
4. Approve the behavior when a pre-write input recheck detects a changed
   Submission.
5. Provide access to the actual Miaoda frontend or its view-model contract.
6. Approve staged rollout/allowlist and rollback ownership.
