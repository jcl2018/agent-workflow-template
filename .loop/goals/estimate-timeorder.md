# The board picks its estimate model by a time-ordered backtest (each goal predicted only from goals finished before it started), which matches real use, instead of leave-one-out (owner, 2026-11-10: "do these" on "the time-ordered test, as a follow-up")

- Slug: estimate-timeorder
- Touches: skills/workflow-monitoring/scripts, dev/toy, .loop/regression.tsv, docs/wiki/Monitoring.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. The model choice uses the time-ordered score; the board line names the model and its time-ordered typical error
2. Leave-one-out stays available as a diagnostic in the PR or report, not as the selector
3. A regression row proves a model that only looks good with future data is not chosen, seen failing then passing

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
