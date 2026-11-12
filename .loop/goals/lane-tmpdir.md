# The regression lane's temp folder lives outside any git checkout, so tests that refuse to write inside a repo pass under the lane as they do when run directly, while REG-8's isolation stays

- Slug: lane-tmpdir
- Touches: skills/workflow-delivery/scripts/lane.py, skills/workflow-delivery/scripts/lanekit.py, skills/workflow-regression, dev/toy, .loop/regression.tsv, docs/wiki/Regression.md, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. TMPDIR for every lane points under the system temp directory, keyed by repo, goal and lane, never inside a git checkout, emptied at each lane start and removed after
2. A regression row whose test refuses to write inside a git checkout fails on the current lane and passes after the fix
3. REG-8's existing rows still pass, and two lanes of different goals never share a temp folder
4. lanekit.py copies stay identical where test-lane-control.sh checks them, every script stays under 20 KB and the package at 99 files or fewer

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
