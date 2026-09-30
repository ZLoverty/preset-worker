"""M1-B preview processing for explicit PREVIEW_REQUESTED submissions."""

from __future__ import annotations

import json
from typing import Any

from .enrichment import (
    CandidateFailure,
    CandidateResult,
    SubmissionEnrichment,
    UnsupportedSlicerError,
    ValidationFailure,
)


PREVIEW_REQUESTED_STATUS = "PREVIEW_REQUESTED"
DRAFT_STATUS = "DRAFT"


class PreviewService:
    """Compute and persist a preview without creating publication artifacts."""

    def __init__(self, client: Any):
        self.client = client
        self.candidate_processor = SubmissionEnrichment(client)

    @staticmethod
    def _candidate_validation(exc: Exception) -> dict[str, Any]:
        if isinstance(exc, ValidationFailure):
            return exc.validation
        return {"valid": False, "errors": [str(exc)], "warnings": []}

    def _write_preview_result(
        self,
        record: dict[str, Any],
        submission_id: str,
        candidate: CandidateResult,
    ) -> None:
        file_token = self.candidate_processor._canonical_attachment(
            record,
            submission_id,
            candidate.canonical_artifact,
        )
        record_id = record["record_id"]
        # Persist the complete result before handing ownership back to Miaoda.
        self.client.update_submission(
            record_id,
            {
                "operation": candidate.operation,
                "base_version_id": [candidate.base_version_record_id]
                if candidate.base_version_record_id
                else [],
                "canonical_json": [{"file_token": file_token}],
                "diff": json.dumps(candidate.diff, ensure_ascii=False),
                "validation": json.dumps(candidate.validation, ensure_ascii=False),
            },
        )
        self.client.update_submission(record_id, {"status": DRAFT_STATUS})

    def _write_candidate_failure(
        self,
        record: dict[str, Any],
        exc: Exception,
    ) -> None:
        validation = self._candidate_validation(exc)
        record_id = record["record_id"]
        self.client.update_submission(
            record_id,
            {"validation": json.dumps(validation, ensure_ascii=False)},
        )
        self.client.update_submission(record_id, {"status": DRAFT_STATUS})

    def preview_submission(self, submission_id: str) -> CandidateResult:
        """Preview one authoritative PREVIEW_REQUESTED Submission."""
        record = self.client.get_submission(submission_id)
        fields = record.get("fields", {})
        if fields.get("status") != PREVIEW_REQUESTED_STATUS:
            raise RuntimeError(
                f"Submission is {fields.get('status', 'unknown')} and is not eligible for preview."
            )
        try:
            candidate = self.candidate_processor.process_candidate(record, submission_id)
        except (CandidateFailure, ValidationFailure, UnsupportedSlicerError) as exc:
            self._write_candidate_failure(record, exc)
            raise
        self._write_preview_result(record, submission_id, candidate)
        return candidate


__all__ = ["PreviewService", "PREVIEW_REQUESTED_STATUS"]
