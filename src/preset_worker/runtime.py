"""Serial polling runtime for durable Submission workflow states."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from .services.enrichment import SubmissionEnrichment, _lookup_text
from .services.publication import SubmissionPublisher


logger = logging.getLogger(__name__)

ENRICHMENT_STATUS = "DRAFT"
PUBLICATION_STATUS = "APPROVING"


class WorkerRuntime:
    """Discover and serially dispatch actionable Submission records."""

    def __init__(
        self,
        client: Any,
        *,
        batch_size: int = 20,
        poll_interval: float = 10.0,
        enrichment_service: Callable[[str], object] | None = None,
        publication_service: Callable[[str], object] | None = None,
        stop_event: threading.Event | None = None,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        if poll_interval <= 0:
            raise ValueError("poll_interval must be > 0")
        self.client = client
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.enrichment_service = enrichment_service or SubmissionEnrichment(client).enrich_submission
        self.publication_service = publication_service or SubmissionPublisher(client).publish_submission
        self.stop_event = stop_event or threading.Event()

    @staticmethod
    def _candidate_id(record: dict[str, Any]) -> str | None:
        fields = record.get("fields", {})
        value = _lookup_text(fields.get("submission_id"))
        return value or record.get("record_id") or record.get("id")

    def _discover(self, status: str) -> list[dict[str, Any]]:
        try:
            candidates = self.client.find_submission_candidates(
                status,
                limit=self.batch_size,
            )
        except Exception:
            logger.exception("candidate discovery failed status=%s", status)
            return []
        action = "enrich" if status == ENRICHMENT_STATUS else "publish"
        for record in candidates:
            logger.info(
                "candidate discovered submission=%s action=%s",
                self._candidate_id(record) or "unknown",
                action,
            )
        return candidates

    def _dispatch(
        self,
        candidates: list[dict[str, Any]],
        *,
        action: str,
        service: Callable[[str], object],
    ) -> None:
        for record in candidates:
            submission_id = self._candidate_id(record)
            if not submission_id:
                logger.error(
                    "candidate has no submission_id record=%s action=%s",
                    record.get("record_id"),
                    action,
                )
                continue
            logger.info("processing started submission=%s action=%s", submission_id, action)
            try:
                service(str(submission_id))
            except Exception:
                logger.exception("processing failed submission=%s action=%s", submission_id, action)
                continue
            logger.info("processing completed submission=%s action=%s", submission_id, action)

    def run_once(self) -> None:
        """Process one bounded cycle; never sleeps or loops indefinitely."""
        enrichment_candidates = self._discover(ENRICHMENT_STATUS)
        self._dispatch(
            enrichment_candidates,
            action="enrich",
            service=self.enrichment_service,
        )
        publication_candidates = self._discover(PUBLICATION_STATUS)
        self._dispatch(
            publication_candidates,
            action="publish",
            service=self.publication_service,
        )

    def request_stop(self) -> None:
        logger.info("shutdown requested")
        self.stop_event.set()

    def run(self) -> None:
        logger.info(
            "Worker starting poll_interval=%s batch_size=%s",
            self.poll_interval,
            self.batch_size,
        )
        try:
            while not self.stop_event.is_set():
                self.run_once()
                self.stop_event.wait(self.poll_interval)
        finally:
            logger.info("Worker stopped")
