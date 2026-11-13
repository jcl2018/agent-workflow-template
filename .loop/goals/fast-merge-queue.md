# The pr queue merges as fast as it safely can: affected-only reruns, parallel lanes for goals with disjoint files, and batch merges (DEL-14)

- Slug: fast-merge-queue
- Touches: skills/workflow-delivery, skills/workflow-release, skills/workflow-monitoring, docs, dev/toy, .loop/regression.tsv

## Done lines

Frozen. A wrong done line needs a new goal.

1. A toy shows a main-moved rerun running only rows touched by both the goal's diff and main's new commits; two goals with disjoint touches run lanes at once while overlapping ones wait; and a batch of 3 passing PRs merges together while a failing batch splits to name the culprit

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
