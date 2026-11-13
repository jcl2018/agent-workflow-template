# pr-queue design (#3877)

## Problem
Four goals used up max_tries in `goal.py pr` on 2026-11-13 because origin/main moved during their 15-minute pr lanes and the merge
conflicted: their own code was not at fault. And nothing orders pr lanes per repo, so the operation session sequences them by hand.

## Approaches
1. Hold merge.lock for the whole pr step. Rejected: `goal.py pr` returns while its lane runs detached and is polled by later calls, so a
   process-held lock is gone before the lane ends, and a held merge.lock would block merges for 15 minutes.
2. A per-repo FIFO queue in files, one per goal, keyed by goal and kept alive by asking again. Chosen.

## Choice
- `<common>/loop/pr-queue/<slug>` holds the time the goal joined; asking refreshes it. The goal first in order runs its lane; the others print
  `WAITING pr queue: <goal> first; run pr again`, merge nothing and return 0.
- A goal leaves by not being at the pr step any more (it failed a try, or opened its PR), by its run record not being running or waiting
  (stopped, failed, merged), or by its file being older than 30 minutes (LOOP_MERGE_LOCK_SECONDS, as MON-15's merge lock). The next asker
  deletes its ticket, so a dead or stale holder is replaced. A goal that fails a try rejoins at the back.
- A conflict with main, or a lane that fails while origin/main moved on, is a try lost to main moving: `state["moved"]` counts it against
  `max_moved` (config, default 5); tries and max_tries are untouched. The sixth counts as an ordinary failed try.
- Code: pr_turn, pr_ahead and pr_moved in workflow-monitoring's pool.py, reached through graph.pr_queue (graph.py is at its size
  budget); goal.py cmd_pr asks first, and routes the conflict and the lane failure. merge.py and merge.lock are untouched.

## What each done line needs
Two goals at pr run in order without BASE_MOVED failures: the queue toy parts queue and pr. A main-moved retry leaves max_tries unchanged: part moved.

## Open questions
None.
