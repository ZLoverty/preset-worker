"""Isolated PrusaSlicer INI/3MF consistency validation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ..slicers.contracts import Artifact, ProcessingContext, ValidationStatus
from ..slicers.prusa_slicer import PrusaSlicerProcessor
from .comparison_core import compare_parameter, select_slot
from .native_consistency import _report_base, _rows
from .prusa_parser import parse_prusa_3mf

TARGET_PARAMETERS = (
    "filament_flow_ratio",
    "filament_max_volumetric_speed",
    "nozzle_temperature",
    "nozzle_temperature_initial_layer",
    "fan_min_speed",
    "fan_max_speed",
    "fan_cooling_layer_time",
    "slow_down_layer_time",
)

NATIVE_MAPPING = {
    "nozzle_temperature": "temperature",
    "nozzle_temperature_initial_layer": "first_layer_temperature",
    "fan_min_speed": "min_fan_speed",
    "fan_max_speed": "max_fan_speed",
    "fan_cooling_layer_time": "fan_below_layer_time",
    "slow_down_layer_time": "slowdown_below_layer_time",
}

UNVERIFIED_MAPPINGS = {
    "filament_flow_ratio": "PrusaSlicer extrusion_multiplier mapping is not verified",
    "filament_max_volumetric_speed": "PrusaSlicer filament_max_volumetric_speed mapping is not verified",
}


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _unresolved_mapping(comparison: dict[str, Any], reason: str) -> None:
    comparison["status"] = "UNRESOLVED"
    comparison["mapping_status"] = "UNRESOLVED"
    comparison.setdefault("evidence", []).append(reason)
    comparison["preset"].setdefault("evidence", []).append(reason)
    comparison["project"].setdefault("evidence", []).append(reason)
    for element in comparison.get("elements", []):
        element["status"] = "UNRESOLVED"
        element.setdefault("evidence", []).append(reason)


def validate_prusa_consistency(
    preset_artifact: Artifact,
    project_artifact: Artifact,
    *,
    context: ProcessingContext | None = None,
) -> dict[str, Any]:
    processor = PrusaSlicerProcessor()
    process_context = context or ProcessingContext("", "", "PrusaSlicer", "")
    report = _report_base("PrusaSlicer", preset_artifact, project_artifact)

    try:
        source = processor.parse(preset_artifact, process_context)
    except Exception as exc:
        report["errors"].append(f"invalid PrusaSlicer Preset: {exc}")
        report["preset"]["status"] = ValidationStatus.INVALID_USER_ARTIFACT.value
        return report
    validation = processor.validate_source(source, process_context)
    if not validation.valid:
        report["errors"].extend(validation.errors)
        report["preset"]["status"] = validation.status.value
        return report
    canonical = processor.normalize(source, process_context)
    report["preset"] = {
        "status": "VALID",
        "identity": {
            "filename": preset_artifact.filename,
            "filename_stem": Path(preset_artifact.filename).stem,
            "filament_settings_id": canonical.values.get("filament_settings_id"),
        },
        "original_parameters": dict(canonical.values),
    }
    report["artifacts"]["canonical_preset_sha256"] = _sha256(
        json.dumps(canonical.values, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )

    try:
        snapshot = parse_prusa_3mf(project_artifact)
    except Exception as exc:
        report["errors"].append(f"invalid PrusaSlicer 3MF: {exc}")
        report["selection"] = {"status": "UNRESOLVED", "filament_slot_id": None, "matching_slot_ids": [], "evidence": ["project archive could not be safely parsed"]}
        return report

    report["source"]["version"] = snapshot.project_context.slicer_version
    report["project_context"] = snapshot.project_context.as_dict()
    report["project_issues"] = snapshot.issues
    if snapshot.issues:
        report["errors"].extend(issue["message"] for issue in snapshot.issues)

    filename_stem = Path(preset_artifact.filename).stem
    selection = select_slot(
        preset_identity_candidates=[filename_stem],
        project_slots=snapshot.filament_slots,
        project_values={name: setting.values for name, setting in snapshot.settings.items()},
        parameter_names=TARGET_PARAMETERS,
    )
    evidence = ["filename stem explicitly enabled by PrusaSlicer adapter", selection.get("reason", "slot selection completed")]
    evidence.extend(selection.get("evidence", []))
    report["selection"] = {
        "status": selection["status"],
        "filament_slot_id": selection.get("filament_slot_id"),
        "matching_slot_ids": selection.get("matching_slot_ids", []),
        "identity_strategy": "FILENAME_STEM_EXACT_PROJECT_PROFILE",
        "evidence": evidence,
    }

    preset_values: dict[str, Any] = {}
    project_values: dict[str, Any] = {}
    source_paths: dict[str, tuple[str, str]] = {}
    for canonical_name, native_name in NATIVE_MAPPING.items():
        if native_name in canonical.values:
            preset_values[canonical_name] = canonical.values[native_name]
            source_paths[canonical_name] = (f"ini.{native_name}", f"{native_name}")
        setting = snapshot.settings.get(native_name)
        if setting is not None:
            project_values[canonical_name] = setting.values
            source_paths[canonical_name] = (f"ini.{native_name}", f"{setting.source_path}:{native_name}")

    for name in TARGET_PARAMETERS:
        comparison = compare_parameter(
            name,
            preset_values,
            project_values,
            slot_id=selection.get("filament_slot_id"),
            slot_count=len(snapshot.filament_slots),
        )
        if name in UNVERIFIED_MAPPINGS:
            _unresolved_mapping(comparison, UNVERIFIED_MAPPINGS[name])
        elif selection["status"] != "UNIQUE" and snapshot.settings:
            comparison["status"] = "UNRESOLVED"
            comparison["identity_resolution"] = selection["status"]
            for element in comparison.get("elements", []):
                element["status"] = "UNRESOLVED"
                element.setdefault("evidence", []).append("filename identity did not resolve to a project slot")
        if name in source_paths:
            preset_path, project_path = source_paths[name]
            comparison["preset"]["source_path"] = preset_path
            comparison["project"]["source_path"] = project_path
            for element in comparison.get("elements", []):
                if element.get("preset_source_path"):
                    element["preset_source_path"] = preset_path
                if element.get("project_source_path"):
                    match = re.search(r"(\[\d+\])$", element["project_source_path"])
                    element["project_source_path"] = project_path + (match.group(1) if match else "")
        comparison["runtime_effective_status"] = "NOT_ESTABLISHED"
        report["comparisons"].append(comparison)

    report["comparison_rows"] = _rows(report["comparisons"])
    summary: dict[str, int] = {}
    for comparison in report["comparisons"]:
        summary[comparison["status"]] = summary.get(comparison["status"], 0) + 1
    report["summary"] = summary
    return report
