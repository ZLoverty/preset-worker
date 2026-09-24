# Preset Worker — P6: Worker Runtime & Submission Dispatcher

## 0. Goal

Convert the existing installable `preset-worker` package from a manually invoked single-record tool into a real long-running Worker.

P1–P5 already implement the business operations:

```text id="2o1lgo"
enrichment
validation
canonicalization
diff
review preparation
publication
Preset / PresetVersion creation
idempotent recovery
current projection
attachment projection
```

P6 must NOT reimplement those rules.

P6 adds only:

```text id="4cnakz"
1. discovery of actionable Submission records
2. dispatch to existing services
3. run_once()
4. polling loop
5. graceful shutdown
6. runtime configuration
7. operational logging
8. preset-worker run
```

The intended architecture is:

```text id="lzr79x"
Feishu Miaoda
     │
     │ user submit / review
     ▼
Submission table
     │
     │ polling
     ▼
Worker Runtime
     │
     ├── discover enrichment candidates
     │          ↓
     │    existing enrichment service
     │
     └── discover publication candidates
                ↓
          existing publication service
```

Bitable remains the source of truth.

Miaoda is only a UI.

---

# 1. Core Architectural Principle

The Worker reacts to persistent Submission state.

It does NOT react directly to UI actions.

The architecture must remain:

```text id="3cyun6"
Miaoda
   ↓
modify Submission
   ↓
Bitable stores durable state
   ↓
Worker discovers state
   ↓
existing service executes
```

Do NOT implement:

```text id="jvz5u3"
Miaoda
   ↓ direct HTTP
Worker
```

Do NOT make the Worker depend on Miaoda.

Any future UI that produces the same valid Submission state should work without changing the Worker.

---

# 2. Polling Is the P6 Runtime Model

P6 deliberately uses polling.

Do NOT implement:

```text id="5u4xzf"
webhooks
event subscriptions
message queues
Redis
Celery
Kafka
RabbitMQ
Feishu event callbacks
```

The Submission table itself contains the durable workflow state.

If the Worker stops for one hour and later restarts, actionable records must still be discoverable and processable.

---

# 3. Inspect Existing P4/P5 Architecture First

Before editing:

1. inspect the current package structure;
2. run the complete P1–P5 test suite;
3. identify the installed CLI entry point;
4. identify the enrichment service public API;
5. identify the publication service public API;
6. inspect Submission repository/query capabilities;
7. inspect current status enums/constants;
8. inspect configuration loading;
9. inspect logging;
10. inspect P3/P5 retry/idempotency behavior.

Record the baseline test result.

Do not start by rewriting existing services.

---

# 4. Preserve Existing Manual Commands

These commands must remain supported:

```bash id="ephqmh"
preset-worker enrich <submission_id>
preset-worker publish <submission_id>
```

P6 adds:

```bash id="09fx61"
preset-worker run
```

Do NOT remove single-record operation.

Manual commands remain important for:

```text id="60e6pj"
debugging
integration testing
manual recovery
incident handling
development
```

All three commands must call the same underlying services.

---

# 5. Actionable States

The Worker should only query records that currently require automatic action.

Use the actual existing status names from the project.

Conceptually there are at least two categories:

```text id="7m2bqa"
enrichment candidate
    ↓
existing enrichment service

publication candidate
    ↓
existing publication service
```

For publication, P3 already defines:

```text id="2qqfqd"
APPROVING
```

as actionable.

For enrichment, inspect the existing P1/P2 state machine and use the existing status representing a newly submitted record awaiting enrichment.

Do NOT invent a new status if the existing workflow already has one.

Do NOT process:

```text id="5dnqgc"
READY_FOR_REVIEW
APPROVED
REJECTED
VERSION_CONFLICT
VALIDATION_FAILED
```

unless existing P1–P5 semantics explicitly say otherwise.

---

# 6. Query Actionable Records Directly

Do NOT retrieve the entire Submission table and filter it in Python.

Bad:

