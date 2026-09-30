# P7.6-B — PrusaSlicer Processor Implementation

## 0. Goal

Implement production `PrusaSlicerProcessor` using the real-artifact and GUI evidence established by P7.6-A.

Validated environment:

```text
PrusaSlicer 2.9.6
```

P7.6-A classification:

```text
READY_FOR_PROCESSOR
```

The current architecture is sufficient:

```text
SlicerProcessor
Artifact(content, filename, media_type)
UnifiedDiff
generic workflow
```

No generic architecture redesign is expected.

---

# 1. Evidence From P7.6-A

Treat the committed P7.6-A reports and fixtures as authoritative.

Established behavior:

```text
visible preset name
    controlled by artifact filename stem
    no internal INI `name` field

unique filename
    sufficient to create a new preset

baseline
    imports successfully
    no overwrite/conflict warning observed

material/printing parameters
    preserved through tested round-trip

inherits
    accepted on import
    cleared by PrusaSlicer on re-export

compatible_printers_condition
    accepted on import
    cleared by PrusaSlicer on re-export

filament_settings_id
    modified variant imports
    external-profile re-export unavailable
    semantics remain uncertain

pm_method_version
    accepted on import
    removed on re-export

Artifact(content, filename, media_type)
    sufficient
```

Do not replace these findings with assumptions derived from OrcaSlicer or ElegooSlicer.

---

# 2. Scope

Implement:

```text
PrusaSlicerProcessor
registry integration
INI parsing/validation
canonical filename generation
company metadata injection
serialization
UnifiedDiff
real-fixture tests
CREATE workflow integration
UPDATE workflow integration
cross-slicer regression tests
```

Do NOT implement:

```text
OrcaSlicer (Snapmaker)
Prusa-family abstraction
cross-slicer conversion
Artifact redesign
UnifiedDiff redesign
generic workflow redesign
```

---

# 3. Dedicated Processor

Create an independent processor:

```python
class PrusaSlicerProcessor:
    slicer_id = "PrusaSlicer"
```

Use the exact project naming convention where necessary.

Do not subclass:

```text
OrcaSlicerProcessor
ElegooSlicerProcessor
CrealityPrintProcessor
BambuStudioProcessor
```

Shared pure helpers are acceptable only when genuinely format-independent.

---

# 4. Critical Difference From Existing JSON Processors

PrusaSlicer 2.9.6 establishes an important semantic distinction:

```text
preset display identity
        =
Artifact.filename stem
```

not:

```text
content["name"]
```

Therefore the processor must treat both:

```text
Artifact.content
Artifact.filename
```

as potentially semantic.

This does NOT require an Artifact redesign.

---

# 5. Filename Is Part of Processor Semantics

The generic workflow must continue treating filename as opaque artifact metadata.

The Prusa processor owns:

```text
filename interpretation
canonical filename generation
filename-based visible-name semantics
```

Do not move filename parsing into generic workflow.

---

# 6. Canonical Visible Name

Application canonical display name remains:

```python
canonical_name = f"{context.pi_code} @{context.printer}"
```

For PrusaSlicer, map this to the **artifact filename stem**.

Conceptually:

```text
L2002CF @MK4S.ini
```

if `.ini` is the validated real artifact extension.

Use the actual extension established by P7.6-A.

---

# 7. Do Not Invent Internal `name`

Because the real Prusa artifact has no internal `name` field:

```text
DO NOT add name=...
```

to the INI merely to resemble other slicers.

The canonical visible name is represented by the filename.

Add an explicit regression test preventing accidental introduction of a synthetic `name` field.

---

# 8. Canonical Filename Rule

Generate a deterministic filename from:

```python
f"{context.pi_code} @{context.printer}"
```

plus the validated Prusa artifact extension.

The processor owns any required filename sanitization.

Do not derive the canonical filename from:

```text
filament_settings_id
inherits
compatible_printers_condition
```

---

# 9. Preserve Native Content

Start from the source artifact content and make only evidence-backed changes.

Do not rebuild the INI from a whitelist.

Preserve:

```text
known filament parameters
unknown parameters
native metadata
section structure
```

except for intentional company-policy mutation.

---

# 10. `pm_method_version`

