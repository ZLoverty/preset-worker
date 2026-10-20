"""Read-only Bambu Studio 3MF inspection and configuration extraction."""

from .bambu_parser import parse_bambu_3mf, resolve_bambu_project
from .models import (
    BambuProjectSnapshot,
    ResolutionStatus,
    ResolvedProjectSettings,
)

__all__ = [
    "BambuProjectSnapshot",
    "ResolutionStatus",
    "ResolvedProjectSettings",
    "parse_bambu_3mf",
    "resolve_bambu_project",
]
