# Design: operate-fit-2

Status: shaped by office-hours with the recommended answer at every question. Nothing approved, merged or pushed.
The goal's done lines are frozen; this design meets them. Delivery fills in the goal's "Verify by hand".

## Problem

`board_status.py` builds the one status block that `operate` prints. Three things in it are still wrong:

1. **Stale wiki errors.** `wiki.py publish` pops `wiki_error` on success, but records that finished before that fix
   (or whose later publish was recorded only in the log) still carry `wiki_error`, so Needs you lists a wiki that is
   in fact published. `error_open` only drops an error when the goal is merged.
2. **Closed pull requests read as awaiting merge.** `github_merged` returns only true/false, so a PR GitHub reports
   CLOSED is indistinguishable from OPEN: the goal is `done`, not merged, and shows `[awaiting merge]` forever.
3. **Goals is a wall.** `goal_lines` prints done lines for every run, merged ones included, so the block grows without end.

## Premises (accepted)

- The fix is on the read side, in the status block. `wiki.py` and `status_graph.py` are outside this goal's Touches
  and stay unchanged; old records must be fixed by how they are read, not by rewriting them.
- A goal is "live" if it is running, waiting or queued. Merged and closed goals are history.
- "Since the last check-in" means since `operate` last printed a full block, not since the last git commit.

## Approach (recommended, taken)

### Done line 1: wiki errors leave Needs you

In `error_open(run, gone, marker)` add a second way an error closes, before the merged test: the run's log has a
`wiki published` entry after its last `wiki not published` entry (`wiki.py save` writes exactly those two phrases,
and a publish that finds nothing to change goes through the same success branch, so "no change" is covered). The
log scan already exists for the merged case, so this is one more `last(...)` comparison. A goal that is merged keeps
the current rule: an error logged before the merge is dropped, whether the merge is in the record or only on GitHub,
including old records with no log markers at all. Release errors keep their own marker and are untouched.

### Done line 2: closed pull requests read as closed

Replace `github_merged(url, cwd) -> bool` with `github_state(url, cwd) -> "MERGED" | "CLOSED" | "OPEN" | ""`
(same `gh pr view --json state`, same timeout, any doubt returns `""`). `merged_now` uses it for MERGED; a new
`closed_now` is true for a `done` run whose PR state is CLOSED and which is not merged by the record. Closed goals
are kept out of the dependency graph (`live`) so they never count as unfinished work in Total or as "no estimate yet".
They appear as one Roadmap line after the merged line, `closed without merging: #71, #72`, and the goal's block under
its own name reads `pull request closed without merging`, never `waiting to merge`. Dependents of a closed goal stay
blocked, as for any goal that is not merged. A run whose PR state is open or unknown keeps `[awaiting merge]`.

### Done line 3: Goals shows only live and newly merged goals

`goal_lines` is called only for runs that are running, waiting, queued (queued goals gain their done lines from
their goal file), or merged since the last check-in. Every other merged goal appears only in the merged line of
Roadmap. Closed goals are not listed under Goals.

"Since the last check-in": new command `board_runs.py checkin` writes `loop/checkin.json` `{"at": <now>}` (atomic
write, like the other run changes). `operate.py` calls it after it prints a full block (not after the one-line
"nothing changed" answer), so the next full block lists what merged in between. `board_status` reads the file; a
goal counts as merged since the check-in when its merge time (the stamp on its `merged` log entry, else the run's
`updated`) is after `at`. With no check-in file yet, every merged goal counts as new once, then the file exists.

### Done line 4: toy test

Extend `dev/toy/test-operate-fit.sh` (it already seeds stale errors and old merged goals; its `rec`, `gh`, `late`,
`fresh` runs stay as they are) with:

- a goal whose log has `wiki not published` then `wiki published` but whose record still holds `wiki_error`, unmerged;
- a goal with a CLOSED pull request and one with an OPEN one, plus two old merged goals and one merged after a
  seeded `checkin.json`;
- `dev/toy/fakegh/gh` learns per-PR state, `FAKE_GH_PR_STATE_<n>` overriding `FAKE_GH_PR_STATE`, so one run can mix
  MERGED, CLOSED and OPEN. This is the only change to the fake.

Checks, one per done line: the cleared-by-publish error is absent from Needs you; the closed goal reads closed and
not `awaiting merge` while the open one still does; Goals holds done lines for running, waiting, queued and the newly
merged goal only, with old merged slugs present in the merged line and absent from Goals. The existing
`test-operate.sh` and `test-wiki.sh` assertions stay green.

## Alternatives rejected

- **Fix the records / wiki.py:** cannot reach finished goals, and is outside Touches.
- **Add a `closed` mark in `status_graph.py`:** outside Touches, and closed goals do not belong in the graph anyway.
- **Time-window ("last 24h") instead of a check-in:** wrong for an operator who is away longer than the window.

## Risks

- `gh` calls per done run grow only if the state is fetched twice; `github_state` is called once per run and reused.
- A clock skew between `checkin.json` and log stamps could show a merged goal one extra time; harmless.
- `board_status.py` and `operate.py` stay under the 20 KB script cap (currently about 11 KB and 5 KB).
