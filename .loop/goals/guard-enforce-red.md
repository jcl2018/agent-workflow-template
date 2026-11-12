# test-guard-enforce passes on main again: its 7 checks that fail identically on main (reported by the milestone-freeform worker, 2026-11-11) are traced to either a test that drifted from the guard or a guard that regressed, and the one that is wrong is fixed

- Slug: guard-enforce-red
- Touches: dev/toy/test-guard-enforce.sh, skills/workflow-delivery/scripts, .loop/regression.tsv, docs/wiki/Delivery.md, docs/wiki/Tests.md, docs/wiki/Health.md, docs/wiki/Setup.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. test-guard-enforce passes on main with every check, and each fix names whether the test or the code was wrong
2. a guard behaviour that regressed gets its own failing-then-passing row
3. no other row changes result

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
