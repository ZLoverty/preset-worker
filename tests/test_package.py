import importlib
import unittest

from preset_worker import __version__
from preset_worker.cli import main
from preset_worker.services.enrichment_api import enrich_submission
from preset_worker.services.publication_api import publish_submission


class PackageTests(unittest.TestCase):
    def test_package_import_has_version(self):
        self.assertTrue(__version__)
        self.assertIs(importlib.import_module("preset_worker"), importlib.import_module("preset_worker"))

    def test_service_imports_are_stable(self):
        self.assertTrue(callable(enrich_submission))
        self.assertTrue(callable(publish_submission))

    def test_cli_enrich_routes_submission(self):
        calls = []
        result = main(["enrich", "S123"], enrich_service=lambda submission_id: calls.append(submission_id) or {"ok": True})
        self.assertEqual(result, 0)
        self.assertEqual(calls, ["S123"])

    def test_cli_publish_routes_submission(self):
        calls = []
        result = main(["publish", "S123"], publish_service=lambda submission_id: calls.append(submission_id) or {"ok": True})
        self.assertEqual(result, 0)
        self.assertEqual(calls, ["S123"])

    def test_cli_run_once_routes_runtime(self):
        class FakeRuntime:
            def __init__(self):
                self.calls = 0

            def run_once(self):
                self.calls += 1

        runtime = FakeRuntime()
        result = main(["run-once"], runtime_factory=lambda _env: runtime)
        self.assertEqual(result, 0)
        self.assertEqual(runtime.calls, 1)

    def test_cli_invalid_command(self):
        with self.assertRaises(SystemExit):
            main(["unknown", "S123"])


if __name__ == "__main__":
    unittest.main()
