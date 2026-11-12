# The board's estimates use whichever model backtests most accurate on this repo's finished goals, and show that accuracy (owner, 2026-11-10: "Yues")

- Slug: estimate-accuracy
- Touches: skills/workflow-monitoring/scripts/board_status.py, skills/workflow-monitoring/scripts/board_runs.py, dev/toy, .loop/regression.tsv, docs/wiki/Monitoring.md, skills/workflow-monitoring/scripts, docs/wiki/Tests.md, skills/workflow-monitoring/references

## Done lines

Frozen. A wrong done line needs a new goal.

1. A leave-one-out backtest over the finished runs compares the candidate models (fixed per-step medians, the size-based rule, any blend) and the board uses the one with the lowest typical error, recomputed as runs finish
2. The board shows each estimate's range and the chosen model's typical error
3. The 3x stall rule gets a floor (a step is never called stalled before 15 minutes), so short steps stop reading stalled after a few minutes
4. A held goal with no pause entry stops adding idle time to its step estimate, and board_status.py goes back under the 90% size warning by moving the model into its own module
5. A regression row proves the chosen model is the backtest's best on a fixture set, seen failing then passing

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Run `python3 skills/workflow-monitoring/scripts/live_board.py` in the repo and read the last line, under the finish time.
   Expect: `estimates: <model>, whole goal off xN.N (N goals)`, at most 60 characters, or `error not known yet (N of 10 goals)`.
2. Run `python3 skills/workflow-monitoring/scripts/board_report.py --root .`.
   Expect: one row per candidate, and the `chosen:` line names the candidate with the lowest loo score, the same model the board's last line names.
3. Look at Issues on the live board for any goal whose current step has run under 15 minutes, and for any goal marked held.
   Expect: none of them is listed as stalled.

## Owner re-review: Documentation (CHANGED)

The Documentation page's Usage gained one factual sentence, on the `render` entry: "The package folds keep the scripts the docs name under 100 files: the digest mail renderer sits in health `rounds.py`, the private rules in `enforce.py` and the issue proposal in setup `sync.py`." It says where three small scripts moved; no requirement changed. The owner's re-review of the Documentation Usage is open.

## Owner re-review: Health (CHANGED)

The Health page's Usage gained one factual sentence on the `check` entry: "The owner's private rules (`--group mine`) run from `enforce.py`, folded in beside the not-enforced check to keep the package under 100 files." No requirement changed. The owner's re-review of the Health Usage is open.
