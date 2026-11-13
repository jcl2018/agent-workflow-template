# Time, token, merge-round, active-goal and plan-usage limits in config stop new work when exceeded

- Slug: budget-enforce
- Touches: skills/workflow-delivery/scripts, skills/workflow-monitoring/scripts, skills/workflow-release/scripts, skills/workflow-health/scripts, docs/wiki, DECISIONS.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A goal past time_budget_minutes or token_budget starts no new step; a 4th merge round is refused; no goal starts past max_active_goals or above plan_pause_percent

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
