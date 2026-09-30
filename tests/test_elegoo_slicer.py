import json
import unittest
from pathlib import Path

from preset_worker.diff import ChangeType, DiffCategory, UnifiedDiff
from preset_worker.services.enrichment import SubmissionEnrichment
from preset_worker.slicers import Artifact, ElegooSlicerProcessor, ProcessingContext
from preset_worker.slicers.registry import default_processor_registry


FIXTURE_DIR = Path(__file__).parent / "fixtures/slicers/elegoo_slicer/reconnaissance"
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
                "slicer": [{"text": "ElegooSlicer"}],
                "method_version": "method-7.5",
                "preset_key": "L2002CF | BBL P2S | ElegooSlicer",
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
                    "preset_key": "L2002CF | BBL P2S | ElegooSlicer",
                    "current_version_id": [{"text": "ES@v1"}],
                },
            }]
            self.versions = [{
                "record_id": "version-record",
                "fields": {
                    "version_id": "ES@v1",
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


class ElegooSlicerProcessorTests(unittest.TestCase):
    def setUp(self):
        self.processor = ElegooSlicerProcessor()
        self.context = ProcessingContext("L2002CF", "BBL P2S", "ElegooSlicer", "method-7.5")
        self.source = Artifact(SOURCE.read_bytes(), "pla_test.json", "application/json")

    def test_registered_and_independent(self):
        registry = default_processor_registry()
        self.assertIsInstance(registry.require("ElegooSlicer"), ElegooSlicerProcessor)
        self.assertIsNot(type(registry.require("ElegooSlicer")), type(registry.require("CrealityPrint")))
        self.assertIsNot(type(registry.require("ElegooSlicer")), type(registry.require("OrcaSlicer")))

    def test_real_fixture_golden_canonicalization(self):
        result = self.processor.process(self.source, self.context)
        self.assertTrue(result.validation_result.valid)
        self.assertEqual(result.canonical_artifact.filename, "L2002CF @BBL P2S.json")
        self.assertEqual(json.loads(result.canonical_artifact.content), json.loads(EXPECTED.read_bytes()))

    def test_minimal_mutation_and_unknown_field_preservation(self):
        source = json.loads(SOURCE.read_bytes())
        source["future_unknown_field"] = {"enabled": True}
        canonical = json.loads(self.processor.process(Artifact(json.dumps(source).encode(), "source.json"), self.context).canonical_artifact.content)
        self.assertEqual(canonical["name"], "L2002CF @BBL P2S")
        self.assertEqual(canonical["pm_method_version"], "method-7.5")
        self.assertEqual(canonical["future_unknown_field"], {"enabled": True})
        for field in ("fan_cooling_layer_time", "fan_min_speed", "filament_extruder_variant", "filament_settings_id", "inherits", "nozzle_temperature", "nozzle_temperature_initial_layer", "version"):
            self.assertEqual(canonical[field], source[field])

    def test_pm_method_version_is_injected_and_stale_value_is_replaced(self):
        source = json.loads(SOURCE.read_bytes())
        first = json.loads(self.processor.process(Artifact(json.dumps(source).encode(), "source.json"), self.context).canonical_artifact.content)
        source["pm_method_version"] = "OLD"
        second = json.loads(self.processor.process(Artifact(json.dumps(source).encode(), "source.json"), self.context).canonical_artifact.content)
        self.assertEqual(first["pm_method_version"], "method-7.5")
        self.assertEqual(second["pm_method_version"], "method-7.5")

    def test_validation_rejects_unrelated_preset(self):
        wrong = {"name": "process", "version": "1.5.3.5", "inherits": "x"}
        result = self.processor.process(Artifact(json.dumps(wrong).encode(), "wrong.json"), self.context)
        self.assertFalse(result.validation_result.valid)
        self.assertTrue(any("filament_settings_id" in error for error in result.validation_result.errors))

    def test_invalid_json_is_rejected(self):
        with self.assertRaises(ValueError):
            self.processor.process(Artifact(b"not-json", "bad.json"), self.context)

    def test_diff_categories_null_missing_and_stable_order(self):
        base = json.loads(SOURCE.read_bytes())
        candidate = json.loads(SOURCE.read_bytes())
        candidate["nozzle_temperature"] = ["235"]
        candidate["future_unknown"] = "new"
        candidate["pm_method_version"] = "new-method"
        candidate["inherits"] = None
        del candidate["fan_min_speed"]
        result = self.processor.diff(
            Artifact(json.dumps(base).encode(), "base.json"),
            Artifact(json.dumps(candidate).encode(), "candidate.json"),
            self.context,
        )
        self.assertIsInstance(result, UnifiedDiff)
        changes = {change.path: change for change in result.changes}
        self.assertEqual(changes["nozzle_temperature[0]"].category, DiffCategory.IMPORTANT_PARAMETER)
        self.assertEqual(changes["future_unknown"].category, DiffCategory.OTHER_PARAMETER)
        self.assertEqual(changes["future_unknown"].change_type, ChangeType.ADDED)
        self.assertEqual(changes["pm_method_version"].category, DiffCategory.SYSTEM_METADATA)
        self.assertEqual(changes["inherits"].new_value, None)
        self.assertEqual(changes["fan_min_speed[0]"].change_type, ChangeType.REMOVED)
        self.assertEqual(tuple(change.path for change in result.changes), tuple(sorted(change.path for change in result.changes)))

    def test_diff_is_deterministic(self):
        candidate = json.loads(SOURCE.read_bytes())
        candidate["z_unknown"] = 1
        candidate["a_unknown"] = 2
        first = self.processor.diff(self.source, Artifact(json.dumps(candidate).encode(), "candidate.json"), self.context)
        second = self.processor.diff(self.source, Artifact(json.dumps(candidate).encode(), "candidate.json"), self.context)
        self.assertEqual(first, second)


class ElegooSlicerWorkflowTests(unittest.TestCase):
    def test_create_selects_elegoo_and_keeps_artifact_opaque(self):
        client = WorkflowClient()
        result = SubmissionEnrichment(client).process_candidate(client.submission, "S1")
        self.assertEqual(result.operation, "CREATE")
        self.assertEqual(result.canonical_artifact.filename, "L2002CF @BBL P2S.json")
        canonical = json.loads(result.canonical_artifact.content)
        self.assertEqual(canonical["name"], "L2002CF @BBL P2S")
        self.assertEqual(canonical["pm_method_version"], "method-7.5")
        self.assertEqual(result.diff, UnifiedDiff.empty())

    def test_update_passes_base_to_elegoo_diff(self):
        client = WorkflowClient(with_base=True)
        result = SubmissionEnrichment(client).process_candidate(client.submission, "S1")
        self.assertEqual(result.operation, "UPDATE")
        self.assertEqual(result.base_version_id, "ES@v1")
        self.assertEqual([change.path for change in result.diff.changes], ["name", "pm_method_version"])
        self.assertTrue(all(change.category is DiffCategory.SYSTEM_METADATA for change in result.diff.changes))


if __name__ == "__main__":
    unittest.main()
