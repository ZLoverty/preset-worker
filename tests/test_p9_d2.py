import io
import json
import unittest
import zipfile
from pathlib import Path

from preset_worker.slicers.contracts import Artifact
from preset_worker.three_mf import validate_creality_consistency, validate_elegoo_consistency


FIXTURES = Path("tests/fixtures/slicers")


def make_project(values=None, identities=("pla_test",)) -> bytes:
    payload = {"filament_settings_id": list(identities), **(values or {
        "filament_flow_ratio": ["1"],
        "filament_max_volumetric_speed": ["12"],
        "nozzle_temperature": ["230"],
        "nozzle_temperature_initial_layer": ["230"],
        "fan_min_speed": ["100"],
        "fan_max_speed": ["100"],
        "fan_cooling_layer_time": ["50"],
        "slow_down_layer_time": ["4"],
    })}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Metadata/project_settings.config", json.dumps(payload))
    return output.getvalue()


class P9D2AdapterTests(unittest.TestCase):
    def artifact_pair(self, slicer: str, project_name: str):
        base = FIXTURES / slicer
        return (
            Artifact((base / "pla_test.json").read_bytes(), "pla_test.json", "application/json"),
            Artifact((base / project_name).read_bytes(), project_name, "model/3mf"),
        )

    def test_real_creality_fixture_report(self):
        preset, project = self.artifact_pair("creality_print", "creality.3mf")
        report = validate_creality_consistency(preset, project)
        self.assertEqual(report["schema_version"], "p9b2.consistency.v1")
        self.assertEqual(report["source"]["slicer"], "CrealityPrint")
        self.assertEqual(report["selection"]["status"], "UNIQUE")
        self.assertEqual(report["selection"]["filament_slot_id"], 1)
        self.assertEqual(report["summary"], {"MISSING_IN_PRESET": 5, "MATCH": 3})
        self.assertEqual(
            {row["parameter_id"] for row in report["comparison_rows"] if row["status"] == "MATCH"},
            {"nozzle_temperature", "nozzle_temperature_initial_layer", "fan_cooling_layer_time"},
        )
        self.assertTrue(all(item["runtime_effective_status"] == "NOT_ESTABLISHED" for item in report["comparisons"]))

    def test_real_elegoo_fixture_report(self):
        preset, project = self.artifact_pair("elegoo_slicer", "elegoo.3mf")
        report = validate_elegoo_consistency(preset, project)
        self.assertEqual(report["schema_version"], "p9b2.consistency.v1")
        self.assertEqual(report["source"]["slicer"], "ElegooSlicer")
        self.assertEqual(report["selection"]["status"], "UNIQUE")
        self.assertEqual(report["selection"]["filament_slot_id"], 1)
        self.assertEqual(report["summary"], {"MISSING_IN_PRESET": 4, "MATCH": 4})
        self.assertEqual(
            {row["parameter_id"] for row in report["comparison_rows"] if row["status"] == "MATCH"},
            {"nozzle_temperature", "nozzle_temperature_initial_layer", "fan_min_speed", "fan_cooling_layer_time"},
        )

    def test_identity_mismatch_is_unresolved(self):
        preset, _ = self.artifact_pair("creality_print", "creality.3mf")
        source = json.loads(preset.content)
        source["filament_settings_id"] = ["not_in_project"]
        report = validate_creality_consistency(
            Artifact(json.dumps(source).encode(), preset.filename, preset.media_type),
            Artifact((FIXTURES / "creality_print/creality.3mf").read_bytes(), "creality.3mf", "model/3mf"),
        )
        self.assertEqual(report["selection"]["status"], "UNRESOLVED")
        self.assertEqual(report["comparisons"][2]["status"], "UNRESOLVED")

    def test_missing_preset_identity_is_rejected_by_native_processor(self):
        preset, project = self.artifact_pair("elegoo_slicer", "elegoo.3mf")
        source = json.loads(preset.content)
        del source["filament_settings_id"]
        report = validate_elegoo_consistency(
            Artifact(json.dumps(source).encode(), preset.filename, preset.media_type), project,
        )
        self.assertEqual(report["source"]["slicer"], "ElegooSlicer")
        self.assertEqual(report["preset"]["status"], "invalid_user_artifact")
        self.assertTrue(report["errors"])

    def test_explicit_mismatch_and_numeric_normalization(self):
        preset, project = self.artifact_pair("creality_print", "creality.3mf")
        source = json.loads(preset.content)
        source["nozzle_temperature"] = ["231"]
        source["fan_cooling_layer_time"] = [50]
        report = validate_creality_consistency(
            Artifact(json.dumps(source).encode(), preset.filename, preset.media_type), project,
        )
        statuses = {item["parameter_id"]: item["status"] for item in report["comparisons"]}
        self.assertEqual(statuses["nozzle_temperature"], "MISMATCH")
        self.assertEqual(statuses["fan_cooling_layer_time"], "MATCH")

    def test_missing_project_settings_is_explicit(self):
        preset, _ = self.artifact_pair("creality_print", "creality.3mf")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("Metadata/model_settings.config", "<config/>")
        report = validate_creality_consistency(
            preset, Artifact(output.getvalue(), "missing.3mf", "model/3mf"),
        )
        self.assertTrue(report["errors"])
        self.assertEqual(report["selection"]["status"], "UNRESOLVED")

    def test_malformed_project_json_is_explicit(self):
        preset, _ = self.artifact_pair("elegoo_slicer", "elegoo.3mf")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("Metadata/project_settings.config", b"not-json")
        report = validate_elegoo_consistency(
            preset, Artifact(output.getvalue(), "bad.3mf", "model/3mf"),
        )
        self.assertTrue(report["errors"])
        self.assertEqual(report["selection"]["status"], "UNRESOLVED")

    def test_unsafe_zip_is_not_bypassed(self):
        preset, _ = self.artifact_pair("creality_print", "creality.3mf")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("../escape", b"bad")
        report = validate_creality_consistency(
            preset, Artifact(output.getvalue(), "unsafe.3mf", "model/3mf"),
        )
        self.assertTrue(any("3MF" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
