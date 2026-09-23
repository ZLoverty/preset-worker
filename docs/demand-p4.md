# Preset Worker — P4: Installable Package Restructure

## 0. Goal

Refactor the existing preset Worker repository into a clean, installable Python package.

P1–P3 business behavior is already implemented and validated.

P4 is a **structural refactor only**.

The primary goals are:

```text
1. make the project installable with pip
2. establish a stable Python package structure
3. expose existing business operations as importable services
4. provide a stable CLI
5. preserve single-Submission manual/debug operations
6. prepare the architecture for future attachment handling and worker polling
```

P4 must NOT change the semantics of:

```text
P1 / P1.1 enrichment
P2 review preparation
P3 publication
```

After P4, the same tests and business scenarios that worked before the refactor must still work.

---

# 1. Core Principle

This phase is:

> packaging + code organization + entry-point cleanup

It is NOT:

> a business-logic rewrite.

Prefer moving and organizing proven code over rewriting it.

Do not introduce new abstractions unless they solve an actual structural problem in the existing code.

Do not redesign working P1–P3 logic merely to make the architecture look cleaner.

---

# 2. Inspect Before Editing

Before making changes:

1. inspect the complete repository structure;
2. identify current executable scripts;
3. identify P1/P1.1 enrichment entry points;
4. identify P3 publication entry points;
5. identify domain models;
6. identify Feishu/Bitable adapters;
7. identify repository abstractions;
8. identify configuration loading;
9. identify tests and fixtures;
10. run the complete existing test suite.

Record the baseline test result.

Do not begin the refactor until the current architecture is understood.

If the repository already contains a partially packaged structure, adapt this instruction to it rather than creating duplicate layers.

---

# 3. Target Package

The installable Python package should be named:

```text
preset_worker
```

Use the modern `src` layout:

```text
repository-root/
│
├── pyproject.toml
├── README.md
│
├── src/
│   └── preset_worker/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       │
│       ├── domain/
│       │
│       ├── services/
│       │
│       ├── repositories/
│       │
│       └── adapters/
│           └── feishu/
│
└── tests/
```

This is a conceptual target.

Adapt existing modules into it sensibly.

Do NOT create empty architectural layers merely to match this diagram.

For example, if an existing module already has a clear home and splitting it provides no benefit, keep it coherent.

---

# 4. pyproject.toml

Create or update:

```text
pyproject.toml
```

so the package can be installed with:

```bash
pip install .
```

and during development:

```bash
pip install -e .
```

Use the packaging/build tooling already present in the repository if reasonable.

Do not introduce unnecessary packaging frameworks.

All runtime dependencies required by the existing Worker must be declared appropriately.

Development/test dependencies should remain distinguishable from runtime dependencies where practical.

---

# 5. Package Import Requirement

After installation, this must work from outside the repository source directory:

```python
import preset_worker
```

Important application services must also be importable through stable package paths.

At minimum, there must be clean programmatic access to operations equivalent to:

```python
enrich_submission(submission_id)
publish_submission(submission_id)
```

The exact internal implementation may use service classes and dependency injection.

Do NOT duplicate the existing enrichment/publication logic just to expose these APIs.

The public entry point must call the existing business implementation.

---

# 6. Service Layer

Existing business orchestration should live under a clear service layer, conceptually:

```text
preset_worker.services
```

For example:

```text
services/
├── enrichment.py
└── publication.py
```

or equivalent existing organization.

The important separation is:

```text
CLI
 ↓
service
 ↓
repository / adapter
 ↓
Feishu
```

NOT:

```text
CLI
 ↓
raw Feishu API calls
```

The service layer owns business workflow.

Adapters own external-system communication.

CLI owns argument parsing and presentation only.

---

# 7. Preserve Existing Business Behavior

Do not intentionally change:

```text
preset_key generation
operation detection
CREATE / UPDATE semantics
canonicalization
validation
diff generation
base_version behavior
review state semantics
version allocation
version_id generation
publication ordering
VERSION_CONFLICT behavior
idempotency
partial publication recovery
Preset.current_version behavior
PresetVersion creation semantics
Submission status transitions
```

