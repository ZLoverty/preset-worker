"""BambuStudio implementation of the slicer processor contract."""

from __future__ import annotations

import copy
import json
from typing import Any

from .contracts import (
    Artifact,
    InvalidArtifactError,
    ProcessedArtifact,
    ProcessingContext,
    SlicerProcessor,
    ValidationResult,
    ValidationStatus,
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


def _calculate_diff(old: Any | None, new: Any) -> dict[str, list[dict[str, Any]]]:
    new_flat = _flatten(new)
    if old is None:
        return {"added": [{"path": p, "new": v} for p, v in new_flat.items()], "removed": [], "modified": []}
    old_flat = _flatten(old)
    added = [{"path": p, "new": new_flat[p]} for p in new_flat.keys() - old_flat.keys()]
    removed = [{"path": p, "old": old_flat[p]} for p in old_flat.keys() - new_flat.keys()]
    modified = [{"path": p, "old": old_flat[p], "new": new_flat[p]} for p in new_flat.keys() & old_flat.keys() if old_flat[p] != new_flat[p]]
    return {key: sorted(value, key=lambda item: item["path"]) for key, value in {"added": added, "removed": removed, "modified": modified}.items()}


class BambuStudioProcessor(SlicerProcessor):
    slicer_id = "BambuStudio"

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

    def diff(self, base_artifact: Artifact | None, candidate_artifact: Artifact, context: ProcessingContext) -> dict[str, list[dict[str, Any]]]:
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


def calculate_diff(old: Any | None, new: Any) -> dict[str, list[dict[str, Any]]]:
    """Compatibility helper retained for callers outside the processor."""
    return _calculate_diff(old, new)
