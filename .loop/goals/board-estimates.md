# Fix issue 93: the live board's time left and finish time follow reality, and the board fits a phone screen

- Slug: board-estimates
- Touches: skills/workflow-monitoring/scripts/board_status.py, skills/workflow-monitoring/scripts/board_runs.py, skills/workflow-monitoring/scripts/graph.py, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. When the current step has run past its estimate, its time left is re-estimated from how long it has already run (never less than a minute), the step is marked "over by Nm", and the goal's time left and the board's finish time grow to match
2. Every line of the live board is at most 60 characters wide, wrapping or shortening the step flow instead of running off the screen
3. A defect test linked to issue 93 proves an overrunning step moves time left and the finish time and that no line passes 60 characters, seen failing once and passing now, and issue 93 closes when this merges

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
