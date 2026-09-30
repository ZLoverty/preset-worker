"""ElegooSlicer filament preset processor."""

from __future__ import annotations

import copy
import json
from typing import Any

from ..diff import ChangeType, DiffCategory, DiffChange, UnifiedDiff
from .contracts import (
    Artifact,
    InvalidArtifactError,
    ProcessedArtifact,
    ProcessingContext,
    SlicerProcessor,
    ValidationResult,
    ValidationStatus,
)


def _parse_json(artifact: Artifact) -> Any:
    try:
        return json.loads(artifact.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidArtifactError(f"ElegooSlicer artifact 不是有效 JSON: {exc}") from exc


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


IMPORTANT_PARAMETER_PATHS = frozenset({
    "fan_cooling_layer_time",
    "fan_min_speed",
    "filament_extruder_variant",
    "nozzle_temperature",
    "nozzle_temperature_initial_layer",
})

SYSTEM_METADATA_PATHS = frozenset({
    "filament_settings_id",
    "from",
    "inherits",
    "name",
    "pm_method_version",
    "version",
})


def _category(path: str) -> DiffCategory:
    field = path.split("[", 1)[0]
    if field in IMPORTANT_PARAMETER_PATHS:
        return DiffCategory.IMPORTANT_PARAMETER
    if field in SYSTEM_METADATA_PATHS:
        return DiffCategory.SYSTEM_METADATA
    return DiffCategory.OTHER_PARAMETER


def _calculate_diff(old: Any | None, new: Any) -> UnifiedDiff:
    old_flat = _flatten(old) if old is not None else {}
    new_flat = _flatten(new)
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


class ElegooSlicerProcessor(SlicerProcessor):
    slicer_id = "ElegooSlicer"

    def parse(self, artifact: Artifact, context: ProcessingContext) -> Any:
        return _parse_json(artifact)

    def validate_source(self, source: Any, context: ProcessingContext) -> ValidationResult:
        errors: list[str] = []
        if not isinstance(source, dict):
            errors.append("Invalid ElegooSlicer preset artifact: top-level JSON must be an object")
        else:
            if not isinstance(source.get("name"), str) or not source["name"].strip():
                errors.append("Invalid ElegooSlicer preset artifact: missing valid name")
            if not isinstance(source.get("version"), str) or not source["version"].strip():
                errors.append("Invalid ElegooSlicer preset artifact: missing valid version")
            settings_id = source.get("filament_settings_id")
            if not isinstance(settings_id, list) or not settings_id or not all(isinstance(item, str) and item for item in settings_id):
                errors.append("Unsupported ElegooSlicer preset type: missing filament_settings_id")
            if not isinstance(source.get("inherits"), str) or not source["inherits"].strip():
                errors.append("Unsupported ElegooSlicer preset type: missing inherits")
            if source.get("from") not in (None, "User"):
                errors.append("Unsupported ElegooSlicer preset type: preset is not a user material preset")
        return ValidationResult(
            ValidationStatus.VALID if not errors else ValidationStatus.INVALID_USER_ARTIFACT,
            tuple(errors),
        )

    def normalize(self, source: Any, context: ProcessingContext) -> Any:
        return copy.deepcopy(source)

    def apply_company_policy(self, normalized: Any, context: ProcessingContext) -> Any:
        canonical = copy.deepcopy(normalized)
        canonical["name"] = f"{context.pi_code} @{context.printer}"
        # ElegooSlicer 1.5.2.5 removes this on re-export, so Worker metadata
        # must be restored from the authoritative processing context each time.
        canonical["pm_method_version"] = context.pm_method_version
        return canonical

    def validate_canonical(self, canonical: Any, context: ProcessingContext) -> ValidationResult:
        validation = self.validate_source(canonical, context)
        if not validation.valid:
            return validation
        errors: list[str] = []
        expected_name = f"{context.pi_code} @{context.printer}"
        if canonical.get("name") != expected_name:
            errors.append(f"ElegooSlicer canonical name must be {expected_name}")
        if canonical.get("pm_method_version") != context.pm_method_version:
            errors.append("ElegooSlicer canonical pm_method_version must match processing context")
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
        base = _parse_json(base_artifact) if base_artifact is not None else None
        candidate = _parse_json(candidate_artifact)
        return _calculate_diff(base, candidate)

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


def calculate_diff(old: Any | None, new: Any) -> UnifiedDiff:
    """Compatibility helper for processor-local diff callers."""
    return _calculate_diff(old, new)
