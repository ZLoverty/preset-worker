"""PrusaSlicer filament preset processor for the real INI artifact format."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
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


_ASSIGNMENT = re.compile(r"^(?P<key>[^=\s][^=]*?)\s*=\s(?P<value>.*)$")


@dataclass
class PrusaDocument:
    filename: str
    lines: list[str]
    values: dict[str, str]
    final_newline: bool


def _parse_ini(artifact: Artifact) -> PrusaDocument:
    try:
        text = artifact.content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidArtifactError(f"PrusaSlicer artifact 不是有效 UTF-8 INI: {exc}") from exc
    final_newline = text.endswith("\n")
    lines = text.splitlines()
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        match = _ASSIGNMENT.match(line)
        if not match:
            raise InvalidArtifactError(f"PrusaSlicer INI 包含无法解析的行: {line!r}")
        key = match.group("key").strip()
        values[key] = match.group("value")
    return PrusaDocument(artifact.filename, lines, values, final_newline)


def _serialize_document(document: PrusaDocument) -> bytes:
    text = "\n".join(document.lines)
    if document.final_newline:
        text += "\n"
    return text.encode("utf-8")


IMPORTANT_PARAMETER_KEYS = frozenset({
    "bed_temperature",
    "first_layer_bed_temperature",
    "chamber_temperature",
    "filament_density",
    "filament_diameter",
    "fan_always_on",
    "fan_below_layer_time",
    "slowdown_below_layer_time",
    "cooling",
    "extrusion_multiplier",
    "filament_max_volumetric_speed",
    "filament_retract_length",
    "filament_retract_speed",
    "filament_retract_length_toolchange",
    "max_fan_speed",
    "min_fan_speed",
    "first_layer_temperature",
    "extrusion_multiplier",
    "retract_length",
    "temperature",
})

SYSTEM_METADATA_KEYS = frozenset({
    "compatible_printers",
    "compatible_printers_condition",
    "compatible_prints",
    "compatible_prints_condition",
    "filament_settings_id",
    "inherits",
    "pm_method_version",
})


def _category(key: str) -> DiffCategory:
    if key in IMPORTANT_PARAMETER_KEYS:
        return DiffCategory.IMPORTANT_PARAMETER
    if key in SYSTEM_METADATA_KEYS:
        return DiffCategory.SYSTEM_METADATA
    return DiffCategory.OTHER_PARAMETER


def _change(old: dict[str, str], new: dict[str, str], key: str) -> DiffChange | None:
    old_present = key in old
    new_present = key in new
    if old_present and new_present:
        if old[key] == new[key]:
            return None
        return DiffChange(f"ini.{key}", ChangeType.MODIFIED, _category(key), old[key], new[key])
    if new_present:
        return DiffChange(f"ini.{key}", ChangeType.ADDED, _category(key), None, new[key])
    return DiffChange(f"ini.{key}", ChangeType.REMOVED, _category(key), old[key], None)


class PrusaSlicerProcessor(SlicerProcessor):
    slicer_id = "PrusaSlicer"

    def parse(self, artifact: Artifact, context: ProcessingContext) -> Any:
        return _parse_ini(artifact)

    def validate_source(self, source: Any, context: ProcessingContext) -> ValidationResult:
        errors: list[str] = []
        if not isinstance(source, PrusaDocument):
            errors.append("Invalid PrusaSlicer preset artifact: expected INI document")
        else:
            if not source.filename.lower().endswith(".ini"):
                errors.append("Invalid PrusaSlicer preset artifact: filename must use .ini extension")
            required = {
                "filament_type": "filament type",
                "filament_vendor": "filament vendor",
                "filament_diameter": "filament diameter",
                "temperature": "temperature",
            }
            for key, label in required.items():
                if key not in source.values or not source.values[key].strip():
                    errors.append(f"Unsupported PrusaSlicer preset type: missing {label} field {key}")
        return ValidationResult(
            ValidationStatus.VALID if not errors else ValidationStatus.INVALID_USER_ARTIFACT,
            tuple(errors),
        )

    def normalize(self, source: Any, context: ProcessingContext) -> Any:
        return copy.deepcopy(source)

    def apply_company_policy(self, normalized: Any, context: ProcessingContext) -> Any:
        canonical = copy.deepcopy(normalized)
        canonical.filename = f"{context.pi_code} @{context.printer}.ini"
        replaced = False
        updated_lines: list[str] = []
        for line in canonical.lines:
            match = _ASSIGNMENT.match(line)
            if match and match.group("key").strip() == "pm_method_version":
                updated_lines.append(f"pm_method_version = {context.pm_method_version}")
                replaced = True
            else:
                updated_lines.append(line)
        if not replaced:
            updated_lines.append(f"pm_method_version = {context.pm_method_version}")
        canonical.lines = updated_lines
        canonical.values["pm_method_version"] = context.pm_method_version
        return canonical

    def validate_canonical(self, canonical: Any, context: ProcessingContext) -> ValidationResult:
        validation = self.validate_source(canonical, context)
        if not validation.valid:
            return validation
        errors: list[str] = []
        expected_filename = f"{context.pi_code} @{context.printer}.ini"
        if canonical.filename != expected_filename:
            errors.append(f"PrusaSlicer canonical filename must be {expected_filename}")
        if canonical.values.get("pm_method_version") != context.pm_method_version:
            errors.append("PrusaSlicer canonical pm_method_version must match processing context")
        if "name" in canonical.values:
            errors.append("PrusaSlicer canonical artifact must not contain synthetic name field")
        return ValidationResult(
            ValidationStatus.VALID if not errors else ValidationStatus.INVALID_USER_ARTIFACT,
            tuple(errors),
        )

    def serialize(self, canonical: Any, context: ProcessingContext) -> Artifact:
        return Artifact(
            content=_serialize_document(canonical),
            filename=canonical.filename,
            media_type="text/plain",
        )

    def diff(self, base_artifact: Artifact | None, candidate_artifact: Artifact, context: ProcessingContext) -> UnifiedDiff:
        base = _parse_ini(base_artifact) if base_artifact is not None else None
        candidate = _parse_ini(candidate_artifact)
        changes: list[DiffChange] = []
        if base is None or base.filename != candidate.filename:
            changes.append(DiffChange(
                "$artifact.filename",
                ChangeType.ADDED if base is None else ChangeType.MODIFIED,
                DiffCategory.SYSTEM_METADATA,
                None if base is None else base.filename,
                candidate.filename,
            ))
        old_values = {} if base is None else base.values
        for key in sorted(set(old_values) | set(candidate.values)):
            change = _change(old_values, candidate.values, key)
            if change is not None:
                changes.append(change)
        return UnifiedDiff(tuple(sorted(changes, key=lambda change: change.path)))

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
    if isinstance(old, PrusaDocument) or old is None:
        return _calculate_documents(old, new)
    raise TypeError("PrusaSlicer diff expects PrusaDocument values")


def _calculate_documents(old: PrusaDocument | None, new: PrusaDocument) -> UnifiedDiff:
    changes: list[DiffChange] = []
    if old is None or old.filename != new.filename:
        changes.append(DiffChange(
            "$artifact.filename", ChangeType.ADDED if old is None else ChangeType.MODIFIED,
            DiffCategory.SYSTEM_METADATA, None if old is None else old.filename, new.filename,
        ))
    old_values = {} if old is None else old.values
    for key in sorted(set(old_values) | set(new.values)):
        change = _change(old_values, new.values, key)
        if change is not None:
            changes.append(change)
    return UnifiedDiff(tuple(sorted(changes, key=lambda change: change.path)))
