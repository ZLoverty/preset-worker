from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from typing import Any

from .models import (
    BambuProjectSnapshot,
    FilamentSlot,
    ObjectContext,
    PlateContext,
    ProjectContext,
    RawParameterValue,
    ResolutionContext,
    ResolutionStatus,
    ResolvedParameterValue,
    ResolvedProjectSettings,
)
from .safe_zip import SafeZipError, SafeZipReader, archive_sha256

PROJECT_ENTRY = "Metadata/project_settings.config"
MODEL_ENTRY = "Metadata/model_settings.config"
SLICE_ENTRY = "Metadata/slice_info.config"
SEQUENCE_ENTRY = "Metadata/filament_sequence.json"
PRIORITY_PARAMETERS = (
    "filament_flow_ratio",
    "filament_max_volumetric_speed",
    "nozzle_temperature",
    "nozzle_temperature_initial_layer",
    "fan_min_speed",
    "fan_max_speed",
    "fan_cooling_layer_time",
    "slow_down_layer_time",
    "cool_plate_temp",
    "cool_plate_temp_initial_layer",
    "eng_plate_temp",
    "eng_plate_temp_initial_layer",
    "hot_plate_temp",
    "hot_plate_temp_initial_layer",
    "textured_plate_temp",
    "textured_plate_temp_initial_layer",
    "supertack_plate_temp",
    "supertack_plate_temp_initial_layer",
    "filament_retraction_length",
    "filament_retraction_speed",
    "retraction_length",
    "retraction_speed",
    "deretraction_speed",
    "enable_pressure_advance",
    "pressure_advance",
)


