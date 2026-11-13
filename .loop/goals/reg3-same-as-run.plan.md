# Plan: reg3-same-as-run

Checked against the code: `actions.py` has `ROW_DROP`, used by `row_env()` (regression.py's local rows, via runs.execute)
and by the rendered workflow (`@ROWDROP@`). `test-regression.sh` runs the rendered block as `ci-block.py`.

1. Add `REGRESSION_SHARD`, `REGRESSION_LEVELS`, `REGRESSION_TARGET`, `REGRESSION_CLEANUP` to `ROW_DROP`. (Done, committed.)
2. Guard row `shard-gone` in test-regression.sh: the block runs with those names set, and a row that tests they are empty
   must PASS. Seen red: on origin/main the row sees `REGRESSION_SHARD=1/2` (shown by running the rendered block with
   shard 1/2 and a row that prints it); with step 1 it sees nothing.
3. Done line: `workflow-same-as-run` passes on Linux CI in both shards.

Could break: a row that wanted the runner's shard or levels (none: grep finds only tests that set them themselves);
actions.py size cap (checked by the size test in qa).
Out of scope: the Mac-only scheduled run (not reproduced here; the issue was opened by github-actions, in shard 1).
