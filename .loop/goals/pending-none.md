# A step reply's "PENDING: none" (or an empty PENDING line) never makes a goal wait on the owner; seen 2026-11-11 three times on other repositories' goals, each costing an operation round trip

- Slug: pending-none
- Touches: skills/workflow-delivery/scripts, dev/toy, .loop/regression.tsv, docs/wiki/Delivery.md, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. a toy goal whose step reply says "PENDING: none", "PENDING: nothing" or "PENDING:" records the step and goes on without waiting
2. a real PENDING item still waits exactly as before

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
