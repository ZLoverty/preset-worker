"""Authoritative Native Preset Important Parameter catalog.

This module owns Native Diff classification only.  Consistency target membership
is exposed as read-only inventory evidence and is deliberately not used to
change the 3MF comparison runtime.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping

from ..diff import DiffCategory
from .contracts import canonical_slicer_id


_INDEX_SUFFIX = re.compile(r"(?:\[\d+\])*$")


@dataclass(frozen=True)
class ParameterDefinition:
    parameter_id: str
    description: str
    native_paths: Mapping[str, tuple[str, ...]]
    consistency_targets: tuple[str, ...] = ()
    semantic_notes: str = ""
    importance: DiffCategory = DiffCategory.IMPORTANT_PARAMETER


def _definition(
    parameter_id: str,
    description: str,
    paths: Mapping[str, tuple[str, ...]],
    *,
    targets: tuple[str, ...] = (),
    notes: str = "",
) -> ParameterDefinition:
    return ParameterDefinition(parameter_id, description, paths, targets, notes)


_JSON_SLICERS = ("BambuStudio", "OrcaSlicer", "CrealityPrint", "ElegooSlicer")
_ORCA_SLICERS = ("OrcaSlicer", "SnapmakerOrcaSlicer")


IMPORTANT_PARAMETER_CATALOG: tuple[ParameterDefinition, ...] = (
    _definition("filament.flow_ratio", "Filament flow ratio", {s: ("filament_flow_ratio",) for s in _JSON_SLICERS + _ORCA_SLICERS} | {"FlashStudio": ("filament_flow_ratio",)}, targets=("filament_flow_ratio",)),
    _definition("filament.max_volumetric_speed", "Maximum filament volumetric speed", {s: ("filament_max_volumetric_speed",) for s in _JSON_SLICERS + _ORCA_SLICERS} | {"FlashStudio": ("filament_max_volumetric_speed",)}, targets=("filament_max_volumetric_speed",)),
    _definition("cooling.fan_min_speed", "Minimum fan speed", {s: ("fan_min_speed",) for s in _JSON_SLICERS + _ORCA_SLICERS} | {"FlashStudio": ("fan_min_speed",)}, targets=("fan_min_speed",)),
    _definition("cooling.fan_max_speed", "Maximum fan speed", {s: ("fan_max_speed",) for s in _JSON_SLICERS + _ORCA_SLICERS} | {"FlashStudio": ("fan_max_speed",)}, targets=("fan_max_speed",)),
    _definition("cooling.fan_below_layer_time", "Fan cooling layer time", {s: ("fan_cooling_layer_time",) for s in _JSON_SLICERS + _ORCA_SLICERS} | {"FlashStudio": ("fan_cooling_layer_time",)}, targets=("fan_cooling_layer_time",)),
    _definition("cooling.slowdown_layer_time", "Slow down below layer time", {s: ("slow_down_layer_time",) for s in _JSON_SLICERS + _ORCA_SLICERS} | {"FlashStudio": ("slow_down_layer_time",)}, targets=("slow_down_layer_time",)),
    _definition("cooling.slowdown_for_layer_cooling", "Slow down for layer cooling", {"CrealityPrint": ("slow_down_for_layer_cooling",)}),
    _definition("nozzle.temperature", "Nozzle temperature", {s: ("nozzle_temperature",) for s in _JSON_SLICERS + _ORCA_SLICERS} | {"FlashStudio": ("nozzle_temperature",)}, targets=("nozzle_temperature",)),
    _definition("nozzle.first_layer_temperature", "First-layer nozzle temperature", {s: ("nozzle_temperature_initial_layer",) for s in _JSON_SLICERS + _ORCA_SLICERS} | {"FlashStudio": ("nozzle_temperature_initial_layer",)}, targets=("nozzle_temperature_initial_layer",)),
    _definition("retraction.filament_length", "Filament retraction length", {s: ("filament_retraction_length",) for s in _JSON_SLICERS + _ORCA_SLICERS}, targets=("filament_retraction_length",)),
    _definition("retraction.length", "Retraction length", {s: ("retraction_length",) for s in _JSON_SLICERS + _ORCA_SLICERS}, targets=("retraction_length",)),
    _definition("pressure.advance", "Pressure advance", {s: ("pressure_advance",) for s in _JSON_SLICERS + _ORCA_SLICERS} | {"FlashStudio": ("pressure_advance",)}),
    _definition("temperature.chamber", "Chamber temperature", {"CrealityPrint": ("chamber_temperature",), "OrcaSlicer": ("chamber_temperature",), "ElegooSlicer": ("chamber_temperature",), "SnapmakerOrcaSlicer": ("chamber_temperature",)}),
    _definition("temperature.chamber_temperatures", "Chamber temperature array", {"BambuStudio": ("chamber_temperatures",), "ElegooSlicer": ("chamber_temperatures",)}),
    _definition("bed.textured_plate_temperature", "Textured plate temperature", {s: ("textured_plate_temp",) for s in _JSON_SLICERS + _ORCA_SLICERS} | {"FlashStudio": ("textured_plate_temp",)}),
    _definition("bed.cool_plate_temperature", "Cool plate temperature", {s: ("cool_plate_temp",) for s in _JSON_SLICERS + _ORCA_SLICERS}),
    _definition("nozzle.temperature_range_low", "Lower nozzle temperature range", {s: ("nozzle_temperature_range_low",) for s in _JSON_SLICERS + _ORCA_SLICERS} | {"FlashStudio": ("nozzle_temperature_range_low",)}),
    _definition("extruder.variant", "Filament extruder variant", {"ElegooSlicer": ("filament_extruder_variant",)}),
    _definition("snapmaker.graphic_effect_plate_temperature", "Snapmaker graphic-effect plate temperature", {"SnapmakerOrcaSlicer": ("graphic_effect_plate_temp", "graphic_effect_plate_temp_initial_layer")}),
    _definition("snapmaker.textured_cool_plate_temperature", "Snapmaker textured cool plate temperature", {"SnapmakerOrcaSlicer": ("textured_cool_plate_temp", "textured_cool_plate_temp_initial_layer")}),
    _definition("material.density", "Filament density", {"PrusaSlicer": ("ini.filament_density",)}),
    _definition("material.diameter", "Filament diameter", {"PrusaSlicer": ("ini.filament_diameter",)}),
    _definition("cooling.enabled", "Cooling enabled", {"PrusaSlicer": ("ini.cooling",)}),
    _definition("material.extrusion_multiplier", "Extrusion multiplier", {"PrusaSlicer": ("ini.extrusion_multiplier",)}),
    _definition("filament.max_volumetric_speed.prusa", "PrusaSlicer maximum volumetric speed", {"PrusaSlicer": ("ini.filament_max_volumetric_speed",)}),
    _definition("retraction.filament_length.prusa", "PrusaSlicer filament retraction length", {"PrusaSlicer": ("ini.filament_retract_length",)}),
    _definition("nozzle.temperature.prusa", "PrusaSlicer nozzle temperature", {"PrusaSlicer": ("ini.temperature",)}, targets=("nozzle_temperature",)),
    _definition("nozzle.first_layer_temperature.prusa", "PrusaSlicer first-layer nozzle temperature", {"PrusaSlicer": ("ini.first_layer_temperature",)}, targets=("nozzle_temperature_initial_layer",)),
    _definition("cooling.fan_max_speed.prusa", "PrusaSlicer maximum fan speed", {"PrusaSlicer": ("ini.max_fan_speed",)}, targets=("fan_max_speed",)),
    _definition("cooling.fan_min_speed.prusa", "PrusaSlicer minimum fan speed", {"PrusaSlicer": ("ini.min_fan_speed",)}, targets=("fan_min_speed",)),
    _definition("cooling.fan_below_layer_time.prusa", "PrusaSlicer fan below layer time", {"PrusaSlicer": ("ini.fan_below_layer_time",)}, targets=("fan_cooling_layer_time",)),
    _definition("cooling.slowdown_layer_time.prusa", "PrusaSlicer slowdown below layer time", {"PrusaSlicer": ("ini.slowdown_below_layer_time",)}, targets=("slow_down_layer_time",)),
    _definition("bed.temperature.prusa", "PrusaSlicer bed temperature", {"PrusaSlicer": ("ini.bed_temperature",)}),
)


SYSTEM_METADATA_PATHS: Mapping[str, frozenset[str]] = {
    "BambuStudio": frozenset({"from", "name", "version", "inherits", "pm_method_version", "filament_settings_id", "printer_settings_id", "print_settings_id", "process_settings_id"}),
    "OrcaSlicer": frozenset({"type", "name", "from", "instantiation", "inherits", "setting_id", "filament_id", "filament_settings_id", "compatible_printers", "is_custom_defined", "printer_settings_id", "print_settings_id", "version", "pm_method_version"}),
    "CrealityPrint": frozenset({"base_id", "filament_settings_id", "from", "inherits", "is_custom_defined", "name", "pm_method_version", "printer_settings_id", "print_settings_id", "version"}),
    "ElegooSlicer": frozenset({"filament_settings_id", "from", "inherits", "name", "pm_method_version", "printer_settings_id", "print_settings_id", "version"}),
    "SnapmakerOrcaSlicer": frozenset({"type", "name", "from", "instantiation", "inherits", "setting_id", "filament_id", "filament_settings_id", "compatible_printers", "is_custom_defined", "printer_settings_id", "print_settings_id", "version", "pm_method_version"}),
    "FlashStudio": frozenset({"name", "from", "version", "inherits", "pm_method_version", "filament_settings_id", "printer_settings_id", "print_settings_id", "process_settings_id"}),
    "PrusaSlicer": frozenset({"ini.compatible_printers", "ini.compatible_printers_condition", "ini.compatible_prints", "ini.compatible_prints_condition", "ini.filament_settings_id", "ini.inherits", "ini.pm_method_version"}),
}


def _canonical_paths(slicer_id: str, *, important_only: bool = True) -> frozenset[str]:
    slicer_id = canonical_slicer_id(slicer_id)
    paths: set[str] = set()
    for definition in IMPORTANT_PARAMETER_CATALOG:
        if not important_only or definition.importance is DiffCategory.IMPORTANT_PARAMETER:
            paths.update(definition.native_paths.get(slicer_id, ()))
    return frozenset(paths)


def important_paths_for_slicer(slicer_id: str) -> frozenset[str]:
    return _canonical_paths(slicer_id)


def system_metadata_paths_for_slicer(slicer_id: str) -> frozenset[str]:
    return SYSTEM_METADATA_PATHS.get(canonical_slicer_id(slicer_id), frozenset())


def classify_native_path(slicer_id: str, path: str) -> DiffCategory:
    slicer_id = canonical_slicer_id(slicer_id)
    base = _INDEX_SUFFIX.sub("", path)
    if path in system_metadata_paths_for_slicer(slicer_id) or base in system_metadata_paths_for_slicer(slicer_id):
        return DiffCategory.SYSTEM_METADATA
    if base in important_paths_for_slicer(slicer_id):
        return DiffCategory.IMPORTANT_PARAMETER
    return DiffCategory.OTHER_PARAMETER


def validate_catalog() -> tuple[str, ...]:
    issues: list[str] = []
    ids = [definition.parameter_id for definition in IMPORTANT_PARAMETER_CATALOG]
    for parameter_id in sorted({item for item in ids if ids.count(item) > 1}):
        issues.append(f"duplicate parameter_id: {parameter_id}")
    for definition in IMPORTANT_PARAMETER_CATALOG:
        for raw_slicer, paths in definition.native_paths.items():
            slicer_id = canonical_slicer_id(raw_slicer)
            if slicer_id != raw_slicer:
                issues.append(f"non-canonical slicer id: {raw_slicer}")
            if len(paths) != len(set(paths)):
                issues.append(f"duplicate native path: {definition.parameter_id}/{slicer_id}")
    path_owners: dict[tuple[str, str], str] = {}
    for definition in IMPORTANT_PARAMETER_CATALOG:
        for raw_slicer, paths in definition.native_paths.items():
            slicer_id = canonical_slicer_id(raw_slicer)
            for path in paths:
                owner_key = (slicer_id, path)
                previous = path_owners.get(owner_key)
                if previous is not None and previous != definition.parameter_id:
                    issues.append(
                        f"conflicting native path: {slicer_id}/{path} -> {previous}, {definition.parameter_id}"
                    )
                path_owners[owner_key] = definition.parameter_id
    for slicer_id, paths in SYSTEM_METADATA_PATHS.items():
        if slicer_id != canonical_slicer_id(slicer_id):
            issues.append(f"non-canonical metadata slicer id: {slicer_id}")
        if len(paths) != len(set(paths)):
            issues.append(f"duplicate metadata path: {slicer_id}")
    return tuple(sorted(set(issues)))


def build_coverage_inventory(
    slicer_ids: Iterable[str],
    consistency_targets: Iterable[str] | None,
) -> tuple[dict[str, object], ...]:
    """Return static catalog-vs-target membership; never runs consistency.

    ``None`` deliberately produces ``Unknown`` coverage: no target catalog was
    supplied, and this function must not infer runtime comparison support.
    """
    targets = None if consistency_targets is None else frozenset(consistency_targets)
    rows: list[dict[str, object]] = []
    for slicer_id in sorted({canonical_slicer_id(item) for item in slicer_ids}):
        for definition in IMPORTANT_PARAMETER_CATALOG:
            paths = definition.native_paths.get(slicer_id, ())
            if not paths:
                continue
            target_names = (
                ()
                if targets is None
                else tuple(sorted(set(definition.consistency_targets) & targets))
            )
            coverage = "Unknown" if targets is None else ("Covered" if target_names else "Not covered")
            rows.append({
                "parameter_id": definition.parameter_id,
                "slicer_id": slicer_id,
                "native_paths": list(paths),
                "important": definition.importance is DiffCategory.IMPORTANT_PARAMETER,
                "consistency_target": list(target_names),
                "coverage": coverage,
                "evidence": "static target membership only; mapping and end-to-end comparison are not verified",
            })
    return tuple(rows)
