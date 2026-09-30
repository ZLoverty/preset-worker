import json
import unittest
from pathlib import Path

from preset_worker.diff import ChangeType, DiffCategory, UnifiedDiff
from preset_worker.services.enrichment import SubmissionEnrichment
from preset_worker.slicers import Artifact, CrealityPrintProcessor, ProcessingContext
from preset_worker.slicers.registry import default_processor_registry


FIXTURE_DIR = Path(__file__).parent / "fixtures/slicers/creality_print/reconnaissance"
SOURCE = FIXTURE_DIR / "source_original.json"
EXPECTED = FIXTURE_DIR / "canonical_expected.json"


class WorkflowClient:
    submission_table_id = "submission"
    preset_table_id = "preset"
    version_table_id = "version"

    def __init__(self, *, with_base=False):
        self.submission = {
            "record_id": "submission-record",
            "fields": {
                "status": "VALIDATING",
                "submission_id": "S1",
                "pi_code": [{"text": "L2002CF"}],
                "printer": [{"text": "BBL P2S"}],
                "slicer": [{"text": "CrealityPrint"}],
                "method_version": "method-7.4",
                "preset_key": "L2002CF | BBL P2S | CrealityPrint",
                "preset data": [{"file_token": "uploaded", "name": "pla_test.json"}],
            },
        }
        self.files = {"uploaded": SOURCE.read_bytes(), "base": SOURCE.read_bytes()}
        self.presets = []
        self.versions = []
        if with_base:
            self.presets = [{
                "record_id": "preset-record",
                "fields": {
                    "preset_key": "L2002CF | BBL P2S | CrealityPrint",
                    "current_version_id": [{"text": "CP@v1"}],
                },
            }]
            self.versions = [{
                "record_id": "version-record",
                "fields": {
                    "version_id": "CP@v1",
                    "version_no": 1,
                    "canonical_json": [{"file_token": "base", "name": "base.json"}],
                },
            }]

    def get_submission(self, _submission_id):
        return self.submission

    def list_records(self, table_id):
        return {
            self.preset_table_id: self.presets,
            self.version_table_id: self.versions,
        }[table_id]

    def download_attachment(self, attachment):
        return self.files[attachment["file_token"]]

    def upload_attachment(self, _filename, content):
        self.files["canonical"] = content
        return {"file_token": "canonical"}

    def update_submission(self, _record_id, fields):
        self.submission["fields"].update(fields)


