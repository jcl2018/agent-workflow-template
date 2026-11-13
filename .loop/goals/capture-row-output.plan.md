# capture-row-output: plan

Checked against the code: `lanes.run_row` returns (code, output, pid, signal); `runs.execute` builds each result's `tail`
and `runs.file_issues` puts `item["tail"]` in the body; `actions.py` builds the body from `said` inside its inline block and
embeds `tests.py` through `render`. All exist at origin/main (v0.28.0).

## Build steps
1. `scripts/rowtail.py`: `again(command)` makes each `| grep -q PATTERN` a `| cat`; `shown(run, command, code, text)`
   reruns a silent failing row with it once, keeps the last 40 lines, never returns an empty string.
2. `runs.execute`: a FAIL row's `tail` comes from `rowtail.shown` (rerun through `lanes.run_row`).
3. `actions.py`: `render` embeds rowtail.py at `@ROWTAIL@`; the inline block's body uses `shown(run, ...)`. Regenerate
   `.github/workflows/regression.yml`.
4. Toy `dev/toy/test-row-output.py` (Python, runs on Windows): Mac path, silent row, printing row, workflow block with gh stubbed.
5. Rows `capture-row-mac`, `capture-row-ci` (defect, linked to #3789), each seen red with `red --break`.
6. Tests tables re-rendered; Regression runbook line.

## Test for the done line
The two rows above: each fails on the old code (the break stops the rerun) and passes now.

## What could break
A rerun of a failing silent row costs its run time again (only failing rows). A row with a `| grep -q` whose upstream
side effects matter reruns them. Size caps: actions.py 20,217 of 20,480.

## Out of scope
Rewriting the 700 rows; the Automation page (owner-reviewed, so it stays STALE until the release step); the
`regression-pr.yml` workflow.

DEPTH: full
