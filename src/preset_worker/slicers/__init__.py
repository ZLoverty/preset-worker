"""Slicer-specific artifact processing."""

from .bambu_studio import BambuStudioProcessor
from .contracts import (
    InternalProcessingError,
    ProcessedArtifact,
    ProcessingContext,
    process_artifact,
    SlicerProcessor,
    SlicerProcessorRegistry,
    ValidationResult,
    ValidationStatus,
)

__all__ = [
    "BambuStudioProcessor",
    "InternalProcessingError",
    "ProcessedArtifact",
    "ProcessingContext",
    "process_artifact",
    "SlicerProcessor",
    "SlicerProcessorRegistry",
    "ValidationResult",
    "ValidationStatus",
]
