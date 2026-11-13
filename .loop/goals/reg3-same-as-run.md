# The Actions workflow's runner and regression.py run give the same exit and open the same issues for a failing row (#3133)

- Slug: reg3-same-as-run
- Touches: dev/toy, skills/workflow-regression/scripts

## Done lines

Frozen. A wrong done line needs a new goal.

1. workflow-same-as-run passes on main and is seen red when the two diverge

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. After the release run, open the `regression (1)` job of the Actions run for the release.
   Expect: `PASS workflow-same-as-run` in its log, and issue #3133 closes with "Passing again."
2. Run `bash dev/toy/test-regression.sh` on a Mac or Linux box.
   Expect: `PASS: a row cannot see the runner's shard, levels or cleanup (issue 3133)` and `ALL PASS`.
