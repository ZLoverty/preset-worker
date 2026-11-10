# Fixtures and Tests

## Inventory

| Slicer | Native fixtures | 3MF | Exercised tests |
|---|---:|---:|---|
| BambuStudio | no committed slicer directory | expected external download | `test_p9_d6_*`, `test_three_mf.py` partly skipped/missing |
| CrealityPrint | 15 JSON incl reconnaissance | `creality.3mf` | `test_creality_print.py`, `test_p9_d2.py`, `test_p9_d3.py` |
| ElegooSlicer | 11 JSON | `elegoo.3mf` | `test_elegoo_slicer.py`, P9-D2/D3 |
| OrcaSlicer | 16 JSON incl valid/experiments/roundtrip | `orca.3mf` | `test_orca_slicer.py`, P9-D2/D3 |
| SnapmakerOrcaSlicer | 13 JSON incl cross variants | `snapmaker-orca.3mf` | `test_snapmaker_orca.py`, P9-D3 |
| PrusaSlicer | 9 INI + `pla_test.ini` | `prusa.3mf` | `test_prusa_slicer.py`, P9-D4 |

Reconnaissance fixtures are strong for structural/name/metadata experiments, but many tests only assert parsing/canonicalization. Multi-filament and array resolution have focused synthetic tests; complete matching/mismatch pairs and publication tests depend on missing external Bambu files.

## Test command result

`python -m pytest -q` could not run because pytest is not installed. With `PYTHONPATH=src`, unittest discovered 240 tests: 6 failures, 8 errors, 2 skips.

Errors are primarily missing `downloads/3mf-fixture/PPS100CF10 H2D (1).json/.3mf` in `test_p9_d6_preview.py` and `test_p9_d6_submit_consistency.py`. Failures include the important-field classification assertions in `test_fixture_field_classification.py:70-145` and `test_p9_d4.py:112` expecting `MISSING_IN_PRESET` but observing `MATCH`.

## Coverage quality

Good: deterministic diff tests, exact canonical filenames/media types, malformed ZIP/XML tests, alias dispatch, exact selected values for several arrays, and status contract tests in `test_comparison_core.py`/P9-D2/P9-D3.

Weak or absent: committed Bambu end-to-end pair, explicit missing-parent/circular inheritance fixtures, complete multi-plate semantics, every important parameter in consistency, diagnostic reason-code assertions, and publication behavior with every slicer using real 3MF. Tests can pass while an extracted parameter is omitted because many consistency loops are driven by fixed eight-item tuples rather than processor important sets.
