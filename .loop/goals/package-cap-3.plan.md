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

## Review record

Autoplan was skipped: its guard hook cannot be used from this session (the transcript carries a stray snapshot init from
an earlier goal), so the operation chose the fallback: a strategy review and an engineering review, each run by a separate
subagent over the real diff. No DX scope (no new command or flag).

- Strategy review: 2 High, 1 Low. (High) The known list had been emptied by a truncating write; restored from main and only
  the 13 entries this goal fixes removed (size-140 stays, docs.py belongs to render-readme-guard). (High) The same cause
  removed six unrelated entries: restored. (Low) package-passes failed where Python had written __pycache__: the row now
  runs on a clean `git archive` copy with PYTHONDONTWRITEBYTECODE=1.
- Engineering review: 2 Medium, 3 Low. (Medium) The wiki said locks go through portlock.py: reworded in Regression and
  Monitoring. (Medium) Moved SKILL.md text sits under a "Moved from SKILL.md" heading in commands.md: kept, the SKILL.md
  pointers name the file. (Low) test-portlock exercises the four host modules, not the re-exporting importers; the
  importers are plain assignments proved by importing every changed script and by the lane. (Low) The blocking retry path is
  as the deleted portlock.py had it, uncovered there too. (Low) the `# reads: skills/` header is wide on purpose.
- The shim's semantics were compared with the deleted portlock.py by both reviewers: lock, unlock (a no-op when not held),
  LOCK_NB's BlockingIOError, the 50 ms poll and the restored file position are the same; only the error text is shorter.
