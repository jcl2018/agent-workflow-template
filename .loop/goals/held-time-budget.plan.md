# Plan: held-time-budget

Claims checked against the code: `board_log.flow_seconds`, `holding`, `HOLD` and `board_status.seconds_by_step` exist in
workflow-monitoring; `goal.cmd_pr` prints `WAITING pr queue` and logs nothing; main's only step-start gate is the token check
in `flow.start`; no minute gate is on main (budget-enforce's `fit.budget_stop` is unmerged and reads wall-clock from log[0]).

## Build steps

1. `board_log.py`: `WAIT` and `waiting(entry)` (waiting, `X waits for the owner`, `X pending:`, `refused (no try used)`); the
   gap after one is paused, and so is the live tail when the last entry is one.
2. `goal.py cmd_pr`: log `waiting: pr queue, behind X` once per wait and `pr queue: its turn` when the queue frees the goal.
3. `board_status.seconds_by_step` returns `flow_seconds` (board OVER time line and health cost rule follow).
4. New `active.py` (delivery): `minutes`, `budget_stop`; `flow.start` calls it in place of the inline token check.
5. Docs: Guardrails page says the time budget counts active step time; commands reference maps it.
6. Toy `dev/toy/test-held-time-budget.py` and six rows in `.loop/regression.tsv`, each seen red with its own `--break`.

## Tests per done line

- Line 1, first half (10 hours in the pr queue then 20 minutes reads 20): rows held-time-pr-queue, held-time-session-hold,
  held-time-owner-wait, held-time-stopped, held-time-3878 (defect).
- Line 1, second half (a goal that truly runs past its budget is still stopped): row held-time-over-still-stops.

## What could break

The board's estimates (est-* rows) read the same flow_seconds: a pause now also follows an owner-wait entry. The bash toys
can't run on this Windows PC (they skip); the python toy and a baseline comparison of test-board-held and test-budget
(same failures on origin/main) were run here, the rest run on the Mac and in CI.

## Out of scope

budget-enforce's own `fit.budget_stop` (not on main); the pr queue's order; the token budget.
