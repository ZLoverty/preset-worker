import copy
import unittest

from preset_worker.services.projection import AttachmentProjection, ProjectionService


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

    def test_empty_source_clears_target(self):
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


if __name__ == "__main__":
    unittest.main()
