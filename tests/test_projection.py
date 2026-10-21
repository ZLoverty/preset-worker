import copy
import unittest

from preset_worker.services.projection import AttachmentProjection, ProjectionService, merge_photos


class FakeProjectionClient:
    preset_table_id = "preset"

    def __init__(self):
        self.calls = []

    def update_record(self, table_id, record_id, fields):
        self.calls.append((table_id, record_id, copy.deepcopy(fields)))


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeProjectionClient()
        self.service = ProjectionService(
            self.client,
            projections=(
                AttachmentProjection("standard_photo", "standard_photo"),
                AttachmentProjection("other_photos", "other_photos"),
            ),
        )
        self.submission = {
            "record_id": "submission-1",
            "fields": {
                "standard_photo": [{"file_token": "new-standard"}],
                "other_photos": [
                    {"file_token": "new-1"},
                    {"file_token": "new-2"},
                ],
            },
        }
        self.preset = {
            "record_id": "preset-1",
            "fields": {
                "standard_photo": [{"file_token": "old-standard"}],
                "other_photos": [{"file_token": "old"}],
            },
        }

    def test_full_replacement_and_order(self):
        self.service.project_submission_to_preset(submission=self.submission, preset=self.preset)
        fields = self.client.calls[-1][2]
        self.assertEqual(fields["standard_photo"], [{"file_token": "new-standard"}])
        self.assertEqual(
            fields["other_photos"],
            [{"file_token": "new-1"}, {"file_token": "new-2"}],
        )

    def test_empty_source_clears_custom_projection_fields(self):
        self.submission["fields"]["standard_photo"] = []
        self.submission["fields"]["other_photos"] = None
        self.service.project_submission_to_preset(submission=self.submission, preset=self.preset)
        self.assertEqual(self.client.calls[-1][2], {"standard_photo": [], "other_photos": []})

    def test_repeat_is_idempotent_and_does_not_mutate_source(self):
        source_before = copy.deepcopy(self.submission["fields"])
        self.service.project_submission_to_preset(submission=self.submission, preset=self.preset)
        self.service.project_submission_to_preset(submission=self.submission, preset=self.preset)
        self.assertEqual(self.submission["fields"], source_before)
        self.assertEqual(self.client.calls[0][2], self.client.calls[1][2])

    def test_preset_3mf_uses_the_same_attachment_projection(self):
        service = ProjectionService(self.client)
        submission = {"record_id": "submission-3mf", "fields": {"preset 3mf": [{"file_token": "measured-3mf"}]}}
        preset = {"record_id": "preset-3mf", "fields": {}}
        service.project_submission_to_preset(submission=submission, preset=preset)
        self.assertEqual(
            self.client.calls[-1][2]["preset 3mf"],
            [{"file_token": "measured-3mf"}],
        )

    def test_default_photo_patch_preserves_unsubmitted_photo_fields(self):
        service = ProjectionService(self.client)
        submission = {
            "record_id": "submission-photo-patch",
            "fields": {"温度塔照片": [{"file_token": "new-temperature"}]},
        }
        preset = {
            "record_id": "preset-photo-patch",
            "fields": {
                "温度塔照片": [{"file_token": "old-temperature"}],
                "流量比例照片": [{"file_token": "old-flow"}],
            },
        }
        service.project_submission_to_preset(submission=submission, preset=preset)
        fields = self.client.calls[-1][2]
        self.assertEqual(fields["温度塔照片"], [{"file_token": "new-temperature"}])
        self.assertEqual(fields["流量比例照片"], [{"file_token": "old-flow"}])

    def test_merge_photos_replaces_only_submitted_fields(self):
        result = merge_photos(
            {"temperature": [{"file_token": "A"}], "flow": [{"file_token": "B"}]},
            {"temperature": [{"file_token": "D"}], "flow": []},
            ("temperature", "flow"),
        )
        self.assertEqual(result, {"temperature": [{"file_token": "D"}], "flow": [{"file_token": "B"}]})

    def test_merge_photos_preserves_missing_and_none(self):
        result = merge_photos(
            {"temperature": [{"file_token": "A"}], "flow": [{"file_token": "B"}]},
            {"flow": None},
            ("temperature", "flow"),
        )
        self.assertEqual(result["temperature"], [{"file_token": "A"}])
        self.assertEqual(result["flow"], [{"file_token": "B"}])

    def test_merge_photos_preserves_multiple_new_attachments(self):
        result = merge_photos(
            {},
            {"temperature": [{"file_token": "A"}, {"file_token": "B"}]},
            ("temperature",),
        )
        self.assertEqual(
            result["temperature"],
            [{"file_token": "A"}, {"file_token": "B"}],
        )


if __name__ == "__main__":
    unittest.main()