Inject authoritative:

```text
pm_method_version = context.pm_method_version
```

into the structurally appropriate Prusa preset section/location established by P7.6-A experiments.

If the source contains:

```text
pm_method_version = OLD
```

and context contains:

```text
NEW
```

canonical output must contain:

```text
pm_method_version = NEW
```

---

# 11. Accepted `pm_method_version` Limitation

PrusaSlicer 2.9.6 removes `pm_method_version` during re-export.

This is accepted.

Do not attempt to preserve it by abusing native fields.

Worker canonicalization restores it from Submission context.

---

# 12. Preserve `filament_settings_id`

P7.6-A did NOT establish reliable semantics for `filament_settings_id`.

Therefore:

```text
PRESERVE ONLY
```

Do not:

```text
generate it
synchronize it with filename
synchronize it with canonical name
delete it
rewrite it
```

If absent, do not invent it.

---

# 13. Preserve `inherits`

Worker canonicalization must preserve the uploaded source value of:

```text
inherits
```

Do NOT proactively clear it merely because PrusaSlicer clears it during re-export.

The observed round-trip behavior describes PrusaSlicer, not Worker policy.

---

# 14. Preserve `compatible_printers_condition`

Likewise preserve:

```text
compatible_printers_condition
```

from the uploaded source.

Do not proactively clear or normalize it merely because PrusaSlicer 2.9.6 clears it during tested external-profile re-export.

---

# 15. External Round-Trip vs Worker Canonicalization

Keep these concepts separate:

```text
Worker canonicalization:
    preserve source-native semantics
    apply minimum company policy

PrusaSlicer re-export:
    may normalize/remove some metadata
```

The Worker must not imitate destructive slicer round-trip normalization unless explicitly required.

---

# 16. Unknown Fields

Preserve unknown INI keys.

Do not reject or discard fields simply because Worker does not understand them.

This is especially important for future PrusaSlicer versions.

---

# 17. Minimum Mutation Principle

For a normal valid source artifact, expected intentional mutations should be limited primarily to:

```text
Artifact.filename
pm_method_version
```

The content itself should otherwise remain semantically equivalent unless a documented normalization is unavoidable.

Add a regression test for this.

---

# 18. Source Validation

Validate that the upload is a supported PrusaSlicer filament/material preset.

Use evidence from the real 2.9.6 fixture.

Reject:

```text
malformed INI
unsupported preset type
clearly unrelated configuration
missing required structural elements
```

Do not reject unknown keys.

---

# 19. Do Not Validate by Filename Alone

Filename is semantically important but insufficient to prove artifact type.

A random INI named:

```text
PLA @MK4S.ini
```

must not automatically pass as a valid Prusa filament preset.

Validate content structure as well.

---

# 20. Parsing

Use an INI parser/representation appropriate to the real artifact semantics.

Important:

Do not accidentally lose information through parser behavior.

Verify preservation of:

```text
unknown keys
empty values
special characters
numeric strings
lists/conditions
duplicate-sensitive structures if present
```

against the real fixture.

If a standard INI parser cannot preserve required semantics, implement the minimum Prusa-specific representation necessary.

Do not change generic architecture.

---

# 21. String Preservation

Do not unnecessarily coerce values such as:

```text
"1"
"1.0"
"0"
""
```

into Python numeric/boolean types and then serialize them differently unless semantic equivalence is proven safe.

Prefer preserving native textual semantics.

---

# 22. Serialization

Serialize into a valid PrusaSlicer-importable artifact.

Byte-for-byte identity is not required.

Semantic preservation is required.

Avoid unnecessary formatting churn where practical.

---

# 23. Canonical Validation

After canonicalization verify:

```text
artifact remains valid supported Prusa filament preset

filename stem ==
    f"{context.pi_code} @{context.printer}"

pm_method_version ==
    context.pm_method_version

required native content remains valid
```

Do NOT require an internal `name` field.

---

# 24. UnifiedDiff

Implement diff using:

```text
UnifiedDiff
DiffChange
ChangeType
DiffCategory
```

No Prusa-specific persisted diff schema.

---

# 25. Filename Diff

Because filename is semantically meaningful for PrusaSlicer, decide explicitly how canonical filename/name changes are represented in UnifiedDiff.

