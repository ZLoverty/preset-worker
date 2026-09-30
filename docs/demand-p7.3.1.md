# P7.3.1 — OrcaSlicer Real-Artifact Compatibility Validation

## 0. Purpose

P7.3 has structurally implemented `OrcaSlicerProcessor`, and all automated tests currently pass.

However, Orca support is NOT yet considered production-validated because the current fixtures are synthetic and based on documented profile structure rather than real OrcaSlicer export/import behavior.

P7.3.1 validates the processor against a **real OrcaSlicer filament preset** and determines the actual identity/display semantics of:

```text
name
setting_id
filament_id
inherits
```

The main question is:

> When the Worker canonicalizes a real OrcaSlicer filament preset, which identity-related fields must be modified, preserved, regenerated, or left untouched so that the resulting artifact imports correctly and appears as the intended custom preset?

This phase is primarily a compatibility experiment.

Do NOT redesign the architecture unless the experiment demonstrates that the current processor contract cannot represent required Orca behavior.

---

# 1. Human / Agent Responsibility Split

The Agent owns:

```text
inspect real exported artifact
analyze relevant fields
generate controlled experiment variants
generate experiment manifest
generate checksums
compare round-trip exports
infer observed field behavior
update OrcaSlicerProcessor
replace/add real fixtures
add regression tests
run full test suite
document findings
```

The human owns only GUI behavior that cannot be reliably determined programmatically:

```text
export one real custom filament preset from OrcaSlicer
import generated experiment variants into OrcaSlicer
record visible behavior
re-export selected successfully imported presets
```

The human must NOT manually edit experiment JSON.

---

# 2. Required Human Input

Before running the experimental generation step, obtain one real filament preset exported from the user's actual OrcaSlicer installation.

Prefer a simple custom filament preset derived from a normal base preset.

The source preset should ideally:

```text
be a filament/material preset
be user-created/custom rather than a built-in system file
import/export normally
contain typical Orca identity fields
have a known visible name
```

Do not require the user to intentionally modify JSON.

---

# 3. Preserve Original Artifact

Once supplied, save the real export unchanged under an appropriate fixture/input location.

For example:

```text
tests/fixtures/slicers/orca_slicer/real/
    source_original.json
```

or an equivalent project-consistent path.

Never modify the original file in place.

Compute and record its checksum before generating variants.

---

# 4. Inspect the Real Export

Analyze the actual source artifact and report the presence, type and value of relevant fields.

At minimum inspect:

```text
type
name
setting_id
filament_id
inherits
filament_type
version
from
instantiation
```

and other identity-looking fields actually present.

Do not assume all listed fields exist.

---

# 5. Compare Against Current Synthetic Fixture

Compare the real export with the current synthetic Orca fixture.

Report:

```text
fields present only in real export
fields present only in synthetic fixture
different value types
different structural assumptions
identity-related differences
inheritance-related differences
```

This comparison is important because the current processor was built before a real export was available.

---

# 6. Do Not Change Processor Yet

Before GUI experiment results are available, do NOT change Orca canonicalization rules merely because a field looks important.

Specifically, do not decide that:

```text
setting_id must change
filament_id must change
inherits must change
```

based only on field names.

First generate controlled experiments.

---

# 7. Establish Baseline

Create an untouched copy of the real source artifact as:

```text
00_baseline.json
```

Its contents must be semantically identical to the source artifact.

Purpose:

> Confirm that the export itself can be re-imported into the same OrcaSlicer environment.

---

# 8. Generate Controlled Experiment Matrix

Generate experiment files automatically.

Use clearly unique experimental names unlikely to collide with existing presets.

For example:

```text
P7TEST_NAME_ONLY
P7TEST_NAME_SETTING
P7TEST_NAME_FILAMENT
P7TEST_ALL_IDENTITY
```

Do not use production PI Codes for experiments.

---

# 9. Variant A — Name Only

Create:

```text
01_name_only.json
```

Modify ONLY:

```text
name
```

Set it to a unique test name.

All other fields must remain semantically unchanged.

Purpose:

> Determine whether changing `name` alone controls the visible imported preset identity.

---

# 10. Variant B — Name + setting_id

Create:

```text
02_name_setting_id.json
```

Modify:

```text
name
setting_id
```

only if `setting_id` exists in the real artifact.

Use distinct values so the GUI result can be unambiguously associated with this experiment.

Do not invent this variant if the field does not exist.

---

# 11. Variant C — Name + filament_id

Create:

```text
03_name_filament_id.json
```

Modify:

```text
name
filament_id
```

only if `filament_id` exists.

Keep all other fields unchanged.

---

# 12. Variant D — All Identity Candidates

Create:

