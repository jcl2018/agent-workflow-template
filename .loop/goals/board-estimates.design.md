# Design: board-estimates

Status: shaped by office-hours with the recommended answer at every question. Nothing approved, merged or pushed.
The goal's done lines are frozen; this design meets them. Delivery fills in the goal's "Verify by hand".

## Problem

Issue 93. On the live board (`live_board.py`, estimates from `board_status.py`):

- `left_time` gives the current step `max(0, median - spent)`. Once a step runs past its usual time that is 0, so the goal
  shows a time left that stops shrinking-then-lies, and the Finish line (`status_graph.chain` over each goal's `left`) stays
  frozen at "now + later steps" while the run is visibly late.
- Lines are not bounded: the header (repo, clock, version, health), the Running line, the 8-step flow line
  (`idea✓ > plan✓ > ... > [release]`, about 70 chars), Issues text (`plain` allows 200) and Dependency edges all exceed a phone screen.

## Approach (recommended, taken)

1. **Overrun re-estimate** (done line 1), in `board_status.py`. Split the current-step part of `left_time` into a small
   helper returning `(left, over)`: with `est` the median of other done runs' time for the step and `spent` this run's time on it,
   - `spent <= est`: `left_step = est - spent`, `over = 0` (unchanged behaviour);
   - `spent > est`: `over = spent - est` and `left_step = max(60, spent / 2)` (re-estimated from how long it has already run,
     never under a minute). The goal's `left` is `left_step` plus the later steps' medians, so it grows as the step keeps running.
   The finish time needs no new code: `status_graph.chain` already sums `left`, so a grown `left` moves "finish about".
   `left_time` keeps its signature (returns seconds or None); a sibling `overrun(run, runs, at)` returns `over` seconds for the
   board, so `board_status.py` callers and `board.py` stay untouched. A step with no estimate (no other done run) is never "over".
2. **Over-by mark** (done line 1), in `live_board.py` `flow_line`: the current step reads `[build over by 12m]` using
   `status_graph.span`; under a minute over shows nothing extra.
3. **60-column board** (done line 2), in `live_board.py`: one `fit(lines, 60)` pass at the end of `render`, so text and
   `--html` share it. It wraps with `textwrap` at word boundaries, continuation lines indented two spaces past the original
   indent, hard-cutting only a word longer than the width. The header splits into `LIVE BOARD  <repo>  <clock>` and a second
   line `<version>  health: <verdict>`; the flow line wraps at its ` > ` joints (steps stay whole); `plain` default size
   drops 200 to 120. No data is dropped except by wrapping.
4. **Defect test** (done line 3): add to `dev/toy/test-board.sh` a fixture with two done runs (known step durations from log
   gaps), one running run that has spent well past the median on its step, and a long repo/slug/issue text. It asserts
   (a) time left is `>= 1m` and larger than the pre-fix value (0 for the step), (b) `over by` appears, (c) "finish about" is later
   than the same board with the step on time, (d) every line is `<= 60` characters. A `defect` row in `.loop/regression.tsv`
   (`category` defect, `link` the issue 93 URL, `seen_red` set by running it once against the unfixed code before the fix is
   applied, then green after). The merge PR body says `Closes #93`.

## Alternatives not taken

- *Linear stretch* (`left = est` again when over): simple but never moves again as the step keeps running; rejected.
- *Truncate lines with an ellipsis*: loses the step flow and issue text; rejected for wrap.
- *Wrap in `board_page.py` CSS only*: leaves the terminal board at full width; rejected.

## Size and risk

`board_status.py` 6.5 KB, `live_board.py` 8.4 KB, both far under the 20 KB script cap; no new file needed. Risk is low:
existing board tests that match whole lines (flow line, header, `no estimate yet`) may need their expectations re-pointed to the
wrapped form; delivery runs the full toy suite. `board_runs.py`, `graph.py` and `dev/toy` are touched only if a helper or
fixture lands there (`graph.flow` edge lines may need the same wrap).

## Distribution

None: repo scripts, shipped with the existing skill.
