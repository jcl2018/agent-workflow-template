# dev/toy/test-board.sh passes on main again: its three failing rows are traced to either drifted test text or a lost phrase in the operation guide, and the wrong side is fixed

- Slug: board-test-fix
- Touches: dev/toy/test-board.sh, skills/workflow-monitoring/references, skills/workflow-monitoring/scripts/watch.py, .loop/regression.tsv, docs/wiki/Monitoring.md, docs/wiki/Tests.md, docs/wiki/Guardrails.md, .loop/regression-known.tsv

## Done lines

Frozen. A wrong done line needs a new goal.

1. test-board.sh passes in full on main
2. each fix names whether the test or the guide was wrong
3. no new file under skills/

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
