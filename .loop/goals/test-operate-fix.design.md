# test-operate-fix design

Problem: `dev/toy/test-operate.sh` calls `goal.py check`, removed in 7ca4e2fa with the checks step, so `flowall` never finishes a goal and three checks fail on Linux (#3906).

Approaches:
1. Delete the two `check` calls. Cost: two lines. Risk: none; `step` already runs flow and records every step the goal needs.
2. Replace `check` with another command. There is no equivalent: the checks step no longer exists. Rejected.

Chosen: 1. Done lines: the toy no longer calls `goal.py check` (new row `operate-toy-no-check`, seen red here); its three checks pass on Linux (the toy skips on native Windows, so that proof is owed to a Linux runner: nightly `operate-all`).

Open questions: the three `test-pods` failures. Budget caps (checkin, operate, sessions, watch, merge) are exceeded on main: a separate cause, filed as its own defect. Not decided here.
