# Design: win-posix-calls

## Problem

On native Windows Python, `lanekit.port_base()` and `slots.port_base()` raise AttributeError (`os.getuid`, `os.O_NOFOLLOW`
don't exist there), so no lane gets ports. Every timeout or mend stop calls `os.killpg` (or `os.getpgrp`, `signal.SIGKILL`,
`ps`), which Windows also lacks, so a step past its limit crashes flow.py instead of stopping, and whatever it started keeps
running. Worse, `os.kill(pid, 0)` on Windows is `GenerateConsoleCtrlEvent(CTRL_C_EVENT, pid)`, so flow.py's `alive()` poll
is not a liveness test there at all.

## Approaches

1. **Guard each call site inline** (`if os.name == "nt": taskkill ... else: os.killpg ...`). Cost: the same ten lines in six
   files; lane.py and lanekit.py are within 200-460 bytes of the 20,480-byte cap, so it doesn't fit. Risk: copies drift.
2. **One small module, `proctree.py`, copied into each scripts folder that needs it** (as `portlock.py` is): `kill(pid, sig)`
   stops a whole tree (POSIX: `os.killpg`, Windows: `taskkill /T /F /PID`), and `alive(pid)` (Windows: OpenProcess +
   GetExitCodeProcess; POSIX callers keep their own). Cost: one new 1.5 KB file per skill; each call site shrinks or stays
   the same size. Risk: low; on POSIX `kill` is exactly `os.killpg`.

**Chosen: 2.** It fits the size cap, follows the portlock precedent (one copy per skill so each folder runs alone), and
leaves Linux and macOS on the very same system calls.

## Changes

- `check()` in lanekit.py and slots.py skips the uid/mode test on Windows (no uid; the pool sits under the user's profile,
  which ACLs keep private); `_open()` uses `getattr(os, "O_NOFOLLOW", 0)`.
- flow.py, lane.py, lanekit.py, mend.py, session_bind.py: `os.killpg(pid, sig)` becomes `proctree.kill(pid, sig)`; lane.py's
  `kill(os.getpgrp())` kills the child's tree on Windows (no group to address there); flow.py, lane.py and mend.py's
  `alive()` use `proctree.alive` on Windows only.
- lanes.py's row timeout (also a step child) uses `proctree.kill` on Windows instead of `ps` + `SIGKILL`.
- actions.py's generated workflow runs on `ubuntu-latest`; its inline `os.killpg` gets a Windows branch so the script it
  writes is portable too, at no cost on Linux.
- `start_new_session=True` stays: Windows Python ignores it, POSIX needs it unchanged.

## Done lines

1. port_base on Windows: a test that calls both with `LOOP_LANES_DIR` set to a temp dir and expects `(fd, 20000)`; on
   POSIX the same test proves nothing regressed.
2. Process tree: a test that starts a parent which starts a sleeping grandchild, calls `proctree.kill` on the parent, and
   expects both gone (`proctree.alive` false) - run on Windows here and on Linux in CI.
3. Linux land tests: the regression lane on CI (ubuntu) and `dev/toy` land rows stay green.

## Open questions

- The other `os.kill(pid, 0)` liveness checks (graph.py, monitor.py, sessions.py, watch.py) have the same Windows problem;
  they don't stop processes, so they are a follow-up, not this goal.
