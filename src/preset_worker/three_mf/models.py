from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class RawParameterValue:
    name: str
    raw_value: Any
    entry: str
    source_path: str
    scope: str = "PROJECT"
    array_index: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "raw_value": self.raw_value,
            "entry": self.entry,
            "source_path": self.source_path,
            "scope": self.scope,
            "array_index": self.array_index,
        }


@dataclass
class FilamentSlot:
    slot_id: int
    settings_id: Any = None
    filament_type: Any = None
    filament_id: Any = None
    raw_values: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class ObjectContext:
    object_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    volumes: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class PlateContext:
    plate_id: int
    metadata: dict[str, Any] = field(default_factory=dict)
    source_entry: str | None = None
    raw_json: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class ProjectContext:
    printer_model: Any = None
    printer_settings_id: Any = None
    process_settings_id: Any = None
    default_print_profile: Any = None
    layer_height: Any = None
    curr_bed_type: Any = None
    slicer_version: Any = None
    raw: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class BambuProjectSnapshot:
    entries: list[str]
    archive_sha256: str
    project_settings: dict[str, Any] | None = None
    model_settings_xml: str | None = None
    slice_info: dict[str, Any] = field(default_factory=dict)
    filament_sequence: dict[str, Any] = field(default_factory=dict)
    project_context: ProjectContext = field(default_factory=ProjectContext)
    filament_slots: list[FilamentSlot] = field(default_factory=list)
    objects: list[ObjectContext] = field(default_factory=list)
    plates: list[PlateContext] = field(default_factory=list)
    embedded_presets: list[dict[str, Any]] = field(default_factory=list)
    raw_parameters: list[RawParameterValue] = field(default_factory=list)
    issues: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "entries": self.entries,
            "archive_sha256": self.archive_sha256,
            "project_settings": self.project_settings,
            "project_context": self.project_context.as_dict(),
            "filament_slots": [item.as_dict() for item in self.filament_slots],
            "objects": [item.as_dict() for item in self.objects],
            "plates": [item.as_dict() for item in self.plates],
            "slice_info": self.slice_info,
            "filament_sequence": self.filament_sequence,
            "embedded_presets": self.embedded_presets,
            "raw_parameters": [item.as_dict() for item in self.raw_parameters],
            "issues": self.issues,
        }


@dataclass(frozen=True)
class ResolutionContext:
    filament_slot_id: int | None = None
    plate_id: int | None = None
    object_id: str | None = None
    volume_id: str | None = None


@dataclass
class ResolvedParameterValue:
    name: str
    status: ResolutionStatus
    raw_value: Any = None
    value: Any = None
    entry: str | None = None
    source_path: str | None = None
    scope: str = "PROJECT"
    value_classification: str = "STORED_ONLY"
    evidence: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        result = self.__dict__.copy()
        result["status"] = self.status.value
        return result


@dataclass
class ResolvedProjectSettings:
    parameters: list[ResolvedParameterValue] = field(default_factory=list)
    issues: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "parameters": [item.as_dict() for item in self.parameters],
            "issues": self.issues,
        }
