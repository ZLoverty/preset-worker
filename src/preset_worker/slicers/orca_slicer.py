"""OrcaSlicer filament preset processor."""

from __future__ import annotations

import copy
import json
from typing import Any

from ..diff import ChangeType, DiffCategory, DiffChange, UnifiedDiff
from .contracts import Artifact, InvalidArtifactError, ProcessedArtifact, ProcessingContext, SlicerProcessor, ValidationResult, ValidationStatus
from .orca_compatible_core import OrcaCompatibleCore


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

    def __init__(self) -> None:
        self._core = OrcaCompatibleCore("OrcaSlicer")

    def parse(self, artifact: Artifact, context: ProcessingContext) -> Any:
        return self._core.parse(artifact, context)

    def validate_source(self, source: Any, context: ProcessingContext) -> ValidationResult:
        return self._core.validate_source(source, context)

    def normalize(self, source: Any, context: ProcessingContext) -> Any:
        return self._core.normalize(source, context)

    def apply_company_policy(self, normalized: Any, context: ProcessingContext) -> Any:
        return self._core.apply_company_policy(normalized, context)

    def validate_canonical(self, canonical: Any, context: ProcessingContext) -> ValidationResult:
        return self._core.validate_canonical(canonical, context)

    def serialize(self, canonical: Any, context: ProcessingContext) -> Artifact:
        return self._core.serialize(canonical, context)

    def diff(self, base_artifact: Artifact | None, candidate_artifact: Artifact, context: ProcessingContext) -> UnifiedDiff:
        return self._core.diff(base_artifact, candidate_artifact, context)

    def process(self, artifact: Artifact, context: ProcessingContext) -> ProcessedArtifact:
        return self._core.process(self, artifact, context)
