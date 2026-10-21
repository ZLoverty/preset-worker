"""Shared orchestration for isolated native JSON slicer adapters."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ..slicers.contracts import Artifact, ProcessingContext, SlicerProcessor, ValidationStatus
from .bambu_parser import parse_bambu_3mf
from .comparison_core import compare_parameter, select_slot

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


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _rows(comparisons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for comparison in comparisons:
        elements = comparison.get("elements") or []
        if not elements:
            rows.append({
                "parameter_id": comparison["parameter_id"],
                "path": comparison["parameter_id"],
                "index": None,
                "status": comparison["status"],
                "preset_value": comparison["preset"].get("raw_value"),
                "project_value": comparison["project"].get("raw_value"),
                "preset_source_path": comparison["preset"].get("source_path"),
                "project_source_path": comparison["project"].get("source_path"),
            })
            continue
        for element in elements:
            rows.append({
                "parameter_id": comparison["parameter_id"],
                "path": element["path"],
                "index": element.get("index"),
                "status": element["status"],
                "preset_value": element.get("preset_value"),
                "project_value": element.get("project_value"),
                "preset_normalized_value": element.get("preset_normalized_value"),
                "project_normalized_value": element.get("project_normalized_value"),
                "preset_source_path": element.get("preset_source_path"),
                "project_source_path": element.get("project_source_path"),
                "evidence": element.get("evidence", []),
            })
    return rows


def _report_base(slicer_id: str, preset_artifact: Artifact, project_artifact: Artifact) -> dict[str, Any]:
    return {
        "schema_version": "p9b2.consistency.v1",
        "source": {"slicer": slicer_id},
        "artifacts": {
            "preset_sha256": _sha256(preset_artifact.content),
            "project_3mf_sha256": _sha256(project_artifact.content),
        },
        "preset": {},
        "selection": {},
        "comparisons": [],
        "comparison_rows": [],
        "summary": {},
        "warnings": [],
        "errors": [],
    }


def validate_native_consistency(
    processor: SlicerProcessor,
    preset_artifact: Artifact,
    project_artifact: Artifact,
    *,
    context: ProcessingContext | None = None,
) -> dict[str, Any]:
    """Validate a native JSON Preset against a Bambu-style project archive.

    The caller chooses the native processor, making slicer identity and native
    validation explicit. The project extraction and comparison are shared.
    """
    slicer_id = processor.slicer_id
    process_context = context or ProcessingContext("", "", slicer_id, "")
    report = _report_base(slicer_id, preset_artifact, project_artifact)

    try:
        preset_source = processor.parse(preset_artifact, process_context)
    except Exception as exc:
        report["errors"].append(f"invalid {slicer_id} Preset: {exc}")
        report["preset"]["status"] = ValidationStatus.INVALID_USER_ARTIFACT.value
        return report
    validation = processor.validate_source(preset_source, process_context)
    if not validation.valid:
        report["errors"].extend(validation.errors)
        report["preset"]["status"] = validation.status.value
        return report

    canonical = processor.normalize(preset_source, process_context)
    report["preset"] = {
        "status": "VALID",
        "identity": {
            "name": canonical.get("name"),
            "inherits": canonical.get("inherits"),
            "filament_settings_id": canonical.get("filament_settings_id"),
        },
        "original_parameters": {name: preset_source.get(name) for name in TARGET_PARAMETERS if name in preset_source},
    }
    report["artifacts"]["canonical_preset_sha256"] = _sha256(
        json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )

    try:
        snapshot = parse_bambu_3mf(project_artifact)
    except Exception as exc:
        report["errors"].append(f"invalid {slicer_id} 3MF: {exc}")
        report["selection"] = {"status": "UNRESOLVED", "filament_slot_id": None, "matching_slot_ids": [], "evidence": ["project archive could not be safely parsed"]}
        return report

    report["source"]["version"] = snapshot.project_context.slicer_version
    report["project_context"] = snapshot.project_context.as_dict()
    report["project_issues"] = snapshot.issues
    if snapshot.project_settings is None:
        report["errors"].extend(issue["message"] for issue in snapshot.issues)

    identity = canonical.get("filament_settings_id")
    candidates = identity if isinstance(identity, list) else ([] if identity is None else [identity])
    selection = select_slot(
        preset_identity_candidates=candidates,
        project_slots=snapshot.filament_slots,
        project_values=snapshot.project_settings or {},
        parameter_names=TARGET_PARAMETERS,
    )
    evidence = [selection.get("reason", "slot selection completed")]
    evidence.extend(selection.get("evidence", []))
    evidence.extend(f"unresolved parameter: {name}" for name in selection.get("unresolved_parameters", []))
    report["selection"] = {
        "status": selection["status"],
        "filament_slot_id": selection.get("filament_slot_id"),
        "matching_slot_ids": selection.get("matching_slot_ids", []),
        "evidence": evidence,
    }

    project = snapshot.project_settings or {}
    slot_id = selection.get("filament_slot_id")
    for name in TARGET_PARAMETERS:
        comparison = compare_parameter(name, canonical, project, slot_id=slot_id, slot_count=len(snapshot.filament_slots))
        if selection["status"] != "UNIQUE" and snapshot.project_settings is not None:
            # Never expose value equality when the Preset cannot be associated
            # with a project slot. Preserve raw evidence, but make the result
            # explicitly non-comparable until identity is resolved.
            comparison["status"] = "UNRESOLVED"
            comparison["identity_resolution"] = selection["status"]
            for element in comparison.get("elements", []):
                element["status"] = "UNRESOLVED"
                element.setdefault("evidence", []).append("filament identity did not resolve to a project slot")
        # Native adapters have no evidence for runtime-effective equivalence.
        comparison["runtime_effective_status"] = "NOT_ESTABLISHED"
        report["comparisons"].append(comparison)
    report["comparison_rows"] = _rows(report["comparisons"])
    summary: dict[str, int] = {}
    for comparison in report["comparisons"]:
        summary[comparison["status"]] = summary.get(comparison["status"], 0) + 1
    report["summary"] = summary
    return report
