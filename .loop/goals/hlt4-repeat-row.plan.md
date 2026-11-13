# Plan: hlt4-repeat-row

Checked against the code: `skills/workflow-health/scripts/file.py` `plan()` (the `old != act["body"]` compare), `issues.py` `by_path()`,
`dev/toy/fakegh/gh` (the `$(cat)` body-file read) and `fake.py` all exist as the design says.

1. `file.py plan()`: compare `old.rstrip()` with `act["body"].rstrip()`. (done)
2. `issues.py by_path()`: normalise backslashes so a Windows subject finds its feature. (done)
3. `dev/toy/test-health-repeat.py`: files twice in a temp repo with feature_labels off and on, against fake.py with the bash
   fake's newline stripping; prints `PASS: a repeat opens no second issue` only when both pass. (done)
4. Row `repeat-no-second` runs that toy; `regression.py red` with the rstrip put back: SEEN RED. (done)

**Test per done line.** repeat-no-second passes with feature_labels off and on; it fails with the dedupe broken (the
`--break` flag of the toy, and the rstrip break used for `red`).

**What could break.** A real body change that differs only in trailing whitespace is no longer an update; every other
change still is. The bash toy `test-milestones.sh` keeps its own repeat assertion and now passes on the Mac.

**Out of scope.** Changing the fake gh; a feature-label change on repeat (covered by the existing `act["feature"] not in names` test).
