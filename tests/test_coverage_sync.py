import copy
import unittest

from preset_worker.services.coverage_sync import (
    CoverageFieldConfig,
    CoverageTableConfig,
    build_plan,
    summarize,
    synchronize,
)


def pi(record_id, code, importance, status="Active"):
    enabled = "yes" if status == "Active" else "no"
    return {"record_id": record_id, "fields": {"PI Code": code, "Importance": importance, "enabled": enabled}}


def printer(record_id, name, importance):
    return {"record_id": record_id, "fields": {"all_printers": name, "Importance": importance, "enabled": "yes"}}


def target(record_id, key, active=True, importance=1, **manual):
    fields = {
        "coverage_key": key,
        "pi_code": [{"record_ids": ["pi-1"]}],
        "printer": [{"record_ids": ["printer-1"]}],
        "importance": importance,
        "active": active,
    }
    fields.update(manual)
    return {"record_id": record_id, "fields": fields}


class CoverageSyncTests(unittest.TestCase):
    def setUp(self):
        self.config = CoverageTableConfig("pi", "printer", "coverage")
        self.field_names = {"coverage_key", "pi_code", "printer", "importance", "active"}

    def test_builds_full_cartesian_product_including_zero_importance(self):
        plans, existing, errors, enabled_pis, enabled_printers, _ = build_plan(
            [pi("pi-1", "PI-A", 0), pi("pi-2", "PI-B", 1, "EOL Complete")],
            [printer("printer-1", "Printer-A", 0), printer("printer-2", "Printer-B", 1)],
            [],
            self.config,
            field_names=self.field_names,
        )
        self.assertFalse(errors)
        self.assertEqual(len(plans), 4)
        self.assertEqual({plan.key for plan in plans}, {"PI-A@Printer-A", "PI-A@Printer-B", "PI-B@Printer-A", "PI-B@Printer-B"})
        self.assertEqual({plan.importance for plan in plans}, {0, 1, 2})
        self.assertEqual(sum(plan.active for plan in plans), 2)
        self.assertEqual((enabled_pis, enabled_printers), (1, 2))
        self.assertEqual(existing, {})

    def test_duplicate_sources_and_targets_are_validation_errors(self):
        _, _, errors, _, _, _ = build_plan(
            [pi("pi-1", "PI-A", 0), pi("pi-2", "pi-a", 1)],
            [printer("printer-1", "Printer-A", 0)],
            [target("target-1", "PI-A@Printer-A"), target("target-2", "pi-a@printer-a")],
            self.config,
            field_names=self.field_names,
        )
        self.assertTrue(any("duplicate PI Code identity" in error for error in errors))
        self.assertTrue(any("duplicate CoverageTarget key" in error for error in errors))

    def test_summary_counts_reactivation_and_deactivation(self):
        plans, existing, errors, enabled_pis, enabled_printers, _ = build_plan(
            [pi("pi-1", "PI-A", 1)],
            [printer("printer-1", "Printer-A", 0), printer("printer-2", "Printer-B", 1)],
            [target("target-1", "PI-A@Printer-A", active=False, importance=0, owner="keep"), target("target-2", "Old@Printer", active=True)],
            self.config,
            field_names=self.field_names,
        )
        summary = summarize(plans, existing, self.config, errors, enabled_pis, enabled_printers)
        self.assertEqual(summary["records_to_create"], 1)
        self.assertEqual(summary["records_to_update"], 1)
        self.assertEqual(summary["records_to_deactivate"], 1)
        self.assertEqual(summary["expected_active_combination_count"], 2)

    def test_apply_only_writes_managed_fields(self):
        class FakeClient:
            def __init__(self):
                self.records = {
                    "pi": [pi("pi-1", "PI-A", 1)],
                    "printer": [printer("printer-1", "Printer-A", 0)],
                    "coverage": [target("target-1", "PI-A@Printer-A", active=False, importance=0, owner="keep")],
                }
                self.created = []
                self.updated = []

            def list_records(self, table_id):
                return copy.deepcopy(self.records[table_id])

            def list_fields(self, _table_id):
                return [
                    {"field_name": "coverage_key", "ui_type": "Text"},
                    {"field_name": "pi_code", "ui_type": "SingleLink"},
                    {"field_name": "printer", "ui_type": "SingleLink"},
                    {"field_name": "importance", "ui_type": "Number"},
                    {"field_name": "active", "ui_type": "Checkbox"},
                ]

            def batch_create_records(self, table_id, records):
                self.created.extend(records)
                return []

            def batch_update_records(self, table_id, records):
                self.updated.extend(records)
                return []

        client = FakeClient()
        config = CoverageTableConfig("pi", "printer", "coverage")
        result = synchronize(client, config, dry_run=False)
        self.assertTrue(result["applied"])
        self.assertEqual(client.created, [])
        self.assertEqual(len(client.updated), 1)
        self.assertEqual(client.updated[0]["fields"], {"active": True})
        self.assertNotIn("owner", client.updated[0]["fields"])

    def test_source_read_failure_never_deactivates(self):
        class BrokenClient:
            def list_records(self, table_id):
                if table_id == "pi":
                    raise RuntimeError("read failed")
                return []

        result = synchronize(BrokenClient(), self.config, dry_run=False)
        self.assertEqual(result["records_to_deactivate"], 0)
        self.assertTrue(any("no writes or deactivation allowed" in error for error in result["validation_errors"]))

    def test_missing_schema_is_reported_before_apply(self):
        _, _, errors, _, _, _ = build_plan([], [], [], self.config, field_names={"coverage_key", "pi_code", "printer", "importance"})
        self.assertTrue(any("active" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