The processor may expose a stable synthetic semantic path such as:

```text
$artifact.filename
```

or another existing project-compatible representation.

The exact path should follow existing conventions if one already exists.

Do not pretend the filename change came from an INI `name` field.

---

# 26. Filename Diff Classification

The filename/display-name change should normally be classified as:

```text
SYSTEM_METADATA
```

unless the existing project convention clearly dictates otherwise.

Document the chosen path and category.

---

# 27. Content Diff

Detect:

```text
ADDED
REMOVED
MODIFIED
```

for INI parameters.

Correctly preserve existing UnifiedDiff missing/null/empty semantics as applicable to the actual INI representation.

---

# 28. Empty String Is Not Missing

Pay particular attention to INI semantics.

Conceptually:

```text
key absent
```

must not automatically equal:

```text
key =
```

if PrusaSlicer distinguishes them.

Add regression coverage using actual format semantics.

---

# 29. Stable Diff Paths

Use deterministic semantic paths.

If the artifact contains sections, paths should distinguish them.

Conceptually:

```text
<section>.<key>
```

or another stable project convention.

Do not rely on physical line number.

---

# 30. Stable Ordering

Repeated diff of the same artifacts must produce identical ordering.

Sort by stable semantic path according to existing UnifiedDiff conventions.

---

# 31. Diff Classification

Prusa-specific classification belongs inside the Prusa processor or Prusa-owned helpers.

Use:

```text
IMPORTANT_PARAMETER
OTHER_PARAMETER
SYSTEM_METADATA
```

Unknown keys default to:

```text
OTHER_PARAMETER
```

Never silently discard unknown changes.

---

# 32. Important Parameter Coverage

Use real Prusa fields to classify relevant material/process parameters, including where appropriate:

```text
temperature
bed temperature
density
diameter
maximum volumetric speed
cooling
retraction
```

Use exact real field names from fixtures rather than inventing names from this instruction.

---

# 33. Metadata Classification

Fields/components such as:

```text
canonical filename
pm_method_version
native identity metadata
inheritance metadata
compatibility metadata
```

may be classified as SYSTEM_METADATA where appropriate.

Document exact choices.

---

# 34. CREATE

CREATE must work without a base artifact:

```text
uploaded Prusa Artifact
        ↓
PrusaSlicerProcessor
        ↓
canonical Prusa Artifact
```

The output must have:

```text
canonical filename
canonical pm_method_version
preserved native parameters
```

Do not manufacture a fake empty-document diff.

---

# 35. UPDATE

For UPDATE:

```text
current canonical Prusa Artifact
candidate uploaded Prusa Artifact
        ↓
PrusaSlicerProcessor
        ↓
canonical candidate
UnifiedDiff
```

The processor may inspect both content and filename.

Generic workflow must inspect neither.

---

# 36. Opaque Boundary Regression

Add an explicit workflow regression proving generic code does NOT need to know:

```text
Prusa filename stem = visible name
Prusa content is INI
Prusa inheritance fields
Prusa parameter names
```

Those remain processor concerns.

---

# 37. Registry Integration

Register:

```text
PrusaSlicer
```

in `default_processor_registry`.

Selection remains strictly based on:

```text
Submission.slicer
```

Do not infer slicer from:

```text
.ini extension
filename
content
printer
```

---

# 38. No Fallback Detection

Do not implement:

```text
try Prusa
then Orca
then Elegoo
```

or any other content-sniffing fallback.

Explicit slicer selection remains authoritative.

---

# 39. Preset Namespace

Use existing `preset_key` behavior so PrusaSlicer remains a distinct logical namespace.

Conceptually:

```text
PI|Printer|PrusaSlicer
```

must remain distinct from:

```text
PI|Printer|OrcaSlicer
PI|Printer|ElegooSlicer
PI|Printer|CrealityPrint
PI|Printer|BambuStudio
```

Do not change preset-key architecture.

---

# 40. Real-Fixture Golden Test

Using the real P7.6-A PrusaSlicer 2.9.6 fixture, verify:

