import json
import unittest

from submission_enrichment import SubmissionEnrichment, ValidationFailure, calculate_diff


class FakeClient:
    submission_table_id = "submission"
    preset_table_id = "preset"
    version_table_id = "version"

    def __init__(self, uploaded):
        self.submission = {
            "record_id": "record-1",
            "fields": {
                "submission_id": "S123",
                "pi_code": [{"text": "L2002CF"}],
                "printer": [{"text": "BBL P2S"}],
                "slicer": [{"text": "BambuStudio"}],
                "uploaded_json": [{"file_token": "uploaded"}],
            },
        }
        self.files = {"uploaded": json.dumps(uploaded).encode() if isinstance(uploaded, dict) else uploaded}
        self.presets = []
        self.versions = []
        self.updates = []
        self.uploads = []

    def get_submission(self, _submission_id):
        return self.submission

    def list_records(self, table_id):
        return {self.preset_table_id: self.presets, self.version_table_id: self.versions}[table_id]

    def download_attachment(self, attachment):
        return self.files[attachment["file_token"]]

    def upload_attachment(self, filename, content):
        self.uploads.append((filename, content))
        self.files["canonical-1"] = content
        return {"file_token": "canonical-1"}

    def update_submission(self, _record_id, fields):
        self.updates.append(fields)
        self.submission["fields"].update(fields)


class SubmissionEnrichmentTests(unittest.TestCase):
    def test_create(self):
        client = FakeClient({"name": "new", "temperature": "220"})
        result = SubmissionEnrichment(client).enrich_submission("S123")
        self.assertEqual(result.operation, "CREATE")
        self.assertEqual(result.base_version_id, "")
        self.assertEqual(result.status, "READY_FOR_REVIEW")
        self.assertEqual(len(result.diff["added"]), 2)

    def test_update_against_current_version(self):
        client = FakeClient({"name": "new", "temperature": "220"})
        client.presets = [{
            "fields": {"preset_key": "L2002CF | BBL P2S | BambuStudio", "current_version_id": [{"text": "P42@v7"}]}
        }]
        client.versions = [{
            "fields": {"version_id": "P42@v7", "canonical_json": [{"file_token": "base"}]}
        }]
        client.files["base"] = b'{"name":"old","temperature":"220"}'
        result = SubmissionEnrichment(client).enrich_submission("S123")
        self.assertEqual(result.operation, "UPDATE")
        self.assertEqual(result.base_version_id, "P42@v7")
        self.assertEqual(result.diff["modified"][0]["path"], "name")

    def test_invalid_json_updates_validation_only(self):
        client = FakeClient(b"not-json")
        with self.assertRaises(ValidationFailure):
            SubmissionEnrichment(client).enrich_submission("S123")
        self.assertEqual(client.updates[-1]["status"], "VALIDATION_FAILED")
        self.assertFalse(client.uploads)

    def test_validation_failure_for_non_object(self):
        client = FakeClient(b"[1, 2]")
        with self.assertRaises(ValidationFailure):
            SubmissionEnrichment(client).enrich_submission("S123")
        self.assertEqual(client.updates[-1]["status"], "VALIDATION_FAILED")

    def test_normalization_keeps_original_and_sorts_keys(self):
        client = FakeClient({"z": 1, "a": {"y": 2, "x": 3}})
        SubmissionEnrichment(client).enrich_submission("S123")
        self.assertEqual(json.loads(client.files["uploaded"]), {"z": 1, "a": {"y": 2, "x": 3}})
        canonical = json.loads(client.uploads[0][1])
        self.assertEqual(list(canonical), ["a", "z"])

    def test_diff(self):
        diff = calculate_diff({"a": 1, "old": True}, {"a": 2, "new": False})
        self.assertEqual(diff["modified"], [{"path": "a", "old": 1, "new": 2}])
        self.assertEqual(diff["added"], [{"path": "new", "new": False}])
        self.assertEqual(diff["removed"], [{"path": "old", "old": True}])

    def test_rerun_does_not_create_preset_or_version(self):
        client = FakeClient({"name": "same"})
        service = SubmissionEnrichment(client)
        first = service.enrich_submission("S123")
        second = service.enrich_submission("S123")
        self.assertEqual(first.diff, second.diff)
        self.assertEqual(len(client.presets), 0)
        self.assertEqual(len(client.versions), 0)
        self.assertEqual(len(client.uploads), 1)


if __name__ == "__main__":
    unittest.main()
