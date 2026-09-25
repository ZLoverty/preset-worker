import threading
import unittest

from preset_worker.runtime import ENRICHMENT_STATUS, PUBLICATION_STATUS, WorkerRuntime


class FakeRepository:
    def __init__(self):
        self.records = {
            ENRICHMENT_STATUS: [
                {"record_id": "r1", "fields": {"submission_id": "S1"}},
                {"record_id": "r2", "fields": {"submission_id": "S2"}},
                {"record_id": "r3", "fields": {"submission_id": "S3"}},
            ],
            "DRAFT": [
                {"record_id": "draft-1", "fields": {"submission_id": "D1"}},
            ],
            PUBLICATION_STATUS: [
                {"record_id": "r4", "fields": {"submission_id": "S4"}},
            ],
        }
        self.queries = []

    def find_submission_candidates(self, status, *, limit):
        self.queries.append((status, limit))
        return self.records[status][:limit]


class RuntimeTests(unittest.TestCase):
    def test_run_once_dispatches_both_categories_in_order(self):
        repo = FakeRepository()
        calls = []
        runtime = WorkerRuntime(
            repo,
            batch_size=2,
            enrichment_service=lambda submission_id: calls.append(("enrich", submission_id)),
            publication_service=lambda submission_id: calls.append(("publish", submission_id)),
        )
        runtime.run_once()
        self.assertEqual(calls, [("enrich", "S1"), ("enrich", "S2"), ("publish", "S4")])
        self.assertEqual(repo.queries, [(ENRICHMENT_STATUS, 2), (PUBLICATION_STATUS, 2)])

    def test_failure_isolated_and_not_retried_in_same_cycle(self):
        repo = FakeRepository()
        calls = []

        def enrich(submission_id):
            calls.append(submission_id)
            if submission_id == "S2":
                raise RuntimeError("temporary failure")

        WorkerRuntime(
            repo,
            batch_size=3,
            enrichment_service=enrich,
            publication_service=lambda _submission_id: None,
        ).run_once()
        self.assertEqual(calls, ["S1", "S2", "S3"])

    def test_draft_is_not_an_actionable_state(self):
        repo = FakeRepository()
        calls = []
        WorkerRuntime(
            repo,
            enrichment_service=lambda submission_id: calls.append(("enrich", submission_id)),
            publication_service=lambda submission_id: calls.append(("publish", submission_id)),
        ).run_once()
        self.assertNotIn(("enrich", "D1"), calls)
        self.assertEqual(repo.queries, [(ENRICHMENT_STATUS, 20), (PUBLICATION_STATUS, 20)])

    def test_invalid_runtime_configuration(self):
        with self.assertRaises(ValueError):
            WorkerRuntime(FakeRepository(), batch_size=0)
        with self.assertRaises(ValueError):
            WorkerRuntime(FakeRepository(), poll_interval=0)

    def test_run_uses_interruptible_wait_until_stop(self):
        repo = FakeRepository()
        stop = threading.Event()
        cycles = []

        runtime = WorkerRuntime(
            repo,
            stop_event=stop,
            enrichment_service=lambda _submission_id: None,
            publication_service=lambda _submission_id: None,
        )
        original = runtime.run_once

        def one_cycle():
            cycles.append(True)
            original()
            stop.set()

        runtime.run_once = one_cycle
        runtime.run()
        self.assertEqual(len(cycles), 1)


if __name__ == "__main__":
    unittest.main()