def _json(data: bytes, label: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON in {label}") from exc


def _xml(data: bytes, label: str) -> ET.Element:
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError(f"external XML entities are not allowed in {label}")
    try:
        return ET.fromstring(data)
    except (ET.ParseError, ValueError) as exc:
        raise ValueError(f"invalid XML in {label}") from exc


def _metadata(element: ET.Element) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for child in element:
        if child.tag.rsplit("}", 1)[-1] == "metadata" and "key" in child.attrib:
            result[child.attrib["key"]] = child.attrib.get("value")
    return result


def _parse_model(data: bytes) -> tuple[list[ObjectContext], list[PlateContext]]:
    root = _xml(data, MODEL_ENTRY)
    objects: list[ObjectContext] = []
    plates: list[PlateContext] = []
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "object" and "id" in element.attrib:
            volumes = []
            for part in element:
                if part.tag.rsplit("}", 1)[-1] == "part":
                    volumes.append({"id": part.attrib.get("id"), "subtype": part.attrib.get("subtype"), "metadata": _metadata(part)})
            objects.append(ObjectContext(element.attrib["id"], _metadata(element), volumes))
        elif tag == "plater":
            metadata = _metadata(element)
            plate_id = int(metadata.get("plater_id", element.attrib.get("id", "0")) or 0)
            plates.append(PlateContext(plate_id, metadata, MODEL_ENTRY))
    return objects, plates


def _raw_parameters(config: dict[str, Any]) -> list[RawParameterValue]:
    values: list[RawParameterValue] = []
    for name, raw in config.items():
        if name not in PRIORITY_PARAMETERS:
            continue
        # Keep the complete array intact. Resolution, not extraction, decides
        # whether an array index can be selected for a given context.
        values.append(RawParameterValue(name, raw, PROJECT_ENTRY, f"$.{name}"))
    return values


def _slots(config: dict[str, Any]) -> list[FilamentSlot]:
    identifiers = config.get("filament_settings_id")
    if not isinstance(identifiers, list):
        identifiers = [] if identifiers is None else [identifiers]
    types = config.get("filament_type", [])
    ids = config.get("filament_ids", [])
    if not isinstance(types, list):
        types = [types]
    if not isinstance(ids, list):
        ids = [ids]
    return [
        FilamentSlot(i + 1, identifiers[i], types[i] if i < len(types) else None, ids[i] if i < len(ids) else None, {})
        for i in range(len(identifiers))
    ]


def parse_bambu_3mf(artifact: Any, *, limits: Any = None) -> BambuProjectSnapshot:
    data = artifact.content if hasattr(artifact, "content") else artifact
    if not isinstance(data, bytes):
        raise TypeError("3MF artifact must contain bytes")
    with SafeZipReader(data, limits) as archive:
        names = archive.names
        snapshot = BambuProjectSnapshot(names, archive_sha256(data))
        if PROJECT_ENTRY not in names:
            snapshot.issues.append({"code": "MISSING_PROJECT_SETTINGS", "message": PROJECT_ENTRY})
            return snapshot
        try:
            config = _json(archive.read(PROJECT_ENTRY), PROJECT_ENTRY)
        except ValueError as exc:
            snapshot.issues.append({"code": "INVALID_PROJECT_SETTINGS", "message": str(exc)})
            return snapshot
        if not isinstance(config, dict):
            snapshot.issues.append({"code": "INVALID_PROJECT_SETTINGS_TYPE", "message": "project settings must be object"})
            return snapshot
        snapshot.project_settings = config
        snapshot.raw_parameters = _raw_parameters(config)
        snapshot.filament_slots = _slots(config)
        snapshot.project_context = ProjectContext(
            config.get("printer_model"),
            config.get("printer_settings_id"),
            config.get("process_settings_id"),
            config.get("default_print_profile"),
            config.get("layer_height"),
            config.get("curr_bed_type"),
            None,
            config,
        )
        if MODEL_ENTRY in names:
            try:
                snapshot.model_settings_xml = archive.read(MODEL_ENTRY).decode("utf-8")
                snapshot.objects, snapshot.plates = _parse_model(archive.read(MODEL_ENTRY))
            except (UnicodeDecodeError, ValueError) as exc:
                snapshot.issues.append({"code": "INVALID_MODEL_SETTINGS", "message": str(exc)})
        if SLICE_ENTRY in names:
            try:
                text = archive.read(SLICE_ENTRY).decode("utf-8")
                match = re.search(r'key="X-BBL-Client-Version" value="([^"]+)"', text)
                if match:
                    snapshot.project_context.slicer_version = match.group(1)
                snapshot.slice_info = {"raw_xml": text}
            except UnicodeDecodeError:
                snapshot.issues.append({"code": "INVALID_SLICE_INFO", "message": "slice info is not UTF-8"})
        if SEQUENCE_ENTRY in names:
            try:
                sequence = _json(archive.read(SEQUENCE_ENTRY), SEQUENCE_ENTRY)
                snapshot.filament_sequence = sequence if isinstance(sequence, dict) else {"raw": sequence}
            except ValueError as exc:
                snapshot.issues.append({"code": "INVALID_FILAMENT_SEQUENCE", "message": str(exc)})
        for name in names:
            if name.startswith("Metadata/filament_settings_") or name.startswith("Metadata/machine_settings_") or name.startswith("Metadata/process_settings_"):
                preset_type = name.split("/", 1)[1].split("_", 1)[0]
                snapshot.embedded_presets.append({"entry": name, "type": preset_type, "parsed": False})
        for name in names:
            match = re.fullmatch(r"Metadata/plate_(\d+)\.json", name)
            if match:
                try:
                    payload = _json(archive.read(name), name)
                    if isinstance(payload, dict):
                        snapshot.plates.append(PlateContext(int(match.group(1)), {}, name, payload))
                except ValueError as exc:
                    snapshot.issues.append({"code": "INVALID_PLATE_METADATA", "message": f"{name}: {exc}"})
        return snapshot


def _resolve_array(raw: RawParameterValue, slot_id: int | None, slot_count: int) -> ResolvedParameterValue:
    context = {"filament_slot_id": slot_id, "filament_config_index": None}
    if not isinstance(raw.raw_value, list):
        return ResolvedParameterValue(raw.name, ResolutionStatus.NOT_APPLICABLE, raw.raw_value, raw.raw_value, raw.entry, raw.source_path, raw.scope, "STORED_ONLY", ["scalar project value"], context)
    values = raw.raw_value
    if slot_id is None:
        return ResolvedParameterValue(raw.name, ResolutionStatus.UNRESOLVED, values, None, raw.entry, raw.source_path, raw.scope, "STORED_ONLY", ["filament slot is required"], context)
    if len(values) == 1:
        context["filament_config_index"] = 0
        return ResolvedParameterValue(raw.name, ResolutionStatus.RESOLVED, values, values[0], raw.entry, raw.source_path, raw.scope, "CONFIG_RESOLVED", ["single configuration value"], context)
    if len(values) == slot_count and 0 < slot_id <= len(values):
        index = slot_id - 1
        context["filament_config_index"] = index
        return ResolvedParameterValue(raw.name, ResolutionStatus.RESOLVED, values, values[index], raw.entry, raw.source_path, raw.scope, "CONFIG_RESOLVED", ["array cardinality equals filament slot count"], context)
    return ResolvedParameterValue(raw.name, ResolutionStatus.UNRESOLVED, values, None, raw.entry, raw.source_path, raw.scope, "STORED_ONLY", ["array cardinality does not identify a verified filament index"], context)


def resolve_bambu_project(snapshot: BambuProjectSnapshot, context: ResolutionContext | None = None) -> ResolvedProjectSettings:
    context = context or ResolutionContext()
    results = []
    slot_count = len(snapshot.filament_slots)
    for raw in snapshot.raw_parameters:
        result = _resolve_array(raw, context.filament_slot_id, slot_count)
        result.context.update({"plate_id": context.plate_id, "object_id": context.object_id, "volume_id": context.volume_id})
        if raw.name in {"enable_pressure_advance", "pressure_advance"} and snapshot.project_context.printer_model and "Bambu" in str(snapshot.project_context.printer_model):
            result.status = ResolutionStatus.NOT_APPLICABLE
            result.value = None
            result.value_classification = "STORED_ONLY"
            result.evidence.append("Bambu printer PA is not runtime-effective according to BambuStudio source")
        results.append(result)
    return ResolvedProjectSettings(results, list(snapshot.issues))
