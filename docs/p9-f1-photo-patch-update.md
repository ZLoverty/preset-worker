# P9-F1 — Photo Patch Update and Evidence Preservation

## Root cause

Approval used `ProjectionService.project_submission_to_preset()` to rebuild
every configured attachment field from the current Submission. Missing or
empty Submission fields were normalized to `[]`, so an Update containing only
one new photo cleared unrelated photos on the master Preset.

The actual approval path is:

```text
WorkerRuntime
  -> SubmissionPublisher.publish_submission()
  -> _publish_submission_timed()
  -> _project_current_state()
  -> ProjectionService.project_submission_to_preset()
```

The same projection is used by normal approval and idempotent recovery. A
rejected or failed approval does not call the projection.

## Implementation

`merge_photos()` was added to `src/preset_worker/services/projection.py`.
For the configured photo fields it:

- copies the current Preset photo state;
- replaces a field only when the Submission contains a non-empty attachment;
- preserves missing, `None`, and empty attachment values;
- preserves attachment metadata through the existing
  `FeishuAttachmentAdapter`;
- preserves all submitted attachments for a field; no artificial per-field
  attachment-count restriction is applied by the Worker.

Create naturally starts from an empty Preset photo state. Update merges against
the Preset record found by the existing `preset_key` and version rules. Repeat
approval remains idempotent because the same submitted attachment replaces the
same field and no append operation is introduced.

The measured `preset 3mf` projection remains on its existing replacement path;
the patch semantics apply to the ten configured photo fields only.

## PresetVersion and attachment limitations

The current `_version_fields()` schema stores canonical JSON, source
Submission, metadata, and version information, but no photo snapshot fields.
Therefore this change corrects the master Preset projection, but cannot claim
that each historical PresetVersion stores a complete effective photo snapshot.
Adding such storage would require an explicit Feishu schema change and is out
of scope for P9-F1.

Existing attachment objects are deep-copied and their file tokens/metadata are
preserved. No new download, upload, or storage service was introduced.

## Miaoda status

No Miaoda/frontend source or form-validation project was available in the
accessible workspace. No frontend files were modified, and Create required
photo validation, Update optional-photo validation, operation detection, and
payload construction remain to be verified in Miaoda.

## Files modified

- `src/preset_worker/services/projection.py`
- `tests/test_projection.py`
- `tests/test_submission_publication.py`

## Verification

Focused projection, approval, and migration tests:

```text
31 passed
```

Full Worker suite:

```text
217 passed, 1 failed, 1 skipped
```

The only failure remains the pre-existing unrelated baseline:

```text
tests/test_diff_contract.py::DiffContractTests::test_added_removed_modified_and_categories
```

It expects `temperature` to be `IMPORTANT_PARAMETER`, while the current
implementation returns `OTHER_PARAMETER`.

Compile check passed:

```text
.venv/bin/python -m compileall -q src tests/test_projection.py tests/test_submission_publication.py
```