In particular, preserve the P3 version format:

```text
{preset_key}@v{version_no}
```

Example:

```text
L2002CF|BBL P2S|BambuStudio@v8
```

P4 must not reinterpret or migrate existing records.

---

# 8. Preserve Attachment Semantics

Do NOT implement the future process-photo copy feature in P4.

Existing attachment handling required by P1–P3 must continue working.

In particular:

```text
PresetVersion.canonical_json
```

remains an attachment field.

Do not convert it to text.

Do not redesign canonical JSON storage.

Attachment projection:

```text
Submission.process_photos
        ↓
Preset.process_photos
```

belongs to a future phase and is explicitly out of scope for P4.

However, organize existing Feishu code so future attachment operations have a natural home.

For example:

```text
adapters/feishu/
```

may eventually contain attachment-specific functionality.

Do not implement speculative attachment APIs merely to prepare for that future.

---

# 9. Domain Layer

Business concepts should not depend unnecessarily on CLI code or raw HTTP responses.

Where the current repository already has models/enums such as:

```text
Submission
Preset
PresetVersion
SubmissionStatus
Operation
```

place or retain them in a sensible domain-oriented location.

For example:

```text
preset_worker.domain
```

Do not rewrite all models solely to satisfy an idealized domain-driven architecture.

Existing tested models should be preserved where possible.

---

# 10. Repository Layer

Existing data-access abstractions should be organized so business services can work with concepts such as:

```text
SubmissionRepository
PresetRepository
PresetVersionRepository
```

or their existing equivalents.

The important property is that service code does not need to know Bitable HTTP details.

If this separation already exists, preserve it.

If existing code mixes business orchestration with Feishu calls, perform only the minimum extraction required to establish a clean boundary.

Do not redesign all repository interfaces in P4.

---

# 11. Feishu Adapter Layer

Feishu-specific implementation should have a clear package location, conceptually:

```text
preset_worker.adapters.feishu
```

This may contain existing concepts such as:

```text
Bitable client
field conversion
record serialization
repository implementations
authentication
```

Do not create a giant generic abstraction for hypothetical future storage backends.

Feishu is the actual backend.

The goal is code organization, not backend-agnostic architecture for its own sake.

---

# 12. Configuration

Centralize configuration loading under a clear module such as:

```text
preset_worker.config
```

Preserve the existing configuration source and behavior unless there is a concrete reason it must change for packaging.

Existing environment variables must continue to work.

Do NOT rename existing environment variables unnecessarily.

Do NOT hard-code:

```text
app_id
app_secret
base/app token
table IDs
field IDs
```

into package modules.

Importing:

```python
import preset_worker
```

must NOT immediately perform network access or require valid Feishu credentials.

Configuration and external clients should be initialized when needed by an application command/service, not as an import side effect.

---

# 13. No Import-Time Side Effects

This is a hard requirement.

The following:

```python
import preset_worker
```

must NOT:

```text
connect to Feishu
query Bitable
process a Submission
start a loop
create files
configure global production state
exit the process
```

Modules should be safe to import in tests and external programs.

---

# 14. CLI

Provide an installed command:

```bash
preset-worker
```

using the package's console-script entry point.

At minimum support:

```bash
preset-worker enrich <submission_id>
```

and:

```bash
preset-worker publish <submission_id>
```

These commands should call the same service layer used by programmatic Python access.

Conceptually:

```text
preset-worker enrich S123
        │
        ▼
EnrichmentService
        │
        ▼
existing P1/P1.1 logic
```

and:

```text
preset-worker publish S123
        │
        ▼
PublicationService
        │
        ▼
existing P3 logic
```

Do not implement the production polling Worker yet.

---

# 15. Keep Single-Record Operations Permanently

The existing ability to process a specific Submission is valuable for:

```text
debugging
integration testing
manual recovery
operations
incident investigation
development
```

Do NOT remove this capability when introducing the package.

It should become a supported CLI interface rather than an ad-hoc repository script.

Future architecture is expected to support both:

```text
manual:
preset-worker enrich S123
preset-worker publish S123
```

and eventually:

