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
