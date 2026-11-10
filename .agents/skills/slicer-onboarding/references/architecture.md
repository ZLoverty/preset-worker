# Current architecture reference

Verify this reference against the current repository before each onboarding.

## Boundaries

- Package: `src/preset_worker/`; tests: `tests/`; fixtures: `tests/fixtures/slicers/`.
- Native boundary: `slicers/contracts.py` defines `Artifact`, `ProcessingContext`, `ValidationResult`, `ProcessedArtifact`, `SlicerProcessor`, and `SlicerProcessorRegistry`.
- Composition: `slicers/registry.py:default_processor_registry()` registers processors. Aliases are also handled in `contracts.py:SlicerProcessorRegistry` and `registry.py:canonical_slicer_id`; check both.
- Native workflow: `services/enrichment.py:SubmissionEnrichment.process_candidate()` selects a processor, creates context, processes the artifact, computes diff, and returns the candidate. `slicers/contracts.py:process_artifact()` expresses the parse -> validate -> normalize -> policy -> canonical validate -> serialize stages.
- Preview: `services/preview.py:PreviewService.preview_submission()` processes `PREVIEW_REQUESTED`, then optionally builds consistency.
- Runtime: `runtime.py:WorkerRuntime` dispatches Preview, enrichment, and publication separately.
- Publication: `services/publication.py:SubmissionPublisher` creates/repairs `PresetVersion`, updates `Preset`, projects attachments, and marks the Submission published.

## 3MF and consistency

- Safe archive access: `three_mf/safe_zip.py`.
- Bambu/Orca-family project parsing: `three_mf/bambu_parser.py`, principally `Metadata/project_settings.config`, with optional model, slice, sequence, plate, and embedded preset entries.
- Prusa project parsing: `three_mf/prusa_parser.py`, principally `Metadata/Slic3r_PE.config`.
- Shared comparison and slot selection: `three_mf/comparison_core.py`.
- Native JSON consistency orchestration: `three_mf/native_consistency.py`; Bambu-specific path also exists in `three_mf/consistency.py`.
- Prusa consistency: `three_mf/prusa_consistency.py`.
- Actual Preview/Submit dispatch: `services/consistency_preview.py:CONSISTENCY_VALIDATORS`.

Native Preset support and 3MF consistency are separate capabilities. A processor in the registry does not prove a validator is registered or reachable. Inheritance is currently generally preserved, not resolved: do not claim effective inherited values without new evidence and approved implementation.

## Onboarding inspection

Inspect both registry locations, all slicer-name comparisons, processor `important_parameter_paths`, fixed consistency parameter sets, fixture directories, and lifecycle tests. Record whether the target needs a new parser, only a facade, a 3MF adapter, a validator, or no code change.
