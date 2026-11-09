# Make Needs you show only the wiki problems that exist now, draw the dependency graph, and print local times

- Slug: operate-fit-3
- Touches: skills/workflow-monitoring/scripts/operate.py, skills/workflow-monitoring/scripts/board_status.py, skills/workflow-monitoring/scripts/board_runs.py, skills/workflow-monitoring/scripts/graph.py, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. Needs you shows at most one wiki line, built from the current docs check on each pass, naming today's stale or failing pages and the fix; old goals' saved wiki errors are dropped once the current check no longer reports their page, without waiting for a publish
2. Whenever queued or running goals have depends-on links, the roadmap draws them as a flow chart with arrows between goals, and always ends with the longest-path total and finish time
3. Every time operate prints is in the local time zone with its name, not UTC
4. A toy test with old saved wiki errors, a now-clean docs check, and chained queued goals proves each line above

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
