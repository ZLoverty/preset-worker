# Acceptance checklist

Do not claim full completion while a mandatory check is missing.

## Native Preset

- [ ] Format and encoding verified; malformed input rejected appropriately.
- [ ] Required identity/type fields validated.
- [ ] Canonical naming and context-authoritative metadata verified.
- [ ] Deterministic canonical output and Native Diff verified.
- [ ] Unknown-field preservation behavior documented.
- [ ] Important-parameter classification tested without changing shared rules.

## Inheritance

- [ ] Declared as resolve, preserve-only, or unsupported.
- [ ] Parent requirements and missing-parent behavior documented.
- [ ] No unsupported effective-value claim.

## 3MF

- [ ] Real archive and required members inspected.
- [ ] Malformed archive behavior tested.
- [ ] Raw values, identity, slot/index semantics asserted.
- [ ] Multi-filament and multi-plate capabilities declared accurately.

## Consistency

- [ ] Validator registered and reachable if claimed.
- [ ] Matching, mismatch, missing, and unresolved cases tested; ambiguous cases tested when relevant.
- [ ] Exact values, source paths, normalization and report schema asserted.
- [ ] Extracted-but-uncompared parameters detected and disclosed.

## Integration and regression

- [ ] Preview path exercised.
- [ ] Formal Submit path exercised.
- [ ] Publication tested or marked `Not Verified`.
- [ ] Feishu mapping unchanged unless separately approved.
- [ ] Targeted and cross-slicer tests run.
- [ ] Current failures classified as pre-existing, new, environment-dependent, or undetermined.
- [ ] No unrelated production behavior changed.

## Stop before acceptance

Stop if registration is incomplete, required tests fail, a new regression exists, claimed parameters are not compared, evidence is missing, or publication is claimed Verified without a suitable test.
