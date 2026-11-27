"""Flash Studio processor backed by the evidence-backed JSON core."""

from __future__ import annotations

from typing import Any

from ..diff import UnifiedDiff
from .contracts import Artifact, ProcessedArtifact, ProcessingContext, ValidationResult, ValidationStatus
from .orca_compatible_core import OrcaCompatibleCore
from .parameter_catalog import important_paths_for_slicer, system_metadata_paths_for_slicer


IMPORTANT_PARAMETER_PATHS = important_paths_for_slicer("FlashStudio")
SYSTEM_METADATA_PATHS = system_metadata_paths_for_slicer("FlashStudio")


class FlashStudioProcessor:
    """Flash Studio business identity over the shared JSON processing core.

    The shared core is used only for the JSON artifact contract.  Flash Studio
    remains a distinct registered slicer so its native diff classification and
    future 3MF semantics can evolve independently.
    """

    slicer_id = "FlashStudio"
    important_parameter_paths = IMPORTANT_PARAMETER_PATHS

    def __init__(self) -> None:
        self._core = OrcaCompatibleCore(
            self.slicer_id,
            IMPORTANT_PARAMETER_PATHS,
            SYSTEM_METADATA_PATHS,
        )

    def parse(self, artifact: Artifact, context: ProcessingContext) -> Any:
        return self._core.parse(artifact, context)

    def validate_source(self, source: Any, context: ProcessingContext) -> ValidationResult:
        validation = self._core.validate_source(source, context)
        errors = list(validation.errors)
        if validation.valid and (not isinstance(source.get("version"), str) or not source["version"].strip()):
            errors.append("FlashStudio preset 缺少有效 version")
        return ValidationResult(
            validation.status if not errors else ValidationStatus.INVALID_USER_ARTIFACT,
            tuple(errors),
            validation.warnings,
        )

    def normalize(self, source: Any, context: ProcessingContext) -> Any:
        return self._core.normalize(source, context)

    def apply_company_policy(self, normalized: Any, context: ProcessingContext) -> Any:
        return self._core.apply_company_policy(normalized, context)

    def validate_canonical(self, canonical: Any, context: ProcessingContext) -> ValidationResult:
        return self._core.validate_canonical(canonical, context)

    def serialize(self, canonical: Any, context: ProcessingContext) -> Artifact:
        return self._core.serialize(canonical, context)

    def diff(self, base_artifact: Artifact | None, candidate_artifact: Artifact, context: ProcessingContext) -> UnifiedDiff:
        return self._core.diff(base_artifact, candidate_artifact, context)

    def process(self, artifact: Artifact, context: ProcessingContext) -> ProcessedArtifact:
        return self._core.process(self, artifact, context)
