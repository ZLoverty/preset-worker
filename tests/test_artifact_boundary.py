import unittest

from preset_worker.services.enrichment import SubmissionEnrichment
from preset_worker.diff import ChangeType, DiffCategory, DiffChange, UnifiedDiff
from preset_worker.slicers import (
    Artifact,
    ProcessingContext,
    SlicerProcessorRegistry,
    ValidationResult,
    ValidationStatus,
)


class NonJsonProcessor:
    slicer_id = "FakeSlicer"

    def parse(self, artifact: Artifact, context: ProcessingContext):
        return artifact.content

    def validate_source(self, source, context):
        return ValidationResult(ValidationStatus.VALID)

    def normalize(self, source, context):
        return source

    def apply_company_policy(self, normalized, context):
        return normalized + b"!"

    def validate_canonical(self, canonical, context):
        return ValidationResult(ValidationStatus.VALID)

    def serialize(self, canonical, context):
        return Artifact(canonical, "example.fake", "application/octet-stream")

    def diff(self, base, candidate, context):
        return UnifiedDiff((DiffChange(
            "fake.parameter",
            ChangeType.ADDED if base is None else ChangeType.MODIFIED,
            DiffCategory.OTHER_PARAMETER,
            None if base is None else "A",
            "B",
        ),))


class FakeClient:
    submission_table_id = "submission"
    preset_table_id = "preset"
    version_table_id = "version"

    def __init__(self):
        self.submission = {
            "record_id": "submission-record",
            "fields": {
                "status": "VALIDATING",
                "submission_id": "S1",
                "pi_code": [{"text": "PI"}],
                "printer": [{"text": "Printer"}],
                "slicer": [{"text": "FakeSlicer"}],
                "method_version": "1",
                "preset_key": "PI | Printer | FakeSlicer",
                "preset data": [{"file_token": "uploaded"}],
            },
        }
        self.presets = [{
            "record_id": "preset-record",
            "fields": {"preset_key": "PI | Printer | FakeSlicer", "current_version_id": [{"text": "P@v1"}]},
        }]
        self.versions = [{
            "record_id": "version-record",
            "fields": {"version_id": "P@v1", "version_no": 1, "canonical_json": [{"file_token": "base"}]},
        }]
        self.files = {"uploaded": b"NOT JSON", "base": b"BASE NOT JSON"}
        self.uploads = []

    def get_submission(self, _submission_id):
        return self.submission

    def list_records(self, table_id):
        return {
            self.preset_table_id: self.presets,
            self.version_table_id: self.versions,
        }[table_id]

    def download_attachment(self, attachment):
        return self.files[attachment["file_token"]]

    def upload_attachment(self, filename, content):
        self.uploads.append((filename, content))
        return {"file_token": "canonical"}

    def update_submission(self, _record_id, fields):
        self.submission["fields"].update(fields)


class ArtifactBoundaryTests(unittest.TestCase):
    def test_non_json_base_and_candidate_stay_opaque(self):
        client = FakeClient()
        result = SubmissionEnrichment(
            client,
            processor_registry=SlicerProcessorRegistry([NonJsonProcessor()]),
        ).process_candidate(client.submission, "S1")

        self.assertEqual(result.canonical_artifact.content, b"NOT JSON!")
        self.assertEqual(result.canonical_artifact.filename, "example.fake")
        self.assertEqual(result.diff.changes[0].path, "fake.parameter")
        self.assertEqual(result.diff.changes[0].change_type, ChangeType.MODIFIED)

    def test_non_json_create_uses_processor_initial_diff_without_parsing(self):
        client = FakeClient()
        client.presets = []
        result = SubmissionEnrichment(
            client,
            processor_registry=SlicerProcessorRegistry([NonJsonProcessor()]),
        ).process_candidate(client.submission, "S1")

        self.assertEqual(result.operation, "CREATE")
        self.assertEqual(result.diff.changes[0].change_type, ChangeType.ADDED)
        self.assertIsNone(result.diff.changes[0].old_value)

    def test_persistence_uses_processor_artifact_bytes_and_filename(self):
        client = FakeClient()
        client.submission["fields"]["status"] = "VALIDATING"
        SubmissionEnrichment(
            client,
            processor_registry=SlicerProcessorRegistry([NonJsonProcessor()]),
        ).enrich_submission("S1")

        self.assertEqual(client.uploads, [("example.fake", b"NOT JSON!")])


if __name__ == "__main__":
    unittest.main()
