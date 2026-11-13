# Design: reg3-same-as-run

## Problem
Row `workflow-same-as-run` (#3133) fails on Actions. The workflow now runs in two shards (REG-7) and sets
`REGRESSION_SHARD=n/2` in the step. The row runs `test-regression.sh`, which runs the workflow's own Python block
(`ci-block.py`) as the "workflow" side of the comparison. A row's environment drops only the token and runner-file names,
so the nested block inherits the outer `REGRESSION_SHARD`. On shard 1 the nested block runs every second wanted row and
skips `bad-row` (third, so shard 0). The workflow side opens 0 issues, the local run opens 1, and the test fails. Shard 0
passes, which matches the logs: the FAIL is only in "regression (1)". The row's output is empty because it ends in `grep -q`.

## Approaches
1. Test only: unset `REGRESSION_SHARD` and friends at the top of `test-regression.sh`. Cheap, but a row that runs
   the runner (or any tool reading these names) still inherits the runner's shard.
2. Product: add `REGRESSION_SHARD`, `REGRESSION_LEVELS`, `REGRESSION_TARGET`, `REGRESSION_CLEANUP` to `ROW_DROP`, so a row
   never sees the runner's own state, like it never sees the token. One line, used by both the workflow and `regression.py`.

## Chosen
2, with a guard row `shard-gone` in test-regression.sh run through the block with those names set.

## Done line
"passes on main and is seen red when the two diverge": the guard row fails without the ROW_DROP names (seen red), passes with.

## Open questions
None. Not verified on a Mac: this fix rests on the CI logs (shard 1 only).
