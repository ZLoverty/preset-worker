"""Narrow shared mechanics proven equivalent for Orca-compatible slicers."""

from __future__ import annotations

import copy
import json
from typing import Any

from ..diff import ChangeType, DiffCategory, DiffChange, UnifiedDiff
from .contracts import Artifact, InvalidArtifactError, ProcessedArtifact, ProcessingContext, ValidationResult, ValidationStatus


IMPORTANT_PARAMETER_PATHS = frozenset({
    "filament_flow_ratio",
    "filament_max_volumetric_speed",
    "fan_min_speed",
    "fan_max_speed",
    "fan_cooling_layer_time",
    "slow_down_layer_time",
    "slow_down_for_layer_cooling",
    "cooling_slowdown_logic",
    "nozzle_temperature",
    "nozzle_temperature_initial_layer",
    "nozzle_temperature_range_low",
    "nozzle_temperature_range_high",
    "pressure_advance",
    "enable_pressure_advance",
    "adaptive_pressure_advance",
    "filament_retraction_length",
    "retraction_length",
    "retraction_speed",
    "retraction_minimum_travel",
    "retract_length_toolchange",
    "chamber_temperature",
    "cool_plate_temp",
    "cool_plate_temp_initial_layer",
    "textured_plate_temp",
    "textured_plate_temp_initial_layer",
    "hot_plate_temp",
    "hot_plate_temp_initial_layer",
    "eng_plate_temp",
    "eng_plate_temp_initial_layer",
    "supertack_plate_temp",
    "supertack_plate_temp_initial_layer",
    "textured_cool_plate_temp",
    "textured_cool_plate_temp_initial_layer",
})

SYSTEM_METADATA_PATHS = frozenset({
    "type",
    "name",
    "from",
    "instantiation",
    "inherits",
    "setting_id",
    "filament_id",
    "filament_settings_id",
    "compatible_printers",
    "is_custom_defined",
    "printer_settings_id",
    "print_settings_id",
    "version",
    "pm_method_version",
})


