# P9-B3-A — Worker Integration and Consistency Report Persistence

## 1. Objective

Integrate the existing P9-B2 Bambu Studio Preset–3MF consistency validator into the current Worker Preview workflow.

The Worker must automatically generate and persist a consistency report when a Bambu Studio submission has both a native Preset JSON artifact and a 3MF project artifact.

This phase covers backend integration only.

**Do not modify Miaoda frontend code in P9-B3-A.**

The consistency report is informational. It must never block submission, review, approval, or publication.

### Core Principles

1. One validator, one persisted report.
2. Reuse the existing Preview lifecycle.
3. Never duplicate native slicer comparison logic.
4. Never expose stale reports as current.
5. Never fail an otherwise valid Preview because consistency validation fails.
6. Preserve the existing Feishu schema and Worker architecture wherever possible.
7. Avoid unnecessary Feishu API requests.

---

## 2. Existing System

Inspect the actual repository before implementation.

The system includes:

- Feishu Bitable as the source of truth.
- A Python Worker.
- `Submission`, `PresetVersion`, and `Preset` tables.
- An existing `PREVIEW_REQUESTED` workflow.
- Native slicer artifact validation.
- Canonicalization.
- UnifiedDiff generation.
- A 3MF project attachment.
- Existing Preview result persistence.
- Existing retry, idempotency, and concurrency handling.

The P9-B2 validator exposes:

```python
validate_bambu_consistency(...)
```

It supports eight parameters:

1. `filament_flow_ratio`
2. `filament_max_volumetric_speed`
3. `nozzle_temperature`
4. `nozzle_temperature_initial_layer`
5. `fan_min_speed`
6. `fan_max_speed`
7. `fan_cooling_layer_time`
8. `slow_down_layer_time`

The validator produces:

- Parameter-level results.
- Element-level results.
- Flat `comparison_rows`.
- Artifact SHA-256 fingerprints.
- Raw and normalized values.
- Source paths and provenance.
- Explicit missing, ambiguous, and unresolved statuses.
- A versioned JSON-serializable report.

The current report schema is identified as:

`p9b2.consistency.v1`

Reuse the existing implementation and schema.

Do not introduce another comparison engine.

---

## 3. Scope

### In Scope

- Worker Preview integration.
- Bambu Studio eligibility detection.
- Reuse of existing downloaded artifacts.
- Consistency validator invocation.
- Exception isolation.
- Feishu report persistence.
- Report status and metadata.
- Report freshness and invalidation.
- Retry and concurrency behavior.
- Backend API/data contract for future Miaoda integration.
- Automated backend tests.
- Documentation and deployment instructions.

### Out of Scope

- Miaoda engineer UI.
- Miaoda reviewer UI.
- Frontend component development.
- Changes to approval eligibility.
- Changes to publication logic.
- New Submission lifecycle states.
- Full Bambu Studio inheritance resolution.
- Runtime G-code validation.
- Other slicers.
- Historical report backfills.

---

## 4. Phase A1 — Inspect the Existing Workflow

Before modifying production code, trace the current implementation.

Identify:

1. The entry point handling `PREVIEW_REQUESTED`.
2. The function responsible for Preview generation.
3. The current artifact download and caching mechanism.
4. How the native Preset artifact is represented.
5. How the uploaded 3MF artifact is represented.
6. The existing canonicalization path.
7. The existing UnifiedDiff generation path.
8. How Preview results are written to Feishu.
9. How Preview errors are handled.
10. How concurrent or repeated Preview requests are handled.
11. How existing Feishu fields are configured or mapped.
12. Whether report attachments are already supported.

Document the actual call chain before implementation.

Do not assume that the implementation matches earlier design documents.

### Required Output

Create:

`docs/p9-B3-A_integration_design.md`

Include the actual Worker entry points, data flow, and proposed minimal integration point.

---

## 5. Phase A2 — Validator Invocation

### 5.1 Eligibility

Run consistency validation only when all conditions hold:

