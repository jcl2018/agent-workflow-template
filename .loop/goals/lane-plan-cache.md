# A lane plans its rows in well under a minute even on a large repo under load, by computing the closure and reference maps once per lane (cached by HEAD) instead of once per row, so lanes stop being cut by the preparation budget (owner, 2026-11-11: "Start it", on starting a goal for #710)

- Slug: lane-plan-cache
- Touches: skills/workflow-regression, skills/workflow-delivery/scripts/lanekit.py, dev/toy, .loop/regression.tsv, docs/wiki/Regression.md, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. On a repo the size of the one where #710 was measured, a lane's planning step finishes in under 60 s at load 20 or more, measured and printed in the lane's .times record, where today it takes 600-1500 s
2. The planned row set is byte-identical to today's for the same HEAD and diff, shown by a test that plans with the cache and without it on fixture repos
3. The cache is keyed by HEAD and invalidated when HEAD or the row file changes; a test moves HEAD and sees a fresh plan
4. A regression row reproduces #710 (planning time grows with rows, uncached) and is seen failing before the fix and passing after
5. lanekit.py's copied functions stay identical to slots.py where test-lane-control.sh checks them, every script stays under 18 KB and the package at 99 files or fewer

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Run `bash dev/toy/test-plan-cache.sh all`.
   Expect: golden, calls, identity, key and sizes all print PASS lines and the run ends with `ALL PASS`.
2. Run `bash dev/toy/test-plan-cache.sh seconds` on a quiet or busy machine.
   Expect: it prints the off, cold and warm planning seconds of a 1,500-row fixture under 20 busy loops, the cold plan under 60 seconds, the cache file under 2 MB, and ends with `ALL PASS`.
3. On a large real repo (owner, not run by the build), rerun a lane that was cut with "planning ran long" at a load average of 20 or more, then read the `planning Ns` part of its LANE line and the `PLAN_CACHE:` line of its log (the planner's first line).
   Expect: planning is under 60 s; run the same lane again at the same HEAD and the log says `PLAN_CACHE: hit (N rows)`; after a new commit it says `PLAN_CACHE: miss (key-head)`. If planning is under 60 s, lower that repo's `prep_budget_minutes` from 25 toward the default.
4. Run `LANES_NO_CACHE=1 python3 skills/workflow-regression/scripts/regression.py run land --reuse --tier goal` in a clean checkout of a feature branch.
   Expect: the first planner line (after any `SKIP <id>: draft` or `covered` lines) is `PLAN_CACHE: off (LANES_NO_CACHE=1)` and the rest of the output is what it was before the cache existed.
5. Done line 5 says "every script stays under 18 KB", but 27 scripts were already over 18,432 bytes before this goal, so it is read as: no script grows past its current size, and tiers.py and narrow.py (the two this goal edits that were under it) stay under 18,432. Run `wc -c skills/workflow-regression/scripts/tiers.py skills/workflow-regression/scripts/narrow.py skills/workflow-regression/scripts/lanes.py`.
   Expect: tiers.py and narrow.py under 18432 and lanes.py at most 19559. If you meant every script under 18 KB, that is a different goal.

## Closes

Closes #710.

## Deferred

- Merge the three `git status` calls of a plan into one.
- A persisted cache for the non-tier `lanes.plan` path.
- A health rule on planning seconds.
- One `lanes.dirty` per plan.
- A `git check-ignore` error, or a stray ignored file under a walked folder (for example `.DS_Store`), permanently stops the cache from saving on such a repo.
- The golden-versus-v0.27.6 proof prints SKIP on a shallow clone (a failure under `STRICT=1`).
