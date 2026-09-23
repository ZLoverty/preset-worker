"""Stable application entry point for Submission enrichment."""

from pathlib import Path
from typing import Any

from .enrichment import FeishuClient, SubmissionEnrichment, load_env


def enrich_submission(submission_id: str, *, client: Any | None = None, env_path: Path | str = ".env"):
    if client is None:
        client = FeishuClient(load_env(Path(env_path)))
    return SubmissionEnrichment(client).enrich_submission(submission_id)
