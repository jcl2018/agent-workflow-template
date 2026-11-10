# Implement the owner-approved Delivery PRD: review depth fits the goal, releases bump patch by default, goals resume from their last step, budgets show on the board, and nothing private ships (owner, 2026-11-10: "Delivery page is okay, so you can queue another goal to implement this")

- Slug: delivery-prd
- Touches: skills/workflow-delivery, skills/workflow-release, skills/workflow-monitoring, dev/toy, .loop/regression.tsv, docs/wiki/Delivery.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. DEL-6: small goals (up to 3 done lines, one skill) run a condensed plan and review, larger goals run full, the owner can override per goal, and every goal still runs its full test lane (merged in from depth-by-size)
2. DEL-5: the release bump is patch unless the goal says minor or major, so an "ask" never becomes a major bump (issue 170), and a release on a protected main goes through a PR instead of a direct push (issue 154)
3. DEL-7: a stopped or crashed goal resumes from its last recorded step, shown by a test that kills a goal mid-step and resumes it
4. DEL-8: each goal carries a time and token budget and the board flags a goal over either
5. DEL-9: goal.py pr and merge.py refuse to push when the private-name scan finds a match
6. Each of DEL-5..DEL-9 has a regression row seen failing then passing, and the Delivery page Tests table lists them
7. Issues 38, 117, 129 and 134 are fixed, each with a defect row seen failing then passing (owner-approved issue mapping 2026-11-10)

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
