"""Slicer-specific artifact processing."""

from .bambu_studio import BambuStudioProcessor
from .creality_print import CrealityPrintProcessor
from .elegoo_slicer import ElegooSlicerProcessor
from .orca_slicer import OrcaSlicerProcessor
from .prusa_slicer import PrusaSlicerProcessor
from .snapmaker_orca import SnapmakerOrcaSlicerProcessor
from ..diff import (
    ChangeType,
    DiffCategory,
    DiffChange,
    UnifiedDiff,
    deserialize_unified_diff,
    serialize_unified_diff,
)
from .contracts import (
    Artifact,
    InternalProcessingError,
    ProcessedArtifact,
    ProcessingContext,
    process_artifact,
    SlicerProcessor,
    SlicerProcessorRegistry,
    ValidationResult,
    ValidationStatus,
)
from .registry import default_processor_registry

__all__ = [
    "BambuStudioProcessor",
    "CrealityPrintProcessor",
    "ElegooSlicerProcessor",
    "OrcaSlicerProcessor",
    "PrusaSlicerProcessor",
    "SnapmakerOrcaSlicerProcessor",
    "ChangeType",
    "DiffCategory",
    "DiffChange",
    "UnifiedDiff",
    "deserialize_unified_diff",
    "serialize_unified_diff",
    "Artifact",
    "InternalProcessingError",
    "ProcessedArtifact",
    "ProcessingContext",
    "process_artifact",
    "SlicerProcessor",
    "SlicerProcessorRegistry",
    "ValidationResult",
    "ValidationStatus",
    "default_processor_registry",
]
