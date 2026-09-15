# databricks-job-example

A minimal Databricks Job — read orders, sum the amount by region, write the
result — used as a real, external consumer of
[`databricks-local-ci`](https://github.com/ViniciusOtoni/databricks-local-ci).
The Spark logic here is intentionally trivial (`transform.py` is 12 lines).
**The point of this repo isn't the PySpark code — it's what happens before you
ever touch a real Databricks cluster.**

## The gain this repo demonstrates

Without `databricks-local-ci`, finding out whether this job actually works
means: push, wait for a job cluster to provision (commonly several minutes of
cold start on a fresh cluster, before a single line of your code runs), then
wait for the run itself, then read the logs to find out you had a typo.

With `databricks-local-ci`, the exact same code — built into the exact same
kind of wheel, run through the exact same Databricks Runtime image — gets a
real pass/fail answer locally, in this repo's own CI, before any cluster is
ever involved:

```
tests/test_transform.py::test_summarize_orders_by_region PASSED
::auto_real_run.py::test_databricks_local_ci_auto_real_run PASSED
2 passed in 43.51s
```

That second test isn't hand-written anywhere in this repo — it's generated
automatically by `databricks-local-ci`'s pytest plugin from the
`[tool.databricks-local-ci]` block in `pyproject.toml`. No
`test_integration.py`, no manual subprocess wiring: declare your entry point
and a bit of sample data, and the plugin builds the input Delta table, runs
the real packaged wheel as a real subprocess, and checks it wrote real output.
No cluster, no waiting, no DBU spent, and it's the exact artifact (built with
`uv`, installed as a real wheel, run as a real subprocess) that would
otherwise ship straight to the job cluster.

## What's here

- `src/orders_summary/transform.py` — the one function with actual logic:
  `summarize_orders_by_region`.
- `src/orders_summary/main.py` — the CLI entry point
  (`python -m orders_summary.main --input-path ... --output-path ...`), the
  same one the Databricks Job task below invokes in production.
- `pyproject.toml`'s `[tool.databricks-local-ci]` block — declares the entry
  point and sample input `databricks-local-ci` needs to run the job for real
  in CI; see `databricks-local-ci`'s README for the schema. This is the whole
  "real run" test — there's no `tests/test_integration.py` in this repo.
- `databricks.yml` — a Databricks Asset Bundle deploying this wheel as a
  `python_wheel_task` job.
- `.github/workflows/ci-cd.yml` — calls `databricks-local-ci`'s two reusable
  workflows: `databricks-ci.yml` (build, test, upload the wheel) on every PR,
  then `databricks-cd.yml` (download the wheel, `databricks bundle deploy`) on
  push to `main`.

## Running it yourself

```bash
docker build -t databricks-local-ci:15.4-lts --build-arg DBR_TAG=15.4-LTS \
  -f <path-to-databricks-local-ci>/docker/Dockerfile <path-to-databricks-local-ci>
docker run --rm -v "$(pwd):/workspace/project" -w /workspace/project \
  databricks-local-ci:15.4-lts \
  bash -c "pip install -e '.[dev]' && uv build --wheel && pip install --force-reinstall --no-deps dist/*.whl && pytest tests/ -v"
```

## Deploying for real

`databricks.yml` targets a real workspace
(`https://dbc-706f8d04-6ed5.cloud.databricks.com`) — a **Free Edition**
workspace, which has no account console and so cannot use Service
Principal/OIDC federation at all (confirmed: `databricks bundle deploy` with
`DATABRICKS_AUTH_TYPE=github-oidc` fails with `TOKEN_INVALID` no matter how a
federation policy is configured, because Free Edition can't create one).
`ci-cd.yml` therefore authenticates with `auth_method: "pat"` — a personal
access token — instead of OIDC.

Two things have to be true before `deploy` actually succeeds, neither of
which this repo or its workflow can do for you:

1. Generate a personal access token from **workspace** Settings → Developer →
   Access tokens (not the account console — Free Edition doesn't have one),
   and set it as this repo's `DATABRICKS_TOKEN` secret:
   `gh secret set DATABRICKS_TOKEN --body "<token>"`. See
   [`databricks-local-ci`'s README](https://github.com/ViniciusOtoni/databricks-local-ci#consuming-the-workflows)
   for the `oidc` vs `pat` trade-off if you're deploying to a workspace that
   *does* have account console access.
2. `/Volumes/main/default/demo/orders` (the `--input-path` the bundle passes)
   needs to actually exist and have `region`/`amount` columns — this repo
   ships the job definition, not sample production data. Adjust the
   `catalog`/`schema` bundle variables or the paths in `databricks.yml` to
   wherever your own demo data lives.
