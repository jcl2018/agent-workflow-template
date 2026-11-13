# fast-merge-queue: design

## Problem
The pr queue (#3877, pr-queue) merges one goal at a time and reruns every row whose inputs changed since it last ran, so each goal waits for every goal ahead of it and for rows main alone changed.

## Approaches
1. A new scheduler script that owns all three: a big rewrite across guarded scripts that are at their size budget.
2. Three small, separate changes on the existing seams: tiers.reason (the row selection), pool.pr_turn (the queue, via a new prqueue.py), and a new wiki.py batch (a command, not in the lane path). Chosen.

## Chosen
2. Affected-only rerun: a row only main's new commits reach keeps its earlier result unless the goal's own diff reaches it. Parallel: a goal waits only for an earlier goal whose touches overlap (no touches overlaps all); merge.lock is unchanged. Batch: wiki.py batch groups ready goals with disjoint touches (3, at most 4), verifies them on one combined tree, bisects a failure to name the culprit, and merges only with --merge, through merge.py.

## Done lines
Met by dev/toy/test-rerun-both.py, test-pr-parallel.py and test-merge-batch.py and their rows, each seen failing.

## Open questions
The Delivery, Monitoring and Regression pages need the owner's un-review for DEL-15 and the sub-bullets; drafted in DECISIONS.md.
