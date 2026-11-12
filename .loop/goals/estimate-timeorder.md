# The board picks its estimate model by a time-ordered backtest (each goal predicted only from goals finished before it started), which matches real use, instead of leave-one-out (owner, 2026-11-10: "do these" on "the time-ordered test, as a follow-up")

- Slug: estimate-timeorder
- Touches: skills/workflow-monitoring/scripts, dev/toy, .loop/regression.tsv, docs/wiki/Monitoring.md, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. The model choice uses the time-ordered score; the board line names the model and its time-ordered typical error
2. Leave-one-out stays available as a diagnostic in the PR or report, not as the selector
3. A regression row proves a model that only looks good with future data is not chosen, seen failing then passing

## Verify by hand

1. Run `python3 skills/workflow-monitoring/scripts/board_report.py --root .` in a repo with finished goal runs.
   Expect: the table labels the selection column `time score`, labels leave-one-out under `diagnostics: loo`, and names the chosen model.
2. Run `python3 skills/workflow-monitoring/scripts/board_report.py --root . --json`.
   Expect: each candidate has a `time_ordered` score and a separate `leave_one_out` score; `chosen` names the time-ordered winner when at least ten goals are scorable.
