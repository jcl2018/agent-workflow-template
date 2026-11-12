# Design: goal-adopt

## Problem

A goal started on another machine (the Mac) has its branch `loop/<slug>` and pull request on origin, but its run record
lives in that machine's `.git/loop/runs/`, so this machine has no state: `goal.py pr` and `merge.py` refuse, and
`goal.py new --here` cannot be used because it rewrites the goal file and, when the file is unchanged, commits nothing.
Issue #2851.

## Approaches

1. **New module `adopt.py`.** Clean, but the package is at its 99-file cap (`dev/package.py` MAX_FILES), so a new file
   fails the package check unless another file is folded. goal.py, guards.py, flow.py, role.py and lane.py are each within
   a few bytes of the 20,480-byte script cap.
2. **`fit.cmd_adopt(g, args)` plus a one-line `adopt` subcommand in goal.py.** fit.py already holds goal.py's overflow
   (`cmd_queue`, `cmd_set`, `frozen_fields`) and has about 1,500 bytes of room. Cost: the code must be compact, and goal.py
   must free about 80 bytes for the parser line.

## Choice

Approach 2. It adds no file, follows the existing split, and reuses `frozen_fields`, `guards.stamp` and `pods.stamp`.

`goal.py adopt <slug>` (a worker command, run from the goal's worktree on branch `loop/<slug>`):

- Refuses a bad slug, an existing run record, a branch that is not on origin (`git ls-remote --exit-code --heads origin`),
  a current branch other than `loop/<slug>`, a worktree HEAD that does not contain `origin/loop/<slug>`, and a goal file
  with no done lines.
- Reads the frozen goal file (title, touches, done lines) and the open PR (`gh pr view`), and creates the run record with
  the same fields `new` writes, `step` qa, `pr` set to the PR url.
- Marks idea, plan and review `done on another machine: <sha>` with the evidence (the branch tip, the commit count, the
  goal commit). It never marks qa, ship or pr done: qa runs again here (ship follows qa in the flow order), then `pr`.
- Logs one line saying where it was adopted from.

## Done lines

1. A run record at step qa, with the PR url and the frozen done lines; `goal.py pr` and `merge.py` then work for it.
2. Refuses a branch not on origin; qa and pr are never marked done from another machine's evidence.

Both are proved by `dev/toy` tests that run adopt against a bare origin repo.

## Open questions

- The goal text says "marks idea through ship"; the done line says qa is never marked done from another machine. ship
  follows qa and `pr` refuses until every flow step is done, so ship is left to run here too. Recorded as the recommended
  answer.
- A handover that calls an unpushed branch pushed: out of scope here beyond adopt's own check; the issue stays open for it.

DEPTH: condensed
