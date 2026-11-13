# Design: hlt4-repeat-row (#3784)

**Problem.** `repeat-no-second` fails on the Mac: the second `health.py file` prints `DONE update #1`, not `SAME #1`.
Since 985d6893 (2026-11-12) the fake gh reads `--body-file` with `$(cat)`, which drops the body's last newline; `file.plan`
compares the stored body with `body_of`, which ends in a newline, so every repeat looked changed. The row pipes into
`grep -q`, so the failing run has an empty output body. feature_labels is not the cause (on or off, same result).

**Approaches.**
1. Make the fake gh keep the newline. Cheap, but the code still treats a trailing-newline difference as a change, and a
   real issue body can lose it too (editing on the web, a body-file read through a shell).
2. Compare the bodies without trailing whitespace in `file.plan`. One line, no risk to real updates (a real change shows
   above the last newline). Chosen.

**Also.** `issues.by_path` takes a Windows subject with backslashes; with feature_labels on, no feature was found, so the
"on" case could not be proved on Windows. It now normalises `\` to `/`.

**Done line.** A Python toy, `dev/toy/test-health-repeat.py` (Windows ok, runs the fake gh in place of gh), files twice with
feature_labels off and on and prints `PASS: a repeat opens no second issue`; row `repeat-no-second` runs it. Red: the
rstrip put back fails the toy (seen red).

**Open questions.** None.
