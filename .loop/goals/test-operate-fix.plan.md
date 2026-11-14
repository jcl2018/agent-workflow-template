# test-operate-fix plan

Checked: `flowall` (dev/toy/test-operate.sh) and the manual merge of s2 call `$goal check`; goal.py has no `check` (test-goal.sh asserts "invalid choice").

Build steps:
1. Remove `; $goal check "$1" >/dev/null` from `flowall` and `; $goal check s2 >/dev/null` after the manual merge. (done)
2. Row `operate-toy-no-check` (land, defect, #3906): `! grep -q 'goal check' dev/toy/test-operate.sh`; seen red by restoring a check call. (done)

Tests: that row for done line 1. For done line 2 (the three checks pass) the toy skips on native Windows (exit 77); the proof is owed to a Linux runner: the nightly `operate-all` row runs the whole toy.

Could break: nothing else reads `flowall`; `step` already records each flow step.

Out of scope: the three test-pods failures (budget caps over on main; the two lock checks unestablished): filed as their own defect. regression-known.tsv untouched.
