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
