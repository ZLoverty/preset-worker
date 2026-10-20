# P9-B1 Implementation Report

## Executive summary

Implemented a standalone, read-only Bambu Studio 3MF parser and diagnostic CLI. The implementation extracts project configuration, model XML metadata, slice version, filament sequence, optional plate JSON metadata, embedded preset entry presence, filament slots, objects, volumes, and provenance-bearing priority parameters.

It does not compare against preset JSON and does not modify Worker lifecycle, Feishu, Miaoda, or BambuStudioProcessor.

## Files added

- src/preset_worker/three_mf/__init__.py
- src/preset_worker/three_mf/models.py
- src/preset_worker/three_mf/safe_zip.py
- src/preset_worker/three_mf/bambu_parser.py
- src/preset_worker/three_mf/diagnostics.py
- tests/test_three_mf.py
- docs/p9-B1_parser_design.md
- docs/p9-B1_resolution_rules.md
- docs/p9-B1_fixture_matrix.md

## Capabilities

- Bounded ZIP inspection with path traversal, duplicate path, entry count, size, compression ratio, and compression method checks.
- JSON/XML parsing without extractall.
- Raw project arrays preserved intact.
- Filament slot extraction from settings identifiers, filament type, and filament IDs.
- Object and volume metadata extraction from model settings.
- Plate JSON extraction when available.
- Source entry and source path provenance.
- Explicit RESOLVED, UNRESOLVED, NOT_APPLICABLE and related statuses.
- Diagnostic JSON CLI without credentials.
- Four cooling parameters: minimum fan speed, maximum fan speed, fan cooling layer-time threshold, and slow-down layer-time threshold.

## Resolution status

Verified limited resolution supports scalar storage, one-element arrays, and arrays whose cardinality equals filament slot count. Other array cardinalities remain unresolved. This intentionally avoids slot-minus-one universal indexing and handles the real H2D fixture without false effective-value claims.

Pressure Advance on Bambu printer projects is marked NOT_APPLICABLE for runtime-effective interpretation.

The cooling thresholds are not collapsed into a single value. fan_cooling_layer_time and slow_down_layer_time are extracted and resolved independently; Bambu source uses the former as the interpolation upper threshold and the latter as the lower threshold for maximum fan behavior.

## Verification

The real fixture was parsed successfully: 105 entries, one filament slot, 29 objects, no parser issues. Its flow ratio and other two-element arrays remain unresolved for the one-slot project, as required.

The diagnostic CLI produced a structured JSON report.

The repository environment has no python command and the virtual environment does not contain pytest. compileall and the CLI were run with .venv/bin/python; the full pytest suite could not be run because pytest is unavailable.

## Limitations and P9-B2 scope

Not implemented: complete Bambu inheritance, full get_filament_config_idx reproduction, runtime G-code verification, preset comparison, submission integration, and real controlled Bambu Studio experiment fixtures.

P9-B2 should consume the raw/provenance models and add comparison only after deciding how separately submitted preset context selects a slot. It should not bypass unresolved and ambiguous results.
