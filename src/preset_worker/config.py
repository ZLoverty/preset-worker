"""Configuration loading without import-time network access."""

from pathlib import Path

from preset_worker.adapters.feishu import FeishuClient
from preset_worker.services.enrichment import load_env


def load_config(env_path: Path | str = ".env") -> dict[str, str]:
    return load_env(Path(env_path))


def build_feishu_client(env_path: Path | str = ".env") -> FeishuClient:
    return FeishuClient(load_config(env_path))
