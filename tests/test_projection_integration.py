"""Opt-in Feishu attachment projection test.

Run only against dedicated test records:

  $env:PRESET_WORKER_P5_INTEGRATION = "1"
  $env:P5_SUBMISSION_ID = "..."
  $env:P5_PRESET_RECORD_ID = "..."
  python -m unittest tests.test_projection_integration -v

The target record is restored after the test.  No record IDs are hard-coded.
"""

import os
import unittest

from preset_worker.services.enrichment import FeishuClient, load_env
from preset_worker.services.projection import PHOTO_PROJECTIONS, ProjectionService


@unittest.skipUnless(
    os.environ.get("PRESET_WORKER_P5_INTEGRATION") == "1",
    "opt-in integration test; use dedicated Feishu test records",
)
class FeishuProjectionIntegrationTests(unittest.TestCase):
    def test_direct_file_token_projection_is_accessible(self):
        submission_id = os.environ.get("P5_SUBMISSION_ID")
        preset_record_id = os.environ.get("P5_PRESET_RECORD_ID")
        if not submission_id or not preset_record_id:
            self.skipTest("P5_SUBMISSION_ID and P5_PRESET_RECORD_ID are required")

        client = FeishuClient(load_env())
        submission = client.get_submission(submission_id)
        preset = next(
            record
            for record in client.list_records(client.preset_table_id)
            if record.get("record_id") == preset_record_id
        )
        original = {
            spec.target_field: preset.get("fields", {}).get(spec.target_field, [])
            for spec in PHOTO_PROJECTIONS
        }
        source = submission.get("fields", {})
        expected = next(
            (item for spec in PHOTO_PROJECTIONS for item in source.get(spec.source_field, []) if item.get("file_token")),
            None,
        )
        if not expected:
            self.skipTest("dedicated Submission has no configured photo attachment")

        try:
            ProjectionService(client).project_submission_to_preset(
                submission=submission,
                preset=preset,
            )
            refreshed = next(
                record
                for record in client.list_records(client.preset_table_id)
                if record.get("record_id") == preset_record_id
            )
            target = next(
                item
                for spec in PHOTO_PROJECTIONS
                for item in refreshed.get("fields", {}).get(spec.target_field, [])
                if item.get("file_token") == expected.get("file_token")
            )
            self.assertIsNotNone(target)
            self.assertTrue(client.download_attachment(target))
        finally:
            client.update_record(client.preset_table_id, preset_record_id, original)


if __name__ == "__main__":
    unittest.main()
