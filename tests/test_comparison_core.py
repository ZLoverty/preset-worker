import io
import json
import unittest
import zipfile
from pathlib import Path

from preset_worker.slicers.contracts import Artifact
from preset_worker.three_mf.comparison_core import compare_parameter, select_slot
from preset_worker.three_mf.consistency import validate_bambu_consistency
from preset_worker.three_mf.models import FilamentSlot


PARAMETERS = (
    "filament_flow_ratio", "filament_max_volumetric_speed", "nozzle_temperature",
    "nozzle_temperature_initial_layer", "fan_min_speed", "fan_max_speed",
    "fan_cooling_layer_time", "slow_down_layer_time",
)


def project(values: dict, identities=("A", "B", "C", "D")) -> bytes:
    payload = {"filament_settings_id": list(identities), **values}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Metadata/project_settings.config", json.dumps(payload))
    return output.getvalue()


class ComparisonCoreTests(unittest.TestCase):
    def slots(self, identities=("A", "B", "C", "D")):
        return [FilamentSlot(i + 1, identity) for i, identity in enumerate(identities)]

    def test_duplicate_identity_with_equivalent_arrays_selects_lowest_slot(self):
        values = {name: ["1", "1", "1", "1"] for name in PARAMETERS}
        result = select_slot(
            preset_identity_candidates=["A"], project_slots=self.slots(("A", "B", "C", "A")),
            project_values=values, parameter_names=PARAMETERS,
        )
        self.assertEqual(result["status"], "UNIQUE")
        self.assertEqual(result["filament_slot_id"], 1)
        self.assertEqual(result["matching_slot_ids"], [1, 4])
        self.assertEqual(result["reason"], "MULTIPLE_EQUIVALENT")

    def test_duplicate_identity_with_different_values_is_ambiguous(self):
        values = {name: ["1", "1", "1", "1"] for name in PARAMETERS}
        values["nozzle_temperature"] = ["230", "220", "220", "240"]
        result = select_slot(
            preset_identity_candidates=["A"], project_slots=self.slots(("A", "B", "C", "A")),
            project_values=values, parameter_names=PARAMETERS,
        )
        self.assertEqual(result["status"], "AMBIGUOUS")
        self.assertIsNone(result["filament_slot_id"])

    def test_duplicate_identity_with_unproven_parameter_is_ambiguous(self):
        values = {name: ["1", "1", "1", "1"] for name in PARAMETERS}
        values.pop("fan_max_speed")
        result = select_slot(
            preset_identity_candidates=["A"], project_slots=self.slots(("A", "B", "C", "A")),
            project_values=values, parameter_names=PARAMETERS,
        )
        self.assertEqual(result["status"], "AMBIGUOUS")
        self.assertIn("fan_max_speed", result["unresolved_parameters"])

    def test_no_identity_match_is_unresolved(self):
        result = select_slot(
            preset_identity_candidates=["missing"], project_slots=self.slots(),
            project_values={}, parameter_names=PARAMETERS,
        )
        self.assertEqual(result["status"], "UNRESOLVED")

    def test_selected_slot_compares_scalar_against_single_preset_value(self):
        result = compare_parameter(
            "nozzle_temperature", {"nozzle_temperature": ["230"]},
            {"nozzle_temperature": ["230", "220", "225", "230"]}, slot_id=1, slot_count=4,
        )
        self.assertEqual(result["status"], "MATCH")
        self.assertEqual(result["project"]["source_path"], "$.nozzle_temperature[0]")
        self.assertEqual(result["preset"]["original_array"], ["230"])
        self.assertEqual(result["comparison_scope"], "STORED_SCALAR")

    def test_unproven_array_cardinality_remains_ambiguous(self):
        result = compare_parameter(
            "fan_max_speed", {"fan_max_speed": ["80"]},
            {"fan_max_speed": ["80", "90"]}, slot_id=1, slot_count=4,
        )
        self.assertEqual(result["status"], "AMBIGUOUS")

    def test_scalar_and_array_are_not_broadcast(self):
        result = compare_parameter(
            "fan_max_speed", {"fan_max_speed": "80"},
            {"fan_max_speed": ["80", "80", "80", "80"]},
        )
        self.assertEqual(result["status"], "NOT_COMPARABLE")

    def test_real_orca_fixture_uses_slot_aware_comparison(self):
        base = Path("tests/fixtures/slicers/orca_slicer")
        report = validate_bambu_consistency(
            Artifact((base / "L2002CF @BBL P2S.json").read_bytes(), "preset.json", "application/json"),
            Artifact((base / "orca.3mf").read_bytes(), "orca.3mf", "model/3mf"),
        )
        self.assertEqual(report["selection"]["status"], "UNIQUE")
        self.assertEqual(report["selection"]["filament_slot_id"], 1)
        self.assertEqual(report["selection"]["matching_slot_ids"], [1, 4])
        self.assertEqual(report["summary"], {"MISSING_IN_PRESET": 5, "MATCH": 3})
        temperature = next(item for item in report["comparisons"] if item["parameter_id"] == "nozzle_temperature")
        self.assertEqual(temperature["status"], "MATCH")
        self.assertEqual(temperature["project"]["source_path"], "$.nozzle_temperature[0]")

    def test_real_snapmaker_fixture_does_not_compare_unrelated_slots(self):
        base = Path("tests/fixtures/slicers/orca_slicer_snapmaker")
        report = validate_bambu_consistency(
            Artifact((base / "pla_test.json").read_bytes(), "preset.json", "application/json"),
            Artifact((base / "snapmaker-orca.3mf").read_bytes(), "project.3mf", "model/3mf"),
        )
        self.assertEqual(report["selection"]["filament_slot_id"], 1)
        self.assertEqual(report["summary"], {"MISSING_IN_PRESET": 5, "MATCH": 3})
        self.assertNotIn("AMBIGUOUS", report["summary"])

    def test_real_creality_and_elegoo_single_slot_pairs(self):
        for slicer, project_name, expected_matches in (
            ("creality_print", "creality.3mf", 3),
            ("elegoo_slicer", "elegoo.3mf", 4),
        ):
            base = Path("tests/fixtures/slicers") / slicer
            report = validate_bambu_consistency(
                Artifact((base / "pla_test.json").read_bytes(), "preset.json", "application/json"),
                Artifact((base / project_name).read_bytes(), project_name, "model/3mf"),
            )
            self.assertEqual(report["selection"]["status"], "UNIQUE")
            self.assertEqual(report["selection"]["filament_slot_id"], 1)
            self.assertEqual(report["summary"].get("MATCH"), expected_matches)

    def test_filename_stem_can_be_explicitly_supplied_by_an_adapter(self):
        # The shared core does not discover filenames; an adapter explicitly
        # supplies the verified Prusa filename stem as an identity candidate.
        result = select_slot(
            preset_identity_candidates=[Path("pla_test.ini").stem],
            project_slots=self.slots(("pla_test", "03_custom_metadata", "03_custom_metadata", "03_custom_metadata")),
            project_values={name: ["1", "1", "1", "1"] for name in PARAMETERS},
            parameter_names=PARAMETERS,
        )
        self.assertEqual(result["status"], "UNIQUE")
        self.assertEqual(result["filament_slot_id"], 1)


if __name__ == "__main__":
    unittest.main()