```python id="msiwza"
records = submission_repository.list_all()

for record in records:
    if record.status == ...:
        ...
```

Instead provide repository operations equivalent to:

```python id="43xj3l"
find_enrichment_candidates(limit=...)
find_publication_candidates(limit=...)
```

The Feishu/Bitable query itself should restrict records by actionable state where supported by the existing API.

This is important for scalability and API efficiency.

---

# 7. Discovery Is Not the Correctness Boundary

Polling only discovers candidate IDs.

A candidate may change between:

```text id="y5ok2x"
query
```

and:

```text id="zwntnv"
processing
```

Therefore:

> every existing business service remains responsible for reloading the Submission and validating its current state before mutation.

For example:

```text id="cj2rsr"
poll:
    finds S123 as APPROVING

later:
    publish_submission("S123")
```

`publish_submission()` must reload S123 and verify that it is still eligible.

Do NOT pass a stale polling snapshot into publication as authoritative business state.

Prefer dispatching by stable Submission record ID.

---

# 8. Small Batch Processing

Do not load an unbounded number of actionable records.

Introduce configurable batch size.

Conceptually:

```text id="ilb5s3"
PRESET_WORKER_BATCH_SIZE=20
```

Use the project's existing configuration naming convention if one exists.

The value:

```text id="43at7f"
20
```

is a reasonable default unless current project constraints suggest another value.

Do not hard-code operational tuning values deep inside runtime logic.

---

# 9. Poll Interval

Introduce configurable polling interval.

Conceptually:

```text id="hnl0ym"
PRESET_WORKER_POLL_INTERVAL=10
```

meaning:

```text id="dwx1l9"
10 seconds
```

Use the existing configuration style.

A default around 10 seconds is appropriate for the current internal workflow.

Do NOT poll aggressively at sub-second frequency.

Do NOT introduce adaptive scheduling in P6.

---

# 10. `run_once()` Is the Core Runtime Operation

Implement a finite operation equivalent to:

```python id="gq8zwv"
worker.run_once()
```

This is the core of P6.

`run_once()` should:

```text id="7rs2dp"
1. discover a batch of enrichment candidates
2. dispatch each candidate to the existing enrichment service
3. discover a batch of publication candidates
4. dispatch each candidate to the existing publication service
5. return
```

It must NOT sleep.

It must NOT loop forever.

It must be independently testable.

---

# 11. Long-Running `run()`

Implement a long-running operation equivalent to:

```python id="j6yk5v"
worker.run()
```

Conceptually:

```python id="4qt5ak"
while not stop_requested:
    run_once()
    wait(poll_interval)
```

Do not duplicate candidate discovery or dispatch logic inside `run()`.

`run()` should primarily own:

```text id="lt7mdk"
loop lifecycle
poll interval
shutdown
top-level operational logging
```

Business work belongs to `run_once()` and existing services.

---

# 12. Runtime / Dispatcher Separation

Use a small runtime/dispatcher abstraction.

Conceptually:

```text id="2ks8jg"
WorkerRuntime
    ├── run_once()
    └── run()
```

or equivalent.

Do not create a large framework.

Do not create generic task abstractions for hypothetical future jobs unless needed by the current implementation.

The current Worker only needs to dispatch known Submission workflow states.

---

# 13. Processing Order

Within one polling cycle, use a deterministic processing order.

Recommended:

```text id="1r7i4n"
1. enrichment candidates
2. publication candidates
```

This allows newly submitted records to progress toward review before publication candidates are processed.

However, do NOT repeatedly loop enrichment within the same cycle until no work remains.

One `run_once()` should process at most the configured batch for each category and return.

The next polling cycle can continue remaining work.

---

# 14. Ordering Within a Batch

If the Bitable API supports stable ordering, prefer oldest actionable records first.

For example:

```text id="j8hw08"
created_at ascending
```

or another existing immutable submission timestamp.

This reduces starvation and gives intuitive FIFO-like behavior.

