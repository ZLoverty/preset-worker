"""The stable boundary between workflow code and slicer implementations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from ..diff import UnifiedDiff


class ValidationStatus(str, Enum):
    VALID = "valid"
    INVALID_USER_ARTIFACT = "invalid_user_artifact"
    UNSUPPORTED_SLICER = "unsupported_slicer"
    INTERNAL_PROCESSING_FAILURE = "internal_processing_failure"


@dataclass(frozen=True)
class ProcessingContext:
    """Inputs needed by a processor; deliberately contains no Submission."""

    pi_code: str
    printer: str
    slicer: str
    pm_method_version: str


@dataclass(frozen=True)
class Artifact:
    """Opaque slicer artifact. Only its owner may interpret ``content``."""

    content: bytes
    filename: str
    media_type: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    status: ValidationStatus
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return self.status is ValidationStatus.VALID

    def as_dict(self) -> dict[str, Any]:
        # Keep the existing persisted shape while exposing the new status.
        return {
            "valid": self.valid,
            "status": self.status.value,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ProcessedArtifact:
    canonical_artifact: Artifact
    validation_result: ValidationResult


class SlicerProcessor(Protocol):
    slicer_id: str

    def parse(self, artifact: Artifact, context: ProcessingContext) -> Any: ...
    def validate_source(self, source: Any, context: ProcessingContext) -> ValidationResult: ...
    def normalize(self, source: Any, context: ProcessingContext) -> Any: ...
    def apply_company_policy(self, normalized: Any, context: ProcessingContext) -> Any: ...
    def validate_canonical(self, canonical: Any, context: ProcessingContext) -> ValidationResult: ...
    def serialize(self, canonical: Any, context: ProcessingContext) -> Artifact: ...
    # ``base_artifact is None`` means CREATE's initial review projection, not
    # a persisted or synthetic empty preset version.
    def diff(self, base_artifact: Artifact | None, candidate_artifact: Artifact, context: ProcessingContext) -> UnifiedDiff: ...


def process_artifact(
    processor: SlicerProcessor,
    artifact: Artifact,
    context: ProcessingContext,
) -> ProcessedArtifact:
    """Run the explicit stages for processors that only implement the contract."""
    source = processor.parse(artifact, context)
    validation = processor.validate_source(source, context)
    if not validation.valid:
        return ProcessedArtifact(Artifact(b"", "", None), validation)
    normalized = processor.normalize(source, context)
    canonical = processor.apply_company_policy(normalized, context)
    validation = processor.validate_canonical(canonical, context)
    if not validation.valid:
        return ProcessedArtifact(Artifact(b"", "", None), validation)
    return ProcessedArtifact(processor.serialize(canonical, context), validation)


class SlicerProcessorRegistry:
    _ALIASES = {
        "OrcaSlicer (Snapmaker)": "SnapmakerOrcaSlicer",
        "OrcaSlicer Snapmaker": "SnapmakerOrcaSlicer",
        "Orca Slicer (Snapmaker)": "SnapmakerOrcaSlicer",
    }

    def __init__(self, processors: list[SlicerProcessor] | None = None):
        self._processors = {processor.slicer_id: processor for processor in processors or []}

    def register(self, processor: SlicerProcessor) -> None:
        self._processors[processor.slicer_id] = processor

    def get(self, slicer_id: str) -> SlicerProcessor | None:
        normalized_id = self._ALIASES.get(slicer_id.strip(), slicer_id.strip())
        return self._processors.get(normalized_id)

    def require(self, slicer_id: str) -> SlicerProcessor:
        processor = self.get(slicer_id)
        if processor is None:
            raise UnsupportedSlicerError(slicer_id)
        return processor


class UnsupportedSlicerError(ValueError):
    def __init__(self, slicer_id: str):
        self.slicer_id = slicer_id
        self.validation = ValidationResult(
            ValidationStatus.UNSUPPORTED_SLICER,
            (f"暂不支持 slicer: {slicer_id}",),
        )
        super().__init__(self.validation.errors[0])


class InvalidArtifactError(ValueError):
    def __init__(self, message: str):
        self.validation = ValidationResult(ValidationStatus.INVALID_USER_ARTIFACT, (message,))
        super().__init__(message)


class InternalProcessingError(RuntimeError):
    """An engineer-facing processor failure, distinct from bad user input."""

    def __init__(self, message: str):
        self.validation = ValidationResult(ValidationStatus.INTERNAL_PROCESSING_FAILURE, (message,))
        super().__init__(message)
