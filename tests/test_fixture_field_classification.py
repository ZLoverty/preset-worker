"""Regression tests for classifications derived from real slicer exports."""

import json
import unittest
import zipfile
from pathlib import Path

from preset_worker.diff import DiffCategory
from preset_worker.slicers import (
    Artifact,
    CrealityPrintProcessor,
    ElegooSlicerProcessor,
    OrcaSlicerProcessor,
    PrusaSlicerProcessor,
    ProcessingContext,
)


FIXTURES = Path(__file__).parent / "fixtures/slicers"


class FixtureFieldClassificationTests(unittest.TestCase):
    def json_diff(self, processor, fixture, changed_fields):
        source = json.loads(fixture.read_text())
        candidate = json.loads(fixture.read_text())
        for key, value in changed_fields.items():
            candidate[key] = value
        return {
            change.path: change
            for change in processor.diff(
                Artifact(json.dumps(source).encode(), fixture.name),
                Artifact(json.dumps(candidate).encode(), fixture.name),
                ProcessingContext("PI", "Printer", processor.slicer_id, "method"),
            ).changes
        }

    def test_creality_real_export_keeps_native_metadata_classified(self):
        fixture = FIXTURES / "creality_print/reconnaissance/source_original.json"
        changes = self.json_diff(
            CrealityPrintProcessor(), fixture,
            {"fan_cooling_layer_time": ["51"], "base_id": "GFSA05"},
        )
        self.assertIs(changes["fan_cooling_layer_time[0]"].category, DiffCategory.IMPORTANT_PARAMETER)
        self.assertIs(changes["base_id"].category, DiffCategory.SYSTEM_METADATA)

    def test_project_settings_config_proves_all_eight_canonical_parameters(self):
        target = {
            "filament_flow_ratio",
            "filament_max_volumetric_speed",
            "nozzle_temperature",
            "nozzle_temperature_initial_layer",
            "fan_min_speed",
            "fan_max_speed",
            "fan_cooling_layer_time",
            "slow_down_layer_time",
        }
        projects = {
            "creality_print": "creality.3mf",
            "elegoo_slicer": "elegoo.3mf",
            "orca_slicer": "orca.3mf",
            "orca_slicer_snapmaker": "snapmaker-orca.3mf",
        }
        for slicer, filename in projects.items():
            with self.subTest(slicer=slicer):
                project = FIXTURES / slicer / filename
                with zipfile.ZipFile(project) as archive:
                    settings = json.loads(archive.read("Metadata/project_settings.config"))
                self.assertTrue(target <= settings.keys())

    def test_project_settings_printing_semantics_are_important(self):
        cases = (
            ("creality_print", "creality.3mf", "reconnaissance/source_original.json", CrealityPrintProcessor()),
            ("elegoo_slicer", "elegoo.3mf", "reconnaissance/source_original.json", ElegooSlicerProcessor()),
            ("orca_slicer", "orca.3mf", "valid/pla_test.json", OrcaSlicerProcessor()),
        )
        fields = (
            "filament_flow_ratio",
            "pressure_advance",
            "retraction_length",
            "chamber_temperature",
            "cool_plate_temp",
            "nozzle_temperature_range_low",
        )
        for slicer, project_name, preset_name, processor in cases:
            with self.subTest(slicer=slicer):
                project = FIXTURES / slicer / project_name
                preset = FIXTURES / slicer / preset_name
                with zipfile.ZipFile(project) as archive:
                    settings = json.loads(archive.read("Metadata/project_settings.config"))
                source = json.loads(preset.read_text())
                candidate = dict(source)
                for field in fields:
                    # These inherited fields are absent from the short preset;
                    # use the project value to exercise the ADDED path.
                    candidate[field] = settings[field]
                changes = self.json_diff(processor, preset, {
                    field: candidate[field] for field in fields
                })
                for field in fields:
                    self.assertIs(changes[field + "[0]"].category, DiffCategory.IMPORTANT_PARAMETER)

    def test_elegoo_real_export_covers_extruder_variant(self):
        fixture = FIXTURES / "elegoo_slicer/reconnaissance/source_original.json"
        changes = self.json_diff(
            ElegooSlicerProcessor(), fixture,
            {"filament_extruder_variant": ["Bowden"], "version": "1.5.3.6"},
        )
        self.assertIs(changes["filament_extruder_variant[0]"].category, DiffCategory.IMPORTANT_PARAMETER)
        self.assertIs(changes["version"].category, DiffCategory.SYSTEM_METADATA)

    def test_orca_real_export_covers_compatibility_metadata(self):
        fixture = FIXTURES / "orca_slicer/valid/pla_test.json"
        changes = self.json_diff(
            OrcaSlicerProcessor(), fixture,
            {"fan_cooling_layer_time": ["51"], "compatible_printers": ["Other"], "version": "2.3.1.1"},
        )
        self.assertIs(changes["fan_cooling_layer_time[0]"].category, DiffCategory.IMPORTANT_PARAMETER)
        self.assertIs(changes["compatible_printers[0]"].category, DiffCategory.SYSTEM_METADATA)
        self.assertIs(changes["version"].category, DiffCategory.SYSTEM_METADATA)

    def test_prusa_real_export_covers_material_and_process_fields(self):
        fixture = FIXTURES / "prusa_slicer/pla_test.ini"
        processor = PrusaSlicerProcessor()
        context = ProcessingContext("PI", "Printer", "PrusaSlicer", "method")
        source = processor.parse(Artifact(fixture.read_bytes(), fixture.name), context)
        candidate = processor.parse(Artifact(fixture.read_bytes(), fixture.name), context)
        for key in ("filament_density", "filament_diameter", "cooling", "extrusion_multiplier"):
            candidate.values[key] = str(candidate.values[key]) + "0"
        # Exercise the public diff with a controlled INI variant while keeping
        # the supplied real export byte-for-byte unchanged.
        candidate_text = fixture.read_text()
        for key in ("filament_density", "filament_diameter", "cooling", "extrusion_multiplier"):
            candidate_text = candidate_text.replace(
                f"{key} = {source.values[key]}", f"{key} = {candidate.values[key]}"
            )
        changes = {
            change.path: change
            for change in processor.diff(
                Artifact(fixture.read_bytes(), fixture.name),
                Artifact(candidate_text.encode(), fixture.name),
                context,
            ).changes
        }
        for key in ("filament_density", "filament_diameter", "cooling", "extrusion_multiplier"):
            self.assertIs(changes[f"ini.{key}"].category, DiffCategory.IMPORTANT_PARAMETER)


if __name__ == "__main__":
    unittest.main()
