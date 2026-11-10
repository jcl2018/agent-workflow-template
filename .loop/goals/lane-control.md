# Test lanes run safely side by side and never go stale after a merge (issues 150, 135, 152, 168, 151, 99)

- Slug: lane-control
- Touches: skills/workflow-regression, skills/workflow-delivery, dev/toy, .loop/regression.tsv, docs/wiki

## Done lines

Frozen. A wrong done line needs a new goal.

1. A machine-wide lane limit (a setting, default 2) makes an extra full lane wait its turn with a clear message instead of starting; flow.py and goal.py honor it (150)
2. Parallel red runs never race on .loop/regression.tsv (135)
3. A lane's latest result has one stable path, and a wait command blocks until it ends (152)
4. ship and pr rerun or refuse when HEAD moved since the lane they reuse (168)
5. Rerunning rows by id and merging main never leave the Tests tables stale for the next lane: the lane re-renders them first (151)
6. The operate-all test waits for the goal's report instead of a fixed sleep and passes 10 of 10 under load (99)
7. A toy test proves each, seen failing on the old code; the issues close when this merges

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