Do NOT rely on ordering for correctness.

If stable ordering is unavailable through the current repository/API, document that limitation rather than building complicated client-side global sorting.

---

# 15. Failure Isolation

One bad Submission must NOT stop the entire Worker.

Example:

```text id="p6s2wb"
S101 enrichment succeeds
S102 enrichment raises
S103 should still be attempted
```

Similarly:

```text id="s6n4t5"
S201 publish succeeds
S202 publish fails
S203 should still be attempted
```

Catch exceptions at the **per-Submission dispatch boundary**.

Log the failure with enough context.

Continue with the remaining records in the batch.

---

# 16. Do Not Hide Business Failure Semantics

Existing services may intentionally transition records to states such as:

```text id="t6ohyb"
VALIDATION_FAILED
VERSION_CONFLICT
```

These are business outcomes, not necessarily Worker crashes.

Do not automatically retry such terminal/non-actionable states.

After the service updates the Submission out of an actionable state, the next poll should naturally stop discovering it.

Do not add a separate retry database in P6.

---

# 17. Infrastructure Failure Retry Model

For transient failures such as:

```text id="68d1cy"
network timeout
Feishu temporary error
connection failure
```

if the Submission remains in an actionable state, the next polling cycle naturally retries it.

This is intentional.

The effective model is:

```text id="x4hmc9"
at-least-once discovery
+
idempotent business services
```

Do NOT build an explicit retry scheduler in P6.

Do NOT introduce retry counters unless already required by existing business logic.

---

# 18. Avoid Tight Failure Loops

Suppose an actionable Submission consistently fails because of an external problem.

The Worker must not retry it continuously without delay.

The normal polling interval provides the minimum retry spacing:

```text id="y8qaqj"
attempt
 ↓
failure
 ↓
continue batch
 ↓
run_once finishes
 ↓
wait poll_interval
 ↓
next attempt
```

Do not immediately recurse or spin on the failed record.

---

# 19. No Parallel Processing in P6

Process records serially.

Do NOT introduce:

```text id="8yy6h1"
threads
asyncio concurrency
multiprocessing
worker pools
parallel publication
```

in P6.

This is intentional.

The current workload does not require parallelism, and serial processing reduces race conditions around:

```text id="u9iq77"
Preset creation
version allocation
current_version
projection
CREATE conflicts
```

A future phase may revisit concurrency if actual throughput requires it.

---

# 20. Single Worker Assumption

P6 may explicitly assume:

> only one production `preset-worker run` instance operates on the same Bitable workflow at a time.

Document this operational assumption.

Do NOT implement distributed locking.

Do NOT pretend multiple Worker instances are safe unless existing P3/P5 mechanisms actually guarantee it.

This assumption is acceptable for the current workload.

---

# 21. Graceful Shutdown

The long-running Worker must support graceful termination.

At minimum handle normal process termination signals appropriate for Linux service operation, especially:

```text id="5cib6w"
SIGTERM
SIGINT
```

Desired behavior:

```text id="dm7bxv"
signal received
    ↓
request stop
    ↓
do not start another polling cycle
    ↓
allow currently executing Submission operation to finish where practical
    ↓
exit cleanly
```

Do NOT abruptly terminate in the middle of a publication operation if avoidable.

P3/P5 recovery still protects against unavoidable termination.

---

# 22. Interruptible Poll Wait

Do not implement shutdown in a way that requires waiting the full polling interval before exit.

For example, if:

```text id="5xibug"
poll_interval = 60 seconds
```

SIGTERM should not necessarily force systemd to wait 60 seconds.

Use a simple interruptible wait/event mechanism if appropriate.

Do not introduce async architecture solely for this.

---

# 23. CLI

Extend the existing P4 CLI with:

```bash id="rtkrv9"
preset-worker run
```

Expected behavior:

```text id="7lz6qy"
load config
build repositories/adapters/services
build WorkerRuntime
start polling
```

The CLI itself must not contain polling business logic.

