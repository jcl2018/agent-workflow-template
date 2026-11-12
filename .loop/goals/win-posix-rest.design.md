# win-posix-rest: design

## Problem
After #2616 three skill folders carry `proctree.py`, but `workflow-health/scripts/workflows.py` (`os.getuid`, `os.killpg`, `os.kill(pid, 0)`) and `workflow-setup/scripts/update.py` (`os.killpg`) still call POSIX-only functions, and `lanekit.py` / `slots.py` call `os.getuid` behind an `os.name` guard. `workflow-delivery/scripts/private.py` is 21,767 bytes (cap 20,480).

## Approaches
1. Import one shared `proctree` across skills. Cheap, but each skill must run alone, so a cross-skill import breaks adoption of a single skill.
2. One copy of `proctree.py` per skill folder (health and setup get new copies), plus `uid()` in it, so no other script calls `os.getuid`. More files (2 new), identical bytes, pinned by the existing "copies are the same" toy row. Chosen: matches the repo rule (each skill runs alone) and the pattern #2616 set.

## Chosen
- `proctree.uid()`: `os.getuid()` on POSIX, 0 on Windows (the value is only used for the launchctl `gui/<uid>` domain and an owner check; neither means anything on Windows). Add to all copies; five copies identical.
- workflows.py: `UID` uses `proctree.uid()`; the mkdir lock's liveness probe uses `proctree.probe`; the child timeout uses `proctree.kill`.
- update.py: `commit()` stop uses `proctree.kill` (term then kill collapse to one tree kill; Windows taskkill /T /F anyway). update.py is at 20,458 bytes so the edit must not grow it.
- lanekit.py / slots.py: `info.st_uid != proctree.uid()` (slots gets `import proctree`; it already has a copy in its folder).
- private.py: trim ~1.3 KB by tightening comments/docstrings and dead code, no behavior change; verify with its tests.
- Extend `dev/toy/test-portable.sh` to grep all of `skills/` for the three calls outside proctree.py and to check all five copies are equal and every script is within the cap (measured in git blobs so CRLF checkouts don't mislead).

## Done lines
1. No script calls the three functions outside proctree: the grep toy row, plus kill/probe behave on Windows (taskkill path already tested).
2. All scripts <= 20,480 bytes: private.py trimmed; a toy row measures `git cat-file -s`.

## Open questions
None for the owner. Note: on a Windows CRLF checkout disk sizes read ~6% high, so the row measures the committed blob.
