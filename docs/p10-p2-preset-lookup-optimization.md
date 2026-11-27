# P10-P2 — Preset Lookup Elimination Audit & Optimization

## Executive summary

`preset_lookup` is retained for Preview. It is not a Base PresetVersion lookup: the exact historical Base Version is already resolved from `Submission.base_version_id` through `get_record`. The Preset query remains the authoritative CREATE/UPDATE classifier and duplicate Preset identity check.

No safe query-elimination optimization was found without changing the existing operation-detection contract. The narrowly scoped implementation adds an explicit guard for the inconsistent state where a Submission contains a base reference but no matching Preset; it must not silently become CREATE.

Conclusions are marked `CONFIRMED`, `INFERRED`, or `NOT_VERIFIED`.

## Baseline and entry point

`CONFIRMED` — Branch: `dev`; baseline revision: `e2e65f811533f49447693d2563a051dfd1adbfaa`. The working tree already contained the prior Base Version optimization and its regression-test changes; those changes were preserved.

`CONFIRMED` — Runtime Preview enters `WorkerRuntime._dispatch`, reuses the discovered Submission record, and calls `PreviewService.preview_submission`. Candidate processing then goes through `SubmissionEnrichment.process_candidate`.

`CONFIRMED` — `preset_lookup` is the stage around `SubmissionEnrichment._find_preset` in `enrichment.py`. The client method is `FeishuClient.find_preset_by_key`.

## Exact lookup chain

For both CREATE and UPDATE Preview:

1. `SubmissionEnrichment.process_candidate` reads the authoritative formula-backed `Submission.preset_key`.
2. `_find_preset` calls `FeishuClient.find_preset_by_key`.
3. The client queries the Preset table with the exact server-side filter:
   `CurrentValue.[preset_key]="<escaped key>"`.
4. `list_records` requests up to 100 records per page, follows `has_more` and `page_token`, and returns all matching pages.
5. `_find_preset` performs an exact client-side equality check as a defensive guard and rejects more than one match.

`CONFIRMED` — The query is server-filtered, but pagination remains possible. It requests the normal record payload; there is no field projection or cache. The current production implementation does not reuse a Preset record from another request.

`CONFIRMED` — The five-call historical trace was a combination of logical reads and pagination pages: Submission candidate discovery, filtered Preset lookup pages, and unfiltered historical PresetVersion pages. The latter pages are now gone from UPDATE Preview. Exact page count is data-dependent because Feishu returns `has_more` and `page_token` at runtime.

## Preset consumers

| Consumed value | Purpose | Alternative source | Can lookup be avoided? |
|---|---|---|---|
| Match existence | CREATE versus UPDATE classification | `base_version_id` is not a trusted user operation selector | No, without changing the contract |
| Match cardinality | Duplicate Preset identity detection | None equivalent in Submission | No |
| Preset record itself during Preview | Truthiness only after Base Version optimization | None needed for Native Diff | The record payload is not needed, but the existence query is |
| `current_version` / `current_version_id` | No longer consumed by Preview Base Version resolution | Exact Submission base reference | Yes for Preview; retained for publication |
| Preset `record_id` | Not consumed by Preview candidate processing | Not needed until publication | Yes for Preview |

`CONFIRMED` — The current Preset record does not provide the Native Diff baseline. `_base_artifact` uses `Submission.base_version_id` and direct PresetVersion retrieval.

`CONFIRMED` — Approval/publication still independently resolves Preset by exact `preset_key`, checks UPDATE base-versus-current version concurrency, and updates the Preset current-version relation. Those safeguards were not changed.

## Submission and version invariants

`CONFIRMED` — `Submission.base_version_id` is represented as a linked-record value such as `[{"record_ids": ["version-record-7"]}]`. A single linked record is retrieved with `get_record`; a plain business ID uses an exact server-side `version_id` filter.

`CONFIRMED` — UPDATE Preview uses the historical record referenced by the Submission, even when the Preset current version has advanced. It does not scan by `preset_key`, printer identity, PI code, or version ordering.

`CONFIRMED` — A missing or malformed base reference is an explicit failure. A base reference with no matching Preset is also rejected rather than silently reclassified as CREATE.

`INFERRED` — `preset_key` is authoritative as an identity formula because the existing contract and client implementation treat it as the exact business identity. The user-supplied `operation` field is not used to classify Preview.

## Optimization decision

### Chosen change

Retain the exact filtered Preset lookup and add the inconsistent-state guard described above. The prior direct Base Version retrieval remains intact. This is the smallest safe change because it removes no required identity check and changes no public report schema.

### Rejected alternatives

- Eliminate the lookup for UPDATE: rejected because Preview must not trust a client-supplied operation or infer UPDATE solely from a mutable/reference field; it would also lose duplicate and missing-Preset detection.
- Use `base_version_id` as the Preset identity: rejected because it identifies a PresetVersion, not the current Preset record.
- Read the Preset by a record ID: not available on the Submission in the current schema.
- Add a cache: rejected because cross-request freshness and invalidation policy are not defined.
- Reintroduce a broad fallback scan: explicitly prohibited and unnecessary.

## Observability and performance

`CONFIRMED` — `preset_lookup`, `base_version_lookup`, attachment download, candidate processing, diff, and write stages remain separately instrumented. Feishu API events classify filtered/list reads as `list_records` and direct record reads as `get_record`.

Provided same-scenario baseline:

| Metric | Before prior Base Version optimization | Current observed scenario | After this audit |
|---|---:|---:|---:|
| Total Preview latency | 28,914.8 ms | 15,407.5 ms | Not measured live |
| Preset lookup latency | 5,135.5 ms | 7,685.6 ms | Retained; not measured live |
| Base Version lookup | ~18,530 ms pagination | 3,624.7 ms direct read | Direct read retained |
| Feishu API calls | 11 | 7 | No additional call |
| Feishu read latency | Not supplied | 11,310.3 ms | Not measured live |
| Attachment download | Not supplied | 2,364.9 ms | Unchanged |
| Feishu write latency | Not supplied | 2,176.0 ms | Unchanged |
| Retries | 0 | 0 | 0 in tests |

`NOT_VERIFIED` — No live Feishu credentials or repeatable production trace were available for a new wall-clock measurement. The deterministic API behavior is covered by tests: UPDATE Preview performs one exact Preset query plus one direct Base Version read and zero PresetVersion pagination calls.

## Tests

Focused tests cover valid linked retrieval, stale historical snapshots, missing/malformed/nonexistent references, missing current Preset, and absence of PresetVersion pagination. Existing CREATE, slicer, Diff, validation, approval, and publication tests remain in place.

Results:

- Focused submission enrichment suite: 29 passed.
- Full unittest suite: 282 passed, 2 expected skips.
- `git diff --check`: passed.
- Python compile check: passed.

## Files changed in this P10-P2 pass

- `src/preset_worker/services/enrichment.py`
- `tests/test_submission_enrichment.py`
- `docs/p10-p2-preset-lookup-optimization.md`

The other modified test files in the working tree belong to the preceding Base Version optimization and were preserved.

## Remaining bottlenecks and follow-up

`preset_lookup` remains the largest measured Preview read stage, but its purpose is still required by the current contract. The next safe opportunity would require an authoritative Preset record reference on Submission or a schema-approved immutable identity/operation contract. Any such change should be evaluated separately from approval-time concurrency checks.
