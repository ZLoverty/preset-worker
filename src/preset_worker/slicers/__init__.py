"""Slicer-specific artifact processing."""

from .bambu_studio import BambuStudioProcessor
from .creality_print import CrealityPrintProcessor
from .orca_slicer import OrcaSlicerProcessor
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
    "OrcaSlicerProcessor",
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
