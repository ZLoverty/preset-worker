"""OrcaSlicer filament preset processor."""

from __future__ import annotations

import copy
import json
from typing import Any

from ..diff import ChangeType, DiffCategory, DiffChange, UnifiedDiff
from .contracts import Artifact, InvalidArtifactError, ProcessedArtifact, ProcessingContext, SlicerProcessor, ValidationResult, ValidationStatus


def _parse_json(artifact: Artifact) -> Any:
    try:
        return json.loads(artifact.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidArtifactError(f"OrcaSlicer artifact 不是有效 JSON: {exc}") from exc


def _flatten(value: Any, path: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            result.update(_flatten(child, f"{path}.{key}" if path else key))
        return result
    if isinstance(value, list):
        result: dict[str, Any] = {}
        for index, child in enumerate(value):
            result.update(_flatten(child, f"{path}[{index}]"))
        return result
    return {path: value}


# Conservative Orca classification. Unknown fields intentionally remain
# visible as OTHER_PARAMETER until their Orca semantics are verified.
IMPORTANT_PARAMETER_PATHS = frozenset({
    "filament_flow_ratio",
    "filament_max_volumetric_speed",
    "filament_retraction_length",
    "filament_retraction_speed",
    "nozzle_temperature",
    "nozzle_temperature_initial_layer",
    "nozzle_temperature_range_low",
    "nozzle_temperature_range_high",
    "fan_min_speed",
    "fan_max_speed",
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
    "pm_method_version",
})


def _category(path: str) -> DiffCategory:
    field = path.split("[", 1)[0]
    if field in IMPORTANT_PARAMETER_PATHS:
        return DiffCategory.IMPORTANT_PARAMETER
    if field in SYSTEM_METADATA_PATHS:
        return DiffCategory.SYSTEM_METADATA
    return DiffCategory.OTHER_PARAMETER


def _diff_values(base: Any, candidate: Any) -> UnifiedDiff:
    old_flat = _flatten(base)
    new_flat = _flatten(candidate)
    changes: list[DiffChange] = []
    changes.extend(
        DiffChange(path, ChangeType.ADDED, _category(path), None, new_flat[path])
        for path in new_flat.keys() - old_flat.keys()
    )
    changes.extend(
        DiffChange(path, ChangeType.REMOVED, _category(path), old_flat[path], None)
        for path in old_flat.keys() - new_flat.keys()
    )
    changes.extend(
        DiffChange(path, ChangeType.MODIFIED, _category(path), old_flat[path], new_flat[path])
        for path in new_flat.keys() & old_flat.keys()
        if old_flat[path] != new_flat[path]
    )
    return UnifiedDiff(tuple(sorted(changes, key=lambda change: change.path)))


class OrcaSlicerProcessor(SlicerProcessor):
    slicer_id = "OrcaSlicer"

    def parse(self, artifact: Artifact, context: ProcessingContext) -> Any:
        return _parse_json(artifact)

    def validate_source(self, source: Any, context: ProcessingContext) -> ValidationResult:
        errors: list[str] = []
        if not isinstance(source, dict):
            errors.append("OrcaSlicer preset 顶层必须是 object")
        else:
            # GUI-exported user filament presets may omit `type`; the
            # authoritative export fixture identifies itself through
            # filament_settings_id and filament settings fields instead.
            if "type" in source and source.get("type") != "filament":
                errors.append("OrcaSlicer preset 必须是 filament 类型")
            if not isinstance(source.get("name"), str) or not source["name"].strip():
                errors.append("OrcaSlicer preset 缺少有效 name")
            elif "type" not in source and not (
                isinstance(source.get("filament_settings_id"), list)
                or any(key.startswith("filament_") for key in source)
            ):
                errors.append("OrcaSlicer preset 不是可识别的 filament preset")
        status = ValidationStatus.VALID if not errors else ValidationStatus.INVALID_USER_ARTIFACT
        return ValidationResult(status, tuple(errors))

    def normalize(self, source: Any, context: ProcessingContext) -> Any:
        return copy.deepcopy(source)

    def apply_company_policy(self, normalized: Any, context: ProcessingContext) -> Any:
        canonical = copy.deepcopy(normalized)
        canonical_name = f"{context.pi_code} @{context.printer}"
        canonical["name"] = canonical_name
        # P7.3.1 GUI experiments showed that changing name alone creates the
        # intended visible preset identity. Preserve filament_settings_id and
        # other Orca identity metadata to minimize native-field mutation.
        canonical["pm_method_version"] = context.pm_method_version
        return canonical

    def validate_canonical(self, canonical: Any, context: ProcessingContext) -> ValidationResult:
        return self.validate_source(canonical, context)

    def serialize(self, canonical: Any, context: ProcessingContext) -> Artifact:
        return Artifact(
            content=json.dumps(canonical, ensure_ascii=False, indent=2).encode("utf-8"),
            filename=f"{context.pi_code} @{context.printer}.json",
            media_type="application/json",
        )

    def diff(self, base_artifact: Artifact, candidate_artifact: Artifact, context: ProcessingContext) -> UnifiedDiff:
        return _diff_values(_parse_json(base_artifact), _parse_json(candidate_artifact))

    def process(self, artifact: Artifact, context: ProcessingContext) -> ProcessedArtifact:
        source = self.parse(artifact, context)
        validation = self.validate_source(source, context)
        if not validation.valid:
            return ProcessedArtifact(Artifact(b"", "", None), validation)
        canonical = self.apply_company_policy(self.normalize(source, context), context)
        validation = self.validate_canonical(canonical, context)
        if not validation.valid:
            return ProcessedArtifact(Artifact(b"", "", None), validation)
        return ProcessedArtifact(self.serialize(canonical, context), validation)
