"""Small consistency-capability and registration-completeness guard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .contracts import SlicerProcessorRegistry, canonical_slicer_id


SUPPORTED = "SUPPORTED"
UNSUPPORTED = "UNSUPPORTED"
_VALID_CAPABILITIES = frozenset({SUPPORTED, UNSUPPORTED})

# This is an explicit capability declaration, not a second processor registry.
# A new processor must intentionally choose whether consistency is supported.
DEFAULT_CONSISTENCY_CAPABILITIES: dict[str, str] = {
    "BambuStudio": SUPPORTED,
    "OrcaSlicer": SUPPORTED,
    "CrealityPrint": SUPPORTED,
    "ElegooSlicer": SUPPORTED,
    "PrusaSlicer": SUPPORTED,
    "SnapmakerOrcaSlicer": SUPPORTED,
}


@dataclass(frozen=True)
class RegistrationIssue:
    code: str
    slicer_id: str
    message: str


def _canonical(value: str) -> str:
    return canonical_slicer_id(value)


def check_registration_completeness(
    processor_registry: SlicerProcessorRegistry,
    validators: Mapping[str, object],
    capabilities: Mapping[str, str] | Iterable[tuple[str, str]],
) -> tuple[RegistrationIssue, ...]:
    """Return deterministic issues for the processor/validator capability boundary."""
    issues: list[RegistrationIssue] = []
    processors = {_canonical(item) for item in processor_registry.registered_ids}
    validator_ids = {_canonical(item) for item in validators}

    declarations: dict[str, str] = {}
    declaration_sources: dict[str, str] = {}
    entries = capabilities.items() if isinstance(capabilities, Mapping) else capabilities
    for raw_id, capability in entries:
        slicer_id = _canonical(raw_id)
        if slicer_id in declarations:
            code = "DUPLICATE_CAPABILITY_DECLARATION"
            issues.append(RegistrationIssue(
                code,
                slicer_id,
                f"consistency capability is declared more than once ({declaration_sources[slicer_id]} and {capability!r})",
            ))
            continue
        declarations[slicer_id] = capability
        declaration_sources[slicer_id] = repr(capability)
        if capability not in _VALID_CAPABILITIES:
            issues.append(RegistrationIssue(
                "INVALID_CAPABILITY_DECLARATION",
                slicer_id,
                f"unknown consistency capability {capability!r}",
            ))

    for slicer_id in sorted(processors - declarations.keys()):
        issues.append(RegistrationIssue(
            "MISSING_CAPABILITY_DECLARATION",
            slicer_id,
            "registered Native Preset processor has no consistency capability declaration",
        ))

    for slicer_id in sorted(declarations.keys() - processors):
        issues.append(RegistrationIssue(
            "UNKNOWN_CAPABILITY_DECLARATION",
            slicer_id,
            "consistency capability declaration has no registered Native Preset processor",
        ))

    for slicer_id in sorted(processors & declarations.keys()):
        capability = declarations[slicer_id]
        has_validator = slicer_id in validator_ids
        if capability == SUPPORTED and not has_validator:
            issues.append(RegistrationIssue(
                "MISSING_EXPECTED_VALIDATOR",
                slicer_id,
                "consistency is declared SUPPORTED but no validator is registered",
            ))
        elif capability == UNSUPPORTED and has_validator:
            issues.append(RegistrationIssue(
                "UNEXPECTED_VALIDATOR",
                slicer_id,
                "consistency is declared UNSUPPORTED but a validator is registered",
            ))

    for slicer_id in sorted(validator_ids - processors):
        issues.append(RegistrationIssue(
            "ORPHAN_VALIDATOR",
            slicer_id,
            "consistency validator has no registered Native Preset processor",
        ))

    return tuple(sorted(issues, key=lambda issue: (issue.code, issue.slicer_id, issue.message)))


def registration_issue_as_dict(issue: RegistrationIssue) -> dict[str, str]:
    return {"code": issue.code, "slicer_id": issue.slicer_id, "message": issue.message}
