import json
import unittest
from pathlib import Path

from preset_worker.diff import DiffCategory
from preset_worker.slicers import Artifact, FlashStudioProcessor, ProcessingContext
from preset_worker.slicers.registry import default_processor_registry
from preset_worker.slicers.contracts import canonical_slicer_id


FIXTURE = Path("tests/fixtures/slicers/flash_studio")
CONTEXT = ProcessingContext("PI", "Creator 5", "FlashStudio", "method-1")


class FlashStudioTests(unittest.TestCase):
    def setUp(self):
        self.processor = FlashStudioProcessor()
        self.artifact = Artifact(
            (FIXTURE / "pla ff creator 5.json").read_bytes(),
            "pla ff creator 5.json",
            "application/json",
        )

    def test_fixture_is_valid_and_registered_as_independent_identity(self):
        source = self.processor.parse(self.artifact, CONTEXT)
        self.assertTrue(self.processor.validate_source(source, CONTEXT).valid)
        registry = default_processor_registry()
        self.assertIs(registry.require("FlashStudio").__class__, FlashStudioProcessor)
        self.assertIsNot(registry.require("FlashStudio"), registry.require("OrcaSlicer"))
        self.assertEqual(canonical_slicer_id("Flash Studio"), "FlashStudio")

    def test_processing_preserves_native_fields_and_applies_policy(self):
        result = self.processor.process(self.artifact, CONTEXT)
        self.assertTrue(result.validation_result.valid)
        canonical = json.loads(result.canonical_artifact.content)
        self.assertEqual(canonical["name"], "PI @Creator 5")
        self.assertEqual(canonical["pm_method_version"], "method-1")
        self.assertIn("hot_plate_temp", canonical)
        self.assertEqual(result.canonical_artifact.filename, "PI @Creator 5.json")

    def test_native_diff_classifies_proven_flash_fields(self):
        candidate = json.loads(self.artifact.content)
        candidate["nozzle_temperature"] = [225, 215]
        candidate_artifact = Artifact(
            json.dumps(candidate).encode(), "candidate.json", "application/json"
        )
        diff = self.processor.diff(self.artifact, candidate_artifact, CONTEXT)
        change = next(item for item in diff.changes if item.path == "nozzle_temperature[0]")
        self.assertEqual(change.category, DiffCategory.IMPORTANT_PARAMETER)

    def test_version_is_required_for_flash_studio_native_presets(self):
        source = self.processor.parse(self.artifact, CONTEXT)
        source.pop("version")
        validation = self.processor.validate_source(source, CONTEXT)
        self.assertFalse(validation.valid)
        self.assertIn("version", " ".join(validation.errors))


if __name__ == "__main__":
    unittest.main()