class CrealityPrintProcessorTests(unittest.TestCase):
    def setUp(self):
        self.processor = CrealityPrintProcessor()
        self.context = ProcessingContext("L2002CF", "BBL P2S", "CrealityPrint", "method-7.4")
        self.source = Artifact(SOURCE.read_bytes(), "pla_test.json", "application/json")

    def test_is_registered_and_independent(self):
        registry = default_processor_registry()
        self.assertIsInstance(registry.require("CrealityPrint"), CrealityPrintProcessor)
        self.assertIsNot(type(registry.require("CrealityPrint")), type(registry.require("BambuStudio")))
        self.assertIsNot(type(registry.require("CrealityPrint")), type(registry.require("OrcaSlicer")))

    def test_real_fixture_canonicalization_matches_expected(self):
        result = self.processor.process(self.source, self.context)
        self.assertTrue(result.validation_result.valid)
        self.assertEqual(result.canonical_artifact.filename, "L2002CF @BBL P2S.json")
        self.assertEqual(json.loads(result.canonical_artifact.content), json.loads(EXPECTED.read_bytes()))

    def test_minimal_mutation_preserves_native_and_unknown_fields(self):
        source = json.loads(SOURCE.read_bytes())
        source["future_unknown_field"] = {"enabled": True}
        source_artifact = Artifact(json.dumps(source).encode(), "source.json")
        canonical = json.loads(self.processor.process(source_artifact, self.context).canonical_artifact.content)
        self.assertEqual(canonical["name"], "L2002CF @BBL P2S")
        self.assertEqual(canonical["pm_method_version"], "method-7.4")
        self.assertEqual(canonical["future_unknown_field"], {"enabled": True})
        for field in ("filament_settings_id", "base_id", "inherits", "fan_cooling_layer_time", "nozzle_temperature", "nozzle_temperature_initial_layer"):
            self.assertEqual(canonical[field], source[field])

    def test_stale_source_method_version_is_overridden(self):
        source = json.loads(SOURCE.read_bytes())
        source["pm_method_version"] = "OLD"
        canonical = json.loads(self.processor.process(Artifact(json.dumps(source).encode(), "source.json"), self.context).canonical_artifact.content)
        self.assertEqual(canonical["pm_method_version"], self.context.pm_method_version)

    def test_validation_rejects_non_filament_creality_preset(self):
        wrong_type = {"name": "process", "version": "26.8.4.20", "inherits": "x"}
        result = self.processor.process(Artifact(json.dumps(wrong_type).encode(), "wrong.json"), self.context)
        self.assertFalse(result.validation_result.valid)
        self.assertTrue(any("filament_settings_id" in error for error in result.validation_result.errors))

    def test_validation_rejects_malformed_json(self):
        with self.assertRaises(ValueError):
            self.processor.process(Artifact(b"not-json", "bad.json"), self.context)

    def test_diff_covers_parameter_unknown_system_and_null_missing(self):
        base = json.loads(SOURCE.read_bytes())
        candidate = json.loads(SOURCE.read_bytes())
        candidate["nozzle_temperature"] = ["235"]
        candidate["new_parameter"] = "new"
        candidate["pm_method_version"] = "new-method"
        candidate["inherits"] = None
        del candidate["base_id"]
        result = self.processor.diff(
            Artifact(json.dumps(base).encode(), "base.json"),
            Artifact(json.dumps(candidate).encode(), "candidate.json"),
            self.context,
        )
        self.assertIsInstance(result, UnifiedDiff)
        changes = {change.path: change for change in result.changes}
        self.assertEqual(changes["nozzle_temperature[0]"].category, DiffCategory.IMPORTANT_PARAMETER)
        self.assertEqual(changes["new_parameter"].change_type, ChangeType.ADDED)
        self.assertEqual(changes["pm_method_version"].category, DiffCategory.SYSTEM_METADATA)
        self.assertEqual(changes["inherits"].change_type, ChangeType.MODIFIED)
        self.assertIsNone(changes["inherits"].new_value)
        self.assertEqual(changes["base_id"].change_type, ChangeType.REMOVED)
        self.assertEqual(tuple(change.path for change in result.changes), tuple(sorted(change.path for change in result.changes)))

    def test_diff_is_deterministic(self):
        candidate = json.loads(SOURCE.read_bytes())
        candidate["z_unknown"] = 1
        candidate["a_unknown"] = 2
        first = self.processor.diff(self.source, Artifact(json.dumps(candidate).encode(), "candidate.json"), self.context)
        second = self.processor.diff(self.source, Artifact(json.dumps(candidate).encode(), "candidate.json"), self.context)
        self.assertEqual(first, second)


class CrealityPrintWorkflowTests(unittest.TestCase):
    def test_generic_workflow_create_uses_opaque_canonical_artifact(self):
        client = WorkflowClient()
        result = SubmissionEnrichment(client).process_candidate(client.submission, "S1")
        self.assertEqual(result.operation, "CREATE")
        self.assertEqual(result.canonical_artifact.filename, "L2002CF @BBL P2S.json")
        canonical = json.loads(result.canonical_artifact.content)
        self.assertEqual(canonical["name"], "L2002CF @BBL P2S")
        self.assertEqual(canonical["pm_method_version"], "method-7.4")
        self.assertEqual(result.diff, UnifiedDiff.empty())

    def test_generic_workflow_update_passes_base_to_creality_diff(self):
        client = WorkflowClient(with_base=True)
        result = SubmissionEnrichment(client).process_candidate(client.submission, "S1")
        self.assertEqual(result.operation, "UPDATE")
        self.assertEqual(result.base_version_id, "CP@v1")
        self.assertEqual([change.path for change in result.diff.changes], ["name", "pm_method_version"])
        self.assertTrue(all(change.category is DiffCategory.SYSTEM_METADATA for change in result.diff.changes))


if __name__ == "__main__":
    unittest.main()