Conceptually:

```python id="h2xkce"
def run_command(...):
    runtime = build_runtime(...)
    runtime.run()
```

Keep CLI thin.

---

# 24. Optional `run-once` CLI

A CLI command such as:

```bash id="k7ttwn"
preset-worker run-once
```

may be added if it is useful for:

```text id="vbh5ap"
debugging
cron-style testing
integration testing
deployment verification
```

This is optional.

If implemented, it must call the exact same:

```python id="e41xlv"
WorkerRuntime.run_once()
```

used by production `run`.

Do not create a second implementation.

---

# 25. Configuration

Add only the runtime configuration required by P6.

At minimum:

```text id="3ljqlh"
poll interval
batch size
```

Conceptually:

```text id="af80jl"
PRESET_WORKER_POLL_INTERVAL=10
PRESET_WORKER_BATCH_SIZE=20
```

Follow existing P4 configuration conventions.

Validate values.

Examples:

```text id="nvr4ap"
poll interval > 0
batch size > 0
```

Invalid configuration should fail clearly at startup rather than producing an uncontrolled loop.

---

# 26. No Import-Time Worker Startup

This remains a hard requirement from P4.

The following:

```python id="yxslpi"
import preset_worker
```

must NOT start polling.

Similarly:

```python id="lxhpgs"
from preset_worker.runtime import WorkerRuntime
```

must not start the Worker.

Only explicit invocation such as:

```bash id="lx4j3f"
preset-worker run
```

or:

```python id="zyt0cb"
runtime.run()
```

starts the long-running loop.

---

# 27. Logging

P6 introduces operational Worker logging.

At startup log useful non-secret configuration such as:

```text id="5ph15w"
Worker starting
poll interval
batch size
```

For each polling cycle, avoid excessively noisy output when no work exists.

Useful events include:

```text id="o3aslv"
candidate discovered
processing started
processing completed
processing failed
business conflict/failure
shutdown requested
Worker stopped
```

For each processed Submission, include the stable Submission identifier.

Where useful include:

```text id="2px52k"
action = enrich / publish
```

Do not log secrets.

Do not dump complete canonical JSON.

Do not dump attachment binary content.

---

# 28. Idle Logging

Do not emit large INFO logs every 10 seconds merely saying:

```text id="5k29su"
0 records found
```

for a permanently idle Worker.

Idle-cycle details may be DEBUG-level.

INFO-level logging should remain operationally useful.

---

# 29. Candidate Query Pagination

If the Bitable API can return fewer records than requested because of pagination, use the existing repository pagination mechanism correctly.

However, one `run_once()` should still respect:

```text id="4nmx4h"
batch_size
```

for each actionable category.

Do not accidentally fetch/process the entire table because pagination exists.

---

# 30. Candidate Snapshot Minimization

Discovery queries only need enough information to identify candidates.

If practical with the current repository/API, do not retrieve large unnecessary fields such as:

```text id="y0pph5"
canonical_json attachments
process photos
large diff payloads
```

just to discover Submission IDs.

The service will reload the full record when processing.

Do not perform a major repository optimization if the API abstraction makes this difficult; correctness comes first.

---

# 31. State Changes During a Poll Cycle

The runtime must tolerate:

```text id="14p6gr"
candidate discovered
        ↓
user/system changes status
        ↓
service invoked
```

The existing service decides whether the record is still eligible.

The runtime must not force processing based solely on the discovery snapshot.

If the service reports that the record is no longer actionable, treat this as a benign stale discovery where appropriate.

---

# 32. Newly Actionable Records During Processing

Suppose:

```text id="i4cyxb"
run_once() starts

S1 is enriched
→ becomes READY_FOR_REVIEW

reviewer later approves another record S2
→ becomes APPROVING
```

P6 does not need to guarantee that every state transition is picked up within the same `run_once()`.

The next polling cycle is sufficient.

Do not make `run_once()` recursively drain all possible work.

---

