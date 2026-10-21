"""Safe, minimal extraction of PrusaSlicer project filament settings."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .models import FilamentSlot, ProjectContext
from .safe_zip import SafeZipReader, archive_sha256

PROJECT_ENTRY = "Metadata/Slic3r_PE.config"
TARGET_NATIVE_KEYS = (
    "temperature",
    "first_layer_temperature",
    "min_fan_speed",
    "max_fan_speed",
    "fan_below_layer_time",
    "slowdown_below_layer_time",
)


@dataclass(frozen=True)
class PrusaRawSetting:
    name: str
    raw_value: str
    values: list[str]
    source_path: str
    line_number: int


@dataclass
class PrusaProjectSnapshot:
    entries: list[str]
    archive_sha256: str
    settings: dict[str, PrusaRawSetting] = field(default_factory=dict)
    filament_slots: list[FilamentSlot] = field(default_factory=list)
    project_context: ProjectContext = field(default_factory=ProjectContext)
    issues: list[dict[str, str]] = field(default_factory=list)

    @property
    def project_values(self) -> dict[str, list[str]]:
        return {name: setting.values for name, setting in self.settings.items() if name in TARGET_NATIVE_KEYS}


def _split_values(value: str) -> list[str]:
    """Split Prusa's semicolon lists without splitting quoted semicolons."""
    result: list[str] = []
    current: list[str] = []
    quoted = False
    escaped = False
    for char in value:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\" and quoted:
            current.append(char)
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
            current.append(char)
            continue
        if char == ";" and not quoted:
            result.append("".join(current))
            current = []
        else:
            current.append(char)
    result.append("".join(current))
    return result


def _split_comma_values(value: str) -> list[str]:
    result: list[str] = []
    current: list[str] = []
    quoted = False
    for char in value:
        if char == '"':
            quoted = not quoted
        if char == "," and not quoted:
            result.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    result.append("".join(current).strip())
    return result


def _parse_config(data: bytes) -> dict[str, PrusaRawSetting]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("PrusaSlicer project config is not valid UTF-8") from exc
    settings: dict[str, PrusaRawSetting] = {}
    assignment = re.compile(r"^\s*;\s*(?P<key>[^=\s][^=]*?)\s*=\s?(?P<value>.*)$")
    for line_number, line in enumerate(text.splitlines(), 1):
        match = assignment.match(line)
        if not match:
            continue
        name = match.group("key").strip()
        raw_value = match.group("value")
        values = _split_comma_values(raw_value) if name in TARGET_NATIVE_KEYS and "," in raw_value else _split_values(raw_value)
        settings[name] = PrusaRawSetting(name, raw_value, values, PROJECT_ENTRY, line_number)
    return settings


def parse_prusa_3mf(artifact: Any, *, limits: Any = None) -> PrusaProjectSnapshot:
    data = artifact.content if hasattr(artifact, "content") else artifact
    if not isinstance(data, bytes):
        raise TypeError("3MF artifact must contain bytes")
    with SafeZipReader(data, limits) as archive:
        snapshot = PrusaProjectSnapshot(archive.names, archive_sha256(data))
        if PROJECT_ENTRY not in archive.names:
            snapshot.issues.append({"code": "MISSING_PRUSA_PROJECT_SETTINGS", "message": PROJECT_ENTRY})
            return snapshot
        try:
            config_bytes = archive.read(PROJECT_ENTRY)
            snapshot.settings = _parse_config(config_bytes)
        except ValueError as exc:
            snapshot.issues.append({"code": "INVALID_PRUSA_PROJECT_SETTINGS", "message": str(exc)})
            return snapshot
        identity = snapshot.settings.get("filament_settings_id")
        identities = identity.values if identity else []
        types = snapshot.settings.get("filament_type")
        type_values = types.values if types else []
        for index, settings_id in enumerate(identities):
            snapshot.filament_slots.append(FilamentSlot(
                index + 1,
                settings_id,
                type_values[index] if index < len(type_values) else None,
                None,
                {"source_path": PROJECT_ENTRY, "filament_config_index": index},
            ))
        printer_model = snapshot.settings.get("printer_model")
        snapshot.project_context = ProjectContext(
            printer_model=printer_model.values[0] if printer_model and printer_model.values else None,
            printer_settings_id=(snapshot.settings.get("printer_settings_id").values[0] if snapshot.settings.get("printer_settings_id") else None),
            raw={name: setting.raw_value for name, setting in snapshot.settings.items()},
        )
        try:
            header = config_bytes.decode("utf-8", errors="strict")
            version_match = re.search(r"generated by PrusaSlicer\s+([^\s]+)", header)
            if version_match:
                snapshot.project_context.slicer_version = version_match.group(1)
        except UnicodeDecodeError:
            pass
        return snapshot