```text
canonical filename stem correct
no synthetic internal name added
pm_method_version injected
filament_settings_id preserved
inherits preserved
compatible_printers_condition preserved
unknown keys preserved
temperature preserved
bed settings preserved
density preserved
diameter preserved
volumetric-speed settings preserved
cooling preserved
retraction preserved
```

Mandatory.

---

# 41. Filename-Only Identity Regression

Add a test demonstrating the architectural fact established by P7.6-A:

```text
same semantic source content
+
different canonical filename
```

is valid processor behavior.

Do not force the processor to encode the display name into content.

---

# 42. No-Synthetic-Name Regression

Explicitly assert:

```text
"name"
```

or the INI-equivalent artificial property is NOT introduced solely for canonical naming.

Use the actual artifact structure when implementing this assertion.

---

# 43. Minimal Mutation Regression

Compare source vs canonical semantically.

Expected intentional changes:

```text
filename
pm_method_version
```

Everything else should remain unchanged unless serialization normalization is explicitly documented.

---

# 44. `filament_settings_id` Regression

If present:

```text
canonical filament_settings_id
==
source filament_settings_id
```

If absent:

```text
canonical must not invent it
```

---

# 45. `inherits` Regression

If present:

```text
canonical inherits
==
source inherits
```

Do not reproduce Prusa's re-export clearing behavior inside Worker.

---

# 46. Compatibility Condition Regression

If present:

```text
canonical compatible_printers_condition
==
source compatible_printers_condition
```

Again, preserve rather than imitate re-export clearing.

---

# 47. Unknown-Key Regression

Add a harmless unknown INI key.

Verify:

```text
source
→ canonicalization
→ unknown key survives unchanged
```

---

# 48. `pm_method_version` Regression

Test:

```text
missing source metadata
+ context NEW
→ canonical NEW
```

and:

```text
source OLD
+ context NEW
→ canonical NEW
```

---

# 49. Parameter Preservation Regression

Use real fixture fields to assert preservation of representative:

```text
temperature
bed temperature
density
diameter
volumetric speed
cooling
retraction
```

Do not rely only on generic unknown-key preservation.

---

# 50. Diff Tests

At minimum cover:

```text
filename/display identity changed
material parameter modified
parameter added
parameter removed
unknown parameter modified
system metadata modified
empty vs missing where meaningful
stable ordering
```

---

# 51. CREATE Workflow Integration

Run a real/fidelity Prusa fixture through generic CREATE with:

```text
Submission.slicer = PrusaSlicer
```

Verify:

```text
Prusa processor selected
canonical filename generated
pm_method_version injected
content preserved
workflow does not parse INI
```

---

# 52. UPDATE Workflow Integration

Run:

```text
existing Prusa base Artifact
+
candidate Prusa Artifact
```

through UPDATE.

Verify:

```text
base passed opaquely
candidate canonicalized
filename handled by processor
UnifiedDiff generated
generic workflow remains format-agnostic
```

---

# 53. Cross-Slicer Regression

Run unchanged tests for:

```text
BambuStudioProcessor
OrcaSlicerProcessor
CrealityPrintProcessor
ElegooSlicerProcessor
fake non-JSON processor
```

No behavior change is allowed.

---

# 54. No Generic Prusa Branches

Search generic production code for new logic equivalent to:

```python
if slicer == "PrusaSlicer":
    ...
```

There should be none outside registry/composition or Prusa-owned modules.

Report any exception.

---

# 55. Do Not Introduce Prusa-Family Abstraction

Even if implementation resembles Orca/Elegoo:

do NOT introduce in P7.6-B:

```text
PrusaFamilyProcessor
OrcaFamilyProcessor
BaseJsonOrIniPresetProcessor
```

Complete the independent processor first.

Cross-slicer refactoring belongs after all planned processors have real evidence.

---

# 56. Publication and Versioning

Do not modify:

```text
Preset
PresetVersion
base_version
current_version
version_no
publication idempotency
VERSION_CONFLICT
```

PrusaSlicer uses the same application lifecycle.

Filename-based slicer identity must not leak into application version identity.

---

# 57. Filename vs `preset_key`

Do not confuse:

```text
Artifact.filename
```

with:

```text
preset_key
```

The filename controls PrusaSlicer-visible preset naming.

`preset_key` remains the application's logical identity derived through existing workflow rules.

