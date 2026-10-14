# Agent Instruction: Backfill Slicer Version in Preset Submissions

## 1. Objective

Implement a standalone Python script that backfills the `slicer_version` field in the existing Feishu/Lark Bitable preset management database.

For each eligible record:

1. Read `slicer` and `created_at`.
2. Identify the corresponding slicer software's official Git repository and its version tags.
3. Find the latest eligible version tag published on or before the record's creation date.
4. Write the resolved version into `slicer_version`.

The script must be safe to run repeatedly, support dry-run mode, and report records that cannot be resolved.

This is a metadata maintenance utility, not a new preset submission or publication workflow.

## 2. First inspect the existing project

Before implementing anything, inspect the current repository and identify:

- The existing Feishu/Lark Bitable API client and authentication mechanism.
- The Bitable App Token, Table ID, and relevant field-name conventions.
- The table containing the preset submission records. The expected table is `Submission`, but verify the actual configuration.
- Existing GitHub API clients, repository configuration, HTTP utilities, logging, and test conventions.
- The actual values stored in `slicer`, the field type and format of `created_at`, and the field type of `slicer_version`.
- The existing slicer adapters and supported slicer names.

Reuse the project's existing infrastructure wherever possible. Do not introduce a second authentication mechanism, duplicate API client, or unnecessary dependencies.

Do not modify the existing submission, validation, review, or publication workflows.

## 3. Business rules

### 3.1 Record selection

For each record, read:

- `record_id`: Bitable record identifier.
- `slicer`: slicer software identifier or display name.
- `created_at`: record creation timestamp.
- `slicer_version`: existing version value.

By default, process only records whose `slicer_version` is empty or null.

Provide an optional `--overwrite` flag to update existing values. Without this flag, never overwrite a nonempty version.

Do not infer `created_at` from another timestamp unless the existing schema explicitly defines that fallback.

### 3.2 Slicer-to-repository mapping

Maintain an explicit, configurable mapping between the Bitable `slicer` values and their upstream repositories.

The currently relevant slicers include:

- Bambu Studio
- OrcaSlicer
- OrcaSlicer (Snapmaker)
- Creality Print
- ElegooSlicer
- PrusaSlicer

Verify each official upstream repository using the existing project configuration or authoritative upstream sources. Do not assume that similarly named slicers share a repository.

The mapping should be centralized in configuration rather than scattered throughout the implementation.

Normalize slicer names only through explicit aliases. Do not use fuzzy matching to silently map an unknown slicer to a different product.

If a slicer is unknown or its repository cannot be verified, skip the record and report the reason.

### 3.3 Historical version resolution

For a record with creation timestamp `created_at`, resolve the latest eligible version tag available as of that timestamp.

Formally, let \(T_s\) be the eligible version tags for slicer \(s\). Select:

\[
t^*=\underset{t\in T_s,\;d(t)\leq d_r}{\arg\max}\;d(t)
\]

where:

- \(d_r\) is the record creation timestamp.
- \(d(t)\) is the best available authoritative publication timestamp for tag \(t\).

Use the following rules:

1. Prefer the official release publication timestamp (`published_at`) when a tag has a corresponding GitHub Release.
2. For tags without a Release, use the annotated tagger timestamp, or the target commit timestamp for lightweight tags.
3. Normalize all timestamps to UTC before comparing them.
4. Include a tag only when its resolved timestamp is less than or equal to `created_at`.
5. When multiple tags share the same timestamp, use a deterministic tie-breaker and log it.
6. Exclude drafts and prereleases by default. Support them only through an explicit configuration option if required.
7. Do not use the current date, the time of script execution, or the latest version today as a substitute for the historical cutoff.

Important: tag names are not necessarily dates. Use timestamps to determine historical eligibility, not lexical ordering of tag names.

Cache tag metadata per repository during each run so that multiple records for the same slicer do not trigger repeated API requests.

### 3.4 Version string normalization

The value written to `slicer_version` should be derived from the actual upstream tag.

Examples:

- Tag `v2.3.1` → `2.3.1`
- Tag `2.3.1` → `2.3.1`

Only remove a leading `v` when the tag uses that conventional version prefix. Preserve the original tag in diagnostic logs.

Do not assume all repositories follow semantic versioning. Support repository-specific tag formats, including tags with product prefixes or build metadata, without inventing a version.

If normalization is ambiguous, skip the record and report the original tag rather than guessing.

## 4. Implementation requirements

Create a standalone script in the existing project's appropriate location. Follow existing naming and packaging conventions.

The script must:

