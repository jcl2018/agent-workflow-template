# Plan: time-ordered estimate selection

The existing seams are `board_model.model`, `folds`, `backtest`, `chosen`, and `accuracy_text`; `board_report.window` and `time_ordered` already implement retrospective scoring. `board_log.stamp` and `named` parse the run log. `dev/toy/test-estimates.sh` owns the backtest fixture and `.loop/regression.tsv` records each named test. `docs/wiki/Monitoring.md` has Reviewed MON-4 wording, which must stay untouched; only its generated Tests table may change.

1. Add an adversarial `check_time_order_selector` fixture and register `est-time-order-selector` under MON-4. It gives a future-data model a better leave-one-out score but a worse time-ordered score than a steady model. Run it red before implementation, then green after.
2. Put time windows and a common eligible-goal time fold in `board_model`, using goals whose finish is strictly before the target's start. Score every candidate on those same folds, cache that as `backtest`, and keep `folds` for leave-one-out diagnostics. Use the time score in `chosen` and `accuracy_text`.
3. Make `board_report` show time-ordered scores as the selector and leave-one-out as a diagnostic, and keep JSON fields clear. Update existing tests for chronological fixtures and the board line's wording.
4. Run the targeted toy tests, regression lane, review the diff, and verify the report and board by hand. Keep `board_model.py` under 18,432 bytes and other scripts under their existing budgets. Commit the result and the goal's Verify by hand steps.

Risks: missing or malformed timestamps reduce scorable goals; simultaneous starts must not leak overlapping goals; the report and board must use identical eligibility and selection; a later run changing must invalidate cached scores. Keep the 10-goal minimum and size-rule fallback. No change to estimate cells, queue prediction, Reviewed requirement text, or release behavior.

No owner decision is needed.