# 33. Interaction With P3/P5 Idempotency

P6 relies on existing P3/P5 guarantees.

Publication may be retried because:

```text id="ct2fdn"
Worker crashed
Feishu request timed out
network response was lost
projection partially completed
```

P6 must call the existing publication service rather than trying to determine itself whether publication partially succeeded.

The publication service remains responsible for:

```text id="r9fyyl"
source_submission idempotency
PresetVersion recovery
current_version safety
projection repair
stale retry protection
VERSION_CONFLICT
```

Do not duplicate these checks in WorkerRuntime.

---

# 34. Worker Runtime Must Not Know Version Rules

WorkerRuntime must NOT contain logic such as:

```python id="u4pvhm"
version_no += 1
version_id = ...
if base_version != current_version:
    ...
```

It should only know:

```text id="ec24hr"
this Submission needs publication
        ↓
call publication service
```

Likewise it must not know canonicalization or photo-field rules.

---

# 35. Worker Runtime Must Not Know Slicer Rules

Do not introduce:

```python id="y7fyx4"
if slicer == "BambuStudio":
    ...
```

into runtime/dispatcher code.

Slicer-specific behavior remains in the existing enrichment architecture.

---

# 36. Repository Additions

Add only the query capabilities required for candidate discovery.

Conceptually:

```python id="oxp8wa"
SubmissionRepository.find_enrichment_candidates(
    limit: int
)

SubmissionRepository.find_publication_candidates(
    limit: int
)
```

or a generic equivalent such as:

```python id="w6vr4x"
find_by_status(
    status,
    limit,
)
```

Choose whichever fits the current repository design better.

Avoid creating multiple nearly identical query methods if the existing repository already has a clean generic status query.

---

# 37. Feishu Filtering

Where supported, translate candidate discovery into server-side Bitable filtering.

Conceptually:

```text id="1i84dy"
status == ACTIONABLE_STATUS
```

Do not depend on UI views as the primary query mechanism.

The Worker should query data/state, not a manually maintained Bitable view.

Views may still exist for human convenience.

---

# 38. Miaoda Independence

No P6 code should import, call, or know about Miaoda-specific APIs.

From the Worker's perspective:

```text id="nknwhk"
Miaoda is simply one producer of valid Submission state.
```

This boundary is intentional and must be documented.

---

# 39. Unit Tests

Add focused P6 tests.

## P6-T1 — run_once discovers enrichment candidates

Given:

```text id="5d6j0b"
S1 = enrichment actionable
S2 = READY_FOR_REVIEW
```

Expected:

```text id="uwmgnt"
S1 dispatched to enrichment
S2 not dispatched
```

---

## P6-T2 — run_once discovers publication candidates

Given:

```text id="6o0rqv"
S1 = APPROVING
S2 = APPROVED
```

Expected:

```text id="hz7g2v"
S1 dispatched to publication
S2 not dispatched
```

---

## P6-T3 — Both work categories in one cycle

Given:

```text id="ubcb64"
enrichment candidates exist
publication candidates exist
```

one `run_once()` processes both categories.

---

## P6-T4 — Batch limit

Given more actionable records than:

```text id="52zg13"
batch_size
```

verify no more than the configured batch is dispatched for that category during one `run_once()`.

---

## P6-T5 — Per-record failure isolation

Given:

```text id="ltc8f9"
S1 succeeds
S2 raises
S3 succeeds
```

verify S3 is still attempted.

---

## P6-T6 — No retry spin

A failed record is attempted at most once by a given category within one `run_once()`.

---

## P6-T7 — Stale candidate

A candidate discovered by polling changes state before service execution.

Verify runtime does not force processing and safely handles the service's no-longer-actionable result.

---

## P6-T8 — run_once returns

Verify:

```python id="i4b6ij"
runtime.run_once()
```

is finite and does not sleep indefinitely.

---

## P6-T9 — Poll loop repeats

With a controlled fake wait mechanism, verify:

```text id="eyhhpj"
run_once
wait
run_once
wait
...
```

occurs until stop is requested.

Do not use real 10-second sleeps in unit tests.

---

## P6-T10 — Graceful stop

Request shutdown.

Verify the Worker:

```text id="f89pss"
does not start another cycle
exits cleanly
```

---

## P6-T11 — Existing CLI commands remain

Verify:

```bash id="ue2i1x"
preset-worker enrich S123
preset-worker publish S123
```

still route correctly.

---

## P6-T12 — New run CLI

Verify:

```bash id="ic1j1h"
preset-worker run
```

constructs and starts WorkerRuntime.

Mock/fake the infinite runtime in CLI unit tests.

---

## P6-T13 — No import side effects

Importing Worker runtime modules must not start polling or perform Feishu requests.

---

# 40. Integration Tests

Add focused integration coverage where practical.

## P6-IT1 — Discover real actionable Submission

Against the configured development/test Bitable:

```text id="p8d0ew"
create/use test Submission in enrichment-actionable state
        ↓
run_once()
        ↓
verify existing enrichment service processed it
```

---

## P6-IT2 — Discover APPROVING Submission

Using a safe test Submission:

```text id="o3kr59"
status = APPROVING
        ↓
run_once()
        ↓
existing P3/P5 publication occurs
```

Verify expected final state according to existing publication tests.

Do not use arbitrary production records.

---

## P6-IT3 — Idle cycle

With no actionable test records:

```text id="kij0ai"
run_once()
```

should complete successfully without mutating unrelated records.

---

# 41. Runtime Composition

Reuse the P4 dependency composition approach.

Conceptually:

```python id="hn60zq"
config = load_config()

services = build_services(config)

runtime = WorkerRuntime(
    submission_repository=...,
    enrichment_service=...,
    publication_service=...,
    poll_interval=...,
    batch_size=...,
)
```

Do not instantiate duplicate Feishu clients for every Submission if the existing architecture supports safe client reuse.

Do not introduce a DI framework.

---

# 42. Deployment Boundary

P6 creates a long-running executable Worker, but deployment automation is not part of this phase.

The package should be suitable for a later command such as:

```text id="4z4k0x"
ExecStart=/path/to/venv/bin/preset-worker run
```

but P6 does NOT need to create production systemd configuration unless one already exists and requires a minimal update.

The runtime must behave correctly when managed by a normal Linux service manager:

```text id="ebebob"
start
SIGTERM
restart
```

---

# 43. Health Checks Are Out of Scope

Do not build:

```text id="91ktgc"
HTTP health server
metrics server
Prometheus endpoint
dashboard
```

in P6.

Logs and process exit behavior are sufficient for this phase.

These can be added later if operational experience shows a need.

---

# 44. Do Not Add a Queue Table

Do not create a new:

```text id="w7ysx5"
WorkerQueue
TaskQueue
Job table
```

Submission status is already the durable work-discovery mechanism.

Avoid duplicating workflow state.

---

# 45. Do Not Add an Intermediate "Claimed" State Yet

Do not add states such as:

```text id="4qh19v"
PROCESSING_BY_WORKER
CLAIMED
LOCKED
```

solely for polling.

P6 assumes a single production Worker instance.

Existing service states such as:

```text id="x0c4i7"
VALIDATING
APPROVING
```

should continue to carry their existing business semantics.

If future multi-worker concurrency requires claiming/leases, solve it then.

---

# 46. Important Operational Invariant

The Worker must be restart-safe.

At any time:

```text id="q1s2bl"
kill worker
restart worker
```

must not require manual reconstruction of an in-memory queue.

All actionable work must be rediscoverable from Bitable state.

This is one of the main reasons P6 uses polling.

---

# 47. README

Update README with the new production runtime command.

Document:

```bash id="f4bdm6"
preset-worker run
```

and the runtime configuration:

```text id="73ww2b"
poll interval
batch size
```

Also retain documentation for:

```bash id="spj2d9"
preset-worker enrich <submission_id>
preset-worker publish <submission_id>
```

Clearly state:

> only one production polling Worker instance should operate on the same workflow in P6.

Do not document webhook behavior.

---

# 48. Explicitly Out of Scope

Do NOT implement:

```text id="iwfpph"
webhooks
Miaoda API integration
Feishu event subscriptions
Redis
Celery
Kafka
RabbitMQ
new queue tables
distributed locks
multi-worker claiming
parallel processing
asyncio migration
thread pools
automatic exponential backoff
retry counters
dead-letter queues
HTTP server
health endpoint
Prometheus metrics
new business statuses
new validation rules
P1–P5 business-rule changes
new slicer support
systemd deployment automation
```

If one of these appears useful, document it as future work rather than implementing it.

---

# 49. Acceptance Criteria

P6 is complete when:

```text id="n47npd"
[ ] preset-worker run exists

[ ] existing enrich command still works

[ ] existing publish command still works

[ ] actionable Submission records are queried server-side where supported

[ ] entire Submission table is not scanned every cycle

[ ] enrichment candidates dispatch to existing enrichment service

[ ] publication candidates dispatch to existing publication service

[ ] run_once() is finite and independently testable

[ ] run() repeatedly calls run_once()

[ ] poll interval is configurable

[ ] batch size is configurable

[ ] one failing Submission does not stop the batch

[ ] one failing Submission does not stop the Worker

[ ] failed actionable records can naturally retry on a later poll

[ ] no record is tight-loop retried inside one run_once()

[ ] service reloads remain the correctness boundary

[ ] Worker processing is serial

[ ] graceful SIGTERM/SIGINT shutdown works

[ ] shutdown does not unnecessarily wait a full long polling interval

[ ] Worker restart requires no in-memory queue recovery

[ ] idle polling does not mutate unrelated records

[ ] no webhook/Miaoda coupling exists

[ ] no queue table was introduced

[ ] no distributed locking was introduced

[ ] only one production Worker instance is assumed/documented

[ ] all P1–P5 regression tests pass

[ ] all P6 unit tests pass
```

---

# 50. Acceptance Scenario

Initial Bitable state:

```text id="22c9ad"
S101
status = <existing enrichment-actionable state>

S102
status = READY_FOR_REVIEW

S103
status = APPROVING

S104
status = APPROVED
```

Worker executes:

```python id="j2e6z8"
runtime.run_once()
```

Expected dispatch:

```text id="71p40i"
S101
    ↓
existing enrichment service

S103
    ↓
existing publication service
```

No dispatch:

```text id="nxkl2a"
S102
S104
```

After processing, exact resulting statuses are determined by existing P1–P5 business logic.

WorkerRuntime must not reproduce those state-transition rules.

Then:

```text id="fwy99d"
run_once()
```

returns.

Production:

```bash id="8dp7mh"
preset-worker run
```

performs:

```text id="e2axpb"
run_once
   ↓
wait configured interval
   ↓
run_once
   ↓
wait
   ↓
...
```

until graceful shutdown is requested.

---

# 51. Completion Report

After implementation, report:

1. baseline P1–P5 test result;
2. actionable enrichment status actually used;
3. actionable publication status actually used;
4. candidate-query implementation;
5. whether filtering occurs server-side;
6. batch-size implementation;
7. polling-interval implementation;
8. `run_once()` implementation location;
9. `run()` implementation location;
10. dispatch behavior;
11. per-record failure isolation behavior;
12. retry behavior;
13. graceful shutdown implementation;
14. CLI changes;
15. configuration changes;
16. files created;
17. files modified;
18. tests added;
19. integration tests performed;
20. final complete test result;
21. any known Feishu API limitations;
22. confirmation that P1–P5 business logic was not intentionally changed;
23. confirmation that no webhook/Miaoda dependency was introduced;
24. confirmation of the single-production-Worker assumption.

Do not implement a later phase unless explicitly requested.