def parse_json(artifact: Artifact) -> Any:
    try:
        return json.loads(artifact.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidArtifactError(f"Orca-compatible artifact 不是有效 JSON: {exc}") from exc


def flatten(value: Any, path: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            result.update(flatten(child, f"{path}.{key}" if path else key))
        return result
    if isinstance(value, list):
        result: dict[str, Any] = {}
        for index, child in enumerate(value):
            result.update(flatten(child, f"{path}[{index}]"))
        return result
    return {path: value}


def category(
    path: str,
    important_parameter_paths: frozenset[str] = IMPORTANT_PARAMETER_PATHS,
    system_metadata_paths: frozenset[str] = SYSTEM_METADATA_PATHS,
) -> DiffCategory:
    field = path.split("[", 1)[0]
    if field in important_parameter_paths:
        return DiffCategory.IMPORTANT_PARAMETER
    if field in system_metadata_paths:
        return DiffCategory.SYSTEM_METADATA
    return DiffCategory.OTHER_PARAMETER


def calculate_diff(
    old: Any | None,
    new: Any,
    important_parameter_paths: frozenset[str] = IMPORTANT_PARAMETER_PATHS,
    system_metadata_paths: frozenset[str] = SYSTEM_METADATA_PATHS,
) -> UnifiedDiff:
    old_flat = flatten(old) if old is not None else {}
    new_flat = flatten(new)
    changes: list[DiffChange] = []
    changes.extend(
        DiffChange(path, ChangeType.ADDED, category(path, important_parameter_paths, system_metadata_paths), None, new_flat[path])
        for path in new_flat.keys() - old_flat.keys()
    )
    changes.extend(
        DiffChange(path, ChangeType.REMOVED, category(path, important_parameter_paths, system_metadata_paths), old_flat[path], None)
        for path in old_flat.keys() - new_flat.keys()
    )
    changes.extend(
        DiffChange(path, ChangeType.MODIFIED, category(path, important_parameter_paths, system_metadata_paths), old_flat[path], new_flat[path])
        for path in new_flat.keys() & old_flat.keys()
        if old_flat[path] != new_flat[path]
    )
    return UnifiedDiff(tuple(sorted(changes, key=lambda change: change.path)))


class OrcaCompatibleCore:
    """Shared behavior with no business slicer identity of its own."""

    def __init__(
        self,
        label: str,
        important_parameter_paths: frozenset[str] = IMPORTANT_PARAMETER_PATHS,
        system_metadata_paths: frozenset[str] = SYSTEM_METADATA_PATHS,
    ):
        self.label = label
        self.important_parameter_paths = important_parameter_paths
        self.system_metadata_paths = system_metadata_paths

    def parse(self, artifact: Artifact, context: ProcessingContext) -> Any:
        return parse_json(artifact)

    def validate_source(self, source: Any, context: ProcessingContext) -> ValidationResult:
        errors: list[str] = []
        if not isinstance(source, dict):
            errors.append(f"{self.label} preset 顶层必须是 object")
        else:
            if "type" in source and source.get("type") != "filament":
                errors.append(f"{self.label} preset 必须是 filament 类型")
            if not isinstance(source.get("name"), str) or not source["name"].strip():
                errors.append(f"{self.label} preset 缺少有效 name")
            elif "type" not in source and not (
                isinstance(source.get("filament_settings_id"), list)
                or any(key.startswith("filament_") for key in source)
            ):
                errors.append(f"{self.label} preset 不是可识别的 filament preset")
        return ValidationResult(
            ValidationStatus.VALID if not errors else ValidationStatus.INVALID_USER_ARTIFACT,
            tuple(errors),
        )

    def normalize(self, source: Any, context: ProcessingContext) -> Any:
        return copy.deepcopy(source)

    def apply_company_policy(self, normalized: Any, context: ProcessingContext) -> Any:
        canonical = copy.deepcopy(normalized)
        canonical["name"] = f"{context.pi_code} @{context.printer}"
        canonical["pm_method_version"] = context.pm_method_version
        return canonical

    def validate_canonical(self, canonical: Any, context: ProcessingContext) -> ValidationResult:
        validation = self.validate_source(canonical, context)
        if not validation.valid:
            return validation
        errors: list[str] = []
        expected_name = f"{context.pi_code} @{context.printer}"
        if canonical.get("name") != expected_name:
            errors.append(f"{self.label} canonical name must be {expected_name}")
        if canonical.get("pm_method_version") != context.pm_method_version:
            errors.append(f"{self.label} canonical pm_method_version must match processing context")
        return ValidationResult(
            ValidationStatus.VALID if not errors else ValidationStatus.INVALID_USER_ARTIFACT,
            tuple(errors),
        )

    def serialize(self, canonical: Any, context: ProcessingContext) -> Artifact:
        return Artifact(
            content=json.dumps(canonical, ensure_ascii=False, indent=2).encode("utf-8"),
            filename=f"{context.pi_code} @{context.printer}.json",
            media_type="application/json",
        )

    def diff(self, base_artifact: Artifact | None, candidate_artifact: Artifact, context: ProcessingContext) -> UnifiedDiff:
        base = parse_json(base_artifact) if base_artifact is not None else None
        candidate = parse_json(candidate_artifact)
        return calculate_diff(
            base,
            candidate,
            self.important_parameter_paths,
            self.system_metadata_paths,
        )

    def process(self, processor: Any, artifact: Artifact, context: ProcessingContext) -> ProcessedArtifact:
        source = self.parse(artifact, context)
        validation = self.validate_source(source, context)
        if not validation.valid:
            return ProcessedArtifact(Artifact(b"", "", None), validation)
        canonical = self.apply_company_policy(self.normalize(source, context), context)
        validation = self.validate_canonical(canonical, context)
        if not validation.valid:
            return ProcessedArtifact(Artifact(b"", "", None), validation)
        return ProcessedArtifact(self.serialize(canonical, context), validation)