```text
04_all_identity.json
```

Modify:

```text
name
setting_id
filament_id
```

for fields that actually exist.

Do not modify `inherits` in this variant.

---

# 13. Variant E — Name + Remove setting_id

If the real artifact contains `setting_id`, create:

```text
05_name_without_setting_id.json
```

Modify:

```text
name
```

and remove:

```text
setting_id
```

Purpose:

> Determine whether `setting_id` is mandatory, optional, regenerated, or significant to import identity.

---

# 14. Variant F — Name + Remove filament_id

If the real artifact contains `filament_id`, create:

```text
06_name_without_filament_id.json
```

Modify:

```text
name
```

and remove:

```text
filament_id
```

---

# 15. Variant G — Inherits Preservation

If the source contains:

```text
inherits
```

create:

```text
07_name_inherits_preserved.json
```

Modify only:

```text
name
```

while explicitly preserving the original `inherits` value.

This may overlap semantically with Variant A; retain it only if useful for making the inheritance experiment explicit.

---

# 16. Do Not Generate Dangerous Inheritance Values

Do not randomly mutate `inherits` to arbitrary nonexistent values in the first experiment set.

We are first determining identity semantics.

A deliberately broken inheritance experiment may be added later if required.

---

# 17. `pm_method_version`

Do NOT include `pm_method_version` as an independent variable in the identity experiment.

Its purpose is already defined by the Worker business model.

After identity behavior is understood, validate separately that Orca preserves this custom field through import/export.

---

# 18. One Variable at a Time

Except for explicitly named combination variants, each experiment must change exactly the documented field(s).

Do not accidentally change:

```text
JSON formatting-dependent semantics
field ordering-dependent semantics
timestamps
version
inherits
filament_type
printer compatibility
other parameters
```

---

# 19. Experiment Manifest

Generate:

```text
experiment_manifest.md
```

or equivalent.

For every variant record:

```text
filename
source checksum
variant checksum
fields intentionally changed
old values
new values
question being tested
```

This is mandatory.

The human should not need to inspect JSON manually to know what each file tests.

---

# 20. Generate Human Test Sheet

Generate a compact:

```text
GUI_TEST_RESULTS.md
```

with a table the human can fill in.

Use columns:

```text
Variant
Import succeeds?
Visible preset name
Created new preset?
Overwrote/replaced existing preset?
Duplicate/conflict warning?
Other visible behavior
Re-exported filename
```

Pre-fill the Variant column.

Leave observation columns blank.

---

# 21. Human GUI Procedure

The human performs the following in the same OrcaSlicer installation from which the source artifact was exported.

For each variant:

```text
1. Import the file.
2. Record whether import succeeds.
3. Record the visible preset name.
4. Record whether a new preset appears.
5. Record whether an existing preset is replaced/merged.
6. Record any duplicate/conflict/error dialog.
```

Do not ask the human to inspect internal Orca files unless later required.

---

# 22. Test Baseline First

The first GUI test must be:

```text
00_baseline.json
```

If baseline cannot be imported successfully, STOP the identity experiment.

The test setup is invalid or the export/import workflow is misunderstood.

Investigate before interpreting other variants.

---

# 23. Avoid Cross-Variant Contamination

Identity experiments can interfere with one another if Orca considers two variants the same preset.

Therefore the human should record overwrite/merge behavior carefully.

Where practical:

```text
restart from a known state
delete experimental presets between tests
or use unique identity values
```

Do not infer identity solely from visible name.

Overwrite behavior is itself important evidence.

---

# 24. Re-export Successful Variants

After GUI testing, re-export selected successfully imported variants.

At minimum attempt to re-export:

```text
baseline
name-only
one variant involving setting_id if applicable
one variant involving filament_id if applicable
all-identity variant
```

If Orca does not expose a straightforward re-export path for a particular case, record that instead.

---

# 25. Preserve Round-Trip Files

Store re-exported files separately.

Example:

```text
tests/fixtures/slicers/orca_slicer/roundtrip/
    00_baseline_reexport.json
    01_name_only_reexport.json
    ...
```

Never overwrite the input experiment variants.

---

# 26. Automated Round-Trip Analysis

After the human supplies the re-exported files, automatically compare:

```text
input variant
vs
Orca re-export
```

Generate a structured report of every changed field.

Classify changes as:

```text
identity-related
Orca-generated metadata
formatting-only
unknown
```

Do not ignore unexpected changes.

---

# 27. Key Question — `name`

Determine from GUI observation and round-trip evidence:

```text
Does `name` control visible preset name?

Is `name` sufficient?

Does Orca rewrite it?

Does it interact with `inherits`?
```

Do not infer the answer from BambuStudio behavior.

