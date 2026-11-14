# monitor-report-crash design

Problem: `monitor.py runs()` loads every `loop/runs/*.json` and calls `.get` on it. A stray list-shaped file (for example `runs/issues.json`) raises AttributeError, so `report` and `dashboard` crash (#3862).

Approaches:
1. Skip non-objects in `load()` (return None): one line, covers every caller, no extra bytes of note (monitor.py stays far under 19,000).
2. Filter in `runs()` only: leaves `load()` callers by slug exposed to the same crash.

Chosen: approach 1, because `load()` is the single reader of a run record.

Done line: with a list-shaped JSON in loop/runs, `monitor.py report` prints the board and exits 0. A Python toy (`dev/toy/test-monitor-stray-runs.py`) checks report and dashboard; it was seen red before the fix.

Open questions: none.
