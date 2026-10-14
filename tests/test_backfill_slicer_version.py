import unittest
from datetime import datetime, timezone

from preset_worker.backfill_slicer_version import (
    VersionTag,
    normalize_version_tag,
    parse_timestamp,
    select_latest_tag,
    run_backfill,
)


class FakeClient:
    submission_table_id = "submission"

    def __init__(self, records):
        self.records = records
        self.updates = []

    def list_records(self, _table_id, limit=None):
        return self.records[:limit] if limit else self.records

    def get_record(self, _table_id, record_id):
        return next(record for record in self.records if record["record_id"] == record_id)

    def update_submission(self, record_id, fields):
        self.updates.append((record_id, fields))
        next(record for record in self.records if record["record_id"] == record_id)["fields"].update(fields)


class FakeGitHub:
    def __init__(self, tags):
        self.tags_by_repo = tags
        self.calls = []

    def tags(self, repository):
        self.calls.append(repository)
        return self.tags_by_repo[repository]


class BackfillTests(unittest.TestCase):
    def test_selects_latest_tag_at_or_before_cutoff_and_excludes_prerelease(self):
        tags = [
            VersionTag("v1.0.0", parse_timestamp("2024-01-01T00:00:00Z")),
            VersionTag("v1.1.0", parse_timestamp("2024-02-01T00:00:00+08:00")),
            VersionTag("v2.0.0", parse_timestamp("2024-04-01T00:00:00Z")),
            VersionTag("v1.9.0-beta", parse_timestamp("2024-03-01T00:00:00Z"), prerelease=True),
        ]
        selected = select_latest_tag(tags, parse_timestamp("2024-02-01T00:00:00Z"))
        self.assertEqual(selected.name, "v1.1.0")

    def test_timestamp_parsing_supports_milliseconds_and_offsets(self):
        self.assertEqual(parse_timestamp(1704067200000), datetime(2024, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(parse_timestamp("2024-01-01T08:00:00+08:00"), datetime(2024, 1, 1, tzinfo=timezone.utc))

    def test_normalization_preserves_nonstandard_names(self):
        self.assertEqual(normalize_version_tag("v2.3.1"), "2.3.1")
        self.assertEqual(normalize_version_tag("release-2024.01"), "release-2024.01")

    def test_dry_run_does_not_write_and_existing_is_idempotent(self):
        records = [
            {"record_id": "r1", "fields": {"slicer": "PrusaSlicer", "created_at": 1704067200000, "slicer_version": ""}},
            {"record_id": "r2", "fields": {"slicer": "PrusaSlicer", "created_at": 1704067200000, "slicer_version": "old"}},
        ]
        client = FakeClient(records)
        github = FakeGitHub({"prusa3d/PrusaSlicer": [VersionTag("v2.7.0", parse_timestamp("2023-12-01T00:00:00Z"))]})
        result = run_backfill(client, github, {"PrusaSlicer": "prusa3d/PrusaSlicer"}, dry_run=True)
        self.assertEqual(result["WOULD_UPDATE"], 1)
        self.assertEqual(result["SKIPPED_EXISTING"], 1)
        self.assertFalse(client.updates)

    def test_unknown_slicer_invalid_date_and_overwrite(self):
        records = [
            {"record_id": "unknown", "fields": {"slicer": "Cura", "created_at": 1}},
            {"record_id": "bad-date", "fields": {"slicer": "PrusaSlicer", "created_at": "not-a-date"}},
            {"record_id": "existing", "fields": {"slicer": "PrusaSlicer", "created_at": 1704067200000, "slicer_version": "old"}},
        ]
        client = FakeClient(records)
        github = FakeGitHub({"prusa3d/PrusaSlicer": [VersionTag("2.7.0", parse_timestamp("2023-12-01T00:00:00Z"))]})
        result = run_backfill(client, github, {"PrusaSlicer": "prusa3d/PrusaSlicer"}, overwrite=True)
        self.assertEqual(result["SKIPPED_UNKNOWN_SLICER"], 1)
        self.assertEqual(result["SKIPPED_INVALID_DATE"], 1)
        self.assertEqual(client.updates, [("existing", {"slicer_version": "2.7.0"})])


if __name__ == "__main__":
    unittest.main()
