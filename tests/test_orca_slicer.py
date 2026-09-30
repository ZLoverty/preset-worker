import json
import unittest
from pathlib import Path

from preset_worker.diff import ChangeType, DiffCategory, UnifiedDiff
from preset_worker.slicers import Artifact, OrcaSlicerProcessor, ProcessingContext
from preset_worker.slicers.registry import default_processor_registry


FIXTURE = Path(__file__).parent / "fixtures/slicers/orca_slicer/valid/filament.json"


class OrcaSlicerProcessorTests(unittest.TestCase):
    def setUp(self):
        self.processor = OrcaSlicerProcessor()
        self.context = ProcessingContext("PI", "Printer", "OrcaSlicer", "method-1")
        self.source = Artifact(FIXTURE.read_bytes(), "source.json", "application/json")

    def test_registered_and_independent(self):
        registry = default_processor_registry()
        self.assertIsInstance(registry.require("OrcaSlicer"), OrcaSlicerProcessor)
        self.assertNotEqual(type(registry.require("BambuStudio")), OrcaSlicerProcessor)

    def test_process_preserves_fields_and_returns_orca_artifact(self):
        processed = self.processor.process(self.source, self.context)
        self.assertTrue(processed.validation_result.valid)
        self.assertEqual(processed.canonical_artifact.filename, "PI @Printer.json")
        canonical = json.loads(processed.canonical_artifact.content)
        self.assertEqual(canonical["name"], "PI @Printer")
        self.assertEqual(canonical["pm_method_version"], "method-1")
        self.assertEqual(canonical["future_unknown_field"], "preserve-me")
        self.assertEqual(canonical["inherits"], "fdm_filament_pla")

    def test_real_gui_export_shape_is_accepted_and_identity_is_updated(self):
        source = Artifact((FIXTURE.parent / "pla_test.json").read_bytes(), "pla_test.json")
        processed = self.processor.process(source, self.context)
        self.assertTrue(processed.validation_result.valid)
        canonical = json.loads(processed.canonical_artifact.content)
        self.assertEqual(canonical["name"], "PI @Printer")
        self.assertEqual(canonical["filament_settings_id"], ["pla_test"])
        self.assertEqual(canonical["nozzle_temperature"], ["230"])

    def test_invalid_or_wrong_preset_is_rejected(self):
        invalid = Artifact(b"not-json", "bad.json")
        with self.assertRaises(ValueError):
            self.processor.process(invalid, self.context)
        wrong_type = Artifact(b'{"type":"process","name":"x"}', "wrong.json")
        result = self.processor.process(wrong_type, self.context)
        self.assertFalse(result.validation_result.valid)

    def test_diff_returns_unified_diff_and_unknown_is_other(self):
        base = Artifact(FIXTURE.read_bytes(), "base.json")
        candidate_data = json.loads(FIXTURE.read_bytes())
        candidate_data["filament_flow_ratio"] = ["1.00"]
        candidate_data["future_unknown_field"] = "changed"
        candidate = Artifact(json.dumps(candidate_data).encode(), "candidate.json")
        result = self.processor.diff(base, candidate, self.context)
        self.assertIsInstance(result, UnifiedDiff)
        changes = {change.path: change for change in result.changes}
        flow_change = next(change for path, change in changes.items() if path.startswith("filament_flow_ratio"))
        self.assertEqual(flow_change.category, DiffCategory.IMPORTANT_PARAMETER)
        self.assertEqual(changes["future_unknown_field"].category, DiffCategory.OTHER_PARAMETER)
        self.assertEqual(changes["future_unknown_field"].change_type, ChangeType.MODIFIED)

    def test_diff_missing_and_null(self):
        base = Artifact(b'{"type":"filament","name":"x"}', "base.json")
        candidate = Artifact(b'{"type":"filament","name":"x","optional":null}', "candidate.json")
        result = self.processor.diff(base, candidate, self.context)
        self.assertEqual(result.changes[0].change_type, ChangeType.ADDED)
        self.assertIsNone(result.changes[0].new_value)

    def test_real_worker_roundtrip_records_orca_dropping_custom_metadata(self):
        worker = json.loads((FIXTURE.parents[1] / "roundtrip/worker_canonical_candidate.json").read_text())
        reexport = json.loads((FIXTURE.parents[1] / "roundtrip/L2002CF @BBL P2S.json").read_text())
        self.assertEqual(worker["name"], reexport["name"])
        self.assertEqual(worker["inherits"], reexport["inherits"])
        self.assertIn("pm_method_version", worker)
        self.assertNotIn("pm_method_version", reexport)


if __name__ == "__main__":
    unittest.main()
