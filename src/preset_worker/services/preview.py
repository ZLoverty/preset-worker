"""M1-B preview processing for explicit PREVIEW_REQUESTED submissions."""

from __future__ import annotations

import json
from contextlib import nullcontext
from typing import Any

from ..diff import serialize_unified_diff
from ..profiling import current_timing, preview_timing
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
        timing = current_timing()
        with timing.stage("canonical_attachment") if timing else nullcontext():
            file_token = self.candidate_processor._canonical_attachment(
                record, submission_id, candidate.canonical_artifact
            )
        record_id = record["record_id"]
        # Persist the complete result before handing ownership back to Miaoda.
        fields = {
                "operation": candidate.operation,
                "base_version_id": [candidate.base_version_record_id]
                if candidate.base_version_record_id
                else [],
                "canonical_json": [{"file_token": file_token}],
                "diff": serialize_unified_diff(candidate.diff),
                "validation": json.dumps(candidate.validation, ensure_ascii=False),
        }
        fields["status"] = DRAFT_STATUS
        with timing.stage("write_preview_result_and_status", summary_key="feishu_write_ms") if timing else nullcontext():
            self.client.update_submission(record_id, fields)

    def _write_candidate_failure(
        self,
        record: dict[str, Any],
        exc: Exception,
    ) -> None:
        validation = self._candidate_validation(exc)
        record_id = record["record_id"]
        timing = current_timing()
        fields = {
            "validation": json.dumps(validation, ensure_ascii=False),
            "status": DRAFT_STATUS,
        }
        with timing.stage("write_preview_failure_and_status", summary_key="feishu_write_ms") if timing else nullcontext():
            self.client.update_submission(
                record_id,
                fields,
            )

    def preview_submission(
        self,
        submission_id: str,
        *,
        record: dict[str, Any] | None = None,
    ) -> CandidateResult:
        """Preview one authoritative PREVIEW_REQUESTED Submission."""
        with preview_timing(submission_id):
            timing = current_timing()
            if record is None:
                with timing.stage("get_submission", summary_key="feishu_read_ms") if timing else nullcontext():
                    record = self.client.get_submission(submission_id)
            else:
                # The polling query already returned this complete record.
                with timing.stage("reuse_discovered_submission") if timing else nullcontext():
                    record = record
            fields = record.get("fields", {})
            if fields.get("status") != PREVIEW_REQUESTED_STATUS:
                raise RuntimeError(
                    f"Submission is {fields.get('status', 'unknown')} and is not eligible for preview."
                )
            try:
                with timing.stage("candidate_processing") if timing else nullcontext():
                    candidate = self.candidate_processor.process_candidate(record, submission_id)
            except (CandidateFailure, ValidationFailure, UnsupportedSlicerError) as exc:
                self._write_candidate_failure(record, exc)
                raise
            self._write_preview_result(record, submission_id, candidate)
            return candidate


__all__ = ["PreviewService", "PREVIEW_REQUESTED_STATUS"]
