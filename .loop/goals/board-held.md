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

## Plan

Reviewed by autoplan in full (CEO, DX, eng, each with a native and an outside voice; design skipped, no UI). Steps:

1. `graph.py`: `read_pool` (returns the pool or unknown, with the reason), `assigned`, and slot accounting that counts
   pool-assigned goals.
2. `live_board.py`: latest report wins (after `bound_at`); held goals listed under Queued goals marked `held`;
   freezing goals under Running goals; "finish release"; `try N of M`; off-flow steps drawn at the last known flow step;
   Issues for an unreadable pool, a held goal holding a slot, and a stale assignment.
3. `sessions.py`: bind before freezing, `free`, `--force`, a lock around pool writes, nothing written on an unreadable
   pool, and `done` final for every report (issue 108).
4. `watch.py`: leaves assigned goals alone, fails closed on an unreadable pool, and doesn't reuse an assigned slug.
5. `dev/toy/test-board-held.sh` and defect rows (four for issue 102, one for issue 108), each seen failing once.
6. Monitoring wiki page and SKILL.md: board states, worked sequences, messages, limits.

Done line 1 is proved by the stale-next check, 2 by the held checks, 3 by the freezing checks, and 4 by `regression.py
red` on each defect row.

## Verify by hand

1. In the main checkout after the merge, start a session with the app's own tools for a goal that isn't frozen yet, run
   `python3 skills/workflow-monitoring/scripts/sessions.py bind <new-slug> <session-id>`, then print the live board
   (`python3 skills/workflow-monitoring/scripts/board_status.py`).
   Expect: the bind prints `ASSIGNED ... not frozen yet`, and the board shows `<new-slug>` under Running goals at once,
   with `[freezing]` and `worker: session worker · <new-slug>`.
2. Look at a goal you put on hold (its session reassigned, its worktree kept) on the same board.
   Expect: it is listed under Queued goals ending in `held`, with `worker: none (held, ...)` and a `sessions.py bind`
   line naming it. It is not under Running goals and not called background.
3. Look at a session goal that failed once and was bound again, after its worker sent a new report.
   Expect: its next line is the newest report, not the old failure, and its bar line ends `try 2 of 3`.
4. After a goal's pull request opens, send `python3 skills/workflow-monitoring/scripts/sessions.py report <slug> --status running`.
   Expect: it prints `KEPT done for <slug>: ...`, and the goal still reads `next: merge the pull request` (or its merged report).
