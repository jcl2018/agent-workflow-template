# Design: operate-fit

Status: APPROVED (office-hours, non-interactive; recommended answer taken at every question)
Goal: `.loop/goals/operate-fit.md` (done lines frozen)
Mode: builder/intrapreneurship, small change to an existing tool. No new surface.

## Problem

`operate.py run` prints the status block from `board_status.py`. Compared with wiki MON-4 ("Needs you first, then the roadmap as a
dependency graph ... then Goals") the block lies or over-shows in four ways:

1. **Stale Needs you.** `board_status.sections` adds `- slug (wiki not published)` whenever `run["wiki_error"]` is set, whatever
   the goal's state afterwards. `wiki.py publish` pops the key on success, but a record that was never re-published, or a goal
   that has since merged, keeps the line forever. `release_error` has the same shape.
2. **Merged shows as awaiting merge.** `graph.merged(run)` trusts only the run record (`release` in merged/cut, or the worker's
   report status). `board.py` already asks GitHub (`pr_state`, via `gh pr view`) for the board page, but the status block never
   does, so a PR merged by hand on GitHub reads `[awaiting merge]` and its dependants read "waits on".
3. **Roadmap is not the live graph.** `status_graph.render_text` draws every goal, merged ones included, with an 8-cell bar,
   then `features()` and milestone bars are appended. MON-4 and done line 3 want: live goals only (running, queued, waiting),
   arrows for depends-on, stage, a **10-cell** bar, time left, then the longest-path total with a **finish time**; merged goals
   collapse to one line of PR numbers.
4. **Quiet pass is not always one line.** `operate.one_pass` prints one line only when `board.py` emits `NO_CHANGE`, and that
   line is emitted only when `doc["open"] and doc["next_at"]`. With cadence off, or nothing open, a no-change pass falls through
   and prints the whole block again.

## Premises (all accepted)

1. The fix belongs in the existing renderers, not a new one: `board_status.py` + `status_graph.py` stay the single source for
   report, board, dashboard and operate (the board and artifact page embed the same fragment).
2. GitHub is the authority on "merged"; the run record is a cache. A failed or unknown `gh` answer must never flip a goal to
   merged (same rule `board.py` uses: unknown keeps the old state).
3. "Open" for an error means: goal not merged AND no later successful publish/release. Merged clears `wiki_error`, per done line 1.
4. No new run-record fields are needed to meet the lines; derive from what is already stored.

## Approaches

- **A. Minimal, patch in place (recommended).** Keep the file layout. Add one `merged_on_github(run)` helper (reads
  `run["pr"]`, calls the same `gh pr view --json state` as `board.pr_state`, returns False on any doubt); thread an
  `effective merged` flag through `board_status.sections`. Filter Needs you with it. Change `status_graph` bar width to 10 and
  have `render_text` take only live nodes. Add a `merged_line` (`merged: #71, #72, #77`) and a finish-time suffix to `total`.
  Make `operate.one_pass` print exactly one line whenever `CHANGED no` and not first, whatever the cadence. Effort S-M, risk low.
- **B. Cache GitHub state on the run record.** `board.py` writes `prstate` into the record; `board_status` reads it. Cheaper at
  render time but adds a writer to a read path and goes stale between passes. Rejected: more moving parts, same result.
- **C. Rewrite the status as a new module.** Cleaner long-term, but breaks the "one block, many surfaces" contract and the
  existing `test-status-graph.sh`. Rejected as out of scope.

**Recommendation: A.**

## Design (approach A)

### `board_status.py`
- `merged_now(run)`: `graph.merged(run)` or (`run["pr"]` set and status `done` and `gh pr view` says MERGED). `gh` timeout
  20s as in `board.py`, one call per done-and-unmerged run per render; any error or non-MERGED answer returns False.
  Takes an injectable lookup so the toy test can run offline (the fake `gh` already honours `FAKE_GH_PR_STATE`).
- Needs you: skip `wiki_error` / `release_error` when `merged_now(run)` or when the record carries a publish stamp newer than the
  error (use `wiki.py`'s existing `wiki published` log entry as the "later publish" signal; if absent, merged is the only clear).
  Waiting/failed/stopped asks are unchanged and still always shown (MON-4 last sentence).
- "waiting to merge" under-lines and the `awaiting merge` mark use `merged_now`, so a GitHub-merged goal is `merged`.
- Roadmap: build `items` for live goals only; collect merged goals' PR numbers (parse the trailing `/pull/N` of `run["pr"]`)
  into one line. Drop `features()` and the milestone bars from the Roadmap section (they are not in the done lines; milestones
  remain on the board page). Dependencies on a merged goal are dropped from the arrows (merged goals are not drawn).

### `status_graph.py`
- `STAGES` for the bar becomes 10 cells; stage numbers map 1..7 steps onto 10 cells by `round(10 * stage / len(STEPS))`, and
  "x of N" text uses the step count, not the cell count.
- `render_text(items, under)` draws only the nodes handed in (caller passes live ones); each line keeps
  `<- waits on a, b`, the arrow carrying depends-on.
- `merged_line(prs)`: `merged: #71 #72 #77` or `(no merged goals yet)`.
- `total(items, at)` appends `, finish about HH:MM` (local clock) computed from `at + longest chain`; "no estimate yet" cases
  keep their current wording and print no finish time.

### `operate.py`
- `one_pass`: after `board.py board --since`, if not `first` and `CHANGED no`, print one line (`NO_CHANGE ...` if present, else a
  built `Nothing changed. <digest>.` from the `DIGEST` line) and never the block. The first pass and any changed pass print the
  full block as now.
- `signature`/change detection: add `wiki_error` and `release_error` presence to `board.FIELDS`-style state so clearing an
  error counts as a change (otherwise a cleared line would never be reprinted). Small edit in `board.py`'s `FIELDS`/`collect`
  row; `board_runs.py` and `graph.py` need only the touched-file list adjustments if their helpers are reused (`graph.merged`
  stays record-only; the GitHub check lives in `board_status`).

### `dev/toy`
- New `test-operate-fit.sh` (wired into whatever runs the other toy tests), using `make.sh`, `fakegh` and the pattern in
  `test-status-graph.sh`: a made-up mix of one record-merged goal, one GitHub-only-merged goal (`FAKE_GH_PR_STATE=MERGED`,
  record still `done`), one running, one queued with `depends-on`, one waiting, and one stale goal carrying an old `wiki_error`
  (a merged one and a re-published one). Asserts, one `check` per done line: stale errors absent from Needs you; GitHub-merged
  goal marked merged and not "awaiting merge"; roadmap lists only live goals with arrows, a 10-cell bar, time left, a total line
  with a finish time, and a one-line `merged:` PR list; a second `operate.py run --once` with nothing changed prints exactly
  one line.

## Risks
- `gh` latency per render: bounded by done-and-unmerged runs only; offline/unknown falls back to the record.
- Changing the bar width touches the board page, which embeds the fragment; `test-status-graph.sh` expectations on the 8-cell
  bar must be updated in the same change.
- Hiding a merged goal's `wiki_error` hides a real failed publish. Accepted because the done line says so; `workflow-health`
  still reports unmapped/stale wiki pages.

## Not in scope
Release/merge behaviour, milestone display, run-record schema, the board artifact page layout beyond the shared fragment.

## The Assignment
Run `operate.py run --once` against the toy repo after the build and compare its Needs you, Roadmap, and Total sections line by
line with MON-4.
