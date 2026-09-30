"""Slicer-neutral diff model and persistence codec."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


DIFF_SCHEMA_VERSION = 1


class ChangeType(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"


class DiffCategory(str, Enum):
    IMPORTANT_PARAMETER = "IMPORTANT_PARAMETER"
    OTHER_PARAMETER = "OTHER_PARAMETER"
    SYSTEM_METADATA = "SYSTEM_METADATA"


@dataclass(frozen=True)
class DiffChange:
    path: str
    change_type: ChangeType
    category: DiffCategory
    old_value: object | None = None
    new_value: object | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "change_type": self.change_type.value,
            "category": self.category.value,
            "old_value": self.old_value,
            "new_value": self.new_value,
        }


@dataclass(frozen=True)
class UnifiedDiff:
    changes: tuple[DiffChange, ...] = ()

    @classmethod
    def empty(cls) -> "UnifiedDiff":
        return cls(())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": DIFF_SCHEMA_VERSION,
            "changes": [change.to_dict() for change in self.changes],
        }


def serialize_unified_diff(diff: UnifiedDiff) -> str:
    """Serialize the generic diff format, preserving deterministic order."""
    return json.dumps(diff.to_dict(), ensure_ascii=False, sort_keys=True)


def _transport_safe(value: object) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(_transport_safe(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _transport_safe(item) for key, item in value.items())
    return False


def _change_from_dict(value: object) -> DiffChange:
    if not isinstance(value, dict):
        raise ValueError("diff change must be an object")
    required = {"path", "change_type", "category", "old_value", "new_value"}
    if set(value) != required:
        raise ValueError("diff change has invalid fields")
    try:
        change_type = ChangeType(value["change_type"])
        category = DiffCategory(value["category"])
    except (KeyError, ValueError) as exc:
        raise ValueError("diff change has unknown change_type or category") from exc
    path = value["path"]
    if not isinstance(path, str) or not path:
        raise ValueError("diff change path must be a non-empty string")
    old_value = value["old_value"]
    new_value = value["new_value"]
    if not _transport_safe(old_value) or not _transport_safe(new_value):
        raise ValueError("diff values are not transport-safe")
    return DiffChange(path, change_type, category, old_value, new_value)


def _legacy_diff(value: dict[str, Any]) -> UnifiedDiff:
    """Read the pre-v1 {added, removed, modified} representation."""
    changes: list[DiffChange] = []
    for item in value.get("added", []):
        changes.append(DiffChange(item["path"], ChangeType.ADDED, DiffCategory.OTHER_PARAMETER, None, item.get("new")))
    for item in value.get("removed", []):
        changes.append(DiffChange(item["path"], ChangeType.REMOVED, DiffCategory.OTHER_PARAMETER, item.get("old"), None))
    for item in value.get("modified", []):
        changes.append(DiffChange(item["path"], ChangeType.MODIFIED, DiffCategory.OTHER_PARAMETER, item.get("old"), item.get("new")))
    return UnifiedDiff(tuple(changes))


def deserialize_unified_diff(value: object) -> UnifiedDiff:
    """Strictly read v1 diffs while accepting historical worker output."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("diff is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("diff must be an object")
    if "schema_version" not in value:
        return _legacy_diff(value)
    if value.get("schema_version") != DIFF_SCHEMA_VERSION or not isinstance(value.get("changes"), list):
        raise ValueError("unsupported or malformed diff schema")
    changes = tuple(_change_from_dict(item) for item in value["changes"])
    return UnifiedDiff(changes)
