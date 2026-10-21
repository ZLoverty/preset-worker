import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from preset_worker.diff import UnifiedDiff
from preset_worker.services.enrichment import CandidateResult, SubmissionEnrichment, ValidationFailure
from preset_worker.slicers.contracts import Artifact


ROOT = Path("tests/fixtures/slicers")


class SubmitClient:
    submission_table_id = "submission"
    preset_table_id = "preset"
    version_table_id = "version"

    def __init__(self, slicer, preset, project=None, failures=0):
        self.submission = {
            "record_id": "record-1",
            "fields": {
                "submission_id": "S1",
                "status": "VALIDATING",
                "pi_code": "L2002CF",
                "printer": "BBL P2S",
                "slicer": slicer,
                "method_version": "2.1",
                "preset_key": f"L2002CF | BBL P2S | {slicer}",
                "preset data": [{"file_token": "preset"}],
            },
        }
        if project is not None:
            self.submission["fields"]["preset 3mf"] = [{"file_token": "project"}]
        self.files = {"preset": preset}
        if project is not None:
            self.files["project"] = project
        self.updates = []
        self.failures = failures

    def get_submission(self, _submission_id):
        return self.submission

    def find_preset_by_key(self, _key):
        return []

    def list_records(self, _table_id):
        return []

    def download_attachment(self, attachment):
        return self.files[attachment["file_token"]]

    def upload_attachment(self, _filename, _content):
        return {"file_token": "canonical"}

    def update_submission(self, _record_id, fields):
        if self.failures:
            self.failures -= 1
            raise RuntimeError("invalid field consistency_report")
        self.updates.append(fields)
        self.submission["fields"].update(fields)


def candidate(source, filename="preset.json"):
    artifact = Artifact(source, filename, "application/json" if filename.endswith(".json") else "text/plain")
    return CandidateResult(
        operation="CREATE",
        preset_key="key",
        base_version_id="",
        base_version_record_id=None,
        base_version_no_text="",
        source_artifact=artifact,
        canonical_artifact=artifact,
        diff=UnifiedDiff(()),
        validation={"valid": True, "errors": [], "warnings": []},
    )


def fixture_pair(slicer):
    if slicer == "BambuStudio":
        base = Path("downloads/3mf-fixture")
        return (base / "PPS100CF10 H2D (1).json").read_bytes(), (base / "PPS100CF10 H2D (1).3mf").read_bytes(), "PPS100CF10 H2D (1).json"
    directories = {
        "CrealityPrint": ("creality_print", "creality.3mf"),
        "ElegooSlicer": ("elegoo_slicer", "elegoo.3mf"),
        "OrcaSlicer": ("orca_slicer", "orca.3mf"),
        "SnapmakerOrcaSlicer": ("orca_slicer_snapmaker", "snapmaker-orca.3mf"),
        "PrusaSlicer": ("prusa_slicer", "prusa.3mf"),
    }
    directory, project_name = directories[slicer]
    base = ROOT / directory
    preset = next(path for path in base.iterdir() if path.suffix in (".json", ".ini") and path.name != "manifest.json")
    return preset.read_bytes(), (base / project_name).read_bytes(), preset.name


class P9D6SubmitConsistencyTests(unittest.TestCase):
    def run_submit(self, slicer, project=True):
        preset, project_bytes, filename = fixture_pair(slicer)
        client = SubmitClient(slicer, preset, project_bytes if project else None)
        service = SubmissionEnrichment(client)
        with patch.object(service, "process_candidate", return_value=candidate(preset, filename)):
            result = service.enrich_submission("S1", record=client.submission)
        return client, result

    def test_submit_without_preview_writes_ready_for_all_six_slicers(self):
        for slicer in ("BambuStudio", "CrealityPrint", "ElegooSlicer", "OrcaSlicer", "SnapmakerOrcaSlicer", "PrusaSlicer"):
            client, result = self.run_submit(slicer)
            payload = json.loads(client.updates[-1]["consistency_report"])
            self.assertEqual(result.status, "READY_FOR_REVIEW", slicer)
            self.assertEqual(payload["status"], "READY", slicer)

    def test_submit_without_3mf_clears_previous_preview_report(self):
        client, _result = self.run_submit("BambuStudio", project=False)
        self.assertEqual(client.updates[-1]["consistency_report"], "")

    def test_submit_recomputes_report_from_current_project(self):
        preset, project, _filename = fixture_pair("BambuStudio")
        client = SubmitClient("BambuStudio", preset, project)
        client.submission["fields"]["consistency_report"] = json.dumps({"status": "READY", "marker": "old"})
        service = SubmissionEnrichment(client)

        def validator(_preset, current_project):
            return {"schema_version": "p9b2.consistency.v1", "marker": str(len(current_project.content))}

        with patch.object(service, "process_candidate", return_value=candidate(preset)):
            with patch("preset_worker.services.consistency_preview.validate_bambu_consistency", validator):
                service.enrich_submission("S1")
        payload = json.loads(client.updates[-1]["consistency_report"])
        self.assertEqual(payload["report"]["marker"], str(len(project)))
        self.assertNotIn("old", client.updates[-1]["consistency_report"])

    def test_invalid_project_and_validator_exception_do_not_block_native_result(self):
        preset, project, _filename = fixture_pair("BambuStudio")
        for project_bytes, patcher in (
            (b"not a 3mf", None),
            (project, patch("preset_worker.services.consistency_preview.validate_bambu_consistency", lambda *_: (_ for _ in ()).throw(ValueError("secret")))),
        ):
            client = SubmitClient("BambuStudio", preset, project_bytes)
            service = SubmissionEnrichment(client)
            with patch.object(service, "process_candidate", return_value=candidate(preset)):
                if patcher is None:
                    service.enrich_submission("S1")
                else:
                    with patcher:
                        service.enrich_submission("S1", record=client.submission)
            self.assertEqual(client.updates[-1]["status"], "READY_FOR_REVIEW")
            self.assertEqual(json.loads(client.updates[-1]["consistency_report"])["status"], "ERROR")

    def test_native_failure_clears_previous_report(self):
        preset, project, _filename = fixture_pair("BambuStudio")
        client = SubmitClient("BambuStudio", preset, project)
        client.submission["fields"]["consistency_report"] = '{"status":"READY"}'
        client.files["preset"] = b"not-json"
        with self.assertRaises(ValidationFailure):
            SubmissionEnrichment(client).enrich_submission("S1", record=client.submission)
        self.assertEqual(client.updates[-1]["consistency_report"], "")

    def test_formal_report_write_failure_does_not_preserve_old_ready(self):
        preset, project, _filename = fixture_pair("BambuStudio")
        client = SubmitClient("BambuStudio", preset, project, failures=1)
        service = SubmissionEnrichment(client)
        with patch.object(service, "process_candidate", return_value=candidate(preset)):
            service.enrich_submission("S1", record=client.submission)
        self.assertEqual(len(client.updates), 1)
        self.assertEqual(json.loads(client.updates[0]["consistency_report"])["status"], "ERROR")


if __name__ == "__main__":
    unittest.main()
