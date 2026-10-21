from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Any

from ..slicers.bambu_studio import BambuStudioProcessor
from ..slicers.creality_print import CrealityPrintProcessor
from ..slicers.elegoo_slicer import ElegooSlicerProcessor
from ..slicers.orca_slicer import OrcaSlicerProcessor
from ..slicers.snapmaker_orca import SnapmakerOrcaSlicerProcessor
from ..slicers.contracts import Artifact, ProcessingContext, ValidationStatus
from .bambu_parser import parse_bambu_3mf, resolve_bambu_project
from .comparison_core import compare_parameter, select_slot
from .models import ResolutionContext, ResolutionStatus
from .native_consistency import validate_native_consistency

REQUIRED_PARAMETERS = (
    "filament_flow_ratio",
    "filament_max_volumetric_speed",
    "nozzle_temperature",
    "nozzle_temperature_initial_layer",
    "fan_min_speed",
    "fan_max_speed",
    "fan_cooling_layer_time",
    "slow_down_layer_time",
)

PARAMETER_UNITS = {
    "filament_flow_ratio": "dimensionless",
    "filament_max_volumetric_speed": "mm3/s",
    "nozzle_temperature": "C",
    "nozzle_temperature_initial_layer": "C",
    "fan_min_speed": "%",
    "fan_max_speed": "%",
    "fan_cooling_layer_time": "s",
    "slow_down_layer_time": "s",
}


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_value(value: Any) -> Any:
    if isinstance(value, list):
        return value
    return value


def _preset_value(source: dict[str, Any], name: str) -> tuple[str, Any, str, list[str]]:
    if name not in source or source[name] is None:
        return "MISSING_IN_PRESET", None, f"$.{name}", ["parameter is absent or null"]
    value = _json_value(source[name])
    if isinstance(value, list):
        non_nil = [item for item in value if item not in (None, "", "nil")]
        if len(value) == 1 and non_nil:
            return "RESOLVED", non_nil[0], f"$.{name}[0]", ["single preset configuration value"]
        if len(non_nil) == 1 and len(non_nil) < len(value):
            return "RESOLVED", non_nil[0], f"$.{name}", ["exactly one non-nil preset value; nil entries preserved as unresolved variants"]
        return "UNRESOLVED", None, f"$.{name}", ["preset array has no uniquely supported effective value"]
    if value in ("", "nil"):
        return "UNRESOLVED", None, f"$.{name}", ["preset value is nil or empty"]
    return "RESOLVED", value, f"$.{name}", ["scalar preset value"]


def _numeric(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, AttributeError):
        return None


def _normalize(name: str, value: Any) -> tuple[str | None, str | None]:
    number = _numeric(value)
    if number is None:
        return None, "value is not numeric"
    if name in {"nozzle_temperature", "nozzle_temperature_initial_layer"} and number != number.to_integral_value():
        return None, "temperature is not an integer Celsius value"
    return format(number.normalize(), "f"), None


def _stored_value(source: dict[str, Any], name: str) -> tuple[str, Any, str, list[str]]:
    if name not in source or source[name] is None:
        return "MISSING", None, f"$.{name}", ["parameter is absent or null"]
    value = source[name]
    if isinstance(value, list):
        return "ARRAY", value, f"$.{name}", ["stored array preserved without index resolution"]
    return "SCALAR", value, f"$.{name}", ["stored scalar preserved"]


def _element(
    name: str,
    index: int,
    preset_value: Any,
    project_value: Any,
    preset_path: str,
    project_path: str,
) -> dict[str, Any]:
    path = f"{name}[{index}]"
    if preset_value in (None, "", "nil"):
        status = "MISSING_IN_PRESET"
        preset_normalized = None
        project_normalized, project_error = _normalize(name, project_value)
        return {
            "path": path,
            "index": index,
            "preset_value": preset_value,
            "project_value": project_value,
            "preset_source_path": f"{preset_path}[{index}]",
            "project_source_path": f"{project_path}[{index}]",
            "preset_normalized_value": preset_normalized,
            "project_normalized_value": project_normalized,
            "status": status,
            "evidence": ["preset element is nil or empty"] + ([project_error] if project_error else []),
        }
    if project_value in (None, "", "nil"):
        preset_normalized, preset_error = _normalize(name, preset_value)
        return {
            "path": path,
            "index": index,
            "preset_value": preset_value,
            "project_value": project_value,
            "preset_source_path": f"{preset_path}[{index}]",
            "project_source_path": f"{project_path}[{index}]",
            "preset_normalized_value": preset_normalized,
            "project_normalized_value": None,
            "status": "MISSING_IN_3MF",
            "evidence": ["project element is nil or empty"] + ([preset_error] if preset_error else []),
        }
    preset_normalized, preset_error = _normalize(name, preset_value)
    project_normalized, project_error = _normalize(name, project_value)
    if preset_error or project_error:
        status = "UNRESOLVED"
    elif preset_normalized == project_normalized:
        status = "MATCH"
    else:
        status = "MISMATCH"
    return {
        "path": path,
        "index": index,
        "preset_value": preset_value,
        "project_value": project_value,
        "preset_source_path": f"{preset_path}[{index}]",
        "project_source_path": f"{project_path}[{index}]",
        "preset_normalized_value": preset_normalized,
        "project_normalized_value": project_normalized,
        "status": status,
        "evidence": [error for error in (preset_error, project_error) if error],
    }


