# P8-C Feishu write latency audit and safe optimization

## Final status

`PARTIALLY_COMPLETE` — the safe one-request write optimization is implemented and regression-tested. Live before/after Feishu latency samples were not available, so measured performance improvement is not claimed.

## Exact write operations

The Preview target is the Submission record identified by `record["record_id"]` in the Submission table. The underlying client sends `PUT /bitable/v1/apps/{app}/tables/{submission_table}/records/{record_id}`.

Before this change, successful Preview used two PUT requests:

1. `write_preview_result` wrote:
   - `operation`: CREATE or UPDATE result.
   - `base_version_id`: linked PresetVersion record ID list, or empty list for CREATE.
   - `canonical_json`: one attachment reference containing the canonical artifact file token.
   - `diff`: serialized UnifiedDiff JSON.
   - `validation`: serialized validation JSON.
2. `write_preview_status` wrote:
   - `status`: `DRAFT`.

Validation failures similarly wrote `validation` first and `status=DRAFT` second. The current implementation combines each pair into one PUT. No field is dropped or renamed.

Request-body and response-body byte counts are now emitted by the existing `preview_api` log for every JSON request. Values are intentionally not included in this report because they vary with diff and validation content. The log records byte counts only, never field contents, tokens, or URLs.

## State transition and dependency audit

Normal path:

`PREVIEW_REQUESTED` → process/download/parse/validate/diff/upload → one PUT with result fields plus `status=DRAFT`.

Failure path:

`PREVIEW_REQUESTED` → validation/infrastructure failure → one PUT with validation plus `status=DRAFT` for handled candidate failures.

No code reads the intermediate result-only state, and the frontend does not need to observe it. The status is changed only after all required artifact work has completed. If artifact processing or upload fails, no success PUT is issued and the record remains `PREVIEW_REQUESTED` for the existing retry behavior. If the PUT fails, the final status is not reported as successful by the worker.

The combined update is idempotent for the same candidate and preserves the existing status transition. Concurrent processing safeguards were not expanded; this change does not add a new race or bypass existing lifecycle checks.

## HTTP connection-management findings

The client uses Python `urllib.request.urlopen` for each request. It does not create a persistent `requests.Session`, explicit connection pool, or shared opener. The bearer token is reused and refreshed only when required, but connection reuse is not explicitly controlled. No proxy configuration is added by this repository.

Because no live trace separates TCP connection setup from server response time, connection establishment cannot be identified as the source of the measured write latency. No HTTP client replacement was introduced. The one-request reduction is smaller, safer, and directly supported by the state audit.

## Changes implemented

- Combined successful Preview result and final status into one `update_submission` call.
- Combined handled validation failure and final status into one `update_submission` call.
- Added request/response byte counts to `preview_api` instrumentation.
- Kept retry behavior, lifecycle semantics, field contracts, artifact content, diff schema, and slicer implementations unchanged.

## API calls before and after

For the P8-C baseline CREATE Preview with no retries:

| Request | Before | After |
|---|---:|---:|
| Uploaded attachment download | 1 | 1 |
| Preset lookup | 1 | 1 |
| Canonical attachment upload | 1 | 1 |
| Submission writes | 2 | 1 |
| Total Preview API requests | 5 | 4 |

UPDATE retains its PresetVersion lookup and base artifact download; only the two Submission writes become one. A retry still adds the existing retry request as before.

## Before/after latency measurements

Available baseline from the demand document:

- Total Preview: 8,380.7 ms
- `write_preview_result`: 2,276.8 ms
- `write_preview_status`: 1,900.5 ms
- Total Feishu writes: 4,177.3 ms
- API requests: 5
- Retries: 0

No live after sample was available. The expected after request count is four for the equivalent CREATE path, but this is an API-count result from code inspection, not a measured latency result. Median/P95 collection should use `preview_timing_summary` and `preview_api` over equivalent CREATE and UPDATE records.

## Regression tests

Verified:

- Successful CREATE Preview.
- Successful UPDATE Preview.
- Canonical artifact reference and diff persistence.
- Final `DRAFT` status.
- Upload failure leaves the record in `PREVIEW_REQUESTED` and writes no success fields.
- Feishu authentication/retry compatibility.
- Runtime dispatch and discovered-record reuse.
- Existing migrated/logical Submission ID behavior remains covered by existing lookup tests.

The targeted suite ran 29 tests successfully after adding the combined-write and upload-failure coverage. Full live integration and concurrency tests were not run because no Feishu integration environment was available.

## Remaining bottlenecks

After removing one write round trip, remaining latency is likely dominated by the remaining Feishu reads and attachment transfer. The existing timing logs now expose write request sizes, response sizes, status, and duration so a live sample can distinguish payload size from network/server latency.

## Files changed

- `src/preset_worker/services/preview.py`
- `src/preset_worker/profiling.py`
- `src/preset_worker/services/enrichment.py`
- `tests/test_submission_enrichment.py`
