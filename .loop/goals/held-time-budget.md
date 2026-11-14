# A goal's time budget counts only active step time, never time held in the pr queue, on an owner answer or after a stop (#3878)

- Slug: held-time-budget
- Touches: skills/workflow-delivery, skills/workflow-monitoring, dev/toy, .loop/regression.tsv

## Done lines

Frozen. A wrong done line needs a new goal.

1. A toy goal held 10 hours in the pr queue then run 20 minutes reads 20 minutes spent, and a goal that truly runs past its budget is still stopped

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
