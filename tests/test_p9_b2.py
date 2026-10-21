import io
import json
import zipfile
import unittest

from preset_worker.slicers.contracts import Artifact
from preset_worker.three_mf.consistency import validate_bambu_consistency


def project(values: dict) -> bytes:
    payload = {
        "filament_settings_id": ["TEST"],
        "printer_model": "Bambu Lab P1S",
        **values,
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Metadata/project_settings.config", json.dumps(payload))
        archive.writestr("Metadata/model_settings.config", "<config/>")
    return output.getvalue()


PARAMETERS = {
    "filament_flow_ratio": ["0.98"],
    "filament_max_volumetric_speed": ["12"],
    "nozzle_temperature": ["220"],
    "nozzle_temperature_initial_layer": ["225"],
    "fan_min_speed": ["20"],
    "fan_max_speed": ["80"],
    "fan_cooling_layer_time": ["40"],
    "slow_down_layer_time": ["8"],
}


class P9B2Tests(unittest.TestCase):
    def artifacts(self, preset: dict | None = None, values: dict | None = None):
        preset_data = {"version": "1.0", "filament_settings_id": ["TEST"], **(preset or PARAMETERS)}
        return (
            Artifact(json.dumps(preset_data).encode(), "preset.json", "application/json"),
            Artifact(project(values or PARAMETERS), "project.3mf", "model/3mf"),
        )

    def test_all_eight_parameters_match(self):
        report = validate_bambu_consistency(*self.artifacts())
        self.assertEqual(report["summary"], {"MATCH": 8})
        self.assertEqual(report["selection"]["status"], "UNIQUE")

    def test_equal_length_arrays_compare_element_wise(self):
        values = dict(PARAMETERS)
        values["nozzle_temperature"] = ["220", "230"]
        preset = dict(PARAMETERS)
        preset["nozzle_temperature"] = [220, 230]
        report = validate_bambu_consistency(*self.artifacts(preset=preset, values=values))
        item = next(item for item in report["comparisons"] if item["parameter_id"] == "nozzle_temperature")
        self.assertEqual(item["status"], "MATCH")
        self.assertEqual(item["comparison_scope"], "STORED_ARRAY")
        self.assertEqual([element["status"] for element in item["elements"]], ["MATCH", "MATCH"])

    def test_one_array_element_mismatch_is_parameter_mismatch(self):
        values = dict(PARAMETERS)
        values["fan_max_speed"] = ["80", "90"]
        preset = dict(PARAMETERS)
        preset["fan_max_speed"] = ["80", "85"]
        report = validate_bambu_consistency(*self.artifacts(preset=preset, values=values))
        item = next(item for item in report["comparisons"] if item["parameter_id"] == "fan_max_speed")
        self.assertEqual(item["status"], "MISMATCH")
        self.assertEqual(item["elements"][1]["status"], "MISMATCH")

    def test_different_lengths_preserve_unmatched_elements(self):
        values = dict(PARAMETERS)
        values["fan_min_speed"] = ["20", "30"]
        preset = dict(PARAMETERS)
        preset["fan_min_speed"] = ["20"]
        report = validate_bambu_consistency(*self.artifacts(preset=preset, values=values))
        item = next(item for item in report["comparisons"] if item["parameter_id"] == "fan_min_speed")
        self.assertEqual(item["status"], "AMBIGUOUS")
        self.assertEqual(len(item["elements"]), 2)
        self.assertEqual(item["elements"][1]["status"], "AMBIGUOUS")

    def test_scalar_and_array_are_not_comparable(self):
        values = dict(PARAMETERS)
        values["fan_max_speed"] = ["80"]
        preset = dict(PARAMETERS)
        preset["fan_max_speed"] = "80"
        report = validate_bambu_consistency(*self.artifacts(preset=preset, values=values))
        item = next(item for item in report["comparisons"] if item["parameter_id"] == "fan_max_speed")
        self.assertEqual(item["status"], "NOT_COMPARABLE")

    def test_invalid_and_missing_elements_are_explicit(self):
        values = dict(PARAMETERS)
        values["fan_cooling_layer_time"] = ["bad", "40"]
        preset = dict(PARAMETERS)
        preset["fan_cooling_layer_time"] = ["bad", "40"]
        report = validate_bambu_consistency(*self.artifacts(preset=preset, values=values))
        item = next(item for item in report["comparisons"] if item["parameter_id"] == "fan_cooling_layer_time")
        self.assertEqual(item["status"], "UNRESOLVED")
        self.assertEqual(item["elements"][0]["status"], "UNRESOLVED")

    def test_nil_element_is_compared_at_its_index_as_missing(self):
        values = dict(PARAMETERS)
        values["filament_flow_ratio"] = ["1", "0.96"]
        preset = dict(PARAMETERS)
        preset["filament_flow_ratio"] = ["1", "nil"]
        report = validate_bambu_consistency(*self.artifacts(preset=preset, values=values))
        item = next(item for item in report["comparisons"] if item["parameter_id"] == "filament_flow_ratio")
        self.assertEqual(item["elements"][0]["status"], "MATCH")
        self.assertEqual(item["elements"][1]["status"], "MISSING_IN_PRESET")

    def test_flat_comparison_rows_use_unified_diff_style_paths(self):
        values = dict(PARAMETERS)
        values["nozzle_temperature"] = ["220", "230"]
        preset = dict(PARAMETERS)
        preset["nozzle_temperature"] = ["220", "230"]
        report = validate_bambu_consistency(*self.artifacts(preset=preset, values=values))
        rows = [row for row in report["comparison_rows"] if row["parameter_id"] == "nozzle_temperature"]
        self.assertEqual([row["path"] for row in rows], ["nozzle_temperature[0]", "nozzle_temperature[1]"])
        self.assertEqual([row["status"] for row in rows], ["MATCH", "MATCH"])

    def test_mismatch_is_reported_only_after_both_values_resolve(self):
        preset = dict(PARAMETERS)
        preset["fan_max_speed"] = ["70"]
        report = validate_bambu_consistency(*self.artifacts(preset=preset))
        statuses = {item["parameter_id"]: item["status"] for item in report["comparisons"]}
        self.assertEqual(statuses["fan_max_speed"], "MISMATCH")
        self.assertEqual(statuses["fan_cooling_layer_time"], "MATCH")

    def test_missing_preset_value_is_not_mismatch(self):
        preset = dict(PARAMETERS)
        del preset["slow_down_layer_time"]
        report = validate_bambu_consistency(*self.artifacts(preset=preset))
        item = next(item for item in report["comparisons"] if item["parameter_id"] == "slow_down_layer_time")
        self.assertEqual(item["status"], "MISSING_IN_PRESET")

    def test_project_array_with_unknown_cardinality_is_unresolved(self):
        values = dict(PARAMETERS)
        values["filament_flow_ratio"] = ["1", "0.98"]
        report = validate_bambu_consistency(*self.artifacts(values=values))
        item = next(item for item in report["comparisons"] if item["parameter_id"] == "filament_flow_ratio")
        self.assertEqual(item["status"], "AMBIGUOUS")

    def test_slot_identity_must_match(self):
        preset = dict(PARAMETERS)
        report = validate_bambu_consistency(*self.artifacts(preset={"filament_settings_id": ["OTHER"], **preset}))
        self.assertEqual(report["selection"]["status"], "UNRESOLVED")
        self.assertEqual(report["comparisons"][0]["status"], "MATCH")


if __name__ == "__main__":
    unittest.main()
