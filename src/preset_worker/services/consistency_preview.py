"""Optional P9-B3 consistency work attached to Preview."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from ..slicers.contracts import Artifact
from ..three_mf.consistency import validate_bambu_consistency
from .enrichment import _attachment_list, _lookup_text, _timed_download

logger = logging.getLogger(__name__)

CONSISTENCY_REPORT_FIELD = "consistency_report"
PROJECT_FIELD = "preset 3mf"
# Conservative limit for a Bitable multiline text value. Reports are never
# truncated; an oversized report is replaced by a small error envelope.
CONSISTENCY_REPORT_MAX_BYTES = 100_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _envelope(status: str, report: dict[str, Any] | None = None, *, error: dict[str, str] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": status, "generated_at": _now()}
    if report is not None:
        payload["report"] = report
    if error is not None:
        payload["error"] = error
    return payload


def _error_text(code: str) -> str:
    payload = _envelope(
        "ERROR",
        error={"code": code, "message": "Unable to generate consistency report"},
    )
    return _serialize(payload, allow_fallback=False) or ""


def _serialize(payload: dict[str, Any], *, allow_fallback: bool = True) -> str:
    try:
        value = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        if len(value.encode("utf-8")) <= CONSISTENCY_REPORT_MAX_BYTES:
            json.loads(value)
            return value
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    if allow_fallback:
        return _error_text("CONSISTENCY_REPORT_SERIALIZATION_FAILED")
    return ""


def build_consistency_report(client: Any, record: dict[str, Any], candidate: Any) -> str:
    """Return the complete report envelope as text, or empty text when unavailable."""
    fields = record.get("fields", {})
    if _lookup_text(fields.get("slicer")) != "BambuStudio":
        return ""
    attachments = _attachment_list(fields.get(PROJECT_FIELD))
    if not attachments:
        return ""
    try:
        attachment = attachments[0]
        project = Artifact(
            content=_timed_download(client, attachment, "consistency_3mf_download"),
            filename=str(attachment.get("name") or attachment.get("file_name") or "project.3mf"),
            media_type=attachment.get("type") or attachment.get("mime_type"),
        )
        report = validate_bambu_consistency(candidate.source_artifact, project)
        return _serialize(_envelope("READY", report=report))
    except Exception as exc:  # optional boundary: never fail native Preview
        logger.warning("consistency validation failed: %s", type(exc).__name__)
        return _error_text("CONSISTENCY_VALIDATION_FAILED")


__all__ = ["CONSISTENCY_REPORT_FIELD", "build_consistency_report"]
