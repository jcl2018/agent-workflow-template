# graph-times design

## Problem
The check-in's Dependencies (checkin.py, MON-5/MON-14) lists bare goal ids: no time left, no arrows for waits, a stray record
with only a slug, stopped and left goals, and goals held at pr shown as stuck.

## Approaches
1. Rewrite the section with a new layout (cost: high; risk: breaks the reply hook's per-repo slug check and the layout check).
2. Keep board_lines.render for the boxes and add lines under each repo block: one `a -> b` per wait, one `slug ~time left` per
   goal with an estimate, and an `expected finish` line (cost: low; risk: checkin.py size, 15,968 of 19,000 bytes).

## Chosen
Approach 2. Time left is `board_status.left_time` (the MON-4 estimate); the finish is now plus the largest time left in the
block. `shown()` drops records with no goal or status, stopped goals and `release: leave` goals. `mood()` calls a silent
worker at step pr `held`, so it draws [=] holding. No file is added under skills/.

## Done line
Live goals only, each with its time left, every wait an arrow, each repo block ends with its expected finish: needs shown,
mood, the arrow lines, the time lines and the finish line; dev/toy/test-graph-times.py checks each, seen red.

## Open
The stray `g.json` comes from a toy writing into the real common dir (release-head-status's test-release-head-status.py,
release_statuses saves the run it is given by slug); that branch is another goal's. The MON-14 wording waits in DECISIONS.md.
