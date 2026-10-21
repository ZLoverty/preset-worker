import json
import unittest
from unittest.mock import patch

from preset_worker.services.consistency_preview import build_consistency_report
from preset_worker.slicers.contracts import Artifact


class Client:
    def __init__(self, slicer="BambuStudio", project=True):
        self.record = {"record_id": "r1", "fields": {"slicer": slicer}}
        if project:
            self.record["fields"]["preset 3mf"] = [{"file_token": "p3mf"}]
        self.files = {"p3mf": b"3mf-bytes"}
        self.uploads = []

    def download_attachment(self, attachment):
        return self.files[attachment["file_token"]]


class Candidate:
    source_artifact = Artifact(b"preset", "preset.json", "application/json")


class P9B3ATests(unittest.TestCase):
    def test_unsupported_slicer_is_empty(self):
        client = Client("UnknownSlicer")
        self.assertEqual(build_consistency_report(client, client.record, Candidate()), "")

    def test_missing_project_is_empty(self):
        client = Client(project=False)
        self.assertEqual(build_consistency_report(client, client.record, Candidate()), "")

    @patch("preset_worker.services.consistency_preview.validate_bambu_consistency")
    def test_ready_report_is_json_text_and_preserves_rows(self, validate):
        validate.return_value = {
            "schema_version": "p9b2.consistency.v1",
            "comparison_rows": [{"path": "fan_min_speed[0]"}],
            "comparisons": [],
            "artifacts": {},
        }
        client = Client()
        value = build_consistency_report(client, client.record, Candidate())
        payload = json.loads(value)
        self.assertEqual(payload["status"], "READY")
        self.assertEqual(payload["report"]["comparison_rows"][0]["path"], "fan_min_speed[0]")
        self.assertRegex(payload["generated_at"], r"Z$")
        validate.assert_called_once()
        self.assertEqual(client.uploads, [])

    @patch("preset_worker.services.consistency_preview.validate_bambu_consistency")
    def test_mismatch_remains_ready(self, validate):
        validate.return_value = {"schema_version": "p9b2.consistency.v1", "summary": {"MISMATCH": 1}}
        client = Client()
        payload = json.loads(build_consistency_report(client, client.record, Candidate()))
        self.assertEqual(payload["status"], "READY")
        self.assertEqual(payload["report"]["summary"], {"MISMATCH": 1})

    @patch("preset_worker.services.consistency_preview.validate_bambu_consistency", side_effect=ValueError("bad 3mf"))
    def test_validator_error_is_minimal_and_sanitized(self, validate):
        client = Client()
        payload = json.loads(build_consistency_report(client, client.record, Candidate()))
        self.assertEqual(payload["status"], "ERROR")
        self.assertEqual(payload["error"]["code"], "CONSISTENCY_VALIDATION_FAILED")
        self.assertNotIn("bad 3mf", json.dumps(payload))

    @patch("preset_worker.services.consistency_preview.validate_bambu_consistency")
    def test_oversized_report_uses_error_fallback(self, validate):
        validate.return_value = {"schema_version": "p9b2.consistency.v1", "large": "x" * 110_000}
        client = Client()
        payload = json.loads(build_consistency_report(client, client.record, Candidate()))
        self.assertEqual(payload["status"], "ERROR")
        self.assertEqual(payload["error"]["code"], "CONSISTENCY_REPORT_SERIALIZATION_FAILED")


if __name__ == "__main__":
    unittest.main()
