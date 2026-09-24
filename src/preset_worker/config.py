"""Configuration loading without import-time network access."""

from pathlib import Path
from dataclasses import dataclass

from preset_worker.adapters.feishu import FeishuClient
from preset_worker.services.enrichment import load_env


@dataclass(frozen=True)
class WorkerRuntimeConfig:
    poll_interval: float = 10.0
    batch_size: int = 20


def load_runtime_config(env_path: Path | str = ".env") -> WorkerRuntimeConfig:
    values = load_config(env_path)
    try:
        poll_interval = float(values.get("PRESET_WORKER_POLL_INTERVAL", "10"))
        batch_size = int(values.get("PRESET_WORKER_BATCH_SIZE", "20"))
    except ValueError as exc:
        raise ValueError(
            "PRESET_WORKER_POLL_INTERVAL must be a number and "
            "PRESET_WORKER_BATCH_SIZE must be an integer"
        ) from exc
    if poll_interval <= 0:
        raise ValueError("PRESET_WORKER_POLL_INTERVAL must be > 0")
    if batch_size <= 0:
        raise ValueError("PRESET_WORKER_BATCH_SIZE must be > 0")
    return WorkerRuntimeConfig(poll_interval=poll_interval, batch_size=batch_size)


def load_config(env_path: Path | str = ".env") -> dict[str, str]:
    return load_env(Path(env_path))


def build_feishu_client(env_path: Path | str = ".env") -> FeishuClient:
    return FeishuClient(load_config(env_path))
