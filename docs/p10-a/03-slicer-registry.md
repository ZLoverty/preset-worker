# Slicer Registry and Dispatch

## Registration points

| Location | Purpose | Current slicers | Onboarding action |
|---|---|---|---|
| `slicers/registry.py:28-36` | production processor composition | six processors | instantiate/register processor |
| `slicers/contracts.py:98-119` | lookup and aliases | six registered; three Snapmaker aliases | add alias if needed; currently duplicated |
| `services/consistency_preview.py:30-37` | Preview/formal consistency dispatch | six validators | add validator map entry |
| `three_mf/consistency.py:358-419` | validator functions | Bambu + four native adapters + Prusa | implement or delegate validator |
| `backfill_slicer_version.py:31-41` | GitHub version repository and aliases | Bambu absent; Orca/Snapmaker/Elegoo/Prusa mappings | conditional metadata mapping |
| `services/enrichment.py:577-656` | processor lookup from record slicer | registry-driven | no workflow change if id resolves |
| `publication.py:170-177` | Preset fields | generic `slicer` relation | no slicer branch |

The exact internal identifiers are the processor `slicer_id` values. `registry.py` only aliases `OrcaSlicer (Snapmaker)`; `contracts.py` additionally accepts `OrcaSlicer Snapmaker` and `Orca Slicer (Snapmaker)`. This is a concrete duplication risk: `canonical_slicer_id()` and registry lookup do not share one alias source.

## Conditional branches

Slicer-name comparisons occur in consistency dispatch, backfill normalization, migration inference and tests. 3MF parsing itself is not auto-detected by filename or content: the caller selects a validator by slicer id. `consistency_preview.py:82-85` returns empty for an unsupported id rather than falling back to Bambu.

## Audit conclusion

`CONFIRMED`: adding a slicer requires at least processor composition and consistency dispatch changes. If version backfill is in scope, it also needs repository/alias configuration. The main enrichment and publication services are shared and should not require slicer-specific edits.

`HIGH_VALUE`: centralize aliases or expose a registry capability check (processor + consistency + 3MF), because current partial registration is possible. Do not introduce a plugin framework; the existing composition boundary is adequate.