```text
production:
preset-worker run
```

P4 implements only the manual commands.

---

# 16. CLI Must Stay Thin

`cli.py` should primarily handle:

```text
argument parsing
configuration initialization
dependency construction
calling application services
displaying result/errors
exit codes
```

It must NOT contain copies of business rules such as:

```text
if operation == CREATE ...
if base_version != current_version ...
version_no += 1
```

Those belong to existing services.

---

# 17. CLI Error Behavior

Provide sensible process exit behavior.

Conceptually:

```text
success
→ exit code 0

invalid arguments/configuration
→ non-zero

business failure
→ non-zero

unexpected external/API failure
→ non-zero
```

Do not hide exceptions in a way that makes operational debugging impossible.

Existing domain errors such as validation or version conflict should retain meaningful messages.

Avoid printing credentials or secrets in error output.

---

# 18. Logging

P4 may normalize logging only where required to make the installed CLI usable.

Do NOT build the future daemon logging system yet.

Avoid widespread logging rewrites.

At minimum, command execution should make it possible to determine:

```text
which submission was processed
which operation ran
whether it succeeded or failed
```

Do not log:

```text
app_secret
access tokens
complete credential-bearing HTTP headers
```

---

# 19. Legacy Scripts

After the new CLI works, inspect existing scripts.

If an old script duplicates:

```text
enrich submission
```

or:

```text
publish submission
```

prefer one of:

```text
A. convert it into a very thin compatibility wrapper

or

B. remove it if nothing depends on it
```

Do NOT maintain two independent implementations.

Before deleting an existing script, search the repository for references to it.

If deployment or documentation still depends on it, preserve a compatibility path during P4.

Report what was retained or removed.

---

# 20. Tests Must Use Installed Package Imports

Update tests so they import from:

```python
preset_worker...
```

rather than relying on repository-relative path hacks.

Remove unnecessary patterns such as:

```python
sys.path.insert(...)
```

where the package structure makes them obsolete.

Do not weaken existing tests simply to make the refactor pass.

---

# 21. Existing Tests Are Regression Tests

All existing P1–P3 tests must remain passing.

If moving code breaks tests because of import paths, update the imports.

If tests fail because behavior changed, treat that as a regression unless the behavior change is absolutely required for packaging.

Do not silently update expected business behavior to match an accidental refactor change.

---

# 22. New P4 Tests

Add focused tests for packaging/application entry points.

## P4-T1 — Package import

Verify:

```python
import preset_worker
```

succeeds.

No network operation should occur.

---

## P4-T2 — Service import

Verify the enrichment service can be imported through the installed package.

Verify the publication service can be imported through the installed package.

---

## P4-T3 — CLI enrich routing

Given a fake/test service environment:

```bash
preset-worker enrich S123
```

must route to enrichment for:

```text
S123
```

Do not require a live Feishu call for this unit-level test.

---

## P4-T4 — CLI publish routing

Given a fake/test service environment:

```bash
preset-worker publish S123
```

must route to publication for:

```text
S123
```

Do not require a live Feishu call for this unit-level test.

---

## P4-T5 — Invalid command

Invalid CLI input should return a non-zero exit status and useful usage/error information.

---

## P4-T6 — No import side effects

Importing package modules must not:

```text
start processing
start polling
make Feishu requests
```

---

## P4-T7 — Existing regression suite

Run the complete P1–P3 test suite after the restructuring.

All previously passing business tests must remain passing.

---

# 23. Installation Verification

In a clean environment if practical, verify:

```bash
pip install -e .
```

Then verify:

```bash
python -c "import preset_worker"
```

and:

```bash
preset-worker --help
```

Then verify that the CLI exposes at least:

```text
enrich
publish
```

Do not rely on running Python from the repository root as proof that packaging works.

---

# 24. Desired Dependency Direction

Aim for a dependency direction similar to:

```text
CLI
 │
 ▼
Services
 │
 ├────────────► Domain
 │
 ▼
Repository interfaces / existing data abstractions
 │
 ▼
Feishu adapters
```

Avoid:

```text
Domain → CLI

Domain → argparse

Domain → environment-variable parsing

Feishu adapter → CLI
```

