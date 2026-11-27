import unittest

from preset_worker.diff import (
    ChangeType,
    DiffCategory,
    DiffChange,
    UnifiedDiff,
    deserialize_unified_diff,
    serialize_unified_diff,
)
from preset_worker.slicers import Artifact, BambuStudioProcessor, ProcessingContext


class DiffContractTests(unittest.TestCase):
    def setUp(self):
        self.processor = BambuStudioProcessor()
        self.context = ProcessingContext("PI", "Printer", "BambuStudio", "1")

    def diff(self, base, candidate):
        return self.processor.diff(
            Artifact(base, "base.json"),
            Artifact(candidate, "candidate.json"),
            self.context,
        )

    def test_added_removed_modified_and_categories(self):
        result = self.diff(
            b'{"temperature": 200, "removed": true, "unknown": "A", "nullable": null}',
            b'{"temperature": 210, "added": 1, "unknown": "B", "nullable": null}',
        )
        changes = {change.path: change for change in result.changes}
        self.assertEqual(changes["temperature"].change_type, ChangeType.MODIFIED)
        # The Bambu JSON contract does not establish a generic ``temperature``
        # field as one of its important native parameters.  Slicer-specific
        # temperature paths remain classified explicitly where evidenced.
        self.assertEqual(changes["temperature"].category, DiffCategory.OTHER_PARAMETER)
        self.assertEqual(changes["removed"].change_type, ChangeType.REMOVED)
        self.assertEqual(changes["added"].change_type, ChangeType.ADDED)
        self.assertEqual(changes["unknown"].category, DiffCategory.OTHER_PARAMETER)
        self.assertNotIn("nullable", changes)

    def test_missing_and_null_are_distinct(self):
        added_null = self.diff(b'{}', b'{"parameter": null}')
        removed_null = self.diff(b'{"parameter": null}', b'{}')
        unchanged_null = self.diff(b'{"parameter": null}', b'{"parameter": null}')
        self.assertEqual(added_null.changes[0].change_type, ChangeType.ADDED)
        self.assertIsNone(added_null.changes[0].new_value)
        self.assertEqual(removed_null.changes[0].change_type, ChangeType.REMOVED)
        self.assertIsNone(removed_null.changes[0].old_value)
        self.assertEqual(unchanged_null, UnifiedDiff.empty())

    def test_deterministic_v1_serialization_and_legacy_read(self):
        result = self.diff(b'{"b": 1, "a": 1}', b'{"b": 2, "c": 3}')
        serialized = serialize_unified_diff(result)
        self.assertEqual(serialized, serialize_unified_diff(result))
        restored = deserialize_unified_diff(serialized)
        self.assertEqual(restored, result)
        legacy = deserialize_unified_diff('{"modified":[{"path":"a","old":1,"new":2}]}')
        self.assertEqual(legacy.changes[0].category, DiffCategory.OTHER_PARAMETER)

    def test_diff_model_rejects_unknown_enums(self):
        with self.assertRaises(ValueError):
            deserialize_unified_diff({
                "schema_version": 1,
                "changes": [{
                    "path": "x",
                    "change_type": "UNKNOWN",
                    "category": "OTHER_PARAMETER",
                    "old_value": 1,
                    "new_value": 2,
                }],
            })


if __name__ == "__main__":
    unittest.main()
