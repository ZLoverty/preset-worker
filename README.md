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

Backfill historical slicer versions (the default command writes only the
`slicer_version` field; use `--dry-run` to preview):

```powershell
python scripts/backfill_slicer_version.py --dry-run --limit 10
python scripts/backfill_slicer_version.py --limit 10
python scripts/backfill_slicer_version.py --overwrite --slicer PrusaSlicer
python scripts/backfill_slicer_version.py --refresh-cache --dry-run --limit 10
python scripts/backfill_slicer_version.py --refresh-repository SoftFever/OrcaSlicer --dry-run --slicer OrcaSlicer
```

The script compares each Submission `created_at` with official GitHub release
publication times, falling back to annotated-tag or commit times. Supported
repository mappings can be replaced with a JSON object in
`SLICER_REPOSITORIES_JSON`; GitHub authentication uses `GITHUB_TOKEN` or the
existing `GIT_ACCESS_TOKEN` environment variable.

GitHub metadata is cached locally in `.cache/slicer-version-github.json` for
24 hours by default. Use `--cache-ttl-hours 168` to change the TTL,
`--refresh-cache` to reload it, or `--no-cache` to disable local caching.
Use `--refresh-repository owner/repo` to refresh only one repository while
preserving the other cached repositories.

Install a Linux systemd service from the repository root (the script must run
as root and expects an existing `.env` file):

```bash
sudo bash scripts/install_systemd_service.sh
sudo systemctl enable --now preset-worker.service
sudo journalctl -u preset-worker.service -f
```

The installer creates or reuses `.venv`, installs the package in editable mode,
and writes `/etc/systemd/system/preset-worker.service`. Use `--user`,
`--env-file`, or `--venv-dir` to customize the deployment; use `--start` to
enable and restart the service as part of installation.
