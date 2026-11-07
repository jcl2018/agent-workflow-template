# Make the operation session govern only, and run POCs and goals in batches elsewhere

- Slug: operation-role
- Level: 1
- Touches: skills/workflow-monitoring, skills/workflow-delivery/SKILL.md, skills/loop-files.md, listing.json, dev/toy/test-batch.sh, .loop/config.json, .loop/regression.tsv, docs/wiki/Monitoring.md, docs/wiki/Delivery.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. A new self-contained scripts/batch.py in workflow-monitoring adds and starts a batch: queue lines may be poc or goal lines under a named batch heading, and each runs in its own session or background agent, never in the governing session
2. A POC runs read-only in its own worktree, saves its answer and go line to the loop folder outside the repo, and shows on the board as finished with that answer, and a goal line can be promoted from a saved POC
3. references/operation.md and both SKILL files state that the operation session is for governance only: it assigns and watches, and runs neither poc nor go itself
4. docs/wiki/Monitoring.md gains new criteria for these rules, marked (draft) for the owner's approval, each with a row in Enforced by and a real regression row seen failing once; the 30 approved criteria are not reworded
5. dev/toy/test-batch.sh proves each line above with a stand-in agent and is listed in checks, and every script stays under 20 KB
6. The repo checks pass

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->

## Design

## Plan
