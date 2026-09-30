import json
import unittest
from pathlib import Path

from preset_worker.diff import ChangeType, DiffCategory, UnifiedDiff
from preset_worker.services.enrichment import SubmissionEnrichment
from preset_worker.slicers import Artifact, ProcessingContext, PrusaSlicerProcessor
from preset_worker.slicers.registry import default_processor_registry


FIXTURE_DIR = Path(__file__).parent / "fixtures/slicers/prusa_slicer/reconnaissance"
SOURCE = FIXTURE_DIR / "source_original.ini"


class WorkflowClient:
    submission_table_id = "submission"
    preset_table_id = "preset"
    version_table_id = "version"

    def __init__(self, *, with_base=False):
        self.submission = {
            "record_id": "submission-record",
            "fields": {
                "status": "VALIDATING",
                "submission_id": "S1",
                "pi_code": [{"text": "L2002CF"}],
                "printer": [{"text": "MK4S"}],
                "slicer": [{"text": "PrusaSlicer"}],
                "method_version": "method-7.6",
                "preset_key": "L2002CF | MK4S | PrusaSlicer",
                "preset data": [{"file_token": "uploaded", "name": "pla_test.ini"}],
            },
        }
        self.files = {"uploaded": SOURCE.read_bytes(), "base": SOURCE.read_bytes()}
        self.presets = []
        self.versions = []
        if with_base:
            self.presets = [{
                "record_id": "preset-record",
                "fields": {
                    "preset_key": "L2002CF | MK4S | PrusaSlicer",
                    "current_version_id": [{"text": "PS@v1"}],
                },
            }]
            self.versions = [{
                "record_id": "version-record",
                "fields": {
                    "version_id": "PS@v1",
                    "version_no": 1,
                    "canonical_json": [{"file_token": "base", "name": "base.ini"}],
                },
            }]

    def get_submission(self, _submission_id):
        return self.submission

    def list_records(self, table_id):
        return {
            self.preset_table_id: self.presets,
            self.version_table_id: self.versions,
        }[table_id]

    def download_attachment(self, attachment):
        return self.files[attachment["file_token"]]

    def upload_attachment(self, _filename, content):
        self.files["canonical"] = content
        return {"file_token": "canonical"}

    def update_submission(self, _record_id, fields):
        self.submission["fields"].update(fields)


