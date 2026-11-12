# private-size-pc plan

Files: skills/workflow-delivery/scripts/private.py (module docstring tail, mend/where/scan/worker_push/hook/required_checks docstrings, a few trailing comments). Confirmed to exist.

Steps: 1. strip those docstrings and comments (done, commit 99d52135). 2. check git blob size <= 20,480 (20,348). 3. py_compile, `private.py check`, usage line unchanged.

Tests per done line: existing land row `size-budget` (fails on main with private.py at 21,767; passes on Linux CI after; it skips on Windows because CRLF working files read over the cap, so the LF blob size was checked by hand). The toy rows covering private.py skip on Windows ('# windows: ok' missing).

Could break: usage output, which prints `__doc__.splitlines()[5]` (position kept). Out of scope: any code change.
