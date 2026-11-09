# Design: stale-groups (issue 89)

Status: APPROVED (recommended answers taken; owner approves nothing here, the PR is the gate)

## Problem
Release and Milestones stopped being feature groups, and Documentation replaced "Criteria and tests", but leftovers remain. Done lines 1-4 of `.loop/goals/stale-groups.md` are frozen and are met as written.

## Findings (from the repo)
Removed group names that are real leftovers:
- `skills/design-guide.md:19` names the docs feature "Criteria and tests"; line 52 mentions milestones as a feature-level concept to check.
- `docs/ROADMAP.md:47` lists "Release" among the wiki pages.
- `.loop/docs.tsv`: the Delivery row has `skills/workflow-release`, and Documentation carries `milestone.py` and `dev/toy/fakegh`. These are file paths, not group names, so they get checked, not blindly removed.
- `.loop/regression.tsv` rows 13-15 (`cut-needs-verify`, `cut-draft`, `batch-cut-user`) call `test-rows.sh REL-1..3`, criteria of the removed Release group.
- GitHub milestones `Release` (8) and `Milestones` (5): both 0 open issues. Open issue 89 itself has no milestone.

Not leftovers (must NOT be flagged): "release" as a delivery step, `workflow-release`, `DEL-5`, README "Release the work", and the CHANGELOG. The defect test must separate a group name from the step.

## Premises
1. The allowed group set is exactly Delivery, Monitoring, Documentation, Regression, Health, Setup, plus Backlog. It matches the wiki pages and the docs.tsv pages.
2. The release step stays in the loop under Delivery, so only group usage is removed.
3. Milestone closure is a GitHub-side action and needs the owner's `gh` access.

## Approaches
- A (minimal): hand-edit the named files, close the milestones, add a grep test. Fast, but the test is a loose grep.
- B (recommended): A, plus the test derives the allowed set from `.loop/docs.tsv` page names (minus Home) plus Backlog. It checks the four surfaces for any group-like name outside the set: wiki page titles and headings, the `.loop/docs.tsv` pages, the board's group list and the `milestone.py` list (run against `dev/toy/fakegh`), and the design-guide parts table. The step word "release" is allowlisted by context (skill names, step lists). Moderate effort, and it won't go stale when a group is added.
- C (ideal): make one group list the single source of truth that the board, milestone.py and docs all read. This is a larger refactor and out of scope.

Recommendation: B.

## Plan (for the plan step)
1. Edit `design-guide.md` ("Criteria and tests" becomes Documentation), `ROADMAP.md`, `loop-files.md` and README where they name a removed group. Check `docs.tsv` and drop only entries that name a group, not a real path.
2. Relink rows 13-15 in `regression.tsv`. If REL-1..3 still exist in a wiki page, link the rows to the Delivery criterion that proves them, else retire them with a reason. This depends on what `test-rows.sh` and the Delivery page currently hold, so check before choosing.
3. Make `board.py` and `milestone.py` take their group list from `.loop/docs.tsv` and Backlog only. Verify with `dev/toy` (fakegh seeded with Release and Milestones must not appear).
4. Add `dev/toy/test-stale-groups.sh` and a regression row with category `defect` and link to issue 89. Show it failing on the base commit and passing now, then record `seen_red`.
5. Run `docs check` and health. Both must stay green.
6. After merge, the owner closes milestones `Release` and `Milestones` (0 open issues, nothing to move) and issue 89.

## Risks
- The grep test can false-positive on the release step and hit CHANGELOG history, so it is scoped to the named surfaces with an allowlist.
- Retiring REL rows could hide a real untested criterion, so each retirement carries a reason.

## Assignment
Run the new test against the base commit and confirm it fails there.
