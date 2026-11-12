# skills/workflow-delivery/scripts/private.py is back under the 20,480-byte script cap (it is 21,767 bytes on main since goal-pr-try-budget, v0.27.28) by moving a self-contained part unchanged into an existing delivery module, with no behaviour change, and goal.py (20,475 bytes, 5 under) gets headroom the same way

- Slug: private-size
- Touches: skills/workflow-delivery/scripts, dev/toy, .loop/regression.tsv, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. every skills/ script is at or under 20,480 bytes on main and the size check row passes
2. the delivery toy tests that cover the moved code still pass unchanged
3. no new file under skills/ (the package stays at 99)

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
