"""Slicer-specific artifact processing."""

from .bambu_studio import BambuStudioProcessor
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
