import io
import json
import unittest
import zipfile
from pathlib import Path

from preset_worker.slicers import Artifact
from preset_worker.three_mf.consistency import validate_flash_studio_consistency


FIXTURE = Path("tests/fixtures/slicers/flash_studio")


def change_nozzle_temperature(value):
    changed = False
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "nozzle_temperature" and isinstance(child, list):
                for index in range(len(child)):
                    child[index] = 225
                changed = True
            elif change_nozzle_temperature(child):
                changed = True
    elif isinstance(value, list):
        for child in value:
            if change_nozzle_temperature(child):
                changed = True
    return changed


def artifact(name: str) -> Artifact:
    path = FIXTURE / name
    return Artifact(path.read_bytes(), name, "model/3mf" if path.suffix == ".3mf" else "application/json")


class FlashStudioConsistencyTests(unittest.TestCase):
    def test_real_fixture_resolves_equivalent_slots_and_matches_targets(self):
        report = validate_flash_studio_consistency(
            artifact("pla ff creator 5.json"), artifact("pla ff creator 5.3mf")
        )
        self.assertEqual(report["source"]["slicer"], "FlashStudio")
        self.assertEqual(report["selection"]["status"], "UNIQUE")
        self.assertEqual(report["selection"]["matching_slot_ids"], [1, 2, 3, 4])
        self.assertEqual(report["summary"], {"MATCH": 8})
        self.assertEqual(report["errors"], [])

    def test_project_value_change_is_reported_as_mismatch(self):
        original = artifact("pla ff creator 5.3mf")
        output = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(original.content), "r") as source, zipfile.ZipFile(output, "w") as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == "Metadata/project_settings.config":
                    settings = json.loads(data)
                    self.assertTrue(change_nozzle_temperature(settings))
                    data = json.dumps(settings).encode("utf-8")
                target.writestr(info, data)
        report = validate_flash_studio_consistency(
            artifact("pla ff creator 5.json"), Artifact(output.getvalue(), "changed.3mf", "model/3mf")
        )
        self.assertEqual(report["summary"].get("MISMATCH"), 1)


if __name__ == "__main__":
    unittest.main()