class PrusaSlicerProcessorTests(unittest.TestCase):
    def setUp(self):
        self.processor = PrusaSlicerProcessor()
        self.context = ProcessingContext("L2002CF", "MK4S", "PrusaSlicer", "method-7.6")
        self.source = Artifact(SOURCE.read_bytes(), "pla_test.ini", "text/plain")

    def test_registered_and_independent(self):
        registry = default_processor_registry()
        self.assertIsInstance(registry.require("PrusaSlicer"), PrusaSlicerProcessor)
        self.assertIsNot(type(registry.require("PrusaSlicer")), type(registry.require("OrcaSlicer")))
        self.assertIsNot(type(registry.require("PrusaSlicer")), type(registry.require("ElegooSlicer")))

    def test_real_fixture_golden_preserves_native_content_and_filename_identity(self):
        result = self.processor.process(self.source, self.context)
        self.assertTrue(result.validation_result.valid)
        self.assertEqual(result.canonical_artifact.filename, "L2002CF @MK4S.ini")
        text = result.canonical_artifact.content.decode()
        self.assertIn("pm_method_version = method-7.6\n", text)
        self.assertNotIn("\nname =", text)
        for line in (
            'filament_settings_id = ""',
            'inherits = Generic PLA @COREONEINDX HF0.4',
            'compatible_printers_condition = printer_model=~/(COREONE_INDX8T|COREONE_INDX4T|COREONEL_INDX8T|COREONEL_INDX4T)/ and nozzle_diameter[0]==0.4 and nozzle_high_flow[0]',
            "temperature = 230",
            "bed_temperature = 60",
            "filament_density = 1.24",
            "filament_diameter = 1.75",
            "filament_max_volumetric_speed = 17",
            "filament_retract_length_toolchange = 0.8",
        ):
            self.assertIn(line, text)

    def test_filename_is_only_display_identity_and_no_synthetic_name(self):
        result = self.processor.process(Artifact(SOURCE.read_bytes(), "P7PS_NAME_ONLY.ini"), self.context)
        self.assertTrue(result.validation_result.valid)
        self.assertEqual(result.canonical_artifact.filename, "L2002CF @MK4S.ini")
        self.assertNotIn("name =", result.canonical_artifact.content.decode())

    def test_stale_and_missing_pm_method_version_are_context_authoritative(self):
        source = SOURCE.read_text()
        missing = self.processor.process(Artifact(source.encode(), "source.ini"), self.context)
        self.assertIn("pm_method_version = method-7.6", missing.canonical_artifact.content.decode())
        stale = self.processor.process(Artifact((source + "pm_method_version = OLD\n").encode(), "source.ini"), self.context)
        text = stale.canonical_artifact.content.decode()
        self.assertEqual(text.count("pm_method_version = "), 1)
        self.assertIn("pm_method_version = method-7.6", text)

    def test_unknown_key_and_empty_string_are_preserved(self):
        source = SOURCE.read_text() + "future_unknown = 1.0\n"
        result = self.processor.process(Artifact(source.encode(), "source.ini"), self.context)
        self.assertIn("future_unknown = 1.0\n", result.canonical_artifact.content.decode())
        self.assertIn('filament_settings_id = ""', result.canonical_artifact.content.decode())

    def test_validation_rejects_random_ini_and_non_ini_filename(self):
        random_ini = b"name = PLA @MK4S\n"
        result = self.processor.process(Artifact(random_ini, "PLA @MK4S.ini"), self.context)
        self.assertFalse(result.validation_result.valid)
        wrong_extension = self.processor.process(self.source, self.context)
        wrong_extension = self.processor.validate_source(self.processor.parse(Artifact(SOURCE.read_bytes(), "source.txt"), self.context), self.context)
        self.assertFalse(wrong_extension.valid)

    def test_diff_includes_filename_and_ini_changes_with_categories(self):
        candidate = SOURCE.read_text().replace("temperature = 230", "temperature = 235")
        candidate = candidate.replace('filament_settings_id = ""\n', '')
        candidate += "future_unknown = changed\n"
        result = self.processor.diff(
            Artifact(SOURCE.read_bytes(), "base.ini"),
            Artifact(candidate.encode(), "candidate.ini"),
            self.context,
        )
        changes = {change.path: change for change in result.changes}
        self.assertEqual(changes["$artifact.filename"].category, DiffCategory.SYSTEM_METADATA)
        self.assertEqual(changes["ini.temperature"].category, DiffCategory.IMPORTANT_PARAMETER)
        self.assertEqual(changes["ini.temperature"].change_type, ChangeType.MODIFIED)
        self.assertEqual(changes["ini.filament_settings_id"].change_type, ChangeType.REMOVED)
        self.assertEqual(changes["ini.future_unknown"].category, DiffCategory.OTHER_PARAMETER)
        self.assertEqual(tuple(change.path for change in result.changes), tuple(sorted(change.path for change in result.changes)))

    def test_diff_distinguishes_empty_from_missing(self):
        base = Artifact(b"filament_type = PLA\ntemperature = 230\nfilament_diameter = 1.75\nfilament_vendor = Generic\nfilament_settings_id = \n", "base.ini")
        candidate = Artifact(b"filament_type = PLA\ntemperature = 230\nfilament_diameter = 1.75\nfilament_vendor = Generic\n", "base.ini")
        result = self.processor.diff(base, candidate, self.context)
        change = next(change for change in result.changes if change.path == "ini.filament_settings_id")
        self.assertEqual(change.change_type, ChangeType.REMOVED)
        self.assertEqual(change.old_value, "")
        self.assertIsNone(change.new_value)

    def test_diff_is_deterministic(self):
        candidate = SOURCE.read_text() + "z_unknown = 1\na_unknown = 2\n"
        first = self.processor.diff(self.source, Artifact(candidate.encode(), "candidate.ini"), self.context)
        second = self.processor.diff(self.source, Artifact(candidate.encode(), "candidate.ini"), self.context)
        self.assertEqual(first, second)


class PrusaSlicerWorkflowTests(unittest.TestCase):
    def test_create_uses_prusa_processor_and_opaque_artifact(self):
        client = WorkflowClient()
        result = SubmissionEnrichment(client).process_candidate(client.submission, "S1")
        self.assertEqual(result.operation, "CREATE")
        self.assertEqual(result.canonical_artifact.filename, "L2002CF @MK4S.ini")
        self.assertIn("pm_method_version = method-7.6", result.canonical_artifact.content.decode())
        self.assertEqual(result.diff, UnifiedDiff.empty())

    def test_update_passes_base_to_prusa_diff(self):
        client = WorkflowClient(with_base=True)
        result = SubmissionEnrichment(client).process_candidate(client.submission, "S1")
        self.assertEqual(result.operation, "UPDATE")
        self.assertEqual(result.base_version_id, "PS@v1")
        self.assertEqual([change.path for change in result.diff.changes], ["$artifact.filename", "ini.pm_method_version"])
        self.assertTrue(all(change.category is DiffCategory.SYSTEM_METADATA for change in result.diff.changes))


if __name__ == "__main__":
    unittest.main()
