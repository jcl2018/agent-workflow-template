# Fix issue 102: the board shows held and newly assigned session goals truthfully and drops stale next lines

- Slug: board-held
- Touches: skills/workflow-monitoring, docs/wiki/Monitoring.md, .loop/regression.tsv, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A session goal's next line comes from its latest session report, never an older failure
2. A goal on hold (session reassigned, worktree kept) shows as held, not running and not as a background worker
3. A goal assigned to a worker session shows at once as assigned to that session with step freezing, before it is frozen
4. Defect tests linked to issue 102, each seen failing once, prove all three

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
