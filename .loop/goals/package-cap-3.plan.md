# Plan: package-cap-3

Goal file: .loop/goals/package-cap-3.md (done lines frozen). Design: .loop/goals/package-cap-3.design.md.

## Implementation plan

Already built on branch loop/package-cap-3 before this step (commits a1ac5aa4, 569eaf6e and the design commit); the plan
is reviewed against the real diff (`git diff origin/main...HEAD`).

1. Fold the four skill-local portlock.py copies into existing modules: slots.py, lanekit.py (guards.py and lane.py use
   `lanekit.fcntl`), session_bind.py (sessions.py imports `fcntl` from it) and update.py; lanes.py imports it from slots.py.
   Behaviour on POSIX is `import fcntl`, unchanged; on Windows the same msvcrt byte-range lock, now in 20 lines.
2. Keep every script under 20 KB and inside the row budgets (sessions.py 19800, lanes.py 19710): docstring wording only.
3. Add `automation` to listing.json commands.
4. Make rows narrow again: reword reap.sh's comment (it named test-guard-enforce.sh, which made every row depend on it),
   declare the folder reads of test-adopt-fixtures, test-pods, test-prep-budget, test-push-guard, test-setup-adopt and
   test-portlock, and declare entry.py instead of skills/ in test-settings-table.sh.
5. test-defect.sh `real()` copies .github; workflow-docs SKILL.md goes under 150 lines by moving the automation registry
   and audit detail to references/commands.md (no content lost).
6. Add dev/toy/test-portlock.sh and rows portlock-fallback and package-passes (seen failing under a planted break).
7. Remove KNOWN entries for defect-categories, lanes-headers, lanes-repo-narrow, narrow-root-172, prd-repo-green,
   plan-sizes, pods-size, sync-check-preview, sync-board-lag, skill-size-116 and adopt-set-3/4/5. size-140 stays KNOWN
   (docs.py belongs to render-readme-guard), handed to the operation session.

Verification: dev/package.py PASS 99 files; lanes_cli.py check clean; each named row run by id; test-portlock; the lane.
