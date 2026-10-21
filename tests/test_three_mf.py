import io
import json
import unittest
import zipfile
from pathlib import Path

from preset_worker.three_mf import parse_bambu_3mf, resolve_bambu_project
from preset_worker.three_mf.models import ResolutionContext, ResolutionStatus
from preset_worker.three_mf.safe_zip import SafeZipError, SafeZipReader


def make_3mf(project: dict, model: str = "<config/>", extra: dict[str, bytes] | None = None) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Metadata/project_settings.config", json.dumps(project))
        archive.writestr("Metadata/model_settings.config", model)
        for name, data in (extra or {}).items():
            archive.writestr(name, data)
    return output.getvalue()


class ThreeMfTests(unittest.TestCase):
    def test_extracts_raw_project_and_slot_context(self):
        data = make_3mf({
            "filament_settings_id": ["A"],
            "filament_type": ["PLA"],
            "filament_ids": ["ID"],
            "filament_flow_ratio": ["0.98"],
            "printer_model": "Bambu Lab P1S",
        })
        snapshot = parse_bambu_3mf(data)
        self.assertEqual(snapshot.filament_slots[0].settings_id, "A")
        self.assertEqual(snapshot.raw_parameters[0].raw_value, ["0.98"])

    def test_array_cardinality_is_not_assumed_to_be_slot_index(self):
        data = make_3mf({
            "filament_settings_id": ["A"],
            "filament_flow_ratio": ["1", "0.96"],
        })
        snapshot = parse_bambu_3mf(data)
        resolved = resolve_bambu_project(snapshot, ResolutionContext(filament_slot_id=1))
        flow = next(item for item in resolved.parameters if item.name == "filament_flow_ratio")
        self.assertEqual(flow.status, ResolutionStatus.UNRESOLVED)
        self.assertIsNone(flow.value)

    def test_single_value_can_be_resolved_without_slot_array_assumption(self):
        snapshot = parse_bambu_3mf(make_3mf({
            "filament_settings_id": ["A"],
            "filament_flow_ratio": ["0.98"],
        }))
        resolved = resolve_bambu_project(snapshot, ResolutionContext(filament_slot_id=1))
        flow = next(item for item in resolved.parameters if item.name == "filament_flow_ratio")
        self.assertEqual(flow.status, ResolutionStatus.RESOLVED)
        self.assertEqual(flow.value, "0.98")

    def test_bambu_pressure_advance_is_not_runtime_claim(self):
        snapshot = parse_bambu_3mf(make_3mf({
            "filament_settings_id": ["A"],
            "enable_pressure_advance": ["1"],
            "pressure_advance": ["0.02"],
            "printer_model": "Bambu Lab H2D",
        }))
        resolved = resolve_bambu_project(snapshot, ResolutionContext(filament_slot_id=1))
        statuses = {item.name: item.status for item in resolved.parameters}
        self.assertEqual(statuses["pressure_advance"], ResolutionStatus.NOT_APPLICABLE)

    def test_all_four_cooling_parameters_preserve_arrays_and_resolve_independently(self):
        snapshot = parse_bambu_3mf(make_3mf({
            "filament_settings_id": ["A"],
            "fan_min_speed": ["20"],
            "fan_max_speed": ["80"],
            "fan_cooling_layer_time": ["40"],
            "slow_down_layer_time": ["8"],
        }))
        resolved = resolve_bambu_project(snapshot, ResolutionContext(filament_slot_id=1))
        values = {item.name: item for item in resolved.parameters}
        self.assertEqual(values["fan_min_speed"].value, "20")
        self.assertEqual(values["fan_max_speed"].value, "80")
        self.assertEqual(values["fan_cooling_layer_time"].value, "40")
        self.assertEqual(values["slow_down_layer_time"].value, "8")
        self.assertEqual(values["fan_cooling_layer_time"].context["filament_config_index"], 0)
        self.assertEqual(values["slow_down_layer_time"].context["filament_config_index"], 0)

    def test_cooling_threshold_does_not_infer_missing_counterpart(self):
        snapshot = parse_bambu_3mf(make_3mf({
            "filament_settings_id": ["A"],
            "fan_min_speed": ["20"],
            "fan_max_speed": ["80"],
            "fan_cooling_layer_time": ["40"],
        }))
        resolved = resolve_bambu_project(snapshot, ResolutionContext(filament_slot_id=1))
        names = {item.name for item in resolved.parameters}
        self.assertNotIn("slow_down_layer_time", names)

    def test_real_fixture_is_read_only_and_does_not_claim_h2d_effective_values(self):
        path = Path("downloads/legacy_preset_data_audit/recvgKBtHJUrDm_1_PPS100CF10 H2D.3mf")
        if not path.exists():
            self.skipTest("real fixture is not available")
        snapshot = parse_bambu_3mf(path.read_bytes())
        self.assertEqual(len(snapshot.entries), 105)
        self.assertEqual(snapshot.filament_slots[0].settings_id, "PPS100CF10 H2D")
        raw = {item.name: item.raw_value for item in snapshot.raw_parameters}
        self.assertEqual(raw["fan_min_speed"], ["0"])
        self.assertEqual(raw["fan_max_speed"], ["30"])
        self.assertEqual(raw["fan_cooling_layer_time"], ["20"])
        self.assertEqual(raw["slow_down_layer_time"], ["6"])
        resolved = resolve_bambu_project(snapshot, ResolutionContext(filament_slot_id=1))
        flow = next(item for item in resolved.parameters if item.name == "filament_flow_ratio")
        self.assertEqual(flow.status, ResolutionStatus.UNRESOLVED)

    def test_safe_zip_rejects_duplicate_normalized_names(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("a", b"1")
            archive.writestr("./a", b"2")
        with self.assertRaises(SafeZipError):
            SafeZipReader(output.getvalue())


if __name__ == "__main__":
    unittest.main()
