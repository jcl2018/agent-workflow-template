# suite-shard: plan

Checked against the code: `skills/workflow-regression/scripts/actions.py` holds `SHARDS = 2`, `BUDGET_MINUTES = 30`, the `WORKFLOW` text (matrix, `REGRESSION_SHARD`, the skip at `time.time() - start + ROW_SECONDS > JOB_SECONDS`, the per-job summary step), and `render()`. `tests.py summary --results FILE --took S` reads one results file. `.github/workflows/regression.yml` is its rendered output (`regression.py workflow`). `dev/toy/test-automation-budgets.sh:25` asserts the matrix is `list(range(actions.SHARDS))`.

## Build steps
1. actions.py: `SHARDS = 4`. In the row loop, skip only when under 30 s remain, and run each row with a timeout of min(ROW_SECONDS, time left). `run()` takes the timeout. A time skip also writes `# unrun <id>` to the results file.
2. actions.py: each shard uploads its results file as artifact `results-<shard>` (always). Replace the per-job summary step with a `summary` job (`needs: regression`, `if: always()`, same routine check) that downloads `results-*`, merges them into one file, runs `tests.py issues --write` and `tests.py summary` once, and prints `UNRUN <n>` (the count of `# unrun` lines) and `SHARDS <n> of 4 reported`.
3. Render `.github/workflows/regression.yml` with `regression.py workflow`; update docs/wiki/Regression.md where it names the shard count.
4. Toy tests in dev/toy/test-regression.sh: (a) with REGRESSION_JOB_SECONDS=120 and REGRESSION_ROW_SECONDS=900, rows run and none is skipped for time (red before: skipped); (b) with JOB_SECONDS so small that no row fits, rows are SKIPPED and recorded `# unrun`; (c) the rendered workflow has 4 shards, a `summary` job needing `regression`, and no per-job summary step; (d) the shard split covers every wanted row exactly once across 4 shards.
5. A regression row for the done line, seen red once, in .loop/regression.tsv.
6. Real run: `gh workflow run regression.yml --ref loop/suite-shard`, then post the summary counts in the PR.

## What could break
- A shard that fills its budget on slow rows: UNRUN shows it; raise SHARDS to 5 and say so.
- Rows inherit the runner's environment: ROW_DROP stays unchanged.
- The summary job runs even when a shard died: it reports the shards that did, and prints `SHARDS n of 4 reported`.

## Out of scope
The local (Mac) schedule, the lane's own budget, row speed-ups, a dynamic work queue.
