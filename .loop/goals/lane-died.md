# A goal's lane is never killed by another session's work: on 2026-11-12 two pr lanes (guards-null-report, docs-small-fixes) ended LANE_DIED mid-run with only PASS lines, costing tries, while many lanes and scheduled suites ran at once (issue 435 was closed as a suspected cross-lane reap); the killer is found (a reap, a pkill pattern, a process-group kill, a timeout, memory) and fixed, and a lane that dies without a failing row never counts as a try

- Slug: lane-died
- Touches: skills/workflow-delivery/scripts/lane.py, skills/workflow-delivery/scripts/lanekit.py, skills/workflow-regression/scripts/regression.py, dev/toy, .loop/regression.tsv, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. the killer is named with evidence and a toy test reproduces it, seen failing on main and passing on the fix
2. a lane killed from outside reports LANE_DIED with the signal and does not consume a try
3. no new file under skills/

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
