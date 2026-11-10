import unittest

from preset_worker.slicers.capabilities import (
    SUPPORTED,
    UNSUPPORTED,
    check_registration_completeness,
)
from preset_worker.slicers.contracts import SlicerProcessorRegistry
from preset_worker.slicers.registry import default_processor_registry


class FakeProcessor:
    def __init__(self, slicer_id):
        self.slicer_id = slicer_id


class RegistrationCompletenessTests(unittest.TestCase):
    def test_default_composition_is_complete(self):
        registry = default_processor_registry()
        validators = {name: object() for name in registry.registered_ids}
        capabilities = {name: SUPPORTED for name in registry.registered_ids}
        self.assertEqual(check_registration_completeness(registry, validators, capabilities), ())

    def test_aliases_are_checked_by_canonical_id(self):
        registry = default_processor_registry()
        validators = {name: object() for name in registry.registered_ids}
        capabilities = {name: SUPPORTED for name in registry.registered_ids}
        capabilities["OrcaSlicer (Snapmaker)"] = capabilities.pop("SnapmakerOrcaSlicer")
        self.assertEqual(check_registration_completeness(registry, validators, capabilities), ())

    def test_missing_capability_declaration(self):
        registry = SlicerProcessorRegistry([FakeProcessor("Synthetic")])
        issues = check_registration_completeness(registry, {}, {})
        self.assertEqual([issue.code for issue in issues], ["MISSING_CAPABILITY_DECLARATION"])

    def test_missing_expected_validator(self):
        registry = SlicerProcessorRegistry([FakeProcessor("Synthetic")])
        issues = check_registration_completeness(registry, {}, {"Synthetic": SUPPORTED})
        self.assertEqual([issue.code for issue in issues], ["MISSING_EXPECTED_VALIDATOR"])

    def test_explicitly_unsupported_has_no_validator_requirement(self):
        registry = SlicerProcessorRegistry([FakeProcessor("NativeOnly")])
        issues = check_registration_completeness(registry, {}, {"NativeOnly": UNSUPPORTED})
        self.assertEqual(issues, ())

    def test_orphan_validator(self):
        registry = SlicerProcessorRegistry([])
        issues = check_registration_completeness(registry, {"Orphan": object()}, {})
        self.assertEqual([issue.code for issue in issues], ["ORPHAN_VALIDATOR"])

    def test_unsupported_conflict_and_unknown_declaration(self):
        registry = SlicerProcessorRegistry([FakeProcessor("NativeOnly")])
        issues = check_registration_completeness(
            registry,
            {"NativeOnly": object()},
            {"NativeOnly": UNSUPPORTED, "Unknown": SUPPORTED},
        )
        self.assertEqual(
            [issue.code for issue in issues],
            ["UNEXPECTED_VALIDATOR", "UNKNOWN_CAPABILITY_DECLARATION"],
        )

    def test_invalid_capability_and_deterministic_order(self):
        registry = SlicerProcessorRegistry([FakeProcessor("B"), FakeProcessor("A")])
        issues = check_registration_completeness(
            registry,
            {"Z": object()},
            {"B": "MAYBE", "A": SUPPORTED},
        )
        self.assertEqual(
            [(issue.code, issue.slicer_id) for issue in issues],
            [
                ("INVALID_CAPABILITY_DECLARATION", "B"),
                ("MISSING_EXPECTED_VALIDATOR", "A"),
                ("ORPHAN_VALIDATOR", "Z"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
