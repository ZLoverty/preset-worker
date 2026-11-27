import hashlib
import unittest

from scripts.compare_attachment_tables import (
    attachment_fingerprints,
    attachment_url,
    compare_attachment_lists,
    compare_tables,
    normalize_identity,
    normalize_printer,
    record_key,
)


class CompareAttachmentTablesTests(unittest.TestCase):
    def test_normalizes_case_unicode_and_separators(self):
        self.assertEqual(normalize_identity(" PI_Code-001 "), "pi_code001".replace("_", ""))
        self.assertEqual(normalize_identity("Bambu P-2S"), "bambup2s")

    def test_record_key_uses_pi_code_and_printer(self):
        self.assertEqual(record_key({"PI Code": " PI_001 ", "Printer": "Bambu P-2S"}), ("pi001", "bambup2s"))
        self.assertEqual(normalize_printer("bbl P-2S"), "bambup2s")
        self.assertEqual(normalize_printer("Anycubic Kobra S1"), "anycubics1")
        self.assertEqual(normalize_printer("Anycubic S1"), "anycubics1")
        self.assertEqual(record_key({"PI Code": "PI_001", "Printer": "bbl P-2S"}), ("pi001", "bambup2s"))
        self.assertIsNone(record_key({"PI Code": "PI_001"}))

    def test_attachment_fingerprints_and_content_comparison(self):
        files = {"a": b"same", "b": b"same", "c": b"different"}
        download = lambda item: files[item["file_token"]]
        left, errors = attachment_fingerprints([{"name": "preset.json", "file_token": "a"}], download)
        right, _ = attachment_fingerprints([{"name": "renamed.json", "file_token": "b"}], download)
        self.assertEqual(errors, [])
        self.assertEqual(left[0]["sha256"], hashlib.sha256(b"same").hexdigest())
        self.assertEqual(compare_attachment_lists(left, right), "same_content_different_name")

    def test_attachment_url_prefers_direct_url_and_supports_token_shapes(self):
        self.assertEqual(attachment_url({"url": "https://example.test/file"}), "https://example.test/file")
        self.assertEqual(attachment_url({"tmp_url": "https://example.test/tmp"}), "https://example.test/tmp")
        self.assertIn("token-1", attachment_url({"attachmentToken": "token-1"}))
        self.assertIsNone(attachment_url({"name": "missing"}))

    def test_compare_tables_reports_missing_and_different_records(self):
        files = {
            "same-a": b'{"name":"source","speed":50}',
            "same-b": b'{"name":"target","speed":50,"added_by_target":true}',
            "different": b'{"speed":60}',
        }
        download = lambda item: files[item["file_token"]]
        source = [
            {"record_id": "s1", "fields": {"PI Code": "PI_1", "Printer": "Bambu P2S", "preset data": [{"file_token": "same-a"}]}},
            {"record_id": "s2", "fields": {"PI Code": "PI_2", "Printer": "Bambu P2S", "preset data": [{"file_token": "different"}]}},
        ]
        target = [
            {"record_id": "t1", "fields": {"pi_code": "pi1", "printer": "bambu-p2s", "preset data": [{"file_token": "same-b"}]}},
            {"record_id": "t3", "fields": {"PI Code": "PI_3", "Printer": "Bambu P2S", "preset data": []}},
        ]
        report = compare_tables(source, target, download)
        statuses = {item["key"]: item["status"] for item in report["results"]}
        self.assertEqual(statuses["pi1::bambup2s"], "same_parameters")
        self.assertEqual(statuses["pi2::bambup2s"], "source_only")
        self.assertEqual(statuses["pi3::bambup2s"], "target_only")

    def test_compare_tables_ignores_metadata_and_target_only_fields(self):
        files = {
            "source": b'{"name":"old","version":"1","speed":50}',
            "target": b'{"name":"renamed","version":"2","speed":50,"target_field":true}',
        }
        download = lambda item: files[item["file_token"]]
        records = [{
            "record_id": "r1",
            "fields": {
                "PI Code": "PI_1",
                "Printer": "Bambu P2S",
                "preset data": [{"file_token": "source"}],
            },
        }]
        target = [{
            "record_id": "r2",
            "fields": {
                "PI Code": "PI_1",
                "Printer": "bbl p2s",
                "preset data": [{"file_token": "target"}],
            },
        }]
        report = compare_tables(records, target, download)
        self.assertEqual(report["results"][0]["status"], "same_parameters")
        self.assertEqual(report["results"][0]["parameter_differences"], [])


if __name__ == "__main__":
    unittest.main()
