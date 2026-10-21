import io
import json
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from inspect_3mf import inspect  # noqa: E402


def make_zip(entries):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in entries.items():
            archive.writestr(name, value)
    return output.getvalue()


class Inspect3MFTests(unittest.TestCase):
    def test_repository_manifests_are_valid(self):
        root = Path(__file__).parent / "fixtures" / "slicers"
        manifests = sorted(root.glob("*/manifest.json"))
        self.assertEqual(len(manifests), 5)
        required = {"schema_version", "slicer", "project_file", "preset_file", "filament_count"}
        for path in manifests:
            value = json.loads(path.read_text())
            self.assertTrue(required <= set(value), path)
            self.assertEqual(value["schema_version"], "p9d0.fixture.v1")

    def write_pair(self, project=b"", preset=b"{}"):
        directory = TemporaryDirectory()
        root = Path(directory.name)
        project_path = root / "project.3mf"
        preset_path = root / "preset.json"
        project_path.write_bytes(project)
        preset_path.write_bytes(preset)
        return directory, project_path, preset_path

    def test_missing_files_are_reported(self):
        with TemporaryDirectory() as directory:
            result = inspect(Path(directory) / "missing.3mf", Path(directory) / "missing.json", "OrcaSlicer")
        self.assertEqual(result["project"]["status"], "MISSING")
        self.assertEqual(result["preset"]["status"], "MISSING")

    def test_invalid_zip_is_reported_without_bypassing_safe_reader(self):
        directory, project, preset = self.write_pair(b"not a zip")
        try:
            result = inspect(project, preset, "OrcaSlicer")
        finally:
            directory.cleanup()
        self.assertEqual(result["project"]["status"], "ERROR")
        self.assertIn("SafeZipError", result["project"]["errors"][0])

    def test_json_ini_xml_and_target_evidence_are_detected(self):
        project = make_zip({
            "Metadata/project_settings.config": json.dumps({
                "filament_settings_id": ["A", "B"],
                "filament_flow_ratio": ["0.97", "0.98"],
                "printer_model": "Test Printer",
            }),
            "Metadata/Slic3r_PE.config": "; temperature = 225,230\n; fan_below_layer_time = 50,50\n",
            "Metadata/model_settings.config": '<config><metadata key="name" value="cube"/></config>',
        })
        directory, project_path, preset_path = self.write_pair(project, b"name = test\n")
        preset_path = preset_path.with_suffix(".ini")
        preset_path.write_bytes(b"name = test\n")
        try:
            result = inspect(project_path, preset_path, "PrusaSlicer")
        finally:
            directory.cleanup()
        configurations = {item["path"]: item for item in result["project"]["configuration"]}
        self.assertEqual(configurations["Metadata/project_settings.config"]["format"], "json")
        self.assertEqual(configurations["Metadata/Slic3r_PE.config"]["format"], "ini")
        self.assertEqual(configurations["Metadata/model_settings.config"]["format"], "xml")
        self.assertEqual(configurations["Metadata/project_settings.config"]["candidates"]["filament_settings_id"], ["A", "B"])
        self.assertEqual(configurations["Metadata/Slic3r_PE.config"]["candidates"]["temperature"], "225,230")

    def test_unsafe_member_path_is_reported(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("../escape.config", "filament_flow_ratio = 1")
        directory, project, preset = self.write_pair(output.getvalue())
        try:
            result = inspect(project, preset, "OrcaSlicer")
        finally:
            directory.cleanup()
        self.assertEqual(result["project"]["status"], "ERROR")
        self.assertIn("SafeZipError", result["project"]["errors"][0])

    def test_oversized_member_is_reported(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_STORED) as archive:
            archive.writestr("Metadata/huge.config", b"x" * (32 * 1024 * 1024 + 1))
        directory, project, preset = self.write_pair(output.getvalue())
        try:
            result = inspect(project, preset, "OrcaSlicer")
        finally:
            directory.cleanup()
        self.assertEqual(result["project"]["status"], "ERROR")
        self.assertIn("SafeZipError", result["project"]["errors"][0])

    def test_output_is_deterministic(self):
        project = make_zip({"Metadata/project_settings.config": b'{"filament_ids":["A"]}'})
        directory, project_path, preset_path = self.write_pair(project)
        try:
            first = inspect(project_path, preset_path, "OrcaSlicer")
            second = inspect(project_path, preset_path, "OrcaSlicer")
        finally:
            directory.cleanup()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
