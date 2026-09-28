# preset-worker

Install the package in development mode:

```powershell
pip install -e .
```

Run a single Submission operation:

```powershell
preset-worker enrich <submission_id>
preset-worker publish <submission_id>
preset-worker backfill-base-version-no-text

Run the polling Worker:

```powershell
preset-worker run
```

Runtime configuration is read from `.env`:

```env
PRESET_WORKER_POLL_INTERVAL=10
PRESET_WORKER_BATCH_SIZE=20
```

The Worker processes `PREVIEW_REQUESTED` preview candidates, `VALIDATING`
enrichment candidates, and `APPROVING` publication candidates serially. P6
assumes only one production Worker
instance operates on the same Bitable workflow.
```

The commands read the existing `.env` configuration. Use `--env path\to\.env`
to select another configuration file.

`backfill-base-version-no-text` repairs only empty historical UPDATE snapshots
from the linked PresetVersion and is safe to run repeatedly. Use `--limit` to
bound one run.
