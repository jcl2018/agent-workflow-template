# monitor-report-crash plan

1. `monitor.py load()` (skills/workflow-monitoring/scripts/monitor.py): return None unless the JSON is an object. `runs()` already drops None. Confirmed: `runs()` and `load()` exist and `runs()` is what report, dashboard and the ready list call.
2. Add `dev/toy/test-monitor-stray-runs.py` and a regression row `mon-stray-runs` (feature Monitoring, requirement MON-1) running it; record `regression.py red mon-stray-runs`, seen failing on the unfixed copy, passing with the fix.
3. Re-render docs (Tests page) with the wiki step.

Could break: a run record that is a valid object is unaffected; a non-object was already a crash. monitor.py stays under 19,000 bytes (14,362 now).
Out of scope: removing the stray files, other readers of loop/runs outside monitor.py.
