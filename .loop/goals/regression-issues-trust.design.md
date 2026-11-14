# Design: regression-issues-trust

**Problem.** (1) A failing row can hold several open issues: package-passes has #2596, #3119 and #3700, stop-tree-step-limit
two, portlock-fallback three, 423 rows in all (1,948 extra open issues). (2) #2614: `regression.py run` writes issues
whenever GH_TOKEN or GITHUB_TOKEN is set; GRD-5 and REG-5 want an explicit `--live`.

**Why the older copies were missed.** Three causes, found by running both writers on an in-memory gh:
- The workflow's issue read was `gh issue list --limit 1000` until 64036576 (paged `gh api` now), so once 1,000 newer issues
  existed, the older copies were invisible and each run opened another. That is how #3700 came after #3119 and #2596.
- The local writer (`runs.sync_issues`) picks the first open issue of a newest-first list, so it works on the newest copy,
  and closes no duplicate when the row still fails.
- The workflow picks "the oldest not-skipped-only" issue, not the oldest, and closes at most 20 duplicates a run
  (a rate-limit guard), so a 2,000-copy backlog drains slowly (the cleanup dispatch closes 600).

**Approaches.** (a) Leave the readers and cap, only add --live. (b) Make both writers pick the oldest open issue, close
newer open copies as duplicates, and gate every write on `--live`. Chosen: (b); the cap and the cleanup dispatch stay.

**Done lines.** Two open issues for a failing row: a run leaves one open (the oldest), for the workflow block and for the
local run. A token with no `--live`: no write (WOULD lines) in both. The workflow step passes `--live`.
Python toy `dev/toy/test-regression-issues.py` (Windows ok) holds both; four rows seen red.

**Open questions.** None. actions.py stays under 20,480 bytes (20,156 now); #3792 and #3793 touch the same scripts, so main is merged before the PR.
