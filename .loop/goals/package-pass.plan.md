# Plan: package-pass
1. Trim fit.py and lane.py prose; render.py --help exits 0.
2. Merge session_bind into worker (update sessions.py and the toys' reads lines); default-flow and start into the commands references (update flow.py, entry.py, loop-files.md, SKILL.md, test-sync.sh).
3. Toy test-package-caps.py and its regression row, seen red on origin/main.
4. Re-render the Tests tables; add Usage lines for the moved places so the three pages are not stale.

## Full pass
- Scope: touches are skills and dev; no file added under skills/.
- Behaviour: flow.routine() returns the same five sections (checked); entry.narrative reads the same seven parts (checked); sessions.py and worker.py --help run; sessions.py already imported worker and ran the same stdin guard.
- Failure modes: a merged script over the cap (worker.py 18,934); CRLF checkouts (sizes measured as LF); the fcntl shim moved with session_bind (test-portlock names worker).
- Not runnable on Windows here: test-sync, test-portlock (not marked windows: ok) are skipped, not counted as passes.
- Merge last: other goals edit delivery, regression and release scripts; merge origin/main again before pr and re-run package.py.
DEPTH: full