---

# 28. Key Question — `setting_id`

Determine:

```text
Is setting_id required for import?

Does Orca regenerate it?

Does changing it create a distinct preset?

Does preserving it cause overwrite/merge?

Does it affect visible name?

Does it survive round-trip?
```

---

# 29. Key Question — `filament_id`

Determine:

```text
Is filament_id required?

Does Orca regenerate it?

Does changing it affect preset identity?

Does preserving it cause overwrite/merge?

Does it affect display?

Does it survive round-trip?
```

---

# 30. Key Question — `inherits`

Determine at minimum:

```text
Does preserving inherits allow successful import?

Does visible naming still follow the custom name?

Does Orca resolve the referenced base?

Does re-export preserve inherits?
```

If the source preset has no `inherits`, do not manufacture conclusions.

Record:

```text
not tested with this fixture
```

---

# 31. Key Question — Custom Field Preservation

Using a controlled variant or Worker-generated canonical artifact, include:

```text
pm_method_version
```

with a recognizable test value.

Import into OrcaSlicer and re-export.

Determine whether:

```text
pm_method_version survives unchanged
is removed
is rewritten
causes import failure
```

This is mandatory before production approval because the current Worker requires this field in canonical artifacts.

---

# 32. Worker Canonical Artifact Test

Once identity behavior is known, run the real source artifact through the actual:

```text
OrcaSlicerProcessor
```

using a controlled `ProcessingContext`.

Produce the real Worker canonical artifact.

Do not manually reconstruct what the Worker would output.

---

# 33. Human Import of Actual Worker Output

The human must import the actual processor-produced artifact.

This is the decisive compatibility test.

Verify:

```text
import succeeds
expected preset appears
expected visible name appears
parameters remain intact
no unexpected overwrite occurs
inheritance behaves acceptably
```

---

# 34. Re-export Actual Worker Output

If import succeeds, re-export that preset from OrcaSlicer.

Compare:

```text
Worker canonical artifact
vs
Orca re-export
```

This becomes the strongest real-world fixture for future regression tests.

---

# 35. Update Canonicalization Rules Only From Evidence

After completing the experiment, update `OrcaSlicerProcessor` if necessary.

Possible evidence-based outcomes include:

```text
change name only
change name + setting_id
change name + filament_id
change multiple identity fields
preserve IDs
remove/regenerate a field
```

Do not choose a rule merely for symmetry with BambuStudio.

---

# 36. Prefer Minimum Necessary Mutation

Among behaviors that successfully produce the intended result, prefer the canonicalization rule that changes the fewest slicer-native fields.

Principle:

> Preserve the user's real Orca artifact unless a field must change to satisfy company identity or metadata requirements.

---

# 37. Never Generate Random Identity During Canonicalization

Canonicalization must remain deterministic.

Do not solve an Orca identity problem by generating:

```text
random UUID
timestamp-based ID
random setting_id
```

unless Orca explicitly requires such an identifier and the architecture is updated deliberately.

If Orca requires globally unique generated IDs, report that as an architectural finding before implementation.

---

# 38. Fixture Promotion

After validation, promote appropriate real artifacts into the Orca fixture corpus.

At minimum retain sanitized versions of:

```text
real source export
Worker canonical output
Orca round-trip re-export
```

Do not retain personal paths, usernames, machine-specific secrets, tokens, or unrelated private metadata.

---

# 39. Fixture Sanitization

If sanitization is necessary, perform it carefully.

Do not sanitize identity fields whose exact behavior is under test.

Document every sanitization transformation.

Keep an untouched local experimental copy if required, but only commit safe fixtures.

---

# 40. Replace Synthetic Assumptions

Review current synthetic Orca tests.

Classify them:

```text
still useful unit fixture
superseded by real fixture
incorrect assumption
redundant
```

Do not automatically delete all synthetic fixtures.

Small synthetic fixtures remain useful for focused unit tests.

But important compatibility tests should use real-export-derived fixtures.

---

# 41. Golden Canonical Test

Create a golden test using a real-export-derived fixture.

Verify the final evidence-backed canonicalization behavior.

At minimum assert:

```text
intended identity fields
pm_method_version
inherits behavior where applicable
unrelated field preservation
unknown field preservation
```

---

# 42. Golden Round-Trip Regression

Where possible, preserve a real:

```text
Orca export
→ Worker canonical
→ Orca import/re-export
```

fixture set.

Automated tests cannot reproduce GUI import itself, but they can detect future Worker changes that diverge from the previously validated artifact.

---

# 43. Parameter Preservation

Compare source vs Worker canonical artifact.

Outside the explicitly approved canonical mutations, material/printing parameters must remain semantically unchanged.

