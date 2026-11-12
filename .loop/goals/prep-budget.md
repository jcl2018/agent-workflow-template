# The work a lane does before its first test row (prep, planning, waiting for a slot) gets its own time budget, so a whole pr, qa or ship lane is bounded, not just its rows (owner, 2026-11-11, after lane-control's pr step took 42 minutes with 13 before any row ran: "I really want the 15-minute budget to ... maybe you should apply an additional budget set a budget for that to cover that step. Let's make it 15 minutes as well.")

- Slug: prep-budget
- Touches: skills/workflow-delivery, skills/workflow-regression, skills/workflow-health, skills/workflow-monitoring, dev/toy, .loop/config.json, .loop/regression.tsv, docs/wiki/Regression.md, docs/wiki/Delivery.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. REG-7 adds, Unreviewed: "The work before a lane's first test row (preparing, planning and waiting for a slot) has its own budget, a setting that defaults to 15 minutes and can't be set lower; a lane whose preparation reaches it stops, says which part ran long, and the goal can rerun it instead of starting over."
2. A setting prep_budget_minutes in .loop/config.json (default 15) refuses a value under 15 with a fix line, and the lanes read it
3. The lane records how long preparation, planning and the slot wait each took, and the board and health show a lane that hit the preparation budget and which part ran long
4. Each change has a regression row seen failing then passing, and the goal's own pr lane, preparation and rows, finishes within both budgets

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