def _compare_stored_parameter(name: str, preset: dict[str, Any], project: dict[str, Any]) -> dict[str, Any]:
    preset_kind, preset_value, preset_path, preset_evidence = _stored_value(preset, name)
    project_kind, project_value, project_path, project_evidence = _stored_value(project, name)
    result: dict[str, Any] = {
        "parameter_id": name,
        "unit": PARAMETER_UNITS[name],
        "comparison_scope": "STORED_VALUE",
        "status": "UNRESOLVED",
        "elements": [],
        "preset": {
            "kind": preset_kind,
            "original_array": preset_value if preset_kind == "ARRAY" else None,
            "raw_value": preset_value,
            "source_path": preset_path,
            "evidence": preset_evidence,
        },
        "project": {
            "kind": project_kind,
            "original_array": project_value if project_kind == "ARRAY" else None,
            "raw_value": project_value,
            "source_path": project_path,
            "evidence": project_evidence,
        },
        "runtime_effective_status": "NOT_CLAIMED",
    }
    if preset_kind == "MISSING":
        result["status"] = "MISSING_IN_PRESET"
        return result
    if project_kind == "MISSING":
        result["status"] = "MISSING_IN_3MF"
        return result
    if preset_kind != project_kind:
        result["comparison_scope"] = "STORED_VALUE"
        result["status"] = "NOT_COMPARABLE"
        result["elements"] = [
            {"path": f"{name}[{i}]" if (preset_kind == "ARRAY" or project_kind == "ARRAY") else name, "index": i, "status": "NOT_COMPARABLE", "preset_value": preset_value if i == 0 else None, "project_value": project_value[i] if project_kind == "ARRAY" and i < len(project_value) else project_value if i == 0 else None}
            for i in range(max(len(preset_value) if preset_kind == "ARRAY" else 1, len(project_value) if project_kind == "ARRAY" else 1))
        ]
        return result
    if preset_kind == "ARRAY":
        result["comparison_scope"] = "STORED_ARRAY"
        common = min(len(preset_value), len(project_value))
        result["elements"] = [
            _element(name, index, preset_value[index], project_value[index], preset_path, project_path)
            for index in range(common)
        ]
        for index in range(common, len(preset_value)):
            result["elements"].append({
                "path": f"{name}[{index}]",
                "index": index, "preset_value": preset_value[index], "project_value": None,
                "preset_source_path": f"{preset_path}[{index}]", "project_source_path": None,
                "status": "AMBIGUOUS", "evidence": ["unmatched preset array element"],
            })
        for index in range(common, len(project_value)):
            result["elements"].append({
                "path": f"{name}[{index}]",
                "index": index, "preset_value": None, "project_value": project_value[index],
                "preset_source_path": None, "project_source_path": f"{project_path}[{index}]",
                "status": "AMBIGUOUS", "evidence": ["unmatched project array element"],
            })
        if len(preset_value) != len(project_value):
            result["status"] = "AMBIGUOUS"
        elif any(item["status"] == "MISMATCH" for item in result["elements"]):
            result["status"] = "MISMATCH"
        elif any(item["status"] == "MISSING_IN_PRESET" for item in result["elements"]):
            result["status"] = "MISSING_IN_PRESET"
        elif any(item["status"] == "MISSING_IN_3MF" for item in result["elements"]):
            result["status"] = "MISSING_IN_3MF"
        elif any(item["status"] == "UNRESOLVED" for item in result["elements"]):
            result["status"] = "UNRESOLVED"
        else:
            result["status"] = "MATCH"
        return result
    result["comparison_scope"] = "STORED_SCALAR"
    scalar_element = _element(name, 0, preset_value, project_value, preset_path, project_path)
    scalar_element["path"] = name
    result["elements"] = [scalar_element]
    result["status"] = result["elements"][0]["status"]
    return result


def _slot_match(snapshot: Any, preset: dict[str, Any]) -> tuple[str, int | None, list[str], list[int]]:
    ids = preset.get("filament_settings_id")
    candidates = ids if isinstance(ids, list) else ([] if ids is None else [ids])
    selection = select_slot(
        preset_identity_candidates=candidates,
        project_slots=snapshot.filament_slots,
        project_values=snapshot.project_settings or {},
        parameter_names=REQUIRED_PARAMETERS,
    )
    evidence = [selection.get("reason", "slot selection completed")]
    evidence.extend(selection.get("evidence", []))
    evidence.extend(f"unresolved parameter: {name}" for name in selection.get("unresolved_parameters", []))
    return selection["status"], selection.get("filament_slot_id"), evidence, selection.get("matching_slot_ids", [])