- Read all relevant Bitable records, handling pagination correctly.
- Handle Bitable API rate limits and transient network failures with bounded retries.
- Retrieve tag and release metadata efficiently, using pagination and caching.
- Handle GitHub API rate limits and missing release metadata.
- Parse Bitable timestamps consistently, including ISO-8601 strings and Unix timestamps if supported by the actual schema.
- Validate that the selected version is historically eligible before writing.
- Batch updates where supported by the existing Bitable client.
- Respect Bitable API batch-size limits.
- Never update fields other than `slicer_version`.
- Avoid updating a record if its current value has changed since it was read, where the API and existing client permit a reliable check.
- Keep credentials in existing environment variables or secret-management configuration. Never hardcode tokens.
- Produce actionable logs and a final summary.

Do not download, modify, or regenerate preset JSON artifacts. Do not create new `Submission`, `PresetVersion`, or `Preset` records.

## 5. Command-line interface

Support at least the following commands:

```bash
# Preview changes without modifying Bitable
python scripts/backfill_slicer_version.py --dry-run

# Apply changes to records with missing versions
python scripts/backfill_slicer_version.py

# Explicitly allow replacing existing values
python scripts/backfill_slicer_version.py --overwrite

# Process a limited number of records for testing
python scripts/backfill_slicer_version.py --limit 10
```

If the repository uses a different established CLI convention, adapt the commands accordingly.

Dry-run should be the default if consistent with the existing project's operational conventions. If the script defaults to writing, require an explicit dry-run flag and clearly document the behavior.

Provide an optional filter by slicer if it can be implemented cleanly.

## 6. Safety and error handling

The script must distinguish these outcomes:

- `UPDATED`: version resolved and written successfully.
- `WOULD_UPDATE`: version resolved in dry-run mode.
- `SKIPPED_EXISTING`: field already has a value and overwrite is disabled.
- `SKIPPED_UNKNOWN_SLICER`: slicer mapping is missing.
- `SKIPPED_INVALID_DATE`: creation timestamp is missing or invalid.
- `SKIPPED_NO_ELIGIBLE_TAG`: no qualifying historical tag exists.
- `SKIPPED_AMBIGUOUS_TAG`: version resolution is ambiguous.
- `FAILED_READ`: record or metadata could not be read.
- `FAILED_WRITE`: Bitable update failed.

A failed lookup must never result in writing the current version as a fallback.

Transient errors should be retried within configured limits. Persistent errors should be logged and reflected in the final exit status.

The script must be idempotent: rerunning it without `--overwrite` should not change already-populated records.

## 7. Testing requirements

Add automated tests covering at least:

1. Correct selection of the latest tag before the creation timestamp.
2. Exclusion of tags published after the creation timestamp.
3. Correct handling of a tag published exactly at the cutoff.
4. Correct handling of timezone offsets.
5. Correct parsing of the actual Bitable `created_at` field format.
6. Annotated tags and lightweight tags.
7. Tags with and without a leading `v`.
8. Repositories with nonstandard tag naming.
9. Unknown slicers.
10. Missing or invalid creation timestamps.
11. Empty version fields versus existing values.
12. `--overwrite` behavior.
13. Dry-run performs no writes.
14. API pagination, caching, rate limits, and retry exhaustion.
15. Bitable write failures and concurrent changes where supported.
16. Repeated execution does not produce unnecessary updates.

Use mocked Bitable and GitHub API responses for deterministic unit tests. Do not require live credentials to run the test suite.

Add at least one integration-test procedure using a small, explicitly selected set of records. Never use the entire production table for initial validation.

## 8. Execution plan

Implement in this order:

1. Inspect the existing repository and actual Bitable schema.
2. Verify official repository mappings and tag metadata semantics for every supported slicer.
3. Implement timestamp parsing and historical version resolution as independently testable functions.
4. Implement the Bitable reader and narrowly scoped writer using existing clients.
5. Add CLI flags, dry-run output, logging, and a summary report.
6. Add unit tests and run the existing regression suite.
7. Run dry-run against a small sample of real records, if credentials are available.
8. Review the proposed updates and only then execute a production write.

Do not silently change the business rules if upstream metadata is inconsistent. Report the issue and make the resolution strategy explicit.

## 9. Acceptance criteria

The implementation is complete when:

- Every supported slicer has a verified upstream repository mapping.
- Each resolved version corresponds to an eligible tag at the record's historical cutoff.
- Existing nonempty values remain untouched by default.
- Dry-run produces a reviewable list of proposed changes without modifying Bitable.
- Production writes update only `slicer_version`.
- Failures and unresolved records are identifiable from the final report.
- Automated tests pass without network access.
- Existing preset worker behavior and regression tests remain unaffected.

## 10. Final deliverables

Provide:

1. The implemented script.
2. Any minimal configuration changes.
3. Automated tests.
4. Usage documentation and CLI examples.
5. A concise implementation report describing the repository mappings, timestamp policy, test results, and any unresolved cases.

Before claiming completion, report which commands were actually run and their results. Do not claim a production backfill succeeded unless the Bitable writes were confirmed.