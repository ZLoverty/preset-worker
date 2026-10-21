#!/usr/bin/env python3
"""Read-only, bounded inspection of a slicer project 3MF and Preset.

This is an investigation utility, not part of the production Preview path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from preset_worker.three_mf.safe_zip import SafeZipError, SafeZipReader, ZipLimits

TARGETS = (
    "filament_flow_ratio",
    "filament_max_volumetric_speed",
    "nozzle_temperature",
    "nozzle_temperature_initial_layer",
    "fan_min_speed",
    "fan_max_speed",
    "fan_cooling_layer_time",
    "slow_down_layer_time",
)
IDENTITY_KEYS = (
    "name",
    "filament_settings_id",
    "filament_ids",
    "filament_type",
    "printer_model",
    "printer_settings_id",
    "default_filament_profile",
)
READ_LIMIT = 2 * 1024 * 1024


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _candidate_values(mapping: dict[str, Any]) -> dict[str, Any]:
    keys = set(TARGETS) | set(IDENTITY_KEYS)
    related = {
        key for key in mapping
        if any(token in key.lower() for token in (
            "filament", "temperature", "fan", "cooling", "slowdown", "printer",
            "version", "application", "company", "client", "creation",
        ))
    }
    return {key: mapping[key] for key in sorted(keys | related) if key in mapping}


def _parse_json(data: bytes) -> tuple[str, dict[str, Any] | None, list[str]]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return "invalid_json", None, [str(exc)]
    if not isinstance(value, dict):
        return "json", None, ["top-level JSON value is not an object"]
    return "json", value, []


def _parse_ini(data: bytes) -> tuple[str, dict[str, Any], list[str]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return "invalid_ini", {}, [str(exc)]
    values: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(";"):
            line = line[1:].strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return "ini", values, []


def _parse_xml(data: bytes) -> tuple[str, dict[str, Any], list[str]]:
    try:
        root = ET.fromstring(data)
    except (UnicodeDecodeError, ET.ParseError) as exc:
        return "invalid_xml", {}, [str(exc)]
    values: dict[str, Any] = {}
    for element in root.iter():
        key = element.attrib.get("key")
        value = element.attrib.get("value")
        if key is not None:
            values[key] = value
    return "xml", values, []


def _detect(data: bytes, suffix: str) -> tuple[str, dict[str, Any], list[str]]:
    stripped = data.lstrip()
    if suffix.endswith(".json") or stripped.startswith((b"{", b"[")):
        kind, value, errors = _parse_json(data)
        return kind, value or {}, errors
    if suffix.endswith(".xml") or stripped.startswith(b"<"):
        return _parse_xml(data)
    return _parse_ini(data)


def _preset_report(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "status": "MISSING"}
    data = path.read_bytes()
    kind, values, errors = _detect(data, path.name.lower())
    return {
        "path": str(path),
        "status": "ERROR" if errors else "READY",
        "format": kind,
        "size": len(data),
        "sha256": _sha256(data),
        "candidates": _candidate_values(values),
        "errors": errors,
    }


def _project_report(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "status": "MISSING"}
    data = path.read_bytes()
    result: dict[str, Any] = {
        "path": str(path),
        "status": "READY",
        "size": len(data),
        "sha256": _sha256(data),
        "members": [],
        "configuration": [],
        "errors": [],
    }
    try:
        # Permit normal model members to pass the archive safety check, but
        # never read them; configuration members remain bounded by READ_LIMIT.
        limits = ZipLimits(max_entry_size=32 * 1024 * 1024, max_total_uncompressed_size=128 * 1024 * 1024)
        with SafeZipReader(data, limits) as archive:
            result["members"] = sorted(archive.names)
            for name in sorted(archive.names):
                if not name.startswith("Metadata/"):
                    continue
                if not name.endswith((".config", ".json", ".xml")):
                    continue
                try:
                    member = archive.read(name, max_bytes=READ_LIMIT)
                    kind, values, errors = _detect(member, name.lower())
                    result["configuration"].append({
                        "path": name,
                        "size": len(member),
                        "format": kind,
                        "candidates": _candidate_values(values),
                        "errors": errors,
                    })
                except (KeyError, SafeZipError, OSError) as exc:
                    result["errors"].append(f"{name}: {type(exc).__name__}")
            result["configuration"].sort(key=lambda item: item["path"])
    except (SafeZipError, OSError) as exc:
        result["status"] = "ERROR"
        result["errors"].append(type(exc).__name__ + ": " + str(exc))
    return result


def inspect(project: Path, preset: Path, slicer: str) -> dict[str, Any]:
    return {
        "schema_version": "p9d0.inspection.v1",
        "slicer": slicer,
        "project": _project_report(project),
        "preset": _preset_report(preset),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--preset", type=Path, required=True)
    parser.add_argument("--slicer", required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.project, args.preset, args.slicer), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
