# win-posix-rest: plan

Checked against the code: `workflows.py` lines 26 (UID), 94 (probe), 212 (killpg); `update.py` lines 112 and 116 (killpg in `commit`); `lanekit.py:103` and `slots.py:116` (getuid behind an nt guard); `private.py` 21,767 bytes in git; `test-portable.sh` already pins the three-copy equality and the stop-site grep.

## Build steps
1. `proctree.py`: add `uid()` (POSIX `os.getuid()`, Windows 0) and mention it in the docstring. Copy the identical file into `workflow-health/scripts` and `workflow-setup/scripts`.
2. `workflows.py`: `import proctree`; UID from `proctree.uid()`; lock probe `proctree.probe(holder)`; timeout `proctree.kill(run.pid)`. Drop the now-unused `signal` import if unused.
3. `update.py`: `commit()` except branch calls `proctree.kill(proc.pid)` then waits; same or fewer bytes (limit 20,480).
4. `lanekit.py`, `slots.py`: use `proctree.uid()` for the owner check (slots imports its own proctree copy).
5. `private.py`: trim to at most 20,480 bytes in git with no behavior change.
6. `dev/toy/test-portable.sh`: compare all five proctree copies; grep all of `skills/` for `os.getuid`, `os.killpg`, `os.kill(..., 0)` outside proctree; assert every `skills/*/scripts/*.py|sh` blob is at most 20,480 bytes (`git cat-file -s`, not disk size).
7. Regression rows (land): `win-posix-calls-gone` (PASS line for the grep) and `win-posix-size-cap` (PASS line for the size check); each proven failing with `regression.py red` against a break command (re-add `os.getuid` to workflows.py; append padding to private.py).
8. `## Verify by hand` in the goal file; run the portable, adopt and update toys that touch these files.

## Tests per done line
- Done 1: `win-posix-calls-gone` plus the existing `port-base-windows`, `stop-takes-tree`.
- Done 2: `win-posix-size-cap`.

## What could break
- Terminating `commit()` in update.py: kill is now one tree kill instead of SIGTERM then SIGKILL; git hooks get no grace period. Accepted (proctree has no graceful signal on Windows, and the old code waited only 10 s).
- Copies drift: the existing equality row covers it after step 6 includes the two new copies.
- private.py trim touching a private-name scan: run its toys.

## Out of scope
Other skills' files, a graceful-stop signal, the CRLF working-tree size effect on Windows.