---

# 58. UI Enablement

If slicer choices are configured in this repository, add only the minimal production option:

```text
PrusaSlicer
```

after tests pass.

Otherwise report the external UI follow-up.

---

# 59. Manual Smoke Test

After implementation, preferably generate a canonical artifact using the actual production `PrusaSlicerProcessor`.

Import it into:

```text
PrusaSlicer 2.9.6
```

Verify:

```text
import succeeds
visible name equals "{pi_code} @{printer}"
preset is created as expected
material parameters remain correct
no unexpected conflict
```

Do not require another full experiment matrix.

Expected re-export limitations remain:

```text
pm_method_version may disappear

inherits may be cleared

compatible_printers_condition may be cleared
```

These are slicer round-trip behaviors, not automatically Worker defects.

---

# 60. Acceptance Criteria

P7.6-B is complete when:

```text
[ ] independent PrusaSlicerProcessor implemented
[ ] existing SlicerProcessor contract unchanged
[ ] registered in default registry
[ ] real PrusaSlicer 2.9.6 fixture used
[ ] real INI/source structure validated
[ ] canonical visible name implemented through filename
[ ] no synthetic internal name introduced
[ ] pm_method_version injected from context
[ ] filament_settings_id preserved/not synthesized
[ ] inherits preserved
[ ] compatible_printers_condition preserved
[ ] unknown keys preserved
[ ] material/printing parameters preserved
[ ] processor owns filename semantics
[ ] processor owns parsing/serialization
[ ] deterministic UnifiedDiff implemented
[ ] filename identity represented correctly in diff
[ ] CREATE integration passes
[ ] UPDATE integration passes
[ ] Bambu regression passes
[ ] Orca regression passes
[ ] Creality regression passes
[ ] Elegoo regression passes
[ ] fake non-JSON regression passes
[ ] no generic Prusa-specific branch introduced
[ ] Artifact unchanged
[ ] UnifiedDiff unchanged
[ ] generic workflow unchanged
[ ] full test suite passes
```

---

# 61. Completion Report

Create:

```text
p7.6-B_completion_report.md
```

Report:

1. files added;
2. files modified;
3. exact `slicer_id`;
4. tested PrusaSlicer version;
5. supported artifact format;
6. source validation rules;
7. filename/display-name semantics;
8. canonical filename rule;
9. content canonicalization rules;
10. exact intentional mutation set;
11. confirmation that no synthetic `name` is added;
12. `filament_settings_id` handling;
13. `inherits` handling;
14. `compatible_printers_condition` handling;
15. `pm_method_version` handling;
16. unknown-key preservation;
17. material/printing parameter preservation;
18. parser choice and preservation considerations;
19. serialization behavior;
20. filename diff representation;
21. UnifiedDiff implementation;
22. diff classifications;
23. real fixtures used;
24. fixture sanitization;
25. golden-test result;
26. filename-identity regression result;
27. minimal-mutation result;
28. `filament_settings_id` regression;
29. inheritance regression;
30. compatibility-condition regression;
31. `pm_method_version` regression;
32. parameter-preservation regression;
33. CREATE workflow result;
34. UPDATE workflow result;
35. Bambu regression result;
36. Orca regression result;
37. Creality regression result;
38. Elegoo regression result;
39. fake non-JSON regression result;
40. full test-suite result;
41. generic workflow changes, if any;
42. slicer-specific leakage found, if any;
43. manual production-artifact GUI smoke-test result, if performed;
44. known limitations;
45. final readiness classification.

Use:

```text
READY_FOR_PRODUCTION
READY_WITH_ACCEPTED_LIMITATIONS
NOT_READY
```

Known PrusaSlicer round-trip normalization should be classified separately from Worker defects.

---

# 62. Expected Architectural Outcome

A successful P7.6-B should demonstrate:

```text
JSON content identity:
    Bambu / Orca / Creality / Elegoo
          ↓
      processor-owned

filename-based identity:
    PrusaSlicer
          ↓
      processor-owned

generic workflow:
    unchanged
```

This is an important validation of the architecture:

`Artifact.filename` is not merely storage decoration; slicer processors may legitimately assign semantic meaning to it while the generic workflow remains completely format-agnostic.