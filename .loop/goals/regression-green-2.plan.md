# Plan: regression-green-2

Checked against the code in this worktree: every file below exists, and the rows named exist once each in `.loop/regression.tsv`.

## Build steps (already on the branch; this rerun merges main and records the steps)

1. `dev/toy/tree-once.sh` (with `test-tree-once.sh`): run `test-tree.sh` once per CI job, replay output and exit code to the
   rows `lanes-headers`, `lanes-repo-narrow`, `one-way-to-run`, `prd-repo-green`; take over a lock left by a dead holder.
   Test was wrong (each row re-ran the whole tree), not the code.
2. `breaking-asks` (`test-release.sh`): the row asserted a major bump waits; code is right (a breaking commit becomes a patch),
   so the row's check was wrong. Fixed in the row.
3. `toy-no-leftovers` (`test-no-leftovers.sh`, `reap.py`): the test assumed this Mac's temp layout; reaps CI leftovers.
4. `skills/workflow-regression/scripts/actions.py` and `.github/workflows/regression.yml`: one open issue a row (oldest
   failure kept), at most 20 duplicates closed a run, stop at a rate-limit reply, nothing filed for a skipped row,
   `cleanup` dispatch closes duplicates, skipped-only issues and issues of removed rows, paced at 2 writes a close.
5. Docs: Regression, Automation, Documentation and Tests pages; `workflow-docs` SKILL.md kept under 150 lines.

## Test for each done line

1. Six rows pass: `breaking-asks`, `lanes-headers`, `lanes-repo-narrow`, `one-way-to-run`, `prd-repo-green`,
   `toy-no-leftovers` (rows exist, `tree-once-lock` guards the runner); the scheduled GitHub run is Verify by hand 1.
2. Test or code named: commits and `.loop/regression-known.tsv`; rows seen red with `red` dates.
3. Issues match failing rows: `test-automation-email.sh` cases for the keeper, quoted text, rewrite and rate-limit warning.

## What could break

- The merge unioned `.loop/regression.tsv` with main's new rows; a duplicate id would fail `sync` (checked: none).
- The CI `test-tree.sh` hang on Linux is not reproduced on Windows, where many toy tests skip.

## Out of scope

The hang's diagnosis (single-row dispatches on Linux, listed in the PR), and the other goals in the merge queue.
