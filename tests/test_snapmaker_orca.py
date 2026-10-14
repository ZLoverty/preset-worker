import json
import unittest
from pathlib import Path

from preset_worker.diff import ChangeType, DiffCategory, UnifiedDiff
from preset_worker.services.enrichment import SubmissionEnrichment
from preset_worker.slicers import Artifact, ProcessingContext, SnapmakerOrcaSlicerProcessor
from preset_worker.slicers.registry import default_processor_registry


FIXTURE_DIR = Path(__file__).parent / "fixtures/slicers/orca_slicer_snapmaker/reconnaissance"
SOURCE = FIXTURE_DIR / "source_original.json"
UPSTREAM_SOURCE = Path(__file__).parent / "fixtures/slicers/orca_slicer/valid/pla_test.json"


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
                "printer": [{"text": "Snapmaker U1"}],
                "slicer": [{"text": "SnapmakerOrcaSlicer"}],
                "method_version": "method-7.7",
                "preset_key": "L2002CF | Snapmaker U1 | SnapmakerOrcaSlicer",
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
                    "preset_key": "L2002CF | Snapmaker U1 | SnapmakerOrcaSlicer",
                    "current_version_id": [{"text": "SM@v1"}],
                },
            }]
            self.versions = [{
                "record_id": "version-record",
                "fields": {
                    "version_id": "SM@v1",
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


class SnapmakerOrcaProcessorTests(unittest.TestCase):
    def setUp(self):
        self.processor = SnapmakerOrcaSlicerProcessor()
        self.context = ProcessingContext("L2002CF", "Snapmaker U1", "SnapmakerOrcaSlicer", "method-7.7")
        self.source = Artifact(SOURCE.read_bytes(), "pla_test.json", "application/json")

    def test_distinct_processor_and_registry_identity(self):
        registry = default_processor_registry()
        upstream = registry.require("OrcaSlicer")
        snapmaker = registry.require("SnapmakerOrcaSlicer")
        self.assertIsInstance(snapmaker, SnapmakerOrcaSlicerProcessor)
        self.assertNotEqual(upstream.slicer_id, snapmaker.slicer_id)
        self.assertIsNot(upstream, snapmaker)

    def test_real_snapmaker_golden_preserves_native_fields(self):
        result = self.processor.process(self.source, self.context)
        self.assertTrue(result.validation_result.valid)
        canonical = json.loads(result.canonical_artifact.content)
        self.assertEqual(canonical["name"], "L2002CF @Snapmaker U1")
        self.assertEqual(canonical["pm_method_version"], "method-7.7")
        self.assertEqual(canonical["filament_settings_id"], ["pla_test"])
        self.assertEqual(canonical["inherits"], "Snapmaker PLA")
        self.assertEqual(canonical["fan_cooling_layer_time"], ["50"])
        self.assertEqual(canonical["nozzle_temperature"], ["230"])
        self.assertEqual(canonical["nozzle_temperature_initial_layer"], ["230"])

    def test_unknown_fields_and_stale_metadata_are_preserved_or_replaced(self):
        source = json.loads(SOURCE.read_bytes())
        source["snapmaker_future_field"] = {"enabled": True}
        source["pm_method_version"] = "OLD"
        canonical = json.loads(self.processor.process(Artifact(json.dumps(source).encode(), "source.json"), self.context).canonical_artifact.content)
        self.assertEqual(canonical["snapmaker_future_field"], {"enabled": True})
        self.assertEqual(canonical["pm_method_version"], "method-7.7")
        self.assertEqual(canonical["inherits"], "Snapmaker PLA")

    def test_missing_metadata_is_injected(self):
        canonical = json.loads(self.processor.process(self.source, self.context).canonical_artifact.content)
        self.assertEqual(canonical["pm_method_version"], self.context.pm_method_version)

    def test_cross_compatible_upstream_fixture_is_accepted(self):
        result = self.processor.process(Artifact(UPSTREAM_SOURCE.read_bytes(), "upstream.json"), self.context)
        self.assertTrue(result.validation_result.valid)
        canonical = json.loads(result.canonical_artifact.content)
        self.assertEqual(canonical["inherits"], "Generic PLA @System")

    def test_invalid_unrelated_preset_is_rejected(self):
        wrong = Artifact(b'{"type":"process","name":"x"}', "wrong.json")
        result = self.processor.process(wrong, self.context)
        self.assertFalse(result.validation_result.valid)

    def test_diff_covers_snapmaker_parameters_metadata_unknown_and_null(self):
        base = json.loads(SOURCE.read_bytes())
        candidate = json.loads(SOURCE.read_bytes())
        candidate["nozzle_temperature"] = ["235"]
        candidate["future_unknown"] = "new"
        candidate["pm_method_version"] = "new-method"
        candidate["inherits"] = None
        del candidate["filament_settings_id"]
        result = self.processor.diff(
            Artifact(json.dumps(base).encode(), "base.json"),
            Artifact(json.dumps(candidate).encode(), "candidate.json"),
            self.context,
        )
        changes = {change.path: change for change in result.changes}
        self.assertEqual(changes["nozzle_temperature[0]"].category, DiffCategory.IMPORTANT_PARAMETER)
        self.assertEqual(changes["future_unknown"].category, DiffCategory.OTHER_PARAMETER)
        self.assertEqual(changes["pm_method_version"].category, DiffCategory.SYSTEM_METADATA)
        self.assertEqual(changes["inherits"].new_value, None)
        self.assertEqual(changes["filament_settings_id[0]"].change_type, ChangeType.REMOVED)
        self.assertEqual(tuple(change.path for change in result.changes), tuple(sorted(change.path for change in result.changes)))

    def test_diff_is_deterministic(self):
        candidate = json.loads(SOURCE.read_bytes())
        candidate["z_unknown"] = 1
        candidate["a_unknown"] = 2
        first = self.processor.diff(self.source, Artifact(json.dumps(candidate).encode(), "candidate.json"), self.context)
        second = self.processor.diff(self.source, Artifact(json.dumps(candidate).encode(), "candidate.json"), self.context)
        self.assertEqual(first, second)

    def test_shared_core_rules_match_upstream_without_merging_identity(self):
        upstream = default_processor_registry().require("OrcaSlicer")
        upstream_context = ProcessingContext("L2002CF", "Snapmaker U1", "OrcaSlicer", "method-7.7")
        upstream_result = upstream.process(Artifact(UPSTREAM_SOURCE.read_bytes(), "upstream.json"), upstream_context)
        snap_result = self.processor.process(Artifact(UPSTREAM_SOURCE.read_bytes(), "upstream.json"), self.context)
        upstream_json = json.loads(upstream_result.canonical_artifact.content)
        snap_json = json.loads(snap_result.canonical_artifact.content)
        upstream_json.pop("name")
        snap_json.pop("name")
        self.assertEqual(upstream_json, snap_json)
        self.assertNotEqual(upstream.slicer_id, self.processor.slicer_id)


class SnapmakerOrcaWorkflowTests(unittest.TestCase):
    def test_create_selects_distinct_snapmaker_processor(self):
        client = WorkflowClient()
        result = SubmissionEnrichment(client).process_candidate(client.submission, "S1")
        self.assertEqual(result.operation, "CREATE")
        self.assertEqual(result.canonical_artifact.filename, "L2002CF @Snapmaker U1.json")
        canonical = json.loads(result.canonical_artifact.content)
        self.assertEqual(canonical["name"], "L2002CF @Snapmaker U1")
        self.assertEqual(canonical["pm_method_version"], "method-7.7")
        self.assertTrue(result.diff.changes)
        self.assertTrue(all(change.change_type is ChangeType.ADDED for change in result.diff.changes))

    def test_update_uses_snapmaker_diff_and_namespace(self):
        client = WorkflowClient(with_base=True)
        result = SubmissionEnrichment(client).process_candidate(client.submission, "S1")
        self.assertEqual(result.operation, "UPDATE")
        self.assertEqual(result.base_version_id, "SM@v1")
        self.assertEqual([change.path for change in result.diff.changes], ["name", "pm_method_version"])
        self.assertTrue(all(change.category is DiffCategory.SYSTEM_METADATA for change in result.diff.changes))

    def test_snapmaker_and_upstream_preset_keys_are_distinct(self):
        self.assertNotEqual(
            "L2002CF | Snapmaker U1 | SnapmakerOrcaSlicer",
            "L2002CF | Snapmaker U1 | OrcaSlicer",
        )


if __name__ == "__main__":
    unittest.main()
