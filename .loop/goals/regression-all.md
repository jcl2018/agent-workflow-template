# Turn on every regression test: enforce every criterion and record a run for every row

- Slug: regression-all
- Touches: .loop/regression.tsv, .loop/regression-runs.tsv, dev/toy, skills/workflow-regression, docs/wiki

## Done lines

Frozen. A wrong done line needs a new goal.

1. Every criterion now marked not enforced (10 on Documentation, 3 on Regression) has a real test, seen failing once and passing now, or the goal's report says exactly why it cannot be tested yet
2. Every one of the regression rows has a recorded result from a full run, all pass, and the regression workflow on GitHub runs all of them and passes
3. Rows that are slow move to the nightly level instead of being dropped, and the Tests tables show each test's level and last result
4. docs check and health stay green

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->

1. Open `docs/wiki/Regression.md` and `docs/wiki/Documentation.md` and read the Tests tables.
   Expect: every row shows its level (`both` or `nightly`) and a last result of `PASS` with a date, and no row says `not enforced`.
2. Open `.loop/regression.tsv`.
   Expect: every row of the suites that take 20 seconds or more (for example `operate-all`, `frozen-done-lines`, `no-pid-left-alone`) is at level `nightly`, faster ones such as `auto-release` stay `land`, and none was removed.
3. On GitHub, open Actions, then the `regression` workflow, and run it on this branch with "Run workflow".
   Expect: the run finishes green and its summary table lists every row as PASS.
