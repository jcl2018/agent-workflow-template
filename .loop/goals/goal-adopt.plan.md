# Plan: goal-adopt

Checked against the code: `goal.py` has `cmd_new`, `state_path`, `done_lines`, `done_sha`, `valid` and `main()` with `add(...)`;
`fit.py` holds `frozen_fields(g, args, lines, touches)`, `cmd_queue(g, args)` and `keep`; `guards.stamp(state, step)` and
`pods.stamp(state)` exist; `cmd_pr` and `merge.py` read `state["flow"]` (values must start with `done` or `skipped`),
`state["branch"]`, `done_sha`, `pr`. Sizes (LF): goal.py 20,465 of 20,480, fit.py 18,980. The package holds 99 of 99 files.

## Build steps

1. `fit.cmd_adopt(g, args)` in fit.py, at most about 1,300 bytes. In order: bad slug; an existing run record; branch
   `loop/<slug>` must be the current branch; `git ls-remote --exit-code --heads origin loop/<slug>` must succeed (else
   `REFUSED ... not on origin`); `origin/loop/<slug>` must be an ancestor of HEAD; read the goal file (first line is the
   title, `- Touches:` the touches, `g.done_lines` the done lines; none means refuse); `gh pr view` for the url (none means
   refuse). Build the record with the fields `new` writes, `step: "qa"`, `pr` the url, `flow` idea, plan and review each
   `done on another machine: <short sha>`, `guards.stamp` and `pods.stamp`, one log line with the origin sha, commit count
   and PR. `qa`, `ship` and `pr` are left unrecorded.
2. goal.py: one `add("adopt", ...)` line calling `fit.cmd_adopt`, and 80 bytes freed elsewhere in goal.py (a docstring
   or comment, no behaviour) to stay under 20,480.
3. `dev/toy/test-goal-adopt.sh` (reads: goal.py fit.py): builds a toy repo with a bare origin, a goal branch pushed with a
   goal file, a fake PR, then runs adopt with no run record.
4. Regression rows in `.loop/regression.tsv`: `adopt-record-qa` (done line 1) and `adopt-refuses-unpushed` (done line 2),
   both seen red with `regression.py red` against a copy where adopt is removed; requirement DEL-10 and DEL-11 on
   docs/wiki/Delivery.md (Unreviewed), a Usage entry for `goal.py adopt`; `docs.py render`, then `docs.py audit`.
5. Verify by hand in the goal file; commit each step.

## Tests per done line

1. `adopt-record-qa`: after adopt on a pushed branch with a PR, the run record has `step` qa, the PR url, idea, plan and
   review recorded `done on another machine`, and `goal.py pr` no longer refuses with "no goal named" (it stops at "the
   flow hasn't finished: qa, ship").
2. `adopt-refuses-unpushed`: a branch not on origin is refused with a one-line reason and no record is written; qa, ship
   and pr stay unrecorded in the adopted record of the first test.

## What could break

- goal.py over the 20,480-byte script cap (checked by `dev/package.py`).
- The package file count: no file is added.
- A record whose `worktree` is wrong: set from `root()`.
- `pr` merging origin/main, which can conflict: that is the normal pr path.
- Windows: `ls-remote` and `gh` calls use list arguments, no shell.

## Out of scope

- Handover tooling that calls an unpushed branch pushed (stays in issue #2851).
- Resuming a Mac goal that has an unpushed branch.
- Copying a Mac's run records.

