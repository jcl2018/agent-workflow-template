# A goal's pr step never spends one of its 3 tries on something that is not the goal's fault: a merge conflict caused only by main moving (generated pages and appended rows) is resolved and retried without spending a try, a lane killed from outside is rerun without spending one, and finding text never carries absolute paths (from issue-cleanup's triage; seen repeatedly on 2026-11-11 when guard-enforce-red burned all 3 tries to a moving main)

- Slug: goal-pr-try-budget
- Touches: skills/workflow-delivery/scripts, dev/toy, .loop/regression.tsv, docs/wiki/Delivery.md, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. a toy goal whose only conflict is a re-rendered Tests page or appended regression rows retries pr without spending a try
2. a lane stopped by SIGTERM from outside reruns without spending a try; a real failure still spends one
3. finding and report text written by goal.py carries no absolute path
4. no new file under skills/

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
