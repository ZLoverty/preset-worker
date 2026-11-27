# Future `slicer-onboarding` Skill Design

The repository has no existing onboarding skill; P10-A does not create one. Recommended future location follows the repository agent convention, preferably `.agents/skills/slicer-onboarding/SKILL.md`, with concise references rather than a source snapshot.

```text
.agents/skills/slicer-onboarding/
  SKILL.md
  references/architecture.md
  references/contracts.md
  references/fixture-guide.md
  references/acceptance-checklist.md
  templates/onboarding-report.md
  templates/compatibility-matrix.md
```

Entry conditions: user names a new slicer and supplies native/3MF fixtures or explicitly accepts a discovery-only assessment. Required inputs are slicer name/aliases, versions, native samples, 3MF samples, expected semantic values and target repository. Optional inputs are Feishu labels, parent presets and publication requirements.

Phases: discovery -> compatibility assessment -> fixture characterization -> implementation -> targeted/cross-slicer verification -> acceptance. Each phase should emit an artifact, list unresolved decisions, and stop before semantic implementation when evidence is insufficient.

Human checkpoints: mapping approval, inheritance/array/slot semantics, runtime-effective claims, and publication readiness. Completion requires processor registration, validation/diff tests, 3MF/consistency coverage where claimed, integration tests, support matrix and explicit limitations.

Failure/stop conditions: unsupported or ambiguous format, missing paired evidence, unresolved identity semantics, missing required fixture, regression failure, or partial registry capability. The skill should inspect current source every run; references describe contracts and procedures, not copied implementation.

Maintenance: update references when contracts/schema/statuses change; run a registration-completeness check and a small cross-slicer regression suite whenever the skill changes.
