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
tests/test_integration.py::test_orders_summary_real_run_writes_expected_summary PASSED
tests/test_transform.py::test_summarize_orders_by_region PASSED
2 passed in 79.46s
```

That's the full local test suite — including two separate Spark session
startups (the test fixture's, and the one the job's own subprocess creates) —
measured end to end in this repo's own Docker-based verification, not a
cherry-picked number. No cluster, no waiting, no DBU spent, and it's the exact
artifact (built with `uv`, installed as a real wheel, run as a real subprocess)
that would otherwise ship straight to the job cluster.

## What's here

- `src/orders_summary/transform.py` — the one function with actual logic:
  `summarize_orders_by_region`.
- `src/orders_summary/main.py` — the CLI entry point
  (`python -m orders_summary.main --input-path ... --output-path ...`), the
  same one the Databricks Job task below invokes in production.
- `tests/test_integration.py` — the "real run": writes a local Delta table,
  invokes `main.py` as a genuine subprocess via
  `databricks_local_ci.subprocess_runner.run_entrypoint`, reads back what it
  wrote, and asserts on it.
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
(`https://dbc-706f8d04-6ed5.cloud.databricks.com`), authenticated via GitHub
OIDC to a Service Principal (`DATABRICKS_CLIENT_ID` secret). Two things have
to be true before `deploy` actually succeeds, neither of which this repo or
its workflow can do for you:

1. That Service Principal needs a GitHub Actions federation policy on the
   Databricks side, trusting this repo's OIDC issuer/subject — see
   [`databricks-local-ci`'s README](https://github.com/ViniciusOtoni/databricks-local-ci#known-limitations-read-before-adopting)
   for what `databricks-cd.yml` expects.
2. `/Volumes/main/default/demo/orders` (the `--input-path` the bundle passes)
   needs to actually exist and have `region`/`amount` columns — this repo
   ships the job definition, not sample production data. Adjust the
   `catalog`/`schema` bundle variables or the paths in `databricks.yml` to
   wherever your own demo data lives.