def validate_bambu_consistency(
    preset_artifact: Artifact,
    project_artifact: Artifact,
    *,
    context: ProcessingContext | None = None,
) -> dict[str, Any]:
    processor = BambuStudioProcessor()
    process_context = context or ProcessingContext("", "", "BambuStudio", "")
    preset_original = processor.parse(preset_artifact, process_context)
    validation = processor.validate_source(preset_original, process_context)
    report: dict[str, Any] = {
        "schema_version": "p9b2.consistency.v1",
        "source": {"slicer": "BambuStudio"},
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
    if validation.status is not ValidationStatus.VALID:
        report["errors"].extend(validation.errors)
        report["preset"]["status"] = validation.status.value
        return report

    normalized = processor.normalize(preset_original, process_context)
    canonical = processor.apply_company_policy(normalized, process_context)
    canonical_bytes = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    report["artifacts"]["canonical_preset_sha256"] = _sha256(canonical_bytes)
    report["preset"] = {
        "status": "VALID",
        "identity": {
            "name": canonical.get("name"),
            "inherits": canonical.get("inherits"),
            "filament_settings_id": canonical.get("filament_settings_id"),
        },
        "original_parameters": {name: preset_original.get(name) for name in REQUIRED_PARAMETERS if name in preset_original},
    }

    snapshot = parse_bambu_3mf(project_artifact)
    report["source"]["version"] = snapshot.project_context.slicer_version
    report["project_context"] = snapshot.project_context.as_dict()
    report["project_issues"] = snapshot.issues
    slot_status, slot_id, slot_evidence, matching_slot_ids = _slot_match(snapshot, canonical)
    report["selection"] = {
        "status": slot_status,
        "filament_slot_id": slot_id,
        "matching_slot_ids": matching_slot_ids,
        "evidence": slot_evidence,
    }
    resolved = resolve_bambu_project(snapshot, ResolutionContext(filament_slot_id=slot_id))
    project_values = {item.name: item for item in resolved.parameters}
    for name in REQUIRED_PARAMETERS:
        entry = compare_parameter(
            name,
            canonical,
            snapshot.project_settings or {},
            slot_id=slot_id,
            slot_count=len(snapshot.filament_slots),
        )
        entry["runtime_effective_status"] = (
            project_values[name].status.value if name in project_values else "UNAVAILABLE"
        )
        report["comparisons"].append(entry)
    for comparison in report["comparisons"]:
        elements = comparison.get("elements") or []
        if not elements:
            report["comparison_rows"].append({
                "parameter_id": comparison["parameter_id"],
                "path": comparison["parameter_id"],
                "index": None,
                "status": comparison["status"],
                "preset_value": comparison["preset"].get("raw_value"),
                "project_value": comparison["project"].get("raw_value"),
                "preset_source_path": comparison["preset"].get("source_path"),
                "project_source_path": comparison["project"].get("source_path"),
            })
        else:
            for element in elements:
                report["comparison_rows"].append({
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
    counts: dict[str, int] = {}
    for item in report["comparisons"]:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    report["summary"] = counts
    return report


def validate_creality_consistency(
    preset_artifact: Artifact,
    project_artifact: Artifact,
    *,
    context: ProcessingContext | None = None,
) -> dict[str, Any]:
    """Run isolated CrealityPrint consistency validation.

    This entry point is intentionally not registered with Preview dispatch.
    """
    return validate_native_consistency(
        CrealityPrintProcessor(), preset_artifact, project_artifact, context=context,
    )


def validate_elegoo_consistency(
    preset_artifact: Artifact,
    project_artifact: Artifact,
    *,
    context: ProcessingContext | None = None,
) -> dict[str, Any]:
    """Run isolated ElegooSlicer consistency validation.

    This entry point is intentionally not registered with Preview dispatch.
    """
    return validate_native_consistency(
        ElegooSlicerProcessor(), preset_artifact, project_artifact, context=context,
    )


def validate_orca_consistency(
    preset_artifact: Artifact,
    project_artifact: Artifact,
    *,
    context: ProcessingContext | None = None,
) -> dict[str, Any]:
    """Run isolated OrcaSlicer consistency validation."""
    return validate_native_consistency(
        OrcaSlicerProcessor(), preset_artifact, project_artifact, context=context,
    )


def validate_snapmaker_orca_consistency(
    preset_artifact: Artifact,
    project_artifact: Artifact,
    *,
    context: ProcessingContext | None = None,
) -> dict[str, Any]:
    """Run isolated SnapmakerOrcaSlicer consistency validation."""
    return validate_native_consistency(
        SnapmakerOrcaSlicerProcessor(), preset_artifact, project_artifact, context=context,
    )
