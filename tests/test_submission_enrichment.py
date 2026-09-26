import json
import unittest

from preset_worker.services.enrichment import (
    FeishuClient,
    SubmissionEnrichment,
    UnsupportedSlicerError,
    ValidationFailure,
    calculate_diff,
)
from preset_worker.services.preview import PreviewService


class FakeClient:
    submission_table_id = "submission"
    preset_table_id = "preset"
    version_table_id = "version"

    def __init__(self, uploaded):
        self.submission = {
            "record_id": "record-1",
            "fields": {
                "submission_id": "S123",
                "status": "VALIDATING",
                "pi_code": [{"text": "L2002CF"}],
                "printer": [{"text": "BBL P2S"}],
                "slicer": [{"text": "BambuStudio"}],
                "method_version": "2.1",
                "preset_key": "L2002CF | BBL P2S | BambuStudio",
                "preset data": [{"file_token": "uploaded"}],
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
    def test_get_submission_accepts_record_id_and_wrapped_submission_id(self):
        client = FeishuClient.__new__(FeishuClient)
        client.submission_table_id = "submission"
        record = {
            "record_id": "recvw7M1BWm0um",
            "fields": {"submission_id": [{"text": "S123"}]},
        }
        client.list_records = lambda _table_id: [record]

        self.assertIs(client.get_submission("recvw7M1BWm0um"), record)
        self.assertIs(client.get_submission("S123"), record)

    def test_draft_is_rejected_without_mutation(self):
        client = FakeClient({"name": "draft", "version": "1"})
        client.submission["fields"]["status"] = "DRAFT"
        before = dict(client.submission["fields"])
        with self.assertRaisesRegex(RuntimeError, "DRAFT.*not eligible"):
            SubmissionEnrichment(client).enrich_submission("S123")
        self.assertEqual(client.submission["fields"], before)
        self.assertFalse(client.updates)

    def test_preview_create_returns_to_draft_without_publication_artifacts(self):
        client = FakeClient({"name": "new", "version": "1"})
        client.submission["fields"]["status"] = "PREVIEW_REQUESTED"

        result = PreviewService(client).preview_submission("S123")

        self.assertEqual(result.operation, "CREATE")
        self.assertEqual(client.submission["fields"]["status"], "DRAFT")
        self.assertEqual(client.presets, [])
        self.assertEqual(client.versions, [])
        self.assertEqual(client.submission["fields"]["canonical_json"], [{"file_token": "canonical-1"}])

    def test_preview_update_uses_current_base_without_publication_artifacts(self):
        client = FakeClient({"name": "new", "version": "1", "temperature": "220"})
        client.submission["fields"]["status"] = "PREVIEW_REQUESTED"
        client.presets = [{
            "fields": {
                "preset_key": "L2002CF | BBL P2S | BambuStudio",
                "current_version_id": [{"text": "P42@v7"}],
            }
        }]
        client.versions = [{
            "record_id": "version-record-7",
            "fields": {"version_id": "P42@v7", "canonical_json": [{"file_token": "base"}]},
        }]
        client.files["base"] = b'{"name":"old","version":"1","temperature":"220"}'

        result = PreviewService(client).preview_submission("S123")

        self.assertEqual(result.operation, "UPDATE")
        self.assertEqual(result.base_version_id, "P42@v7")
        self.assertEqual(result.diff["modified"][0]["path"], "name")
        self.assertEqual(client.submission["fields"]["status"], "DRAFT")
        self.assertEqual(client.presets[0]["fields"]["current_version_id"][0]["text"], "P42@v7")

    def test_preview_invalid_candidate_returns_to_draft(self):
        client = FakeClient(b"not-json")
        client.submission["fields"]["status"] = "PREVIEW_REQUESTED"

        with self.assertRaises(ValidationFailure):
            PreviewService(client).preview_submission("S123")

        self.assertEqual(client.submission["fields"]["status"], "DRAFT")
        self.assertNotEqual(client.submission["fields"].get("status"), "VALIDATION_FAILED")
        self.assertFalse(client.uploads)

    def test_preview_state_guard_does_not_mutate_draft(self):
        client = FakeClient({"name": "draft", "version": "1"})
        client.submission["fields"]["status"] = "DRAFT"
        before = dict(client.submission["fields"])

        with self.assertRaisesRegex(RuntimeError, "DRAFT.*not eligible"):
            PreviewService(client).preview_submission("S123")

        self.assertEqual(client.submission["fields"], before)
        self.assertFalse(client.updates)

    def test_preview_and_enrichment_share_candidate_computation(self):
        formal_client = FakeClient({"name": "new", "version": "1", "temperature": "220"})
        preview_client = FakeClient({"name": "new", "version": "1", "temperature": "220"})
        preview_client.submission["fields"]["status"] = "PREVIEW_REQUESTED"

        formal = SubmissionEnrichment(formal_client).process_candidate(
            formal_client.submission,
            "S123",
        )
        preview = PreviewService(preview_client).preview_submission("S123")

        self.assertEqual(preview.canonical_json, formal.canonical_json)
        self.assertEqual(preview.diff, formal.diff)

    def test_create(self):
        client = FakeClient({"name": "new", "version": "1", "temperature": "220"})
        result = SubmissionEnrichment(client).enrich_submission("S123")
        self.assertEqual(result.operation, "CREATE")
        self.assertEqual(result.base_version_id, "")
        self.assertEqual(result.status, "READY_FOR_REVIEW")
        self.assertEqual(result.canonical_json["name"], "L2002CF @BBL P2S")
        self.assertEqual(result.canonical_json["pm_method_version"], "2.1")
        self.assertEqual(client.uploads[0][0], "L2002CF @BBL P2S.json")

    def test_formula_preset_key_is_read_but_not_written(self):
        client = FakeClient({"name": "new", "version": "1"})
        SubmissionEnrichment(client).enrich_submission("S123")
        self.assertNotIn("preset_key", client.updates[-1])

    def test_update_against_current_version(self):
        client = FakeClient({"name": "new", "version": "1", "temperature": "220"})
        client.presets = [{
            "fields": {"preset_key": "L2002CF | BBL P2S | BambuStudio", "current_version_id": [{"text": "P42@v7"}]}
        }]
        client.versions = [{
            "fields": {"version_id": "P42@v7", "canonical_json": [{"file_token": "base"}]}
        }]
        client.files["base"] = b'{"name":"old","version":"1","temperature":"220"}'
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

    def test_bambu_version_is_required(self):
        client = FakeClient({"name": "preset without version"})
        with self.assertRaises(ValidationFailure) as context:
            SubmissionEnrichment(client).enrich_submission("S123")
        self.assertIn("version", context.exception.validation["errors"][0])
        self.assertEqual(client.updates[-1]["status"], "VALIDATION_FAILED")

    def test_bambu_canonicalization_preserves_other_fields(self):
        uploaded = {
            "name": "Generic PLA",
            "version": "1",
            "inherits": "Generic PLA",
            "filament_settings_id": ["x"],
            "custom": {"nested": True},
            "pm_method_version": "1.0",
        }
        client = FakeClient(uploaded)
        SubmissionEnrichment(client).enrich_submission("S123")
        self.assertEqual(json.loads(client.files["uploaded"]), uploaded)
        canonical = json.loads(client.uploads[0][1])
        self.assertEqual(canonical["name"], "L2002CF @BBL P2S")
        self.assertEqual(canonical["pm_method_version"], "2.1")
        self.assertEqual(canonical["inherits"], uploaded["inherits"])
        self.assertEqual(canonical["custom"], uploaded["custom"])

    def test_diff(self):
        diff = calculate_diff({"a": 1, "old": True}, {"a": 2, "new": False})
        self.assertEqual(diff["modified"], [{"path": "a", "old": 1, "new": 2}])
        self.assertEqual(diff["added"], [{"path": "new", "new": False}])
        self.assertEqual(diff["removed"], [{"path": "old", "old": True}])

    def test_rerun_does_not_create_preset_or_version(self):
        client = FakeClient({"name": "same", "version": "1"})
        service = SubmissionEnrichment(client)
        first = service.enrich_submission("S123")
        second = service.enrich_submission("S123")
        self.assertEqual(first.diff, second.diff)
        self.assertEqual(len(client.presets), 0)
        self.assertEqual(len(client.versions), 0)
        self.assertEqual(len(client.uploads), 1)

    def test_unsupported_slicer(self):
        client = FakeClient({"name": "same", "version": "1"})
        client.submission["fields"]["slicer"] = [{"text": "OrcaSlicer"}]
        with self.assertRaises(UnsupportedSlicerError):
            SubmissionEnrichment(client).enrich_submission("S123")
        self.assertEqual(client.updates[-1]["status"], "VALIDATION_FAILED")

    def test_missing_method_version(self):
        client = FakeClient({"name": "same", "version": "1"})
        del client.submission["fields"]["method_version"]
        with self.assertRaises(ValidationFailure):
            SubmissionEnrichment(client).enrich_submission("S123")
        self.assertEqual(client.updates[-1]["status"], "VALIDATION_FAILED")

    def test_ready_submission_keeps_frozen_baseline(self):
        client = FakeClient({"name": "same", "version": "1"})
        client.submission["fields"].update({
            "status": "READY_FOR_REVIEW",
            "preset_key": "L2002CF | BBL P2S | BambuStudio",
            "operation": "UPDATE",
            "base_version_id": "P42@v7",
            "diff": "{}",
            "validation": '{"valid":true}',
        })
        client.presets = [{"fields": {"preset_key": "L2002CF | BBL P2S | BambuStudio", "current_version_id": [{"text": "P42@v8"}]}}]
        result = SubmissionEnrichment(client).enrich_submission("S123")
        self.assertEqual(result.base_version_id, "P42@v7")
        self.assertFalse(client.updates)


if __name__ == "__main__":
    unittest.main()
