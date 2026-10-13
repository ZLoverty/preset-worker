# P8-B Preview record-access optimization

## Final status

Implemented the safe record-access optimizations. The Preview workflow now reuses the complete Submission record returned by the polling query, and Preset lookup uses an exact server-side filter when the production Feishu client is available. Logical Submission identifiers are not treated as native Bitable record IDs.

## Root cause of repeated Submission scans

`WorkerRuntime._discover` already calls `list_preview_candidates`, which returns a complete Bitable record including `record_id` and all fields required by `PreviewService`. The old `_dispatch` passed only the logical `submission_id` to `PreviewService.preview_submission`. Preview then called `FeishuClient.get_submission`, whose implementation scans `list_records(submission_table_id)` and compares both native `record_id` and logical `fields.submission_id`.

The nine requests in the baseline are therefore pagination requests from that second full-table scan, not nine independent Submission lookups. The exact number depends on table size and page size. `MIGRATED-...` is a logical Submission identifier; it is not interchangeable with the native `record_id`.

## Changes implemented

- `WorkerRuntime` passes the discovered record to the default `PreviewService`.
- `PreviewService.preview_submission` accepts an optional discovered record and skips the redundant `get_submission` scan when it is supplied.
- Standalone callers that do not provide a record retain the old logical-ID lookup behavior.
- `FeishuClient.get_record` was added for callers that explicitly possess a native record ID. It is not used for logical IDs.
- `FeishuClient.find_preset_by_key` uses an exact server-side `CurrentValue.[preset_key]` filter.
- `_find_preset` retains exact client-side matching as a guard and falls back to the previous full list for test doubles or alternate clients.
- Existing P8-A timing logs remain enabled.

No persistent cache, concurrency, retry-policy change, status change, processor change, diff change, or canonical artifact change was introduced.

## API calls before and after

For a Preview dispatched by the polling worker:

| Area | Before | After |
|---|---:|---:|
| Discovered Submission record | polling query | polling query, reused |
| Preview `get_submission` scan | 1 paginated scan, baseline 9 requests | 0 |
| Preset lookup | full table scan | 1 filtered list request, normally |
| PresetVersion lookup for UPDATE | 1 list request | 1 list request |

The polling query itself remains unchanged. Pagination can still produce multiple requests when the candidate query returns multiple pages. Direct native-record retrieval is available through `get_record`, but is intentionally not used for a logical `MIGRATED-...` identifier.

## Timing before and after

The supplied baseline was:

- Total Preview: 29,797 ms
- Feishu record reads: 23,075 ms
- Feishu record writes: 4,333 ms
- Processor: 0.1 ms
- Diff: 0.1 ms
- API calls: 15
- Retries: 0

No live Feishu credentials or equivalent production records were available for an after measurement, so no fabricated improvement is reported. The existing `preview_stage`, `preview_api`, and `preview_timing_summary` logs now make these comparisons directly measurable. Collect multiple identical CREATE and UPDATE samples and report median/P95 for `get_submission` (expected zero for worker-dispatched Preview), `preset_lookup`, writes, and total time.

## CREATE/UPDATE and migrated-record compatibility

- CREATE still results when the exact filtered Preset query returns no matching `preset_key`.
- UPDATE still results when exactly one matching Preset is returned; PresetVersion selection and base artifact download are unchanged.
- Duplicate exact Preset matches still raise `CandidateFailure`.
- Standalone Preview calls with logical IDs still use the old scan-and-compare behavior.
- Migrated logical IDs remain compared against `fields.submission_id`; native `record_id` is only used when supplied as a discovered record or explicitly passed to `get_record`.

## Write review

The two Preview writes remain separate. The first persists the complete result and the second returns the record to `DRAFT`; combining them was not necessary to address the dominant read bottleneck and could change failure recovery or frontend-observable intermediate state.

## Tests

- `python -m compileall -q src` passed.
- Runtime, Preview, and Feishu-auth regression tests: 28 passed.
- No live performance samples were run.

## Remaining bottlenecks

After the redundant Submission scan is removed, remaining network cost is expected in the polling query, Preset/PresetVersion reads, attachment download/upload, and the two writes. The P8-A summary should be used to determine which dominates for CREATE versus UPDATE and for migrated records.
