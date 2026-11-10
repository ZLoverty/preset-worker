# Executive Summary

`preset-worker` has a usable shared native-processing boundary: six registered slicers implement a processor contract for parsing, validation, normalization, canonical serialization and deterministic diff. The workflow and publication layers are mostly slicer-neutral.

The main onboarding hazard is that 3MF consistency is a parallel architecture. Validators are explicitly registered in a second map, use separate parameter/mapping catalogs, and often compare only eight parameters. A parameter can be visibly extracted yet become `UNRESOLVED`, or be silently omitted when it is outside the fixed comparison set. Detailed reports retain evidence, but the Feishu outer envelope collapses many failures to a generic error.

Current reproducibility is limited: pytest is unavailable, and the unittest baseline is `240 tests, 6 failures, 8 errors, 2 skips`; missing external Bambu fixtures account for most errors, while important-parameter classification and one Prusa missing-value assertion fail directly.

Recommended next step is P10-B: create a concise skill that always inspects current registries and catalogs, characterizes fixtures, requires human confirmation for arrays/inheritance/slot semantics, and refuses to claim support until processor, consistency capability, fixtures and integration tests are complete. Do not begin with a plugin framework or broad refactor.
