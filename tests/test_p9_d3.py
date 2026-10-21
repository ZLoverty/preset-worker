import io
import json
import unittest
import zipfile
from pathlib import Path

from preset_worker.slicers.contracts import Artifact
from preset_worker.three_mf import validate_orca_consistency, validate_snapmaker_orca_consistency


FIXTURES = Path("tests/fixtures/slicers")


class P9D3AdapterTests(unittest.TestCase):
    def pair(self, directory: str, project_name: str):
        base = FIXTURES / directory
        preset = next(path for path in base.glob("*.json") if path.name != "manifest.json")
        return (
            Artifact(preset.read_bytes(), preset.name, "application/json"),
            Artifact((base / project_name).read_bytes(), project_name, "model/3mf"),
        )

    def test_real_orca_duplicate_identity_selects_lowest_equivalent_slot(self):
        preset, project = self.pair("orca_slicer", "orca.3mf")
        report = validate_orca_consistency(preset, project)
        self.assertEqual(report["schema_version"], "p9b2.consistency.v1")
        self.assertEqual(report["source"]["slicer"], "OrcaSlicer")
        self.assertEqual(report["selection"]["status"], "UNIQUE")
        self.assertEqual(report["selection"]["matching_slot_ids"], [1, 4])
        self.assertEqual(report["selection"]["filament_slot_id"], 1)
        self.assertIn("MULTIPLE_EQUIVALENT", report["selection"]["evidence"])
        self.assertEqual(report["summary"], {"MISSING_IN_PRESET": 5, "MATCH": 3})
        self.assertTrue(all(item["runtime_effective_status"] == "NOT_ESTABLISHED" for item in report["comparisons"]))
        temperature = next(item for item in report["comparisons"] if item["parameter_id"] == "nozzle_temperature")
        self.assertEqual(temperature["status"], "MATCH")
        self.assertEqual(temperature["project"]["source_path"], "$.nozzle_temperature[0]")
        self.assertEqual(temperature["project"]["original_array"], ["230", "230", "220", "230"])

    def test_real_snapmaker_unique_identity_selects_slot_one(self):
        preset, project = self.pair("orca_slicer_snapmaker", "snapmaker-orca.3mf")
        report = validate_snapmaker_orca_consistency(preset, project)
        self.assertEqual(report["source"]["slicer"], "SnapmakerOrcaSlicer")
        self.assertEqual(report["selection"]["status"], "UNIQUE")
        self.assertEqual(report["selection"]["matching_slot_ids"], [1])
        self.assertEqual(report["selection"]["filament_slot_id"], 1)
        self.assertEqual(report["summary"], {"MISSING_IN_PRESET": 5, "MATCH": 3})
        self.assertNotIn("AMBIGUOUS", report["summary"])

    def test_identity_mismatch_does_not_compare_equal_values(self):
        preset, project = self.pair("orca_slicer_snapmaker", "snapmaker-orca.3mf")
        source = json.loads(preset.content)
        source["filament_settings_id"] = ["not-a-project-slot"]
        report = validate_snapmaker_orca_consistency(
            Artifact(json.dumps(source).encode(), preset.filename, preset.media_type), project,
        )
        self.assertEqual(report["selection"]["status"], "UNRESOLVED")
        self.assertTrue(all(item["status"] == "UNRESOLVED" for item in report["comparisons"]))
        self.assertTrue(all(row["status"] == "UNRESOLVED" for row in report["comparison_rows"]))

    def test_missing_identity_is_rejected_by_native_orca_validation(self):
        preset, project = self.pair("orca_slicer", "orca.3mf")
        source = json.loads(preset.content)
        del source["filament_settings_id"]
        report = validate_orca_consistency(
            Artifact(json.dumps(source).encode(), preset.filename, preset.media_type), project,
        )
        self.assertEqual(report["preset"]["status"], "invalid_user_artifact")
        self.assertTrue(report["errors"])

    def test_mismatch_at_selected_slot_is_reported(self):
        preset, project = self.pair("orca_slicer_snapmaker", "snapmaker-orca.3mf")
        source = json.loads(preset.content)
        source["nozzle_temperature"] = ["231"]
        report = validate_snapmaker_orca_consistency(
            Artifact(json.dumps(source).encode(), preset.filename, preset.media_type), project,
        )
        item = next(item for item in report["comparisons"] if item["parameter_id"] == "nozzle_temperature")
        self.assertEqual(item["status"], "MISMATCH")
        row = next(row for row in report["comparison_rows"] if row["parameter_id"] == "nozzle_temperature")
        self.assertEqual(row["status"], "MISMATCH")
        self.assertEqual(row["project_source_path"], "$.nozzle_temperature[0]")

    def test_missing_project_member_is_explicit(self):
        preset, _ = self.pair("orca_slicer_snapmaker", "snapmaker-orca.3mf")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("Metadata/model_settings.config", "<config/>")
        report = validate_orca_consistency(
            preset, Artifact(output.getvalue(), "missing.3mf", "model/3mf"),
        )
        self.assertTrue(report["errors"])
        self.assertEqual(report["selection"]["status"], "UNRESOLVED")

    def test_malformed_project_json_is_explicit(self):
        preset, _ = self.pair("orca_slicer", "orca.3mf")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("Metadata/project_settings.config", b"broken")
        report = validate_orca_consistency(
            preset, Artifact(output.getvalue(), "broken.3mf", "model/3mf"),
        )
        self.assertTrue(report["errors"])
        self.assertEqual(report["selection"]["status"], "UNRESOLVED")

    def test_unsafe_zip_is_rejected(self):
        preset, _ = self.pair("orca_slicer_snapmaker", "snapmaker-orca.3mf")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("../escape", b"unsafe")
        report = validate_snapmaker_orca_consistency(
            preset, Artifact(output.getvalue(), "unsafe.3mf", "model/3mf"),
        )
        self.assertTrue(any("3MF" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
