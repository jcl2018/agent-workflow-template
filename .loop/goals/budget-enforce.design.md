# Design: budget-enforce (GRD-2)

Problem: only tries and the step and lane limits stop anything; time_budget_minutes and token_budget (in-session goals) and anything on merge rounds, live goals or plan usage stop nothing.

Approaches: (1) one new limits module: no, the package is at its 99-file cap. (2) put each check where the decision is made: budget_stop, add_tokens and round_stop in delivery's fit.py (called by goal.py and flow.py in one line each), active_limit, plan_pause and `usage` in monitoring's pool.py (called by watch.py and the check-in), health's limit_rows in cost.py.
Chosen: 2. Time counts from the freeze (first log line). Tokens come from `goal.py record --tokens N`; unknown records nothing (tokens unread). A 4th merge round makes the goal wait (MERGE_ROUNDS) and restarts the count. Plan usage reaches scripts only through `pool.py usage N`, read for 12 hours, unread pauses nothing. Defaults: max_merge_rounds 3, max_active_goals 20 (owner), plan_pause_percent 80.
Not done: merge.py unchanged (it sends a moved base to goal.py pr, which refuses the 4th round); the proposed DEL-8 and GRD-2 wording is in DECISIONS.md for the owner's un-review, no Reviewed requirement was edited.
Open questions: none.
