# Design: stale-net-diff

## Problem

`docs.py check` marks a page STALE when any commit since the page's last commit touched its mapped paths (after the
block-only filter). An add and its revert, or a branch that nets to the same files, still counts, so workers squash
branches or make cosmetic page edits to clear a page they cannot edit (#3771).

## Approaches

1. Replace the commit count with a net diff from the page's last commit to HEAD. Wrong on a branch: the base's own newer
   changes (judged in their own goals) would then count against the branch.
2. Keep the commit filter and add a net check against the newest commit already judged (the page's, the base's or a
   merged one): when the mapped paths read the same at HEAD as there, the page is not STALE. Conservative: any difference
   keeps today's STALE.

## Chosen

Approach 2, `netless()` in docs.py. The issue's second comment (a mapped change that leaves the page true) needs a
judgement of content, not paths; it is out of scope and stays on the issue.

## What the done line needs

Row `stale-net-diff-revert` (dev/stale_net_check.py): a scratch repo where a change is added and reverted reads not STALE
with and without `--base`, and a real change reads STALE.

## Open questions

None.
