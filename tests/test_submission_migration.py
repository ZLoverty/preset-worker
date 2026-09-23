import unittest

from scripts.migrate_to_submission import (
    PHOTO_FIELDS,
    build_target_fields,
    migration_id,
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
        self.assertEqual(fields["uploaded_json"], [{"file_token": "json-1"}])
        self.assertEqual(fields["preset 3mf"], [{"file_token": "3mf-1"}])
        self.assertNotIn("ignored", fields)
        self.assertEqual(
            set(fields)
            - {"submission_id", "status", "pi_code", "printer", "冷却参数照片", "其他照片", "uploaded_json", "preset 3mf"},
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


if __name__ == "__main__":
    unittest.main()
