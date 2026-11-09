# Fix issue 89: remove every leftover of the removed feature groups (Release, Milestones, the old Criteria and tests name)

- Slug: stale-groups
- Touches: docs/wiki, skills/design-guide.md, skills/loop-files.md, README.md, .loop/regression.tsv, .loop/docs.tsv, skills/workflow-health/scripts/milestone.py, skills/workflow-monitoring/scripts/board.py, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. Only the feature groups Delivery, Monitoring, Documentation, Regression, Health and Setup, plus Backlog, appear in the wiki, README, skill files, .loop/docs.tsv, the board and the milestone list; the GitHub milestones Release and Milestones are closed with their issues moved to the matching feature or Backlog
2. Regression rows that pointed at removed Release criteria are relinked to the criterion they prove now, or retired with a reason
3. A defect test linked to issue 89 fails if a removed group name comes back in those places, seen failing once and passing now, and issue 89 closes when this merges
4. docs check and health stay green

## Verify by hand

1. Run `bash dev/toy/test-stale-groups.sh`.
   Expect: it prints `PASS: no removed feature group comes back`.
2. Run `python3 skills/workflow-health/scripts/milestone.py features`.
   Expect: only Delivery, Documentation, Health, Monitoring, Regression and Setup are listed.
3. Open the repo's Milestones page on GitHub.
   Expect: Release and Milestones are closed; Delivery, Documentation, Health, Monitoring, Regression, Setup and Backlog are open.
4. Run `grep -n "Criteria and tests" skills/design-guide.md`.
   Expect: no output.
