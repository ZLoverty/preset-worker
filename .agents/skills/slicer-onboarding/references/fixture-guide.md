# Fixture intake and characterization

## Minimum

Require one real valid Native Preset, slicer name/version, target repository, and printer/material identity when relevant. For claimed 3MF support also require one real 3MF, its Native Preset relationship, and expected values or an explicit characterization task.

Recommended but conditional: invalid input, inherited child and parent, single- and multi-filament 3MF, multi-plate 3MF, matching pair, known mismatch pair, and unsupported/ambiguous example.

## Automated characterization

Before implementation, inventory each fixture's path, size/hash, extension, signature, encoding, top-level structure, JSON/INI/XML keys, ZIP members, candidate identities, inheritance references, array shapes, filament slots, plate/object metadata, and slicer version markers. Preserve original bytes. Produce a fixture inventory and identify missing evidence.

Use the repository's bounded ZIP reader where available. Read archives in memory or a validated temporary location; never execute embedded content or extract to an arbitrary path.

## Semantic checkpoints

Ask the user only after inspection when evidence does not establish array-index meaning, slot numbering, duplicate identity equivalence, plate selection, parent merge/cycle rules, printer compatibility syntax, unit conversions, parameter aliases, or runtime-effective versus stored values. Do not ask the user to transcribe keys or values that can be extracted reliably.

## Evidence labels

- `CONFIRMED`: directly supported by current code, fixture bytes, or passing test assertions.
- `INFERRED`: plausible proposal requiring validation or approval.
- `NOT_VERIFIED`: unavailable fixture, test, or runtime evidence.

An inference must never become a Supported capability without an appropriate fixture and test. A successful parse is not semantic proof.

## Stop conditions

Stop implementation when format/identity is not understood, required fixtures are missing, mappings or units are uncertain, array/slot semantics are required but unknown, inheritance would be guessed, or shared contracts would need unapproved changes. Continue independent, well-understood discovery and report partial completion accurately.
