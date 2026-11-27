import unittest

from preset_worker.diff import DiffCategory
from preset_worker.slicers import (
    IMPORTANT_PARAMETER_CATALOG,
    build_coverage_inventory,
    classify_native_path,
    important_paths_for_slicer,
    system_metadata_paths_for_slicer,
    validate_catalog,
)
from preset_worker.slicers.bambu_studio import BambuStudioProcessor
from preset_worker.slicers.creality_print import CrealityPrintProcessor
from preset_worker.slicers.elegoo_slicer import ElegooSlicerProcessor
from preset_worker.slicers.orca_slicer import OrcaSlicerProcessor
from preset_worker.slicers.prusa_slicer import PrusaSlicerProcessor
from preset_worker.slicers.snapmaker_orca import SnapmakerOrcaSlicerProcessor
from preset_worker.slicers.registry import default_processor_registry


class ParameterCatalogTests(unittest.TestCase):
    def test_catalog_integrity_and_unique_ids(self):
        ids = [definition.parameter_id for definition in IMPORTANT_PARAMETER_CATALOG]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(validate_catalog(), ())

    def test_exact_and_indexed_matching(self):
        self.assertIs(classify_native_path("OrcaSlicer", "nozzle_temperature"), DiffCategory.IMPORTANT_PARAMETER)
        self.assertIs(classify_native_path("OrcaSlicer", "nozzle_temperature[1]"), DiffCategory.IMPORTANT_PARAMETER)
        self.assertIs(classify_native_path("OrcaSlicer", "nozzle_temperature_extra"), DiffCategory.OTHER_PARAMETER)
        self.assertIs(classify_native_path("OrcaSlicer", "filament_flow_ratio[abc]"), DiffCategory.OTHER_PARAMETER)

    def test_system_metadata_precedes_parameter_classification(self):
        self.assertIn("name", system_metadata_paths_for_slicer("OrcaSlicer"))
        self.assertIs(classify_native_path("OrcaSlicer", "name"), DiffCategory.SYSTEM_METADATA)
        self.assertIs(classify_native_path("OrcaSlicer", "name[0]"), DiffCategory.SYSTEM_METADATA)

    def test_slicer_specific_paths_are_isolated(self):
        self.assertIs(classify_native_path("ElegooSlicer", "filament_extruder_variant[0]"), DiffCategory.IMPORTANT_PARAMETER)
        self.assertIs(classify_native_path("OrcaSlicer", "filament_extruder_variant[0]"), DiffCategory.OTHER_PARAMETER)
        self.assertNotIn("graphic_effect_plate_temp", important_paths_for_slicer("OrcaSlicer"))
        self.assertIn("graphic_effect_plate_temp", important_paths_for_slicer("SnapmakerOrcaSlicer"))

    def test_representative_classification_for_all_registered_processors(self):
        cases = (
            ("BambuStudio", "nozzle_temperature"),
            ("OrcaSlicer", "nozzle_temperature[0]"),
            ("CrealityPrint", "slow_down_for_layer_cooling"),
            ("ElegooSlicer", "filament_extruder_variant[0]"),
            ("SnapmakerOrcaSlicer", "graphic_effect_plate_temp_initial_layer"),
            ("PrusaSlicer", "ini.filament_density"),
        )
        for slicer_id, path in cases:
            with self.subTest(slicer=slicer_id, path=path):
                self.assertIs(classify_native_path(slicer_id, path), DiffCategory.IMPORTANT_PARAMETER)

    def test_every_processor_uses_catalog_derived_paths(self):
        processors = (
            BambuStudioProcessor(),
            OrcaSlicerProcessor(),
            CrealityPrintProcessor(),
            ElegooSlicerProcessor(),
            SnapmakerOrcaSlicerProcessor(),
        )
        for processor in processors:
            with self.subTest(slicer=processor.slicer_id):
                self.assertEqual(processor.important_parameter_paths, important_paths_for_slicer(processor.slicer_id))
        self.assertEqual(
            PrusaSlicerProcessor.important_parameter_paths,
            frozenset(path.removeprefix("ini.") for path in important_paths_for_slicer("PrusaSlicer")),
        )

    def test_coverage_inventory_is_static_and_deterministic(self):
        registry = default_processor_registry()
        before = registry.registered_ids
        targets = (
            "filament_flow_ratio", "filament_max_volumetric_speed", "nozzle_temperature",
            "nozzle_temperature_initial_layer", "fan_min_speed", "fan_max_speed",
            "fan_cooling_layer_time", "slow_down_layer_time",
        )
        first = build_coverage_inventory(registry.registered_ids, targets)
        second = build_coverage_inventory(registry.registered_ids, targets)
        self.assertEqual(first, second)
        self.assertEqual(registry.registered_ids, before)
        self.assertEqual({row["slicer_id"] for row in first}, set(before))
        flow = [row for row in first if row["parameter_id"] == "filament.flow_ratio"]
        pressure = [row for row in first if row["parameter_id"] == "pressure.advance"]
        self.assertTrue(flow)
        self.assertTrue(all(row["coverage"] == "Covered" for row in flow))
        self.assertTrue(pressure)
        self.assertTrue(all(row["coverage"] == "Not covered" for row in pressure))
        self.assertTrue(all("static target membership" in row["evidence"] for row in first))

    def test_coverage_inventory_can_disclose_unknown_target_catalog(self):
        rows = build_coverage_inventory(("OrcaSlicer",), None)
        self.assertTrue(rows)
        self.assertTrue(all(row["coverage"] == "Unknown" for row in rows))


if __name__ == "__main__":
    unittest.main()
