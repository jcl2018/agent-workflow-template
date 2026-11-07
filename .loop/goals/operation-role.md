# Make the operation session govern only, and run POCs and goals in batches elsewhere

- Slug: operation-role
- Level: 1
- Touches: skills/workflow-monitoring, skills/workflow-delivery/SKILL.md, skills/loop-files.md, listing.json, dev/toy/test-batch.sh, .loop/config.json, .loop/regression.tsv, docs/wiki/Monitoring.md, docs/wiki/Delivery.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. A new self-contained scripts/batch.py in workflow-monitoring adds and starts a batch: queue lines may be poc or goal lines under a named batch heading, and each runs in its own session or background agent, never in the governing session
2. A POC runs read-only in its own worktree, saves its answer and go line to the loop folder outside the repo, and shows on the board as finished with that answer, and a goal line can be promoted from a saved POC
3. references/operation.md and both SKILL files state that the operation session is for governance only: it assigns and watches, and runs neither poc nor go itself
4. docs/wiki/Monitoring.md gains new criteria for these rules, marked (draft) for the owner's approval, each with a row in Enforced by and a real regression row seen failing once; the 30 approved criteria are not reworded
5. dev/toy/test-batch.sh proves each line above with a stand-in agent and is listed in checks, and every script stays under 20 KB
6. The repo checks pass

## Verify by hand

1. Run `python3 skills/workflow-monitoring/scripts/batch.py` with no arguments.
   Expect: it prints usage listing add, start and promote.
2. Run `bash dev/toy/test-batch.sh`.
   Expect: the last line is ALL PASS.

## Design

`scripts/batch.py` (stdlib, one file, well under 20 KB) keeps a batch in `.loop/queue.md` under a `## Batch: NAME`
heading. Goal lines are the ordinary `- slug:` lines (watch.py already runs those); a POC line is `- poc: SLUG |
question: Q`, which watch.py ignores. `start NAME` launches each unstarted POC as a detached wrapper (`batch.py _run`,
own session) and hands goal lines to `watch.py watch --once`, so nothing runs in the governing session.

A POC wrapper makes a detached worktree under loop/worktrees/, runs `agent_command` there with a read-only prompt,
and takes the agent's stdout as the answer. It saves `loop/pocs/SLUG.md` (answer) and `SLUG.go` (the last `go "..."`
line) outside the repo, fails the run if the worktree's HEAD or status moved, removes the worktree, and writes
`loop/runs/SLUG.json` with kind poc, status done and the answer as `note`, so the board shows it finished with the
answer. `promote SLUG` parses the saved go line and queues a goal line (slug `SLUG-go`) under the batch.

Risks: a goal line in another batch starts too, because `watch --once` starts every queued goal (documented). A POC
agent could write; the wrapper detects it and marks the run failed. Existing scripts near 20 KB are not touched, only
docs and skill text. New criteria are `(draft)`; the 30 approved ones stay word for word.

## Plan

1. Write dev/toy/test-batch.sh first (stand-in agent); run it to see it fail; record the regression rows seen failing.
2. Write scripts/batch.py until it passes (done lines 1, 2, 5).
3. State governance-only in references/operation.md and both SKILL files; check by grep in the test (line 3).
4. Add MON-4..MON-8 as (draft) to Monitoring.md with Enforced by rows, and rows in .loop/regression.tsv (line 4).
5. Add the test to .loop/config.json checks; update listing.json, loop-files.md, Delivery.md; `goal.py check` (lines 5, 6).
