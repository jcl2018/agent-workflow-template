# Plan: stale-net-diff

Checked: `problems()` in skills/workflow-docs/scripts/docs.py builds `skip` from the page's commits, the base and the merged
parents, and lists `changed` through `counting.real`; `git()` returns stdout.

## Build steps

1. `netless(root, judged, mine)` in docs.py: newest judged commit by date, `git diff --name-only <tip> HEAD -- <paths>`.
2. `problems()` skips the STALE line when `netless` is true.
3. Documentation's `check` Usage says so.
4. dev/stale_net_check.py (Python, runs on Windows) and the row `stale-net-diff-revert`, seen red against main's docs.py.

## What could break

A page whose newest judged commit is not an ancestor-equivalent of the others: its net diff is then nonempty, which keeps
today's STALE (never hides a change). docs.py stays under 20,480 bytes (18.4 KB).

## Out of scope

The second comment on the issue (a page still true after a mapped change).
