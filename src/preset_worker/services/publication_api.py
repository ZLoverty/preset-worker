"""Stable application entry point for Submission publication."""

from pathlib import Path
from typing import Any

from .enrichment import FeishuClient, load_env
from .publication import SubmissionPublisher


def publish_submission(submission_id: str, *, client: Any | None = None, env_path: Path | str = ".env"):
    if client is None:
        client = FeishuClient(load_env(Path(env_path)))
    return SubmissionPublisher(client).publish_submission(submission_id)
