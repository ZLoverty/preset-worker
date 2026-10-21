import io
import json
import unittest
import zipfile
from pathlib import Path

from preset_worker.slicers.contracts import Artifact
from preset_worker.three_mf import validate_prusa_slicer_consistency
from preset_worker.three_mf.prusa_parser import parse_prusa_3mf


BASE = Path("tests/fixtures/slicers/prusa_slicer")


class P9D4PrusaTests(unittest.TestCase):
    def pair(self, filename="pla_test.ini"):
        return (
            Artifact((BASE / filename).read_bytes(), filename, "text/plain"),
            Artifact((BASE / "prusa.3mf").read_bytes(), "prusa.3mf", "model/3mf"),
        )

    def test_real_fixture_parses_native_project_format(self):
        snapshot = parse_prusa_3mf((BASE / "prusa.3mf").read_bytes())
        self.assertIn("Metadata/Slic3r_PE.config", snapshot.entries)
        self.assertEqual([slot.settings_id for slot in snapshot.filament_slots], [
            "pla_test", "03_custom_metadata", "03_custom_metadata", "03_custom_metadata",
        ])
        self.assertEqual(snapshot.settings["temperature"].values, ["230", "230", "230", "230"])
        self.assertEqual(snapshot.settings["filament_settings_id"].values[0], "pla_test")
        self.assertEqual(snapshot.settings["temperature"].source_path, "Metadata/Slic3r_PE.config")

    def test_real_fixture_has_unique_filename_identity_and_six_matches(self):
        preset, project = self.pair()
        report = validate_prusa_slicer_consistency(preset, project)
        self.assertEqual(report["schema_version"], "p9b2.consistency.v1")
        self.assertEqual(report["source"]["slicer"], "PrusaSlicer")
        self.assertEqual(report["selection"]["status"], "UNIQUE")
        self.assertEqual(report["selection"]["filament_slot_id"], 1)
        self.assertEqual(report["selection"]["matching_slot_ids"], [1])
        self.assertEqual(report["selection"]["identity_strategy"], "FILENAME_STEM_EXACT_PROJECT_PROFILE")
        self.assertEqual(report["summary"], {"UNRESOLVED": 2, "MATCH": 6})
        self.assertTrue(all(item["runtime_effective_status"] == "NOT_ESTABLISHED" for item in report["comparisons"]))
        temperature = next(item for item in report["comparisons"] if item["parameter_id"] == "nozzle_temperature")
        self.assertEqual(temperature["preset"]["source_path"], "ini.temperature")
        self.assertEqual(temperature["project"]["source_path"], "Metadata/Slic3r_PE.config:temperature")
        row = next(row for row in report["comparison_rows"] if row["parameter_id"] == "nozzle_temperature")
        self.assertEqual(row["status"], "MATCH")
        self.assertEqual(row["project_source_path"], "Metadata/Slic3r_PE.config:temperature[0]")

    def test_filename_stem_must_match_project_profile(self):
        preset, project = self.pair()
        report = validate_prusa_slicer_consistency(
            Artifact(preset.content, "other.ini", preset.media_type), project,
        )
        self.assertEqual(report["selection"]["status"], "UNRESOLVED")
        self.assertTrue(all(item["status"] == "UNRESOLVED" for item in report["comparisons"]))

    def test_unverified_mappings_remain_unresolved(self):
        preset, project = self.pair()
        report = validate_prusa_slicer_consistency(preset, project)
        statuses = {item["parameter_id"]: item["status"] for item in report["comparisons"]}
        self.assertEqual(statuses["filament_flow_ratio"], "UNRESOLVED")
        self.assertEqual(statuses["filament_max_volumetric_speed"], "UNRESOLVED")

    def test_selected_slot_mismatch_is_reported(self):
        preset, project = self.pair()
        source = preset.content.replace(b"temperature = 230", b"temperature = 231")
        report = validate_prusa_slicer_consistency(
            Artifact(source, preset.filename, preset.media_type), project,
        )
        item = next(item for item in report["comparisons"] if item["parameter_id"] == "nozzle_temperature")
        self.assertEqual(item["status"], "MISMATCH")

    def test_missing_project_member_is_explicit(self):
        preset, _ = self.pair()
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("Metadata/Slic3r_PE_model.config", "<config/>")
        report = validate_prusa_slicer_consistency(
            preset, Artifact(output.getvalue(), "missing.3mf", "model/3mf"),
        )
        self.assertTrue(report["errors"])
        self.assertEqual(report["selection"]["status"], "UNRESOLVED")

    def test_malformed_project_config_is_explicit(self):
        preset, _ = self.pair()
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("Metadata/Slic3r_PE.config", b"\xff\xfe")
        report = validate_prusa_slicer_consistency(
            preset, Artifact(output.getvalue(), "bad.3mf", "model/3mf"),
        )
        self.assertTrue(report["errors"])

    def test_unsafe_zip_is_rejected(self):
        preset, _ = self.pair()
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("../escape", b"unsafe")
        report = validate_prusa_slicer_consistency(
            preset, Artifact(output.getvalue(), "unsafe.3mf", "model/3mf"),
        )
        self.assertTrue(any("3MF" in error for error in report["errors"]))

    def test_missing_preset_parameter_stays_missing(self):
        preset, project = self.pair()
        source = preset.content.replace(b"max_fan_speed = 100\n", b"")
        report = validate_prusa_slicer_consistency(
            Artifact(source, preset.filename, preset.media_type), project,
        )
        item = next(item for item in report["comparisons"] if item["parameter_id"] == "fan_max_speed")
        self.assertEqual(item["status"], "MISSING_IN_PRESET")


if __name__ == "__main__":
    unittest.main()
