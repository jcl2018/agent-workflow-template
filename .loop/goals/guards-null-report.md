# A goal reset never writes a null report, and the goal state file is written under a lock so two writers cannot interleave (follow-ups named in PR #1092)

- Slug: guards-null-report
- Touches: skills/workflow-delivery/scripts, dev/toy, .loop/regression.tsv, docs/wiki/Delivery.md, docs/wiki/Tests.md, skills/workflow-monitoring/scripts/session_bind.py, skills/workflow-monitoring/scripts/mend.py

## Done lines

Frozen. A wrong done line needs a new goal.

1. a goal reset leaves report as an empty record, proven by a toy test
2. two concurrent writers to one goal state file never lose either write, proven by a toy test
3. no new file under skills/

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
