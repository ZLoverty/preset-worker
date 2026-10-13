"""Diagnostic timing helpers for one Preview attempt."""

from __future__ import annotations

import contextvars
import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

logger = logging.getLogger(__name__)
_current_timing: contextvars.ContextVar["PreviewTiming | None"] = contextvars.ContextVar(
    "preview_timing", default=None
)


@dataclass
class PreviewTiming:
    submission_id: str
    attempt_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started_at: float = field(default_factory=time.perf_counter)
    stage_totals: dict[str, float] = field(default_factory=dict)
    api_calls: int = 0
    retry_count: int = 0
    retry_backoff_ms: float = 0.0

    @contextmanager
    def stage(self, name: str, *, summary_key: str | None = None) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            if summary_key:
                self.stage_totals[summary_key] = self.stage_totals.get(summary_key, 0.0) + duration_ms
            logger.info(
                "preview_stage stage=%s duration_ms=%.1f submission_id=%s attempt_id=%s",
                name, duration_ms, self.submission_id, self.attempt_id,
            )

    def api(self, *, operation: str, method: str, endpoint: str, duration_ms: float,
            status: int | str, retry_count: int, succeeded: bool,
            request_bytes: int = 0, response_bytes: int = 0) -> None:
        self.api_calls += 1
        self.retry_count += retry_count
        logger.info(
            "preview_api operation=%s method=%s endpoint=%s duration_ms=%.1f status=%s retry_count=%s retry_backoff_ms=0.0 succeeded=%s request_bytes=%s response_bytes=%s submission_id=%s attempt_id=%s",
            operation, method, endpoint, duration_ms, status, retry_count,
            succeeded, request_bytes, response_bytes, self.submission_id, self.attempt_id,
        )

    def summary(self) -> None:
        total_ms = (time.perf_counter() - self.started_at) * 1000
        other_ms = max(0.0, total_ms - sum(self.stage_totals.values()))
        logger.info(
            "preview_timing_summary submission_id=%s attempt_id=%s total_ms=%.1f feishu_read_ms=%.1f attachment_download_ms=%.1f processor_ms=%.1f diff_ms=%.1f attachment_upload_ms=%.1f feishu_write_ms=%.1f retry_backoff_ms=%.1f other_ms=%.1f api_call_count=%s retry_count=%s",
            self.submission_id, self.attempt_id, total_ms,
            self.stage_totals.get("feishu_read_ms", 0.0),
            self.stage_totals.get("attachment_download_ms", 0.0),
            self.stage_totals.get("processor_ms", 0.0),
            self.stage_totals.get("diff_ms", 0.0),
            self.stage_totals.get("attachment_upload_ms", 0.0),
            self.stage_totals.get("feishu_write_ms", 0.0),
            self.retry_backoff_ms, other_ms, self.api_calls, self.retry_count,
        )


@contextmanager
def preview_timing(submission_id: str) -> Iterator[PreviewTiming]:
    timing = PreviewTiming(submission_id=submission_id)
    token = _current_timing.set(timing)
    try:
        yield timing
    finally:
        timing.summary()
        _current_timing.reset(token)


def current_timing() -> PreviewTiming | None:
    return _current_timing.get()
