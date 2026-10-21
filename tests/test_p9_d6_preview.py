import io
import json
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from preset_worker.diff import UnifiedDiff
from preset_worker.services.consistency_preview import build_consistency_report
from preset_worker.services.preview import PreviewService
from preset_worker.slicers.contracts import Artifact


ROOT = Path("tests/fixtures/slicers")


class ConsistencyClient:
    def __init__(self, slicer: str, preset: Path, project: Path):
        self.record = {
            "record_id": "preview-record",
            "fields": {
                "slicer": slicer,
                "preset 3mf": [{"file_token": "project"}],
            },
        }
        self.files = {
            "project": project.read_bytes(),
            "preset": preset.read_bytes(),
        }
        self.downloads = []

    def download_attachment(self, attachment):
        token = attachment["file_token"]
        self.downloads.append(token)
        return self.files[token]


class PreviewWriteClient:
    def __init__(self, failures=0, error_text="invalid field consistency_report"):
        self.failures = failures
        self.error_text = error_text
        self.updates = []
        self.uploads = []

    def update_submission(self, _record_id, fields):
        if self.failures:
            self.failures -= 1
            raise RuntimeError(self.error_text)
        self.updates.append(fields)

    def upload_attachment(self, filename, content):
        self.uploads.append((filename, content))
        return {"file_token": "canonical"}


def candidate():
    return SimpleNamespace(
        operation="CREATE",
        base_version_record_id=None,
        diff=UnifiedDiff(()),
        validation={"valid": True},
        canonical_artifact=Artifact(b"{}", "preset.json", "application/json"),
    )


class P9D6PreviewTests(unittest.TestCase):
    def test_all_six_real_fixture_dispatches(self):
        cases = [
            ("BambuStudio", None, None, "BambuStudio"),
            ("CrealityPrint", "creality_print", "creality.3mf", "CrealityPrint"),
            ("ElegooSlicer", "elegoo_slicer", "elegoo.3mf", "ElegooSlicer"),
            ("OrcaSlicer", "orca_slicer", "orca.3mf", "OrcaSlicer"),
            ("SnapmakerOrcaSlicer", "orca_slicer_snapmaker", "snapmaker-orca.3mf", "SnapmakerOrcaSlicer"),
            ("PrusaSlicer", "prusa_slicer", "prusa.3mf", "PrusaSlicer"),
        ]
        for slicer, directory, project_name, expected_source in cases:
            if slicer == "BambuStudio":
                base = Path("downloads/3mf-fixture")
                preset = base / "PPS100CF10 H2D (1).json"
                project = base / "PPS100CF10 H2D (1).3mf"
            else:
                base = ROOT / directory
                preset = next(path for path in base.iterdir() if path.suffix in (".json", ".ini") and path.name != "manifest.json")
                project = base / project_name
            client = ConsistencyClient(slicer, preset, project)
            source = Artifact(client.files["preset"], preset.name, "application/json" if preset.suffix == ".json" else "text/plain")
            value = build_consistency_report(client, client.record, SimpleNamespace(source_artifact=source))
            payload = json.loads(value)
            self.assertEqual(payload["status"], "READY", slicer)
            self.assertEqual(payload["report"]["schema_version"], "p9b2.consistency.v1")
            self.assertEqual(payload["report"]["source"]["slicer"], expected_source)
            self.assertEqual(client.downloads, ["project"], slicer)

    def test_unknown_slicer_does_not_fall_back_to_bambu(self):
        base = Path("downloads/3mf-fixture")
        client = ConsistencyClient("UnknownSlicer", base / "PPS100CF10 H2D (1).json", base / "PPS100CF10 H2D (1).3mf")
        source = Artifact(client.files["preset"], "preset.json", "application/json")
        self.assertEqual(build_consistency_report(client, client.record, SimpleNamespace(source_artifact=source)), "")
        self.assertEqual(client.downloads, [])

    def test_validator_exception_is_sanitized(self):
        base = ROOT / "orca_slicer"
        client = ConsistencyClient("OrcaSlicer", base / "L2002CF @BBL P2S.json", base / "orca.3mf")
        with patch.dict("preset_worker.services.consistency_preview.CONSISTENCY_VALIDATORS", {"OrcaSlicer": lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("secret"))}, clear=False):
            payload = json.loads(build_consistency_report(client, client.record, SimpleNamespace(source_artifact=Artifact(client.files["preset"], "preset.json", "application/json"))))
        self.assertEqual(payload["status"], "ERROR")
        self.assertEqual(payload["error"]["code"], "CONSISTENCY_VALIDATION_FAILED")
        self.assertNotIn("secret", json.dumps(payload))

    def test_malformed_project_is_error_envelope(self):
        base = ROOT / "orca_slicer"
        client = ConsistencyClient("OrcaSlicer", base / "L2002CF @BBL P2S.json", base / "orca.3mf")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("Metadata/project_settings.config", b"bad")
        client.files["project"] = output.getvalue()
        payload = json.loads(build_consistency_report(client, client.record, SimpleNamespace(source_artifact=Artifact(client.files["preset"], "preset.json", "application/json"))))
        self.assertEqual(payload["status"], "ERROR")

    def test_candidate_failure_clears_previous_report(self):
        client = PreviewWriteClient()
        service = PreviewService(client)
        service._write_candidate_failure({"record_id": "r1"}, ValueError("bad preset"))
        self.assertEqual(client.updates[0]["consistency_report"], "")

    def test_report_field_failure_retries_with_error_not_omission(self):
        client = PreviewWriteClient(failures=1)
        service = PreviewService(client)
        service.candidate_processor._canonical_attachment = lambda *_args: "canonical"
        service._write_preview_result({"record_id": "r1", "fields": {}}, "S1", candidate(), "old-report")
        self.assertEqual(len(client.updates), 1)
        self.assertIn('"status":"ERROR"', client.updates[0]["consistency_report"])

    def test_report_field_fallback_eventually_clears_explicitly(self):
        client = PreviewWriteClient(failures=2)
        service = PreviewService(client)
        service.candidate_processor._canonical_attachment = lambda *_args: "canonical"
        service._write_preview_result({"record_id": "r1", "fields": {}}, "S1", candidate(), "old-report")
        self.assertEqual(client.updates[-1]["consistency_report"], "")

    def test_unrelated_write_failure_is_not_retried_as_report_failure(self):
        client = PreviewWriteClient(failures=1, error_text="network unavailable")
        service = PreviewService(client)
        service.candidate_processor._canonical_attachment = lambda *_args: "canonical"
        with self.assertRaisesRegex(RuntimeError, "network unavailable"):
            service._write_preview_result({"record_id": "r1", "fields": {}}, "S1", candidate(), "report")
        self.assertEqual(client.updates, [])


if __name__ == "__main__":
    unittest.main()
