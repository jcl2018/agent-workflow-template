# Design: regression-green-2

## Problem

The scheduled regression run on GitHub fails on six rows every time (breaking-asks, lanes-headers, lanes-repo-narrow,
one-way-to-run, prd-repo-green, toy-no-leftovers), and its workflow opens an issue per failing row on every run, so stale
issues pile up for rows that now pass. The branch (rebuilt on this PC from the first attempt's pushed work, merged with
current main) already holds the fixes; this rerun records them through the delivery steps.

## Approaches

1. Fix each row where it is wrong: change a test that assumes this Mac (breaking-asks, toy-no-leftovers, the narrow-lane
   rows), fix code only where a row exposes a real regression, and give the workflow a keeper rule (one open issue a row, the
   oldest failure kept, duplicates closed 20 at a time, a stop at a rate-limit reply, nothing filed for a skipped row) plus a
   by-hand `cleanup` run. Cost: touches tests, `actions.py` and the workflow. Risk: a test loosened too far; held by a
   failing-then-passing row for each code fix.
2. Mark the six rows known-failing and close the issues once. Cost: small. Risk: hides real failures and the issue flood
   returns on the next failure.

## Chosen

Approach 1. Each fix names whether the test or the code was wrong in its commit and in `.loop/regression-known.tsv` while
the fixing goals are unmerged; `tree-once.sh` runs the whole tree once per CI job and replays its output, and the workflow
issue rules live in `actions.py` with tests (`test-automation-email.sh`, `test-tree-once.sh`, `test-no-leftovers.sh`).

## What each done line needs

1. Six rows pass and nothing new fails: the row fixes above, checked by the next scheduled GitHub run (Verify by hand 1) and
   by the lane here on Windows where the rows are not skipped.
2. Test or code, named per fix: the commit messages and known-file reasons; a code regression gets a row seen red first
   (`regression.tsv` rows with `red` dates).
3. Open issues match the failing rows: the keeper and cleanup rules in `actions.py` (Verify by hand 2 and 3).

## Open questions

- The CI `test-tree.sh` hang (the job stalls on Linux) cannot be reproduced on this PC. Its diagnosis is the single-row
  dispatches listed in the PR under "Needs a Linux run".
- Merge order against board-test-fix, lanes-abs-path and package-hang: the operation session's queue decides.
