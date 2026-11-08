# Show the roadmap as a dependency graph in the printout and board, with the owner's new MON-4 wording approved in chat on 2026-11-08

- Slug: status-graph
- Touches: skills/workflow-monitoring, docs/wiki

## Done lines

Frozen. A wrong done line needs a new goal.

1. MON-4 is unreviewed and rewritten word for word as follows, then marked Reviewed 2026-11-08 with criteria.py review --user, since the owner approved this wording in chat: MON-4 "Printout. Each check-in prints the same template as text: Needs you first, then the roadmap as a dependency graph (a flow chart of every goal, done, running and queued, with arrows for what waits on what, each showing its stage, progress bar and estimated time to finish), the total estimated time for the whole graph, then Goals (done lines met). A stuck worker stays at the top of Needs you until I answer."
2. The status block and the board draw that graph from the planner's dependencies, marking merged, running and queued goals, and give the total as the longest chain of estimates, not their sum
3. A goal's step label changes when a step starts, not when it is recorded, so the board, the status block and the graph never show a finished step as current
4. A toy test with a made-up queue of parallel and chained goals proves the graph, the marks, the total and the live step label, and the repo checks pass

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
