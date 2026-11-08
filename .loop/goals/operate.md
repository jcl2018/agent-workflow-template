# Give Monitoring one deterministic operate command and a dependency-graph planner, as MON-1 to MON-5 say

- Slug: operate
- Touches: skills/workflow-monitoring, skills/workflow-delivery, README.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. MON-1 is unreviewed and rewritten word for word as follows, then marked Reviewed 2026-11-08 with criteria.py review --user, since the owner approved this wording in chat: MON-1 "Roles, start and planning. One command starts the operation session and drives the whole process the same way every time. The operation session plans queued goals as a dependency graph and runs every goal whose dependencies are met in parallel, each in its own worker and worktree, and never builds. A goal waits only on goals it truly depends on; sharing files is not a reason to wait: the later goal brings in the earlier one's merged changes and runs its checks again, and only a real conflict sends it back to fix."
2. Queue lines may name depends-on goals; watch starts every goal whose dependencies are merged, up to a parallel limit set in .loop/config.json, and no longer holds a goal back only because its touches overlap a running goal; the board's dependency map draws these dependencies
3. Before its pull request a goal merges the latest base branch; if that merges cleanly it reruns its checks and goes on, and only a real conflict costs it a try
4. One operate command starts the operation loop: it starts queued goals and batches in workers, watches them, updates the board and prints the status block on the cadence from board.py cadence and whenever a worker reports, printing one line when nothing changed
5. goal.py and flow.py refuse goal steps outside a worker, naming the worker command
6. A worker reports each change of step or status as it happens, and the operation session can send a worker an answer or follow-up that the worker picks up
7. The status block's Next shows only queued and waiting work, Roadmap counts merged goals per feature, and each step records its tokens when the agent reports them
8. A toy test with a stand-in agent proves each line above, and every script stays under 20 KB

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