- Submission slicer is `BambuStudio`.
- A readable native Preset JSON artifact is available.
- A readable 3MF project artifact is available.
- The Worker is processing an eligible Preview request.

Do not invoke the validator for:

- OrcaSlicer.
- SnapmakerOrcaSlicer.
- CrealityPrint.
- ElegooSlicer.
- PrusaSlicer.
- Other unsupported slicers.

Use the existing slicer identification mechanism.

Do not rely on arbitrary filename matching when authoritative slicer metadata is available.

### 5.2 Missing Artifacts

If the 3MF artifact is absent:

- Skip consistency validation.
- Record an informational `NOT_AVAILABLE` status.
- Preserve the existing Preview result.
- Do not transition the Submission to FAILED.

If the native Preset artifact is absent:

- Preserve the existing native Preview validation behavior.
- Do not introduce a separate consistency-related failure.

### 5.3 Artifact Reuse

Reuse artifacts already downloaded during Preview whenever possible.

Do not download the same attachment twice within one Preview execution.

If the current Preview implementation downloads only the native preset, extend it to obtain the 3MF through the existing attachment access layer.

Avoid additional Feishu metadata calls when the required metadata is already available.

### 5.4 Validator Contract

Inspect the actual signature of:

```python
validate_bambu_consistency(...)
```

Adapt the Worker integration to the existing public API.

Do not change the validator's comparison semantics to accommodate Worker orchestration.

If an adapter is necessary, keep it thin and focused on artifact representation.

The existing P9-B2 `comparison_rows` must be preserved without frontend-oriented transformations.

---

## 6. Phase A3 — Error Isolation

Consistency validation is an optional informational operation.

It must not determine the success or failure of the existing Preview workflow.

Handle these situations separately:

| Condition | Consistency Status | Existing Preview |
|---|---|---|
| Unsupported slicer | `NOT_APPLICABLE` | Unchanged |
| Missing 3MF | `NOT_AVAILABLE` | Unchanged |
| Successful comparison | `READY` | Unchanged |
| Comparison contains mismatches | `READY` | Unchanged |
| Missing inherited parameters | `READY` | Unchanged |
| Ambiguous comparison | `READY` | Unchanged |
| Invalid 3MF | `ERROR` | Unchanged |
| Validator exception | `ERROR` | Unchanged |

The statuses above describe report availability, not individual parameter comparison results.

Do not confuse `READY` with all parameters matching.

### Error Handling Requirements

- Catch expected validator and artifact-processing errors at the consistency integration boundary.
- Preserve the original Preview outcome.
- Record bounded, sanitized error information.
- Avoid logging raw attachment contents or credentials.
- Do not swallow errors silently.
- Do not create a new Submission failure reason for ordinary consistency mismatches.

If the native Preview itself fails for an existing reason, preserve its current behavior.

---

## 7. Phase A4 — Feishu Persistence Design

Choose the smallest viable schema extension after inspecting existing report-storage patterns.

### Preferred Fields

Use existing equivalent fields when available.

Otherwise propose:

| Field | Type | Purpose |
|---|---|---|
| `consistency_status` | Single select or text | READY / NOT_AVAILABLE / NOT_APPLICABLE / ERROR / STALE |
| `consistency_report` | Attachment | Complete JSON report |
| `consistency_generated_at` | Date/time | Report generation timestamp |

An optional compact summary field may be added only if it materially reduces frontend reads.

Do not create redundant fields without justification.

### 7.1 Complete Report Storage

Persist the complete versioned JSON report.

The report must retain:

- `p9b2.consistency.v1` schema identifier.
- Preset artifact fingerprint.
- Canonical preset fingerprint, if present.
- 3MF artifact fingerprint.
- Filament matching information.
- Eight parameter-level checks.
- Element-level comparison results.
- Flat `comparison_rows`.
- Summary counts.
- Warnings.
- Errors.
- Source provenance.

Do not truncate the report.

Do not store only the summary.

Do not serialize Python