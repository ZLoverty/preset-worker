import json
import unittest

from scripts.migrate_to_submission import (
    PHOTO_FIELDS,
    build_target_fields,
    migration_id,
    replace_invalid_preset_version,
)


class SubmissionMigrationTests(unittest.TestCase):
    def test_builds_only_supported_fields(self):
        source = {
            "record_id": "rec-source",
            "pi_code": [{"record_ids": ["pi-1"]}],
            "printer": [{"record_ids": ["printer-1"]}],
            "冷却参数照片": [{"file_token": "photo-1"}],
            "其他照片": [
                {"file_token": "photo-2"},
                {"file_token": "photo-3"},
            ],
            "preset data": [{"file_token": "json-1"}],
            "preset 3mf": [{"file_token": "3mf-1"}],
            "status": "完成",
            "ignored": "must not be copied",
        }
        fields = build_target_fields("rec-source", source)
        self.assertEqual(fields["submission_id"], "MIGRATED-rec-source")
        self.assertEqual(fields["status"], "DRAFT")
        self.assertEqual(fields["pi_code"], [{"record_ids": ["pi-1"]}])
        self.assertEqual(fields["printer"], [{"record_ids": ["printer-1"]}])
        self.assertEqual(fields["冷却参数照片"], [{"file_token": "photo-1"}])
        self.assertEqual(fields["其他照片"], [{"file_token": "photo-2"}, {"file_token": "photo-3"}])
        self.assertEqual(fields["preset data"], [{"file_token": "json-1"}])
        self.assertEqual(fields["preset 3mf"], [{"file_token": "3mf-1"}])
        self.assertNotIn("ignored", fields)
        self.assertEqual(
            set(fields)
            - {"submission_id", "status", "pi_code", "printer", "冷却参数照片", "其他照片", "preset data", "preset 3mf"},
            set(),
        )

    def test_photo_order_is_preserved_and_source_is_not_mutated(self):
        source = {"其他照片": [{"file_token": "a"}, {"file_token": "b"}]}
        fields = build_target_fields("rec-1", source)
        fields["其他照片"][0]["file_token"] = "changed"
        self.assertEqual([item["file_token"] for item in source["其他照片"]], ["a", "b"])

    def test_existing_submission_id_is_reused(self):
        self.assertEqual(migration_id("rec-1", {"submission_id": "S000010"}), "S000010")

    def test_photo_field_list_matches_current_projection_schema(self):
        self.assertEqual(len(PHOTO_FIELDS), 10)
        self.assertIn("其他照片", PHOTO_FIELDS)

    def test_replaces_invalid_version_for_known_printer(self):
        content = b'{"name":"preset","version":"0.0.0.0","x":"keep"}'
        updated, replacement = replace_invalid_preset_version(
            content, "preset.json", "Bambu P2S"
        )
        self.assertEqual(replacement, "2.8.0.4")
        self.assertEqual(json.loads(updated), {
            "name": "preset",
            "version": "2.8.0.4",
            "x": "keep",
        })

    def test_replaces_invalid_version_for_non_bambu_printer(self):
        content = b'{"version":"0.0.0.0"}'
        updated, replacement = replace_invalid_preset_version(
            content, "preset.json", "Elegoo CC2"
        )
        self.assertEqual(replacement, "1.5.2.2")
        self.assertEqual(json.loads(updated)["version"], "1.5.2.2")

    def test_leaves_unknown_or_non_json_attachments_unchanged(self):
        invalid = b'{"version":"0.0.0.0"}'
        self.assertEqual(
            replace_invalid_preset_version(invalid, "preset.json", "Unknown")[0],
            invalid,
        )
        binary = b'not-json\x00\x01'
        self.assertEqual(
            replace_invalid_preset_version(binary, "preset.3mf", "Bambu P2S")[0],
            binary,
        )

    def test_does_not_change_missing_or_valid_version(self):
        for content in (b'{"name":"no-version"}', b'{"version":"2.8.0.4"}'):
            updated, replacement = replace_invalid_preset_version(
                content, "preset.json", "Bambu P2S"
            )
            self.assertEqual(updated, content)
            self.assertIsNone(replacement)


if __name__ == "__main__":
    unittest.main()
