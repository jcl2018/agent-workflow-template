# Let a machine adopt a goal started on another machine (issue #2851): goal.py adopt <slug> rebuilds this machine's run record from the pushed loop/<slug> branch, its frozen goal file, its PR and its commit history, marks the earlier steps 'done on another machine' with that machine's evidence, and requires qa and pr to run again here before release; and a handover refuses to call a branch pushed when it isn't on origin

- Slug: goal-adopt
- Touches: skills/workflow-delivery/scripts/goal.py, skills/workflow-monitoring/scripts

## Done lines

Frozen. A wrong done line needs a new goal.

1. goal.py adopt <slug> on a pushed branch with a PR creates a run record at step qa, and goal.py pr and merge.py then work for that goal without goal.py new
2. adopt refuses a branch that isn't on origin and never marks qa or pr done from another machine's evidence

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
