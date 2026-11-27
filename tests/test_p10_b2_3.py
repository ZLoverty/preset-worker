import unittest
from pathlib import Path

from preset_worker.slicers.contracts import Artifact
from preset_worker.three_mf.comparison_core import compare_parameter
from preset_worker.three_mf import validate_orca_consistency


class ComparisonInvariantTests(unittest.TestCase):
    def compare(self, preset, project):
        return compare_parameter("nozzle_temperature", preset, project)

    def test_equal_and_unequal_values_are_comparable(self):
        self.assertEqual(self.compare({"nozzle_temperature": "230"}, {"nozzle_temperature": "230"})["status"], "MATCH")
        self.assertEqual(self.compare({"nozzle_temperature": "230"}, {"nozzle_temperature": "231"})["status"], "MISMATCH")

    def test_missing_operands_are_never_match_and_preserve_side(self):
        preset_missing = self.compare({}, {"nozzle_temperature": "230"})
        project_missing = self.compare({"nozzle_temperature": "230"}, {})
        both_missing = self.compare({}, {})
        self.assertEqual(preset_missing["status"], "MISSING_IN_PRESET")
        self.assertEqual(project_missing["status"], "MISSING_IN_3MF")
        self.assertEqual(both_missing["status"], "MISSING_IN_PRESET")
        self.assertEqual(preset_missing["diagnostic"]["missing_side"], "preset")
        self.assertEqual(project_missing["diagnostic"]["missing_side"], "3mf")
        self.assertNotEqual(both_missing["status"], "MATCH")

    def test_invalid_operands_are_unresolved_not_match(self):
        result = self.compare({"nozzle_temperature": "not-a-number"}, {"nozzle_temperature": "230"})
        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertEqual(result["diagnostic"]["resolution"], "SOURCE_PARAMETER_INVALID")

    def test_shape_mismatch_is_not_match(self):
        result = self.compare({"nozzle_temperature": "230"}, {"nozzle_temperature": ["230", "230"]})
        self.assertEqual(result["status"], "NOT_COMPARABLE")
        self.assertEqual(result["diagnostic"]["resolution"], "SHAPE_NOT_COMPARABLE")


class OrcaFixtureDiagnosisTests(unittest.TestCase):
    def test_committed_orca_pair_records_identity_resolution_gap(self):
        base = Path("tests/fixtures/slicers/orca_slicer")
        report = validate_orca_consistency(
            Artifact((base / "valid" / "pla_test.json").read_bytes(), "pla_test.json", "application/json"),
            Artifact((base / "orca.3mf").read_bytes(), "orca.3mf", "model/3mf"),
        )
        self.assertEqual(report["selection"]["status"], "UNRESOLVED")
        self.assertEqual(report["summary"], {"UNRESOLVED": 8})
        self.assertTrue(all(item["diagnostic"]["resolution"] == "FILAMENT_IDENTITY_UNRESOLVED" for item in report["comparisons"]))
        self.assertTrue(all("no identity match" in item["diagnostic"]["reason"] for item in report["comparisons"]))


if __name__ == "__main__":
    unittest.main()