Generate a report of all mutations.

Unexpected mutation = failure.

---

# 44. No Workflow Changes Expected

P7.3.1 should normally require no changes to:

```text
enrichment
publication
review
version allocation
Preset identity
UnifiedDiff contract
Artifact contract
```

If such changes appear necessary, report why before implementing them.

---

# 45. No New Slicer

Do not add a third slicer.

---

# 46. Production Readiness Decision

At the end classify Orca support as one of:

```text
VALIDATED
VALIDATED_WITH_LIMITATIONS
NOT_VALIDATED
```

Definitions:

### VALIDATED

Real Worker canonical artifact successfully imports into OrcaSlicer and required identity/custom-field behavior is confirmed.

### VALIDATED_WITH_LIMITATIONS

Core import works but a documented limitation remains, such as a specific inheritance case not tested.

### NOT_VALIDATED

Import fails, identity behavior remains ambiguous, required custom metadata is lost, or experimental evidence is insufficient.

Do not mark VALIDATED solely because automated tests pass.

---

# 47. Stop Point Before Human Input

If no real Orca export has yet been supplied:

Do all preparation that does not require inventing the real artifact, then STOP.

Request exactly:

> Please provide one real custom filament preset JSON exported from your current OrcaSlicer installation.

Do not substitute another synthetic fixture.

Do not claim compatibility.

---

# 48. Stop Point After Variant Generation

Once variants and the GUI test sheet are generated, STOP and ask the human to perform the GUI import observations.

Do not guess the results.

Provide the generated experiment files and test sheet clearly.

---

# 49. Resume After GUI Results

After the human returns:

```text
completed GUI observations
and available re-exported files
```

resume automatically with:

```text
round-trip analysis
processor correction if required
fixture promotion
regression tests
full suite
production-readiness conclusion
```

---

# Mandatory Outputs Before GUI Testing

Produce:

```text
[ ] preserved real source artifact

[ ] source field analysis

[ ] synthetic-vs-real comparison

[ ] controlled experiment variants

[ ] experiment_manifest.md

[ ] GUI_TEST_RESULTS.md

[ ] checksums for source and variants

[ ] clear statement that processor has not yet been changed based on unverified assumptions
```

---

# Mandatory Outputs After GUI Testing

Produce:

```text
[ ] completed identity-behavior analysis

[ ] input-vs-re-export diffs

[ ] name conclusion

[ ] setting_id conclusion

[ ] filament_id conclusion

[ ] inherits conclusion

[ ] pm_method_version preservation conclusion

[ ] final evidence-backed Orca canonicalization rules

[ ] updated Orca processor if required

[ ] real-export-derived fixtures

[ ] golden canonicalization test

[ ] round-trip regression fixtures/tests where practical

[ ] actual Worker-output import result

[ ] full test-suite result

[ ] production-readiness classification
```

---

# Human Instructions

The human should initially do only this:

```text
1. Open the OrcaSlicer version actually used for this workflow.
2. Select or create one ordinary custom filament preset.
3. Export that filament preset as JSON.
4. Do not edit the JSON.
5. Provide the original exported file to the Agent.
```

Nothing else is required until the Agent generates the experiment variants.

---

# Out of Scope

Do NOT implement:

```text
third slicer support
cross-slicer conversion
universal preset schema
new workflow statuses
new publication semantics
working_base_version
3MF parsing
automatic GUI control unless an already reliable environment exists
large Orca version compatibility matrix
arbitrary inheritance repair
```

---

# Completion Report

Report:

1. OrcaSlicer version used for real validation;
2. source fixture provenance;
3. real source identity-related fields;
4. differences between real and synthetic fixture;
5. generated experiment variants;
6. baseline import result;
7. name-only import result;
8. name + setting_id result;
9. name + filament_id result;
10. all-identity result;
11. missing-setting_id result if tested;
12. missing-filament_id result if tested;
13. inherits behavior;
14. overwrite/merge behavior observed;
15. round-trip changes made by Orca;
16. final `name` semantics conclusion;
17. final `setting_id` semantics conclusion;
18. final `filament_id` semantics conclusion;
19. final `inherits` semantics conclusion;
20. `pm_method_version` round-trip result;
21. final Orca canonicalization rules;
22. exact fields mutated by Worker;
23. confirmation unrelated fields are preserved;
24. actual Worker canonical artifact import result;
25. Worker-output round-trip result;
26. real fixtures added;
27. regression tests added;
28. full automated test result;
29. any generic architecture changes required;
30. production readiness: `VALIDATED`, `VALIDATED_WITH_LIMITATIONS`, or `NOT_VALIDATED`;
31. remaining limitations before enabling OrcaSlicer in production UI.