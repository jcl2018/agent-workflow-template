# Make operate's status block match MON-4 and show only what is live

- Slug: operate-fit
- Touches: skills/workflow-monitoring/scripts/operate.py, skills/workflow-monitoring/scripts/board_status.py, skills/workflow-monitoring/scripts/board_runs.py, skills/workflow-monitoring/scripts/graph.py, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. Needs you lists only items still open: a goal's old wiki_error clears once a later publish succeeds or the goal is merged
2. A goal whose pull request is merged on GitHub shows as merged, never as awaiting merge
3. The roadmap is drawn as a dependency graph of live goals (running, queued, waiting) with arrows for depends-on, each with its stage, a 10-cell bar and time left, followed by the longest-path total and finish time; merged goals collapse to one line of pull request numbers
4. When nothing changed, operate prints one line
5. A toy test with a made-up mix of merged, running, queued and stale goals proves each line above

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
