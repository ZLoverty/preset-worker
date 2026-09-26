"""Stable application entry point for Submission preview processing."""

from pathlib import Path
from typing import Any

from .enrichment import FeishuClient, load_env
from .preview import PreviewService


def preview_submission(
    submission_id: str,
    *,
    client: Any | None = None,
    env_path: Path | str = ".env",
):
    if client is None:
        client = FeishuClient(load_env(Path(env_path)))
    return PreviewService(client).preview_submission(submission_id)
