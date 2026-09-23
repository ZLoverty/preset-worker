import copy
import unittest

from submission_publication import (
    APPROVED,
    APPROVING,
    VERSION_CONFLICT,
    PublicationConflict,
    SubmissionPublisher,
)


class FakeClient:
    submission_table_id = "submission"
    preset_table_id = "preset"
    version_table_id = "version"

    def __init__(self, operation="CREATE"):
        self.submission = {
            "record_id": "sub-rec",
            "fields": {
                "submission_id": "S1",
                "status": APPROVING,
                "operation": operation,
                "preset_key": "X",
                "pi_code": [{"record_ids": ["pi-rec"]}],
                "printer": [{"record_ids": ["printer-rec"]}],
                "slicer": [{"record_ids": ["slicer-rec"]}],
                "canonical_json": [{"file_token": "canonical"}],
                "change_reason": "Improve extrusion",
                "review_comment": "Looks good",
                "submitter": [{"id": "user-submit"}],
                "reviewer": [{"id": "user-review"}],
                "submitted_at": 100,
                "reviewed_at": 200,
                "photos": [{"file_token": "photo-1"}],
            },
        }
        self.presets = []
        self.versions = []
        self.files = {"canonical": b'{"version":"1","name":"X"}'}
        self.created = []
        self.updates = []
        self.fail_preset_update = False

    def get_submission(self, _submission_id):
        return self.submission

    def list_records(self, table_id):
        return {self.preset_table_id: self.presets, self.version_table_id: self.versions}[table_id]

    def create_record(self, table_id, fields):
        record_id = f"{table_id}-new-{len(self.created)}"
        record = {"record_id": record_id, "id": record_id, "fields": copy.deepcopy(fields)}
        if table_id == self.preset_table_id:
            self.presets.append(record)
        else:
            self.versions.append(record)
        self.created.append((table_id, record))
        return record

    def update_record(self, table_id, record_id, fields):
        if self.fail_preset_update and table_id == self.preset_table_id:
            raise RuntimeError("simulated update failure")
        records = self.presets if table_id == self.preset_table_id else self.versions
        record = next(record for record in records if record["record_id"] == record_id)
        record["fields"].update(copy.deepcopy(fields))
        self.updates.append((table_id, record_id, fields))

    def update_submission(self, _record_id, fields):
        self.submission["fields"].update(copy.deepcopy(fields))
        self.updates.append((self.submission_table_id, _record_id, fields))


class SubmissionPublicationTests(unittest.TestCase):
    def test_create_first_version(self):
        client = FakeClient("CREATE")
        result = SubmissionPublisher(client).publish_submission("S1")
        self.assertEqual(result.version_id, "X@v1")
        self.assertEqual(client.submission["fields"]["status"], APPROVED)
        self.assertEqual(client.presets[0]["fields"]["current_version"], ["version-new-1"])
        self.assertEqual(len(client.versions), 1)

    def test_update(self):
        client = FakeClient("UPDATE")
        client.submission["fields"]["base_version_id"] = "X@v7"
        client.presets = [{
            "record_id": "preset-1",
            "fields": {"preset_key": "X", "current_version": [{"record_ids": ["version-7"], "text": "X@v7"}]},
        }]
        client.versions = [{"record_id": "version-7", "fields": {"version_id": "X@v7", "version_no": 7}}]
        result = SubmissionPublisher(client).publish_submission("S1")
        self.assertEqual(result.version_id, "X@v8")
        self.assertEqual(client.submission["fields"]["published_version_id"], "X@v8")

    def test_metadata_snapshot(self):
        client = FakeClient()
        SubmissionPublisher(client).publish_submission("S1")
        version = client.versions[0]["fields"]
        client.submission["fields"]["review_comment"] = "changed later"
        self.assertEqual(version["review_comment"], "Looks good")
        self.assertEqual(version["submitted_by"], [{"id": "user-submit"}])
        self.assertEqual(version["reviewed_by"], [{"id": "user-review"}])

    def test_attachment_and_source_relation(self):
        client = FakeClient()
        SubmissionPublisher(client).publish_submission("S1")
        version = client.versions[0]["fields"]
        self.assertEqual(version["canonical_json"], [{"file_token": "canonical"}])
        self.assertEqual(version["source_submission"], ["sub-rec"])

    def test_update_stale_baseline(self):
        client = FakeClient("UPDATE")
        client.submission["fields"]["base_version_id"] = "X@v7"
        client.presets = [{"record_id": "preset-1", "fields": {"preset_key": "X", "current_version": [{"text": "X@v8"}]}}]
        with self.assertRaises(PublicationConflict):
            SubmissionPublisher(client).publish_submission("S1")
        self.assertEqual(client.submission["fields"]["status"], VERSION_CONFLICT)
        self.assertFalse(client.versions)

    def test_create_conflict(self):
        client = FakeClient("CREATE")
        client.presets = [{"record_id": "preset-1", "fields": {"preset_key": "X"}}]
        with self.assertRaises(PublicationConflict):
            SubmissionPublisher(client).publish_submission("S1")
        self.assertEqual(client.submission["fields"]["status"], VERSION_CONFLICT)
        self.assertFalse(client.versions)

    def test_duplicate_publish_reuses_version(self):
        client = FakeClient()
        publisher = SubmissionPublisher(client)
        first = publisher.publish_submission("S1")
        second = publisher.publish_submission("S1")
        self.assertEqual(first.version_id, second.version_id)
        self.assertEqual(len(client.versions), 1)

    def test_recovery_does_not_roll_back_newer_version(self):
        client = FakeClient()
        client.presets = [{"record_id": "preset-1", "fields": {"preset_key": "X", "current_version": [{"text": "X@v9"}]}}]
        client.versions = [
            {"record_id": "version-8", "fields": {"version_id": "X@v8", "version_no": 8, "source_submission": [{"record_ids": ["sub-rec"]}]}},
            {"record_id": "version-9", "fields": {"version_id": "X@v9", "version_no": 9}},
        ]
        client.submission["fields"]["status"] = APPROVING
        result = SubmissionPublisher(client).publish_submission("S1")
        self.assertEqual(result.version_id, "X@v8")
        self.assertEqual(client.presets[0]["fields"]["current_version"][0]["text"], "X@v9")

    def test_process_photo_projection(self):
        client = FakeClient()
        client.presets = [{"record_id": "preset-1", "fields": {"preset_key": "X", "photos": [], "current_version": [{"text": "X@v1", "record_ids": ["version-1"]}]}}]
        client.submission["fields"]["operation"] = "UPDATE"
        client.submission["fields"]["base_version_id"] = "X@v1"
        client.versions = [{"record_id": "version-1", "fields": {"version_id": "X@v1", "version_no": 1}}]
        SubmissionPublisher(client).publish_submission("S1")
        self.assertEqual(client.presets[0]["fields"]["photos"], [{"file_token": "photo-1"}])


if __name__ == "__main__":
    unittest.main()
