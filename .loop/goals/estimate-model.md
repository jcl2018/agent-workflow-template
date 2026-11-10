# Fix issue 96: estimate each goal from its size and from similar finished goals, not a fixed 15 minutes

- Slug: estimate-model
- Touches: skills/workflow-monitoring/scripts/board_status.py, skills/workflow-monitoring/scripts/board_runs.py, skills/workflow-monitoring/scripts/graph.py, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A goal's estimate comes from finished goals like it: the median actual time of past goals with a similar number of done lines and touched areas, per step, falling back to the median of all finished goals; a goal with more done lines or touched areas gets a longer estimate
2. The live board shows each estimate as a range (for example 20 to 45m) and says "rough" when fewer than 5 similar goals exist
3. Running goals refine their estimate from the steps they have finished
4. Fix issue 37: a goal whose current step has run more than 3 times its estimate shows under Issues as stalled, naming the step and how long it has run
5. A defect test linked to issue 96 proves two queued goals of different sizes get different estimates that fall inside the range of their similar past goals, seen failing once and passing now, and issue 96 closes when this merges
6. Per DOC-3, each done line above is recorded on its PRD page as one or more Given/When/Then scenarios under the requirement it serves, each linked to its regression row with its last result

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
