"""Slicer-neutral stored-value comparison and filament-slot selection.

This module deliberately accepts already extracted values.  It does not know
about ZIP files, slicers, Preview, or runtime-effective settings.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Iterable


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


def _numeric(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, AttributeError):
        return None


def normalize_value(name: str, value: Any) -> tuple[str | None, str | None]:
    number = _numeric(value)
    if number is None:
        return None, "value is not numeric"
    if name in {"nozzle_temperature", "nozzle_temperature_initial_layer"} and number != number.to_integral_value():
        return None, "temperature is not an integer Celsius value"
    return format(number.normalize(), "f"), None


def _is_empty(value: Any) -> bool:
    return value in (None, "", "nil")


def _stored(source: dict[str, Any], name: str) -> tuple[str, Any, str, list[str]]:
    if name not in source or source[name] is None:
        return "MISSING", None, f"$.{name}", ["parameter is absent or null"]
    value = source[name]
    if isinstance(value, list):
        return "ARRAY", value, f"$.{name}", ["stored array preserved without index resolution"]
    return "SCALAR", value, f"$.{name}", ["stored scalar preserved"]


def select_project_slot_value(
    name: str,
    value: Any,
    *,
    slot_id: int | None,
    slot_count: int,
) -> tuple[Any, str, str, list[str] | None]:
    """Select a proven slot-indexed project array element.

    Arrays are indexed only when their cardinality equals the explicit slot
    count.  The final tuple is value, kind, source path, original array.
    """
    if not isinstance(value, list) or slot_id is None or slot_count <= 1 or len(value) != slot_count:
        return value, "ARRAY" if isinstance(value, list) else "SCALAR", f"$.{name}", value if isinstance(value, list) else None
    index = slot_id - 1
    return value[index], "SCALAR", f"$.{name}[{index}]", value


def select_preset_value(name: str, value: Any, *, slot_aware: bool) -> tuple[Any, str, str, list[str] | None]:
    if slot_aware and isinstance(value, list) and len(value) == 1:
        return value[0], "SCALAR", f"$.{name}[0]", value
    return value, "ARRAY" if isinstance(value, list) else "SCALAR", f"$.{name}", value if isinstance(value, list) else None


def _element(name: str, index: int, preset_value: Any, project_value: Any, preset_path: str, project_path: str) -> dict[str, Any]:
    path = f"{name}[{index}]"
    preset_element_path = preset_path if preset_path.endswith(f"[{index}]") else f"{preset_path}[{index}]"
    project_element_path = project_path if project_path.endswith(f"[{index}]") else f"{project_path}[{index}]"
    if _is_empty(preset_value):
        preset_normalized = None
        project_normalized, project_error = normalize_value(name, project_value)
        return {
            "path": path, "index": index, "preset_value": preset_value, "project_value": project_value,
            "preset_source_path": preset_element_path, "project_source_path": project_element_path,
            "preset_normalized_value": preset_normalized, "project_normalized_value": project_normalized,
            "status": "MISSING_IN_PRESET", "evidence": ["preset element is nil or empty"] + ([project_error] if project_error else []),
        }
    if _is_empty(project_value):
        preset_normalized, preset_error = normalize_value(name, preset_value)
        return {
            "path": path, "index": index, "preset_value": preset_value, "project_value": project_value,
            "preset_source_path": preset_element_path, "project_source_path": project_element_path,
            "preset_normalized_value": preset_normalized, "project_normalized_value": None,
            "status": "MISSING_IN_3MF", "evidence": ["project element is nil or empty"] + ([preset_error] if preset_error else []),
        }
    preset_normalized, preset_error = normalize_value(name, preset_value)
    project_normalized, project_error = normalize_value(name, project_value)
    status = "UNRESOLVED" if preset_error or project_error else ("MATCH" if preset_normalized == project_normalized else "MISMATCH")
    return {
        "path": path, "index": index, "preset_value": preset_value, "project_value": project_value,
        "preset_source_path": preset_element_path, "project_source_path": project_element_path,
        "preset_normalized_value": preset_normalized, "project_normalized_value": project_normalized,
        "status": status, "evidence": [error for error in (preset_error, project_error) if error],
    }


def compare_parameter(name: str, preset: dict[str, Any], project: dict[str, Any], *, slot_id: int | None = None, slot_count: int = 0) -> dict[str, Any]:
    raw_preset_kind, raw_preset, raw_preset_path, raw_preset_evidence = _stored(preset, name)
    raw_project_kind, raw_project, raw_project_path, raw_project_evidence = _stored(project, name)
    slot_aware = slot_id is not None and slot_count > 1 and raw_project_kind == "ARRAY" and len(raw_project) == slot_count
    preset_value, preset_kind, preset_path, preset_original = select_preset_value(name, raw_preset, slot_aware=slot_aware)
    project_value, project_kind, project_path, project_original = select_project_slot_value(name, raw_project, slot_id=slot_id, slot_count=slot_count)
    result: dict[str, Any] = {
        "parameter_id": name, "unit": PARAMETER_UNITS[name],
        "comparison_scope": "STORED_VALUE", "status": "UNRESOLVED", "elements": [],
        "preset": {"kind": preset_kind, "original_array": preset_original, "raw_value": raw_preset, "source_path": preset_path, "evidence": raw_preset_evidence},
        "project": {"kind": project_kind, "original_array": project_original, "raw_value": raw_project, "source_path": project_path, "evidence": raw_project_evidence},
        "runtime_effective_status": "NOT_CLAIMED",
    }
    if raw_preset_kind == "MISSING":
        result["status"] = "MISSING_IN_PRESET"
        return result
    if raw_project_kind == "MISSING":
        result["status"] = "MISSING_IN_3MF"
        return result
    if preset_kind != project_kind:
        result["status"] = "NOT_COMPARABLE"
        count = max(len(preset_value) if preset_kind == "ARRAY" else 1, len(project_value) if project_kind == "ARRAY" else 1)
        result["elements"] = [{
            "path": f"{name}[{i}]" if (preset_kind == "ARRAY" or project_kind == "ARRAY") else name,
            "index": i,
            "status": "NOT_COMPARABLE",
            "preset_value": preset_value if i == 0 else None,
            "project_value": project_value[i] if project_kind == "ARRAY" and i < len(project_value) else project_value if i == 0 else None,
        } for i in range(count)]
        return result
    if preset_kind == "ARRAY":
        result["comparison_scope"] = "STORED_ARRAY"
        common = min(len(preset_value), len(project_value))
        result["elements"] = [_element(name, i, preset_value[i], project_value[i], preset_path, project_path) for i in range(common)]
        for i in range(common, len(preset_value)):
            result["elements"].append({"path": f"{name}[{i}]", "index": i, "preset_value": preset_value[i], "project_value": None, "preset_source_path": f"{preset_path}[{i}]", "project_source_path": None, "status": "AMBIGUOUS", "evidence": ["unmatched preset array element"]})
        for i in range(common, len(project_value)):
            result["elements"].append({"path": f"{name}[{i}]", "index": i, "preset_value": None, "project_value": project_value[i], "preset_source_path": None, "project_source_path": f"{project_path}[{i}]", "status": "AMBIGUOUS", "evidence": ["unmatched project array element"]})
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
    item = _element(name, 0, preset_value, project_value, preset_path, project_path)
    item["path"] = name
    result["elements"] = [item]
    result["status"] = item["status"]
    return result


def select_slot(
    *,
    preset_identity_candidates: Iterable[Any],
    project_slots: Iterable[Any],
    project_values: dict[str, Any],
    parameter_names: Iterable[str],
) -> dict[str, Any]:
    def field(slot: Any, name: str) -> Any:
        if isinstance(slot, dict):
            return slot.get(name)
        return getattr(slot, name, None)

    candidates = [str(value) for value in preset_identity_candidates if value not in (None, "", "nil")]
    slots = list(project_slots)
    matches = [slot for slot in slots if str(field(slot, "settings_id")) in candidates]
    if not candidates:
        return {"status": "UNRESOLVED", "filament_slot_id": None, "matching_slot_ids": [], "reason": "identity is absent"}
    if not matches:
        return {"status": "UNRESOLVED", "filament_slot_id": None, "matching_slot_ids": [], "reason": "no identity match"}
    if len(matches) == 1:
        slot_id = field(matches[0], "slot_id")
        return {"status": "UNIQUE", "filament_slot_id": slot_id, "matching_slot_ids": [slot_id], "reason": "exact identity match"}
    matching_ids = [field(slot, "slot_id") for slot in matches]
    equivalent = True
    unresolved: list[str] = []
    for name in parameter_names:
        value = project_values.get(name)
        if not isinstance(value, list) or len(value) != len(slots):
            unresolved.append(name)
            equivalent = False
            continue
        selected = [value[slot_id - 1] for slot_id in matching_ids]
        normalized = [normalize_value(name, item)[0] for item in selected]
        if any(item is None for item in normalized) or len(set(normalized)) != 1:
            equivalent = False
    if equivalent:
        selected_id = min(matching_ids)
        return {"status": "UNIQUE", "filament_slot_id": selected_id, "matching_slot_ids": matching_ids, "reason": "MULTIPLE_EQUIVALENT", "evidence": ["all target arrays are equivalent across matching slots"]}
    return {"status": "AMBIGUOUS", "filament_slot_id": None, "matching_slot_ids": matching_ids, "reason": "duplicate identities are not proven equivalent", "unresolved_parameters": unresolved}
