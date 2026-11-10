"""BambuStudio implementation of the slicer processor contract."""

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
from .parameter_catalog import (
    classify_native_path,
    important_paths_for_slicer,
    system_metadata_paths_for_slicer,
)


def parse_json_artifact(artifact: bytes) -> Any:
    try:
        return json.loads(artifact.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidArtifactError(f"uploaded_json 不是有效 JSON: {exc}") from exc


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


IMPORTANT_PARAMETER_PATHS = important_paths_for_slicer("BambuStudio")
SYSTEM_METADATA_PATHS = system_metadata_paths_for_slicer("BambuStudio")


def _category(path: str) -> DiffCategory:
    return classify_native_path("BambuStudio", path)


def _calculate_diff(old: Any | None, new: Any) -> UnifiedDiff:
    new_flat = _flatten(new)
    changes: list[DiffChange] = []
    if old is None:
        changes = [DiffChange(path, ChangeType.ADDED, _category(path), None, value) for path, value in new_flat.items()]
    else:
        old_flat = _flatten(old)
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


class BambuStudioProcessor(SlicerProcessor):
    slicer_id = "BambuStudio"
    important_parameter_paths = IMPORTANT_PARAMETER_PATHS

    def parse(self, artifact: Artifact, context: ProcessingContext) -> Any:
        return parse_json_artifact(artifact.content)

    def validate_source(self, source: Any, context: ProcessingContext) -> ValidationResult:
        errors: list[str] = []
        if not isinstance(source, dict):
            errors.append("JSON 顶层必须是 object")
        elif not all(isinstance(key, str) and key for key in source):
            errors.append("JSON object 的字段名必须是非空字符串")
        elif "version" not in source:
            errors.append("BambuStudio JSON 缺少必需字段: version")
        return ValidationResult(ValidationStatus.VALID if not errors else ValidationStatus.INVALID_USER_ARTIFACT, tuple(errors))

    def normalize(self, source: Any, context: ProcessingContext) -> Any:
        return copy.deepcopy(source)

    def apply_company_policy(self, normalized: Any, context: ProcessingContext) -> Any:
        canonical = copy.deepcopy(normalized)
        canonical["name"] = f"{context.pi_code} @{context.printer}"
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

    def diff(self, base_artifact: Artifact | None, candidate_artifact: Artifact, context: ProcessingContext) -> UnifiedDiff:
        base = parse_json_artifact(base_artifact.content) if base_artifact is not None else None
        candidate = parse_json_artifact(candidate_artifact.content)
        return _calculate_diff(base, candidate)

    def process(self, artifact: Artifact, context: ProcessingContext) -> ProcessedArtifact:
        source = self.parse(artifact, context)
        validation = self.validate_source(source, context)
        if not validation.valid:
            return ProcessedArtifact(Artifact(b"", "", None), validation)
        normalized = self.normalize(source, context)
        canonical = self.apply_company_policy(normalized, context)
        validation = self.validate_canonical(canonical, context)
        if not validation.valid:
            return ProcessedArtifact(Artifact(b"", "", None), validation)
        return ProcessedArtifact(self.serialize(canonical, context), validation)


def calculate_diff(old: Any | None, new: Any) -> UnifiedDiff:
    """Compatibility helper retained for callers outside the processor."""
    return _calculate_diff(old, new)
