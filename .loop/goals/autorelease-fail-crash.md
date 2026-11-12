# merge.py's refusal path never crashes: autorelease.fail() handles a goal state with no report and prints the refusal with its fix line

- Slug: autorelease-fail-crash
- Touches: skills/workflow-release/scripts/autorelease.py, dev/toy, .loop/regression.tsv, docs/wiki/Delivery.md, docs/wiki/Tests.md, skills/workflow-release/scripts/wiki.py

## Done lines

Frozen. A wrong done line needs a new goal.

1. a toy test with a state lacking "report" gets the REFUSED line, exit non-zero, no traceback
2. existing release rows keep passing

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
