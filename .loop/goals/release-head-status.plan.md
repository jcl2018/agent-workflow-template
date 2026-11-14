# Plan: release-head-status (#3870)

Checked against the code: `autorelease.release_statuses` (called by `merge.advance` before `gh pr merge`), `push_release_commit`
(the release commit holds exactly the version file and CHANGELOG.md on top of origin/<base>), `goal.py pr` (sets
`state["statuses"] = "ok"` after the lane passed and the statuses posted), `private.pr_result` (posts, and for failure only
for a head on the remote), `regression.py run` (prints `FAIL id` per failed row; exits 1 for failed OR unproven rows).

## Build steps
1. autorelease.py: `carried()` (statuses ok and diff of head against its parent within {version_file, CHANGELOG.md}); `lane_at()`
   (the lane in a detached copy, output captured); `release_statuses()` posts success on a carry, failure only for rows that
   printed `FAIL`, nothing when no row ran and failed (state release_status untested), and records `release_status_why`;
   `status_held()` refuses with RELEASE_STATUS_FAILED / RELEASE_STATUS_UNTESTED naming the cause.
2. merge.py: one call, `autorelease.status_held`, in the RELEASE_PR_BLOCKED path before the owner-merge refusal; docstring line;
   stay under 20,480 bytes.
3. Test: dev/toy/test-release-head-status.py (Python), row release-head-status (defect, link #3870), seen red against main's scripts.

## Test per done line
- Bump-only head carries the pass: toy checks 1-3 (carried with no lane; not carried without a recorded pass; not carried when other files move).
- A real failure names its rows: toy checks 4-5. Never a failure for an untested head: toy checks 6-8.

## What could break
- A repo whose goal lane posted no statuses (`statuses` absent): falls back to running the lane, as before.
- The shell toy test-statuses.sh `release` section: same outputs (success without FAIL lines, failure with them); it skips on
  native Windows, so its run is owed on the Mac.

## Out of scope
- thermis itself (needs workflow-setup update); the lane's behaviour in a fresh copy without dependencies.

DEPTH: full
