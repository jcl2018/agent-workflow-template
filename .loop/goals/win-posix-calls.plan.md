# Plan: win-posix-calls

Design checked against the code (all exist on main at b6598d2):

- `skills/workflow-delivery/scripts/lanekit.py`: `check()` (os.getuid), `_open()` (os.O_NOFOLLOW), `port_base()`,
  `prep()`'s commit timeout (os.killpg SIGKILL).
- `skills/workflow-regression/scripts/slots.py`: `check()`, `_open()`, `port_base()` - same code as lanekit.
- `skills/workflow-delivery/scripts/flow.py`: `alive()` (os.kill(pid, 0) = Ctrl+C on Windows), `main`'s limit stop
  (os.killpg SIGTERM, uncaught).
- `skills/workflow-delivery/scripts/lane.py`: `kill()` (os.killpg), `alive()`, `lane-exec`'s deadline (`kill(os.getpgrp())`).
- `skills/workflow-monitoring/scripts/mend.py`: `stop_late_mender()` (os.killpg), `alive()`.
- `skills/workflow-monitoring/scripts/session_bind.py`: the session-tool timeout (os.killpg SIGKILL).
- `skills/workflow-regression/scripts/actions.py`: the generated runner's `run()` (os.killpg 9).
- `skills/workflow-regression/scripts/lanes.py`: `run_row()` timeout (`ps` + `signal.SIGKILL`, both missing on Windows).

Sizes (LF bytes, cap 20,480): lane.py 20,298, lanekit.py 20,019, flow.py 19,658, lanes.py 19,698 - every edit there must be
byte-neutral or close; trim a comment if needed.

## Build steps

1. Add `proctree.py` (identical copy in workflow-delivery, workflow-monitoring and workflow-regression scripts):
   `kill(pid, sig=SIGKILL)` - POSIX `os.killpg`, Windows `taskkill /T /F /PID`; both quiet when the tree is already gone.
   `alive(pid)` - Windows only: OpenProcess + GetExitCodeProcess == STILL_ACTIVE; access denied counts as alive.
2. lanekit.py and slots.py: `check()` returns after makedirs on Windows; `_open()` uses `getattr(os, "O_NOFOLLOW", 0)`.
3. Replace each `os.killpg` with `proctree.kill`; lane.py's own-group kill uses the child's pid where `os.getpgrp` is
   missing; flow.py, lane.py and mend.py `alive()` defer to `proctree.alive` on Windows.
4. lanes.py `run_row()`: on Windows kill with `proctree.kill(proc.pid)`; POSIX path unchanged.
5. actions.py: the generated `run()` kills with taskkill on Windows, killpg elsewhere.
6. Tests: `dev/toy/test-portable.sh`, two rows of category defect linked to issue #1396, seen red on Windows with the
   old scripts put back:
   - done 1 `port-base-windows`: both port_base()s return a base of the form 20000 + 100N with an open fd.
   - done 2 `stop-takes-tree`: a parent that starts a sleeping grandchild; `proctree.kill(parent)` from each copy leaves
     neither alive; and no stop site in the six scripts calls `os.killpg` directly any more.
   - done 3: the existing land rows (lane-ports-tmpdir, session-tool-timeout, lane rows) on Linux in the PR's CI
     (regression.yml) and the qa lane.
7. Fill `## Verify by hand`, commit.

## What could break

- POSIX: `proctree.kill` must be exactly `os.killpg(pid, sig)`; flow.py gains a swallowed ProcessLookupError (a race that
  used to crash).
- Windows `taskkill /T` walks parent pids, so a grandchild orphaned before the kill is missed; acceptable, the root is
  alive at every stop site.
- The copies of proctree.py drifting: the test imports each copy.

## Out of scope

- `os.kill(pid, 0)` liveness checks in graph.py, monitor.py, sessions.py, watch.py (they stop nothing): a follow-up.
- `start_new_session=True` stays (ignored on Windows, needed on POSIX).
