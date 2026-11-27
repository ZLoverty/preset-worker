# Automation Opportunities

## Deterministic

- enumerate repository registrations, aliases and dispatch maps;
- inspect file extensions, encodings, JSON/INI keys and 3MF ZIP entries;
- generate fixture manifests and detect missing valid/invalid/pair categories;
- scaffold processor and test names from `SlicerProcessor` contract;
- run syntax/import/unit/targeted tests and check deterministic diff ordering;
- compare processor important sets against consistency target sets and report omissions.

## Evidence-based inference

An agent may propose native-to-canonical mappings, identity fields, required fields, media type and inheritance candidates when repeated across paired fixtures. It must validate proposed mappings against independent matching and mismatch fixtures and retain source paths/raw values in the report. It must not silently commit inferred semantics.

## Human confirmation required

Confirm multi-element array meaning, 0/1-based slot indexing, duplicate identity equivalence, plate selection, printer compatibility syntax, parent merge/cycle semantics, unit conversions, runtime-effective vs stored values, and whether similarly named fields are semantically equivalent. The agent must stop implementation at these checkpoints when fixtures do not prove the meaning.

## Safety boundary

Automation may add the audit report and test skeleton only when requested. It must not invent mappings or mark unsupported parameters as `MATCH`; unresolved coverage must remain explicit.
