# Implement the owner-approved Monitoring PRD: the operation session re-plans the graph at every check-in to finish soonest, runs in full auto mode by default, cleans up after every goal, and stays govern-only (owner, 2026-11-10: "I want to approve it, but turn on that folder by default. Turn on by default. And add it.")

- Slug: monitoring-prd
- Touches: skills/workflow-monitoring, skills/workflow-setup, skills/workflow-release, docs/wiki/Monitoring.md, .loop/config.json, .loop/regression.tsv, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. MON-10: each check-in re-reads progress and re-plans: every goal whose dependencies are met starts in a free or freed session up to the slot limit, same-PRD same-file goals are proposed merged, a blocking goal with a ready part is proposed split, the critical path goes first in the merge line, no running goal is stopped to re-plan, and every change is logged with its reason and shown in the check-in
2. MON-11: a full_auto setting, on by default, answers each worker decision with its recommended option and logs question, answer and reason for the next check-in; destructive, money, security/access and owner-contradicting decisions always wait under Needs you; turning it off applies at the next decision
3. MON-6: a merged goal's session gets the next ready goal or is archived and its worktree and branch are removed; a merged report always frees the session (issue 175) (merged in from session-cleanup)
4. MON-5's reply hook blocks a check-in that breaks the layout, never checks workers or other repos, and one setting turns it off (merged in from reply-hook)
5. MON-4 board prints only for report, dashboard and "where do things stand"; MON-7 the operation session refuses edits, commits and pushes outside merges and post-merge steps; MON-8 a worker silent 30 minutes shows under Needs you; MON-9 the board builds in under 10 s
6. Each of MON-4 and MON-6..MON-11 has a regression row seen failing then passing, listed in the Monitoring Tests table
7. Issues 94 and 123: the live board draws dependencies as a top-to-bottom graph at most 60 characters wide with running, holding, queued and waiting-on-you markers and a legend (merged in from board-graph, without its old MON-4 rewording, which the owner replaced on 2026-11-10)
8. MON-12 session pool: a pool setting (default 20) of idle worker sessions; ready goals take a pooled session; when the pool runs low the operation session asks the owner at the desktop and creates every missing session in one step on the owner word; finished sessions return to the pool; the board shows free, busy and total; an empty pool waits under Needs you with its fix
9. Issues 97, 111, 112, 113, 114, 115 and 122 are fixed, each with a defect row seen failing then passing (owner-approved issue mapping 2026-11-10)

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. In the main checkout, run `python3 skills/workflow-monitoring/scripts/operate.py run --once`.
   Expect: one headline line, then All sessions, Dependencies, Needs you and Coming up; no `LIVE BOARD` block.
2. Run `python3 skills/workflow-monitoring/scripts/monitor.py report`.
   Expect: the live board, with Dependencies drawn top to bottom (`[>]`, `[ ]`, `<-`, a `|`/`v` between bands and a legend), no line wider than 60 characters, and a HELD OR FREEZING section.
3. Run `python3 skills/workflow-monitoring/scripts/pool.py status`.
   Expect: one line `pool: F free, B busy, T total (target 20)` with this repo's counts.
4. Pipe a routine question into the full-auto check: `echo "Which helper name?" | python3 skills/workflow-monitoring/scripts/auto.py decide-text --kind routine --recommend a`, then the same with "Delete the cache?".
   Expect: `AUTO` for the first, `WAITS: it mentions delete` for the second.
5. Pipe two commands into the govern check: `echo "git -C . commit -m x" | python3 skills/workflow-monitoring/scripts/govern_hook.py check`, then `echo "git status" | ...`.
   Expect: `BLOCK: git commit`, then `PASS`.
6. Run `python3 skills/workflow-monitoring/scripts/replan.py plan` twice.
   Expect: the first run lists each running goal's start with its reason (or REPLAN: no change); the second prints `REPLAN: no change`.

## Also closes

Closes #321: the reply hook now checks the claimed operation session, so a one-line scheduled check-in reply is blocked and told the five missing parts (owner, 2026-11-10, via the operation session; row reply-checkin-321).
