# guards-null-report: plan

1. `guards.py` revive, `session_bind.py` (two updates) and `mend.py` resume: `report=None` becomes `report={}`.
2. `goal.py`: `SEEN` snapshot set in `load` and `save`; `save` takes `<slug>.json.lock` with `fcntl.flock`, re-reads the file,
   writes `dict(disk, **changed_keys)` with the merged log, then updates the caller's state. Trim two long lines (the pods
   loader, one usage line) so goal.py stays under 20,480 bytes (20,341).
3. `dev/toy/test-guards-null-report.sh`: reset (revive writes `{}`, no `report=None` left), writers (two and six unsynchronised
   writers that all load before any saves: every field and log line lands, valid JSON, no temp file), nofiles (no file added
   under skills/ against the merge base).
4. Rows `guards-null-report-reset`, `-writers`, `-nofiles` (goal column `guards-null-report:1..3`), each seen red with a break command.
5. Delivery.md: one true sentence on the `goal.py record` usage line. Tests tables from `criteria.py render` only.
6. Touches: session_bind.py and mend.py are in skills/workflow-monitoring/scripts, outside the frozen touches; the operation
   session was asked to widen them.
