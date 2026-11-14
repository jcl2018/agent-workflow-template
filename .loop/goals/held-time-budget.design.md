# Design: held-time-budget

Problem (#3878): a goal's time budget was read as wall-clock time since freeze. budget-enforce showed "772 minutes spent, at
the minute budget of 300" while it only waited in the pr queue and on operation decisions. Held time must not count; only
active step time does, by the rule the board's estimate already uses (MON-4, est-held-idle).

## Approaches

1. A second held-time rule in delivery (sum the gaps itself). Cost: two rules that drift; the board and the budget would disagree.
2. One rule: the budget reads `board_log.flow_seconds` (workflow-monitoring), loaded by path as goal.py already loads graph.py.
   The rule gains the cases the board missed: waiting in the pr queue, an owner question (`X waits for the owner`, `X pending:`,
   a refusal that asks), and a live tail that ends in such an entry. Cost: small; risk: a log gap after a waiting entry is not counted.

## Chosen: 2

- `goal.py pr` writes one `waiting: pr queue, behind X` entry when it first waits and `pr queue: its turn` when the queue
  frees it, so the pr queue wait is a pause and the work after it counts again.
- `board_log.waiting(entry)` is the one test for a waiting entry; `flow_seconds` pauses the gap after it and the live tail.
- `board_status.seconds_by_step` returns `flow_seconds`, so the board's OVER time line and health's cost rule agree with the gate.
- New `delivery/scripts/active.py`: `minutes(state)` and `budget_stop(...)`; flow.py's step start calls it (tokens as before).
  Over the budget on active time a new step is still refused with BUDGET_MINUTES.

## Done line

Needs: a toy goal held 10 hours in the pr queue then run 20 minutes reads 20 minutes (dev/toy/test-held-time-budget.py), and a
goal that runs 360 active minutes at a 300 budget is still refused. Rows seen red with a break each.

## Open questions

None for the owner. budget-enforce (unmerged) has its own wall-clock `fit.budget_stop`; when it merges, that function must call
`active.minutes` (noted in the pull request).
