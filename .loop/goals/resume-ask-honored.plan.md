# Plan: a resumed goal keeps its release ask (#812)

Checked against the code: `mend.release_text`, `watch.release_text`, `worker.release_step` and the NEXT line in
`goal.py pr` all exist and read `auto_merge` without reading `state["release"]`.

## Build steps
1. `release_text` in mend.py and watch.py: take the ASK branch when `release == "ask"`, before the auto_merge check.
2. `worker.release_step` (also called by `sessions.py report`): skip merge.py when `release == "ask"`.
3. `goal.py pr`: the NEXT line names merge.py only when auto_merge is on and the goal is not set to ask.
4. `dev/toy/test-resume-ask.py` and three land rows in `.loop/regression.tsv`, each seen red on origin/main's code.

## Test per done line
Done line 1: `resume-ask-prompt` and `resume-ask-worker-step` (an ask stops before merge with the ask shown) and
`resume-unasked-merges` (a goal with no ask still merges).

## What could break
A goal started with `--release ask` that the owner later answers "cut": that goes through release.py, not merge.py,
so it is unchanged. goal.py is 20,474 bytes against a cap of 20,480.

## Out of scope
merge.py itself (20,444 bytes, no room); the three uncommitted entry files seen in the issue's report.
