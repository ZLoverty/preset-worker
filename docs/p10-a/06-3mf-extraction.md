# 3MF Extraction

## Architecture

`three_mf/safe_zip.py` provides bounded/safe ZIP reading and hashing. Extraction is split by format family:

- Bambu/Orca-compatible native project structures use `bambu_parser.py:129-199`.
- Prusa uses `prusa_parser.py:108-148` and `Metadata/Slic3r_PE.config` INI parsing.
- Creality, Elegoo, Orca and Snapmaker validators delegate to the shared Bambu-style JSON project settings parser through `native_consistency.py`.

The shared Bambu parser inspects `Metadata/project_settings.config`, optional `model_settings.config`, `slice_info.config`, `filament_sequence.json`, `Metadata/plate_<n>.json`, and embedded preset entries. It records raw parameters, project context, slots, objects, plates, issues and archive hash. Arrays are intentionally kept intact until resolution (`bambu_parser.py:98-110`).

Prusa extracts selected INI keys, filament identities/types, printer model and generated slicer version. It does not parse Bambu XML/JSON structures.

## Slot and parameter handling

`_slots()` creates 1-based slots from `filament_settings_id`; `resolve_bambu_project()` resolves arrays only when a slot is explicit and cardinality is one or equals slot count (`bambu_parser.py:202-231`). `comparison_core.select_slot()` matches native preset identities to project slots and returns `UNIQUE`, `UNRESOLVED`, or `AMBIGUOUS`; duplicate identities are accepted only when all target arrays are normalized-equivalent (`comparison_core.py:169-207`).

Raw values and normalized values are distinct: snapshots retain raw arrays; comparison normalizes numeric strings with `Decimal`. No unit conversion is performed; units are labels only.

## Coverage

Repository fixtures contain one 3MF each for Creality, Elegoo, Orca, Snapmaker and Prusa. No committed Bambu fixture appears under `tests/fixtures`; Bambu integration tests expect `downloads/3mf-fixture`. Multi-plate/object structures are parsed by Bambu code but fixture/test evidence for semantic selection is limited. Multi-filament array resolution has focused unit tests, not complete per-slicer semantic coverage.

Unsupported ZIP entries and malformed XML/JSON become snapshot issues; safe ZIP or type failures can raise to the consistency boundary. The extractor does not infer slicer identity from archive contents; caller-selected slicer controls parser.
