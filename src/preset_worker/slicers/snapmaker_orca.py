"""Snapmaker-distributed OrcaSlicer processor facade."""

from __future__ import annotations

from typing import Any

from ..diff import UnifiedDiff
from .contracts import Artifact, ProcessedArtifact, ProcessingContext, ValidationResult
from .orca_compatible_core import OrcaCompatibleCore


class SnapmakerOrcaSlicerProcessor:
    """Distinct business identity over the evidence-backed Orca core."""

    slicer_id = "SnapmakerOrcaSlicer"

    def __init__(self) -> None:
        self._core = OrcaCompatibleCore("SnapmakerOrcaSlicer")

    def parse(self, artifact: Artifact, context: ProcessingContext) -> Any:
        return self._core.parse(artifact, context)

    def validate_source(self, source: Any, context: ProcessingContext) -> ValidationResult:
        return self._core.validate_source(source, context)

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
