# Actual Architecture

## End-to-end path

```text
Feishu record
  -> SubmissionEnrichment/PreviewService
  -> slicer id lookup + registry
  -> Artifact download
  -> SlicerProcessor.parse/validate/normalize/policy/serialize
  -> canonical_json upload + diff + validation fields
  -> optional consistency validator + preset 3mf download
  -> Feishu status/report update
  -> SubmissionPublisher -> PresetVersion/Preset projection
```

`services/enrichment.py:577-656` is the shared candidate path. It obtains slicer, builds `ProcessingContext`, resolves the optional base version, calls `process_artifact`, then computes processor diff. `services/preview.py:89-120` uses the same candidate processing but only for `PREVIEW_REQUESTED`. `runtime.py:107-125` dispatches preview, enrichment and publication as separate lifecycle operations; it does not merge them.

### Boundaries

| Stage | Entry / module | Input -> output | Failure behavior | Required? |
|---|---|---|---|---|
| Identify | `SubmissionEnrichment.process_candidate:577` | Feishu fields -> slicer id/processor | unsupported id becomes `ValidationFailure` | mandatory |
| Native load | `enrichment.py` attachment helpers | Feishu attachment -> `Artifact` | missing attachment/HTTP failure | mandatory |
| Parse/validate | processor contract `contracts.py:64-77` | bytes -> native object/`ValidationResult` | invalid user artifact | mandatory |
| Normalize/policy | `process_artifact:80-95` or processor `process` | native -> canonical object | invalid canonical result | mandatory |
| Diff | processor `.diff` | base/canonical artifacts -> `UnifiedDiff` | parse errors propagate | CREATE/UPDATE mandatory |
| 3MF consistency | `services/consistency_preview.py:79-104` | native artifact + 3MF -> JSON envelope | optional; failures become ERROR/empty | optional |
| Publication | `SubmissionPublisher.publish_submission:215-324` | approved submission -> PresetVersion/Preset updates | conflicts/failures propagate | only publication |

Consistency is optional informational work: `preview.py:116-120` and `enrichment.py:724-755` isolate it from native candidate success. Publication recomputes consistency from the current project attachment where applicable; it does not trust a stale preview report.

## Component boundaries

`Artifact` is opaque and carries bytes, filename and media type (`slicers/contracts.py:29-36`). Feishu and workflow code do not parse slicer payloads. However, consistency is not part of `SlicerProcessor`; it is a second explicit map in `consistency_preview.py:30-37`, so a processor can be registered while consistency registration is incomplete.

`PresetVersion` stores the uploaded canonical attachment and diff/validation fields in `publication.py:179-213`; `ProjectionService` copies current process-photo and `preset 3mf` attachments (`projection.py:19-39`). No slicer-specific publication branch was found.
