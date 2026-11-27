# Native Preset Architecture

## Implementations

| Slicer | Module | Format / encoding | Validation and canonical output |
|---|---|---|---|
| BambuStudio | `slicers/bambu_studio.py:21-155` | UTF-8 JSON object | requires `version`; deep-copy; injects `name` and `pm_method_version`; JSON `<PI> @<Printer>.json` |
| OrcaSlicer | `slicers/orca_slicer.py:75-104` + `orca_compatible_core.py:106-191` | UTF-8 JSON | requires filament-like object and non-empty name; shared JSON output |
| CrealityPrint | `slicers/creality_print.py:26-183` | UTF-8 JSON object | requires name/version/list `filament_settings_id`/string `inherits`; `from` User/None; JSON output |
| ElegooSlicer | `slicers/elegoo_slicer.py` | UTF-8 JSON | independent JSON processor; same company name/version policy, slicer-specific validation |
| SnapmakerOrcaSlicer | `slicers/snapmaker_orca.py:25-59` | UTF-8 JSON | facade over Orca-compatible core with Snapmaker identity |
| PrusaSlicer | `slicers/prusa_slicer.py:35-205` | UTF-8 INI/plain text | parses key/value INI; requires `.ini`, required material identity fields; preserves native text and emits `<PI> @<Printer>.ini` |

All JSON parsers explicitly decode UTF-8 and reject malformed JSON. Prusa parses text lines and preserves unknown/native fields in a `PrusaDocument` rather than converting to JSON.

## Inheritance and normalization

The processors preserve `inherits`/`base_id`/related fields; they do not resolve parent records. `normalize()` is mostly a deep copy (`bambu_studio.py:121-122`, Orca core `141-142`, Creality `136-137`). No parent repository lookup, cycle detection, multiple inheritance merge, or missing-parent resolution was found. Therefore inherited values remain inherited in canonical artifacts and consistency may see missing values or arrays. This is `CONFIRMED`; an external slicer GUI may have already materialized values, but the worker does not prove that.

Company policy is deliberately separate: canonical `name` is `<pi_code> @<printer>` and `pm_method_version` is context-authoritative. Prusa uses filename as display identity and rejects a synthetic `name` field (`prusa_slicer.py:150-168`).

## Artifact contract

Canonical serialization returns `Artifact` with deterministic filename and media type. JSON uses `application/json`; Prusa uses `text/plain`/INI output. On invalid source or canonical data processors return empty artifact plus `ValidationResult`; malformed byte decoding raises `InvalidArtifactError` and is converted by enrichment into validation failure.

## Onboarding implication

A new slicer must provide parser, source validation, normalization, policy, canonical validation, serialization, and diff. Parent resolution is conditional: unless fixtures prove the worker can safely resolve it, preserve the native inheritance field and require explicit human semantics.
