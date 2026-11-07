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

1. In a repo set up with `workflow-setup`, run `python3 scripts/batch.py add demo --poc "How is the title set?" --slug title-poc`, then `python3 scripts/batch.py start demo`.
   Expect: it starts a background process, and your session stays free. `git status` shows only `.loop/queue.md`.
2. Run `python3 scripts/batch.py status demo` until the POC says `done`, then `python3 scripts/board.py board` and `python3 scripts/board_page.py`, and open `board.html`.
   Expect: a lane with one `poc` box, and the answer as its last message. The answer and `go` line are in `.git/loop/pocs/`.
3. Run `python3 scripts/batch.py promote title-poc`.
   Expect: `.loop/queue.md` gains `title-poc-go` under `## Batch: demo`, with the POC's goal and done lines.

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
agent could write; the wrapper detects it in its own worktree only and marks the run failed. New criteria are `(draft)`;
the 30 approved ones stay word for word.

Changed from the first draft: `dev/package.py` refuses `__file__`, so batch.py re-runs itself through `sys.argv[0]` and uses
watch.py only if it sits beside it, printing the command otherwise. A POC record is `tracked`, so the board draws one
`poc` box and no `resume` hint, and `watch.py resume` refuses a run with no branch.

Not built, waiting on the owner: a POC and its `go` line continuing in one session. It fits as a later change: a POC run
in a visible session would save its answer with a new `batch.py` command, `promote SLUG --session` would add `session: yes`
to the queue line, and `watch` would print `PROMPT` as today, with the worktree named, for the operation session to send
to that same session. Nothing here blocks that.

## Plan

1. Write dev/toy/test-batch.sh first (stand-in agent); run it to see it fail; record the regression rows seen failing.
2. Write scripts/batch.py until it passes (done lines 1, 2, 5).
3. State governance-only in references/operation.md and both SKILL files; check by grep in the test (line 3).
4. Add MON-4..MON-8 as (draft) to Monitoring.md with Enforced by rows, and rows in .loop/regression.tsv (line 4).
5. Add the test to .loop/config.json checks; update listing.json, loop-files.md, Delivery.md; `goal.py check` (lines 5, 6).
