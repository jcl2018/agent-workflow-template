# The board's estimates use whichever model backtests most accurate on this repo's finished goals, and show that accuracy (owner, 2026-11-10: "Yues")

- Slug: estimate-accuracy
- Touches: skills/workflow-monitoring/scripts/board_status.py, skills/workflow-monitoring/scripts/board_runs.py, dev/toy, .loop/regression.tsv, docs/wiki/Monitoring.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. A leave-one-out backtest over the finished runs compares the candidate models (fixed per-step medians, the size-based rule, any blend) and the board uses the one with the lowest typical error, recomputed as runs finish
2. The board shows each estimate's range and the chosen model's typical error
3. The 3x stall rule gets a floor (a step is never called stalled before 15 minutes), so short steps stop reading stalled after a few minutes
4. A held goal with no pause entry stops adding idle time to its step estimate, and board_status.py goes back under the 90% size warning by moving the model into its own module
5. A regression row proves the chosen model is the backtest's best on a fixture set, seen failing then passing

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
