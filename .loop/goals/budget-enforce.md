# Time, token, merge-round, active-goal and plan-usage limits in config stop new work when exceeded

- Slug: budget-enforce
- Touches: skills/workflow-delivery/scripts, skills/workflow-monitoring/scripts, skills/workflow-release/scripts, skills/workflow-health/scripts, docs/wiki, DECISIONS.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A goal past time_budget_minutes or token_budget starts no new step; a 4th merge round is refused; no goal starts past max_active_goals or above plan_pause_percent

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Run `python3 dev/toy/test-budget-enforce.py`.
   Expect: every line starts with PASS and the last line is ALL PASS.
2. Run `python3 skills/workflow-monitoring/scripts/pool.py usage 90`, then `python3 skills/workflow-monitoring/scripts/checkin.py`.
   Expect: the first prints `PLAN USAGE 90% recorded: plan usage 90% is above plan_pause_percent 80%`; with a goal ready, the check-in lists that no new goal starts. Run `pool.py usage 10` to clear it.
