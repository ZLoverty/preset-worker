# preset-worker

Install the package in development mode:

```powershell
pip install -e .
```

Run a single Submission operation:

```powershell
preset-worker enrich <submission_id>
preset-worker publish <submission_id>
```

The commands read the existing `.env` configuration. Use `--env path\to\.env`
to select another configuration file.
