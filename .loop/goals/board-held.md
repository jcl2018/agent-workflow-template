# Fix issue 102: the board shows held and newly assigned session goals truthfully and drops stale next lines

- Slug: board-held
- Touches: skills/workflow-monitoring, docs/wiki/Monitoring.md, .loop/regression.tsv, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A session goal's next line comes from its latest session report, never an older failure
2. A goal on hold (session reassigned, worktree kept) shows as held, not running and not as a background worker
3. A goal assigned to a worker session shows at once as assigned to that session with step freezing, before it is frozen
4. Defect tests linked to issue 102, each seen failing once, prove all three

## Design

Approach A, from the idea step: the live board works out each state from the run records, the session pool and whether
a pid is alive. No new run status. The latest session report wins the next line. A running goal with no busy pool entry
and no live pid shows under Held goals. A busy pool entry with no run file shows as freezing, under its session's name.
`sessions.py bind` records that handoff before the goal is frozen, `free` drops it, and `watch.py` leaves it alone. A
running goal at release reads "finish release", and a goal that has failed tries shows "try N of M". It also folds in
issue 108: a session report never moves a `done` goal back to `running`.

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
