# P8-A Worker Preview profiling

## Status

Instrumentation is implemented. No production latency samples are included because Feishu credentials and representative integration data were not used in this workspace.

## Actual Preview path

`WorkerRuntime._discover("PREVIEW_REQUESTED")` finds records, then `_dispatch` invokes `PreviewService.preview_submission`. The Preview path is:

1. `FeishuClient.get_submission` scans Submission records.
2. Submission fields are checked and the uploaded artifact is downloaded.
3. The registered slicer processor parses, validates, and canonicalizes the artifact.
4. Preset records are searched by `preset_key`. For UPDATE, PresetVersion records are searched and the base canonical artifact is downloaded.
5. The processor generates a CREATE or UPDATE diff.
6. The canonical artifact is compared with the existing canonical attachment, then uploaded when needed.
7. The complete preview result is written to Submission, followed by a status write to `DRAFT`.

The path is serial. There are no sleeps or worker polling changes inside a Preview attempt. No retry/backoff sleep is currently implemented; the existing invalid-token retry remains unchanged.

## START and COMPLETED locations

The existing worker boundary logs are in `src/preset_worker/runtime.py`, in `WorkerRuntime._dispatch`:

- `processing started submission=... action=preview`
- `processing completed submission=... action=preview`

The detailed attempt logs are emitted by `PreviewService.preview_submission` and include `submission_id` plus a generated `attempt_id`.

## Instrumentation added

`src/preset_worker/profiling.py` provides a per-attempt timing context using `time.perf_counter()`.

- `preview_stage`: submission read, uploaded/base/existing attachment download, processor, Preset lookup, diff, canonical upload, and Submission writes.
- `preview_api`: Feishu Bitable requests and media download/upload requests. It records operation, method, endpoint category, duration, HTTP/API status, retry count, and success.
- `preview_timing_summary`: total time, category totals, retry/backoff time, explicit unaccounted `other_ms`, and API call/retry counts.

Endpoint categories intentionally omit full URLs and all credentials, tokens, signed URLs, and artifact contents.

Summary category totals are based on non-overlapping workflow stages. Nested API timing is visible in `preview_api` records and is not added again to the summary.

## Expected API call counts

Counts depend on CREATE/UPDATE and whether the existing canonical attachment matches:

- CREATE: one Submission list/read, one uploaded attachment download, one Preset list, one canonical upload, and two Submission updates.
- UPDATE: the CREATE calls plus one PresetVersion list and one base attachment download.
- If an existing canonical attachment is present, one additional canonical attachment download occurs; a matching artifact avoids the upload.
- Pagination can add additional Bitable list requests.
- An invalid access token can add the existing authentication refresh and one repeated request. No retry policy was changed.

## Latency and bottlenecks

No measurements were fabricated. After running representative previews, rank bottlenecks from `preview_timing_summary` and the individual `preview_api` lines. The likely candidates to validate are sequential Feishu list scans, attachment transfer, and processor/diff CPU time; the logs are intended to confirm or reject these hypotheses.

## Recommended measurement procedure

Run several real samples for CREATE/UPDATE JSON, CREATE/UPDATE INI, and small/large artifacts. Collect all `preview_stage`, `preview_api`, and `preview_timing_summary` lines for each `attempt_id`. Compare medians and high percentiles separately for network and local stages. Record retry occurrences instead of folding them into normal request latency.

## Files changed

- `src/preset_worker/profiling.py`
- `src/preset_worker/services/preview.py`
- `src/preset_worker/services/enrichment.py`

## Tests performed

- `python -m compileall -q src` passed.
- The repository test suite could not be run because `pytest` is not installed in the available environment.

## Remaining uncertainties

- No live Feishu timing samples are available.
- Error-path API calls are not represented in the normal successful-request timing record when the transport fails before a response is available.
- The current retry path has no backoff sleep, so `retry_backoff_ms` remains zero unless a future retry implementation records a delay.