Do not pursue architectural purity beyond what is needed for maintainability.

---

# 25. Prepare for P5 Without Implementing It

The next planned phase will likely implement process-photo projection/copying:

```text
Submission.process_photos
        ↓
Preset.process_photos
```

P4 should leave a natural place for Feishu attachment operations.

However:

> P4 must not implement attachment copying.

Do not add untested token-reuse logic.

Do not add download/re-upload logic.

Do not change publication semantics.

---

# 26. Prepare for P6 Without Implementing It

A later phase will introduce a real long-running Worker:

```text
query Submission
      ↓
dispatch eligible records
      ↓
enrich_submission(...)
publish_submission(...)
      ↓
sleep
      ↓
repeat
```

P4 should make that future runtime easy to add.

The intended future architecture is approximately:

```text
preset-worker run
        │
        ▼
Worker runtime / poller
        │
        ├── enrich_submission(id)
        └── publish_submission(id)
```

Therefore P4 should ensure enrichment/publication can be called cleanly without depending on CLI internals.

But P4 must NOT implement:

```text
polling
daemon loop
scheduler
background threads
async worker runtime
systemd service
automatic retry loop
```

Those belong to P6.

---

# 27. Avoid Premature Async Refactoring

Do not convert the project to:

```text
asyncio
thread pools
multiprocessing
task queues
```

as part of P4 unless the existing implementation already requires them.

The future polling Worker does not justify rewriting currently working synchronous business logic.

Keep P4 focused.

---

# 28. Avoid Dependency Injection Frameworks

Dependency construction should remain explicit and understandable.

For example, a simple factory/composition function is sufficient:

```python
def build_services(config):
    ...
```

Do NOT introduce a dependency injection framework solely for P4.

---

# 29. Preserve Testability

Core business services must remain testable without real Feishu network access.

Where existing tests use fake repositories/adapters, preserve that capability.

The package restructuring must not force unit tests to initialize production Feishu clients.

---

# 30. README Update

Update README only as needed to reflect the new package usage.

At minimum document:

```bash
pip install -e .
```

and:

```bash
preset-worker enrich <submission_id>
preset-worker publish <submission_id>
```

Do not write documentation for the future polling Worker yet.

Do not document commands that do not exist.

---

# 31. Explicitly Out of Scope

Do NOT implement:

```text
process-photo copying
process-photo projection changes
new attachment token logic
polling Submission table
daemon runtime
preset-worker run
systemd service
automatic retry scheduler
webhooks
Miaoda UI
review UI
new slicer support
Git integration
database migration
schema redesign
P1–P3 business-rule changes
distributed locking
async architecture migration
```

If an out-of-scope issue is discovered during refactoring, document it rather than solving it unless it prevents P4 from functioning.

---

# 32. Acceptance Criteria

P4 is complete when all of the following are true:

```text
[ ] project has a valid pyproject.toml

[ ] package uses an installable preset_worker namespace

[ ] pip install -e . succeeds

[ ] import preset_worker succeeds

[ ] importing the package performs no Feishu/network work

[ ] enrichment is available through package code

[ ] publication is available through package code

[ ] preset-worker --help works

[ ] preset-worker enrich <submission_id> works

[ ] preset-worker publish <submission_id> works

[ ] CLI contains no duplicated business logic

[ ] existing P1–P3 business behavior is unchanged

[ ] existing P1–P3 tests still pass

[ ] package tests pass

[ ] no polling Worker has been implemented

[ ] no process-photo copying has been implemented
```

---

# 33. Completion Report

After implementation, report:

1. original repository structure relevant to P4;
2. final repository structure;
3. files created;
4. files moved;
5. files modified;
6. legacy scripts removed or retained;
7. `pyproject.toml` packaging approach;
8. installed CLI entry point;
9. service entry points;
10. configuration changes, if any;
11. whether any business logic had to be changed and why;
12. tests added/updated;
13. baseline test result before refactor;
14. final test result after refactor;
15. installation verification result;
16. remaining technical debt relevant to P5/P6.

Do not implement P5 or P6 unless explicitly requested.
