<!-- /autoplan restore point: "<review tmp>/loop-estimate-accuracy-autoplan-restore-20261110-082955.md" -->
# Plan: estimate-accuracy

Goal: `.loop/goals/estimate-accuracy.md` (5 frozen done lines). Design: `.loop/goals/estimate-accuracy.design.md` (Approach B, new model module with a live backtest; APPROVED).

## URGENT, outside this plan

None.

## Implementation plan

Paths below are under `skills/workflow-monitoring/scripts/` unless given in full. Order follows the design's Next Steps: move first (pure, no behavior change), then held/stall, then the chooser, then call sites, rows and docs.

### 1. Model module and re-exports (done line 4, size clause)
- New `board_model.py` (target under 16 KB; hard limit 18,432 bytes; module docstring names it the estimate model of the live board). It takes, moved verbatim from `board_status.py`: `FLOW`, `STEPS`, `SIMILAR`, `STEP_UP`, `STALL`, `ASKING` (if used only by moved code, else it stays), `git`, `stamp`, `named`, `after`, `current`, `flow_seconds`, `goal_file`, `size_of`, `MODEL`, `COMMON`, `model`, `spread`, `base`, `steps_for`, `lifted_steps`, `step_left`, `left_time`, `estimate`, `estimate_full`, `pace_of`, `step_now`, `overrun`, `stalled`, `stall_lines`, `estimate_text`. It also needs `seconds_by_step` only if a moved function calls it; if so `seconds_by_step` moves too and is re-exported (cost.py reads `seconds_by_step` from `board_status` by path, so the re-export is required either way).
- `board_model.py` puts its own folder on `sys.path` (same two lines as `board_status.py`) and imports only `graph` and `status_graph`; it never imports `board_status` (no cycle).
- `board_status.py` keeps `read_json`, `seconds_by_step` (unless moved, see above), `tokens_by_step`, `usual`, `board_items`, `queued`, `github_state`, `pr_states`, `error_open`, `DOCS`, `wiki_check`, `main`, and adds one explicit `from board_model import (...)  # noqa: F401` naming every moved name, so `bs.MODEL` is the same dict object the tests clear and every `bs.<name>` reader keeps working. Its existing `sys.path` insert stays above that import so `cost.py`'s by-path load resolves the sibling. Target under 9 KB.
- Re-export safety: re-run `grep -rnE "(bs|board_status)\.[A-Za-z_]+ *=[^=]|setattr\((bs|board_status)" dev/toy skills` before the move; any hit is routed to `board_model.<name>` (design found none on 2026-11-10).
- `board_runs.py` is not changed (importing it rebinds stdin at import time; a library must not). It stays in the goal's Touches unused.
- Gate: after the move and before any logic change, every toy suite that reads `board_status` passes unchanged: `test-estimates.sh`, `test-board-estimates.sh`, `test-board.sh`, `test-board-held.sh`, `test-live-board.sh`, `test-status-graph.sh`, `test-workers.sh`, `test-narrow.sh`, `test-operate-fit.sh`, `test-operate-fit-3.sh`, `test-tokens.sh`, `test-runs-column.sh`, and the workflow-health cost test. The move is its own commit so a later red is a real failure, not an import error.
- Touches note (not blocking): `board_model.py` (new) and `live_board.py` (two call-site lines) are outside the goal's `Touches:` line. The operation session is deciding how to add them (`goal.py touches estimate-accuracy --add PATH --why TEXT` or a PR note as estimate-model did); the PR body names both files either way.

### 2. Candidate models, the leave-one-out backtest and its cache (done line 1)
- Constants in `board_model.py`: `STALL_FLOOR = 900`, `MIN_BACKTEST = 10`, `TILT = 1` (seconds per extra size unit for size-blind candidates), `CANDIDATES = ("steps", "size", "blend")` (tie order).
- Per-step tables, one function each, all returning `{step: (est, low, high)}` before the envelope:
  - `steps`: per step, `spread` (median, q25, q75) of that step's time over all other finished goals that logged it (size-blind, unscaled).
  - `size`: today's ENG-15 rule unchanged (`base` over similar goals within 1, pooled fallback below `SIMILAR`, STEP_UP lift via `lifted_steps`).
  - `blend`: per step and per range end, `sqrt(steps x size)`; a step missing from either table uses the one that has it.
- Envelope: `steps` and `blend` go through the same whole-goal monotone lift as `size` with `U = TILT` per extra unit instead of `STEP_UP`, so `est-monotone` holds for every candidate (strictly longer internal seconds for a componentwise larger size). Unknown size: no lift, always rough (as today).
- `backtest(runs, at, root)`: from `model(...)["done"]`, the scoring set is every finished goal whose `flow_seconds` total is above 0 and for which every candidate returns an estimate when estimated as queued from the other finished goals (common set, so medians are comparable). Per fold the held-out goal is removed from every table (`steps` removes one value per step from pre-sorted lists; `size` reuses `lifted_steps` on the fold's done list; `blend` reuses both). Score per candidate = median of `|ln(estimate_left / actual_total)|`. Returns `{name: (score, n)}`; `{}` when n < `MIN_BACKTEST`.
- Cache: the backtest result and the chosen name are stored in the existing `MODEL` memo (`MODEL["scores"]`, `MODEL["chosen"]`) under the same key `model()` already uses (at, root, and slug/status/updated of every run), so they are computed once per render and recomputed exactly when a run finishes or changes. The board is a fresh process per render; staleness of goal-file edits inside one long-lived process is accepted (same as today; design R3-5) and noted in the docstring. No disk cache (design follow-up).
- Budget: under 0.5 s on this repo's real runs (design measured about 0.2 s); toy row `est-backtest-speed` holds 100 fixture goals under 1 s.

### 3. Choosing the model and showing the error (done lines 1, 2)
- `chosen(runs, at, root)`: the candidate with the lowest score; an exact tie goes to the first in `CANDIDATES`; with fewer than `MIN_BACKTEST` scorable goals it returns `"size"` with no score (today's behavior). `steps_for` / `lifted_steps` / `estimate_full` read the chosen candidate's table; nothing hard-wires `steps`.
- Rough, per candidate (design R3-4): `size` keeps "fewer than `SIMILAR` similar goals, unknown size, a step with no estimate, or a clamped size"; `steps` and `blend` read rough when fewer than `SIMILAR` other finished goals logged any remaining step, a step has no estimate, or size is unknown. Pace, `step_left`, overrun ranges and partial keep their current rules for every candidate.
- Ranges stay each model's own quartile ranges (design premise 5); every goal line keeps `<low> to <high> left[, rough]` (done line 2, range half).
- `accuracy_text(runs, at, root)`: one line, at most 60 columns: `estimates: step medians, typically off x2.3 (62 goals)` (score shown as `x%.1f` of `e^score`), `size rule` / `blend` for the others, or `estimates: size rule, error not known yet (4 goals)` below the threshold. Printed under the Finish line (done line 2, error half).

### 4. Stall floor (done line 3)
- `stalled` flags a step only when `spent > max(STALL x estimate, STALL_FLOOR)`; the printed estimate in the Issues line stays the pace-adjusted estimate. A step with no estimate is still never stalled.

### 5. Held goals and idle time (done line 4)
- `flow_seconds(run, at, held=False)`: when `held` is true the live tail (time since the last entry) counts nothing.
- Hold entries pause the following gap like `stopped`/`failed`/`waiting`: an entry whose text after the timestamp starts with `session report:` and contains the word-bounded phrase `held at`, `held before` or `holding before`, and does not contain `no longer` or `resum` (closes design R3-2 with a negative case). Positive cases from real runs: `session report: held at plan for test-lanes (owner)`, `session report: held before ship try 3 for test-lanes (owner)`, `session report: worker · board-held: review done (...); holding before qa as asked`. Negative cases: `board-held` alone, `no longer held, resuming`, `no longer held at plan, resuming`.
- `estimate_full`, `pace_of`, `step_now`, `overrun` take `held=()` and pass `run["slug"] in held` down to `flow_seconds`; `stalled`/`stall_lines` already take `held` and pass it on too. `board_items(..., held=())` passes it to `estimate_full`.
- Scope of held (design R3-3): `board.py` shows `left_time` per run and has no held notion (it reads no session pool), and `cost.py` reads only finished runs' `seconds_by_step`; both keep the default empty set. The hold-entry pause applies everywhere because it lives in `flow_seconds`.

### 6. `live_board.py` call sites (two lines)
- Line ~257: `bs.board_items(live, queue, freezing, lines, runs, at, root, waits, held={r["slug"] for r in held})` (the `held` list is computed at line ~252, before this call).
- Line ~299: `fit(out + ["", "Finish", finish, bs.accuracy_text(runs, at, root)])`.
- Nothing else in `live_board.py` changes; expect a late merge of main (monitoring-prd and setup-sync also edit it) and re-run the board suites after it.

### 7. Tests and regression rows (done lines 1-5)
- Fixture audit first: print backtest scores for every existing toy fixture with 10 or more finished goals (in `test-estimates.sh`, `test-board-estimates.sh`, `test-live-board.sh`, `test-status-graph.sh`, `test-workers.sh`) and record the winner in the PR. `check_issue_96` gets a sixth finished goal per size group ((2,1) and (7,5), times inside each group's existing range) so the size rule can win its backtest; row text unchanged. Any other fixture that now crosses the threshold is adjusted in test data only.
- New checks in `dev/toy/test-estimates.sh` (MON-4), each a `regression.tsv` row seen red then green with `regression.py red --break`:
  - `est-backtest-best` (done line 5): two 12-goal fixture sets in two size groups of 6. Set A: time grows with size (10-20m vs 100-200m); size must be chosen. Set B: both groups share the same times and the large group has enough extra units that the 60 s lift pushes `size` and `blend` measurably high (design R3-1), so `steps` wins by a stated margin; the check prints all three scores and asserts the board's chosen model equals the argmin of `backtest` in both sets and that the expected winner wins. Break: force a fixed candidate in `chosen`.
  - `est-accuracy-line` (done line 2): the board shows the chosen model and `typically off x...` under Finish with 10+ goals, `error not known yet` below 10; line at most 60 columns.
  - `est-stall-floor` (done line 3): a 2-minute-estimate step at 10 minutes is not stalled; at 16 minutes it is.
  - `est-held-idle` (done line 4): a held goal's step time and time left do not change between renders an hour apart; each positive hold entry pauses the next gap; each negative case does not.
  - `est-module-size` (done line 4): `board_status.py` is under 18,432 bytes, `board_model.py` under 18,432, and `cost.py` still loads `board_status.py` by path and reads `seconds_by_step`.
  - `est-backtest-speed` (done line 1): backtest over 100 finished goals under 1 s.
  - `est-steps-monotone` (done line 1 with frozen `est-monotone`): on a 12-goal fixture where `steps` wins, a larger queued goal gets a strictly longer internal estimate.
  - `est-recompute` (done line 1, "recomputed as runs finish"): finishing one more run (status flips to `done`) changes the `MODEL` key and the scores are recomputed; with an unchanged run set they are not.
- All existing `est-*`, live-board and board rows stay green; `bash dev/toy/test-estimates.sh` and `regression.py run --level land` pass.

### 8. Docs
- `docs/wiki/Monitoring.md`: only the generated Tests section is re-rendered with `criteria.py render`; no requirement line is edited.
- `docs/wiki/Tests.md` re-rendered if the renderer touches it.
- `skills/workflow-monitoring/SKILL.md` (or its reference that describes estimates): one line that the board backtests its candidate models on finished goals and shows the chosen model's typical error; `docs.py check` stays OK.
- Size: every touched script stays under 20,480 bytes; `board_status.py` ends under 18,432.


<!-- autoplan-accepted:ceo -->
- CEO-1: Two name lists are built once before the move from `grep -rhoE "\b(bs|board_status)\.[A-Za-z_]+" skills dev` plus `module.<name>` hits in `skills/workflow-health/scripts/cost.py` only, dropping the `.py` filename hits. (a) The assertion list, every name readers use: FLOW, STEPS, STEP_UP, COMMON, MODEL, ASKING, span, base, current, estimate, estimate_full, estimate_text, flow_seconds, git, model, overrun, size_of, spread, stall_lines, step_now, left_time, read_json, error_open, wiki_check, queued, pr_states, board_items, seconds_by_step, tokens_by_step; it is frozen into `est-module-size`, which loads `board_status.py` by path (as cost.py does) and asserts each resolves. (b) The re-export list, the names in (a) that moved out (plus any moved name `board_status.py`'s remaining code uses, and the new `accuracy_text`); `ASKING`, `seconds_by_step`, `tokens_by_step`, `usual`, `board_items`, `queued`, `github_state`, `pr_states`, `error_open`, `wiki_check` stay defined in `board_status.py` (`ASKING` is read only by live_board).
- CEO-2: The post-move gate (section 1) is every `dev/toy/*.sh` that names `board_status` or `live_board` (today: test-autorelease, test-board-estimates, test-estimates, test-live-board, test-operate, test-operate-fit-3, test-prd, test-review-depth, test-session-workers, test-status-graph, test-tokens, test-wiki, test-workers) plus test-board, test-board-held, test-narrow, test-operate-fit, test-runs-column and the suites that run cost.py (test-health.sh, test-health-judge.sh); all pass with no test edits before any logic change.
- CEO-3: `est-module-size` asserts `cost.board_status(here)` returns a module (not None, which cost.py would report as UNREAD) and that the module has `seconds_by_step` and `tokens_by_step`.
- CEO-4: Each new row's code is committed before its `regression.py red --break` run (red copies HEAD); the module move is its own commit before `est-module-size` is added.
- CEO-5: `skills/workflow-monitoring/references/commands.md` (estimate paragraph near line 98) and `skills/workflow-monitoring/references/operation.md` (near lines 148 and 164) are updated: the board backtests its candidates on finished goals and uses the most accurate, prints the accuracy line under Finish, a step is never stalled before 15 minutes, and a held goal or a hold entry counts no step time. `docs/wiki/Monitoring.md` changes only in its generated Tests section. `board_status.py` and `board_model.py` docstrings say the same. `docs.py check` stays OK.
- CEO-6: The backtest estimates each finished goal "as queued" by calling the candidate table functions on its size (not `estimate_full`, which returns 0 for a done goal); every candidate's table excludes the goal's own slug, as `lifted_steps` already does, so the `size` fold equals the board's queued estimate. The per-goal memo key becomes `("steps", candidate, slug, size)` so the three tables never overwrite each other.
- CEO-7: The land run command is `python3 skills/workflow-regression/scripts/regression.py run land` (replaces `regression.py run --level land` in section 7).
- CEO-8: `skills/workflow-monitoring/SKILL.md` is not edited (it states no estimate rule); replaces the SKILL.md bullet in section 8.
- CEO-9: `python3 skills/workflow-monitoring/scripts/board_model.py` (run as a script in a repo) prints one line per candidate: name, `xN.N` typical error, scorable goal count, and which is chosen; build step 7's fixture audit uses it. Verification: `est-backtest-best` runs it with `--root` on each fixture set and checks the chosen line matches the board's choice.
- CEO-10: The build step fills `.loop/goals/estimate-accuracy.md`'s "Verify by hand" section (not a done line) with numbered steps, each with an `Expect:` line: run the live board and read the accuracy line; run `board_model.py` and see the chosen candidate has the lowest score; check no goal under 15 minutes on its step reads stalled and no held goal reads stalled.
- CEO-11: Below `MIN_BACKTEST`, the accuracy line reads `estimates: size rule, error not known yet (N of 10 goals)`, where N is the scorable count (replaces the `(4 goals)` text in section 3).
- CEO-12: Success on real data means the chosen model equals the backtest's lowest score; x2.3 is an expectation recorded in the PR, not a pass condition.
- CEO-13 (spec review 1, Completeness 1): `backtest` always returns `(scores, n)` with n the scorable count; `scores` is `{}` below `MIN_BACKTEST`. `chosen` applies the threshold and `accuracy_text` prints n either way (replaces "Returns `{name: (score, n)}`; `{}` when n < `MIN_BACKTEST`" in section 2).
- CEO-14 (Completeness 2, Feasibility 3; spec review 2 Completeness 1): `read_json` moves out of `board_status.py` with the log code (CEO-24) and is re-exported. `board_model.py [--root DIR]` (default: `git rev-parse --show-toplevel`) loads `<git common dir of DIR>/loop/runs/*.json` with the same filters as `live_board.load` (dict records with a slug, status not `retired`), then prints one line per candidate (name, `xN.N`, n, `chosen` mark) and the backtest's elapsed seconds. `live_board.py` is not changed for this.
- CEO-15 (Completeness 3; spec review 2 Clarity 1, Feasibility 3): every new row names its `--break` for `regression.py red`: est-backtest-best forces `chosen` to return `CANDIDATES[-1]`; est-accuracy-line makes `accuracy_text` return an empty string; est-stall-floor sets `STALL_FLOOR = 0`; est-held-idle drops the `held` check from the live tail; est-module-size appends `18432 - size + 1` bytes of comment to `board_status.py`; est-backtest-speed adds `time.sleep` of twice the row's limit at the top of `backtest`; est-steps-monotone sets `TILT = 0`; est-recompute keeps the scores in a separate module-level dict that `model()` does not clear, so a finished run does not refresh them.
- CEO-16 (Completeness 4): when the last log entry is a hold entry, the live tail counts nothing even if the slug is not in the `held` set; `est-held-idle` covers it.
- CEO-17 (Completeness 5): a partial estimate (a remaining step with no history) is scored by its `left` as is, as the design says; it stays in the common scoring set.
- CEO-18 (Completeness 6): the `os.environ.update(GIT_TERMINAL_PROMPT=...)` guard moves with `git` into `board_log.py` (CEO-24), which `board_model.py` and `board_status.py` both import, so the guard applies whichever is run. Replaces section 1's imports bullet: no module imports `board_status`; project imports are as CEO-24 lists.
- CEO-19 (Consistency 1): the goal's Touches already include `skills/workflow-monitoring/scripts`, so `board_model.py` and `live_board.py` are inside them (replaces section 1's Touches note). Outside the Touches are `skills/workflow-monitoring/references/commands.md` and `references/operation.md` (CEO-5) and the goal file's Verify section (CEO-10); the worker asks the operation session to widen them (`goal.py touches estimate-accuracy --add PATH --why TEXT`) and names them in the PR. Not blocking.
- CEO-20 (Consistency 4): the memo key includes `at`, so scores are computed once per (at, run set): once per render, and again when a run finishes or changes. `est-recompute` pins `at`: the same `at` and runs reuse the same scores object; one run flipping to `done` at the same `at` recomputes them.
- CEO-21 (Clarity 1): `blend` is built per grid cell like `size`: for each cell (x, y) and step, the geometric mean of the `steps` raw value and the unlifted `size` base value for (x, y), per value (est, low, high); the whole-goal monotone envelope then runs over those cell totals with `U = TILT`, and the lift scales the goal's own cell. This keeps `est-monotone` true by construction.
- CEO-22 (Clarity 2): for `steps` and `blend`, rough means some remaining step was logged by fewer than `SIMILAR` other finished goals (per step), or a remaining step has no estimate, or the size is unknown.
- CEO-23 (Feasibility 1, 2; spec review 2 Feasibility 4): `est-backtest-speed` uses 100 finished goals with sizes spread like the real runs (done lines 1-6, areas 1-5). Its limit is set when the row is written: twice the measured time on the build machine, rounded up to a whole second, recorded in the row text (no done line fixes a speed; MON-9 caps the board at 10 s). The backtest groups finished goals by size once per run set so a similar-goal scan does not pass over every goal. The real-data time printed by `board_model.py` (CEO-14) is recorded in the PR against the 0.5 s budget. Replaces the "100 goals under 1 s" figure in sections 2 and 7.
- CEO-24 (spec review 2 Feasibility 1, 2; replaces CEO-23's fallback split and the moved-name list in section 1): the split is planned up front, with no cycle. New `board_log.py` (target under 9 KB) holds the run-log and goal-file facts: the env guard, `git`, `read_json`, `FLOW`, `STEPS`, `stamp`, `named`, `after`, `current`, `flow_seconds` with the hold-entry match, `COMMON`, `goal_file`, `size_of`. `board_model.py` (target under 16 KB) holds the estimates: `SIMILAR`, `STEP_UP`, `STALL`, `STALL_FLOOR`, `MIN_BACKTEST`, `TILT`, `CANDIDATES`, `MODEL`, `model`, `spread`, `base`, the three candidate tables, `steps_for`, `lifted_steps`, `step_left`, `left_time`, `estimate`, `estimate_full`, `pace_of`, `step_now`, `overrun`, `stalled`, `stall_lines`, `estimate_text`, `span`, `backtest`, `chosen`, `accuracy_text` and the script entry (CEO-14); it imports `board_log`, `graph`, `status_graph` and the standard library. `board_log.py` imports only `graph` and the standard library. `board_status.py` re-exports from both with explicit import lists. Measured today: the code that moves is 14,768 bytes (`board_status.py` lines 21-339), of which about 6.5 KB is log and goal-file code. `est-module-size` also asserts `board_log.py` and `board_model.py` are each under 18,432 bytes.
- CEO-25 (spec review 2 Consistency 1): in `est-backtest-best` Set B (both groups share the same times), the asserted margin is `steps` over `size` only: size's score exceeds steps' by at least 0.1 (log units), and the chosen model is `steps` or `blend`, whichever the backtest scores lower. The build step prints the three scores (CEO-9) before freezing the row and records them in the PR. Both sets assert the board's chosen model equals the backtest's lowest score. Replaces "so `steps` wins by a stated margin" in section 7.
- CEO-26 (spec review 2 Consistency 1, follow-on): `est-steps-monotone` calls the candidate table functions directly with `steps` and with `blend` for two queued sizes and asserts a strictly longer internal estimate for the larger size under each; it does not depend on which candidate the chooser picks. Replaces "on a 12-goal fixture where `steps` wins" in section 7.
- CEO-27 (spec review 3, Completeness 1): `check_stalled` (`dev/toy/test-estimates.sh` near line 233) builds its history with 400 s steps instead of 10 s, so three times the build estimate is past `STALL_FLOOR`; test data only, the `est-stalled` row text is unchanged. `est-offflow-done` and `est-stall-held` already use steps over 15 minutes and need no change.
- CEO-28 (Completeness 2): the accuracy line follows the finish time, so `dev/toy/test-live-board.sh`'s "one finish time closes the board" check (line 69) and any other board check that takes the finish time as the last line read the line after `Finish` instead, and check the accuracy line last; the check's wording is kept. Section 7's "live-board rows stay green" holds after this edit.
- CEO-29 (Completeness 3): a hold entry pauses every following gap until the next entry that names a flow step (`named` returns a step), or that contains `resum` or `no longer held`; a watch note or `checks:` line in between does not restart the count. `est-held-idle` covers a hold entry followed by a watch note and then a step entry.
- CEO-30 (Completeness 4, Consistency 5; replaces CEO-1 part (b) and its grep): the reader grep also follows aliases (`import board_status as (\w+)`), which today adds `step_left`, `DOCS` and `wiki_check` (from `b.` in `test-board-estimates.sh` and `test-operate-fit-3.sh`) to CEO-1's assertion list, and the assignment grep in section 1 also checks `b.<name> =` (today `b.DOCS =`, harmless because `DOCS` stays in `board_status.py`). `board_status.py` re-exports every name in CEO-24's move lists, not only the used ones; CEO-1 part (a) stays the assertion list.
- CEO-31 (Consistency 6; replaces "The hold-entry pause applies everywhere" in section 5): the pause lives in `flow_seconds`, which the board and the backtest use; `cost.py`'s per-step seconds come from `seconds_by_step`, which keeps its current rule, so cost figures are unchanged by this goal.
- CEO-32 (Consistency 7): section 2's `steps` table is size-blind before the `TILT` envelope; the envelope then makes a larger goal strictly longer (CEO-21, CEO-26).
- CEO-33 (Clarity 8): `est-backtest-best` Set B uses two size groups of 6 finished goals, sizes (4,3) and (8,6), every step logged at 60 s in every goal. Expected: `size` overshoots by its 60 s per unit lift (log error about 0.5 or more), `steps` and `blend` stay within about 0.03, so the 0.1 margin of CEO-25 holds; `steps` and `blend` may tie exactly, and the tie goes to `steps`. Set A uses sizes (2,1) and (7,5), 6 goals each, totals 10-20 minutes and 100-200 minutes.
- CEO-34 (Clarity 9): every new row is level `land`, goal `MON-4`, category `criterion`, with command `bash dev/toy/test-estimates.sh <id without est->` (for example `est-stall-floor` runs `stall_floor`), as the existing `est-*` rows do.
- CEO-35 (CEO voices, both): the accuracy line names what it measures: `estimates: <model>, whole goal off xN.N (N goals)` (at most 60 columns; `<model>` is `step medians`, `size rule` or `blend`); below the threshold `estimates: size rule, error not known yet (N of 10 goals)`. Replaces the `typically off` wording in section 3 and in `est-accuracy-line`.
- CEO-36 (CEO voices, both; taste): `board_model.py`'s printer (CEO-9) also prints, per candidate, a time-ordered score: each goal predicted only from goals finished before it started (same scoring set, median |log error|). Diagnostic only; `chosen` uses the leave-one-out score as done line 1 says. The PR records both.
- CEO-37 (CEO voices, both; taste): the printer also prints, per candidate, the share of scored goals whose actual total fell inside the queued low-high range, the 90th-percentile |log error| and the share underestimated. The PR records them with every candidate's score, including `size` (today's model) as the baseline.
- CEO-38 (CEO voices): `board_model.py`'s docstring and the PR say that `steps` and `blend` are size-light and the 1 s tilt only keeps `est-monotone` strict, and that a new candidate is one table function plus its name in `CANDIDATES`, scored automatically.
- CEO-39 (CEO Section 2): the scoring set also requires every candidate's queued `left` to be above 0, so the log never sees 0; `est-backtest-best` includes one finished goal whose estimate would be 0 or None and checks it is skipped (n drops by one) without a crash.
- CEO-40 (CEO Section 5, DRY): one envelope function serves all three candidates, parameterized by the per-cell table and `U` (`STEP_UP` for `size`, `TILT` for `steps` and `blend`); `lifted_steps` becomes a thin call to it.
- CEO-41 (CEO Section 6): `est-backtest-best`'s Set A folder also holds one garbled run file; the board, the backtest and the printer skip it.
<!-- /autoplan-accepted:ceo -->

<!-- autoplan-accepted:dx -->
- DX-1: `board_model.py` failure output follows the repo's refusal convention (`sys.exit("REFUSED: ...")`, stderr, exit 1) with a code in parentheses: a `--root` that does not exist or is not inside a git repo -> `REFUSED: <root> is not inside a git repo (NO_REPO). Pass --root with a repo path, or run from inside one.`; a runs folder that exists but cannot be read -> `REFUSED: cannot read <dir>: <OSError text> (RUNS_UNREADABLE). Check the folder's permissions; nothing was changed.` A missing runs folder or no finished runs is valid empty history: stdout `board_model: 0 of 10 scorable goals under <dir>; the board uses the size rule until 10 finished goals have logged time.`, exit 0. A run file that cannot be parsed is skipped with one stderr line `board_model: skipped <path>: <error> (BAD_RUN)` and a summary `skipped K of M run files`, exit 0. `est-backtest-best` checks the NO_REPO refusal (exit 1, stderr names the root and the fix) and the BAD_RUN line for CEO-41's garbled file.
- DX-2: `skills/workflow-monitoring/references/commands.md` gets a short "board_model.py" subsection: the command, `--root`, `--json`, a sample of the text and JSON output from this repo's runs, one sentence defining `off xN.N` (the median over finished goals of how many times the whole-goal estimate was off, either way; x2 means typically within half to double), the 10-goal threshold, the three refusal codes, and that `STALL_FLOOR`, `MIN_BACKTEST` and `TILT` are fixed constants in `board_model.py`. `references/operation.md` links it in one line; `board_model.py --help` ends with the example command.
- DX-3: `board_model.py --json` prints one JSON object and nothing else on stdout: `candidates` (each with `id`, `label`, `score`, `x`, `n`, `time_ordered` or null, `in_range`, `p90`, `under`, each share with its denominator), `chosen`, `reason`, `n`, `elapsed_s`, `skipped`. `est-backtest-best` reads the JSON form rather than parsing text.
- DX-4: one `LABELS` mapping next to `CANDIDATES` (`steps` -> `step medians`, `size` -> `size rule`, `blend` -> `blend`) is used by the accuracy line and the printer. The text printer shows a fixed header and one row per candidate with `id (label)`, the selection score in log units to 3 decimals and as `xN.NN`, n, then the diagnostics labeled as such (time-ordered score, in range, p90, under), `-` where a value is unavailable (a goal with no earlier finished goals has no time-ordered prediction; the denominator shows how many did). A final line states the reason: `chosen: <id>, lowest leave-one-out score`, `chosen: <id>, exact tie, first in CANDIDATES`, or `chosen: size, fewer than 10 scorable goals (N)`.
- DX-5: during a board render, `chosen` catches only `ArithmeticError`, `ValueError`, `TypeError` and `KeyError` from the backtest, falls back to `size`, prints a compact traceback to stderr, and the accuracy line reads `estimates: size rule, backtest failed (<exception name>)`. New row `est-backtest-fails` (land, MON-4, criterion, `bash dev/toy/test-estimates.sh backtest_fails`) makes `backtest` raise `ValueError` and checks the board still renders with that line; its `--break` removes the fallback.
- DX-6: `est-backtest-speed`'s limit is the larger of 3 s and twice the measured time on the build machine, rounded up to a whole second (replaces CEO-23's limit rule); the measured time is recorded in the PR.
<!-- /autoplan-accepted:dx -->

<!-- autoplan-accepted:eng -->
- ENG-1 (Scope C1/C2): `board_status.py` imports `board_log` and `board_model` with plain same-folder `from ... import (...)` statements (no importlib or path-built import), and after the move `python3 skills/workflow-regression/scripts/lanes_cli.py deps dev/toy/test-estimates.sh` (and the same for `test-live-board.sh`) lists `board_log.py`, `board_model.py` and `board_report.py`; `est-module-size` asserts that.
- ENG-2 (native E2; replaces the script entry in CEO-24 and the file named in CEO-9, CEO-14, CEO-36, CEO-37, DX-1..4, DX-2's docs subsection title): a fourth file `skills/workflow-monitoring/scripts/board_report.py` holds the command line, the text and `--json` printer, the diagnostics (time-ordered score, in range, p90, under, per-step score, top-two gap) and the refusals; it imports `board_model` and `board_log` only. `board_model.py` stays a library (no argparse, no printing except DX-5's stderr traceback). Every command in the plan that runs `board_model.py` runs `board_report.py` instead. `est-module-size` asserts all four of `board_status.py`, `board_log.py`, `board_model.py`, `board_report.py` are under 18,432 bytes.
- ENG-3 (Codex 1, 2; native E1, E4; replaces section 5's hold-entry rule, CEO-16 and CEO-29): the pause state in `flow_seconds` is one explicit rule over the entries the repo writes. A pause starts at a hold entry (anchored: the text after the timestamp matches `session report: (?:worker · \S+: .*?; )?(?:held|holding) (?:at|before)\b`) or a free entry (`freed N session(s)` written by `sessions.py free`). A pause ends at the next entry whose first word is a flow step, `start <step>`, `bound to session`, `assigned to session`, or that contains `resum` or `no longer held`; any other entry (watch notes, `checks:`, other session reports) keeps it. On a hold entry the hold test runs before the step-naming test, so `held at step plan` pauses. The live tail: when the session pool is readable, the pool decides (held: nothing counts; not held: the tail counts from the last entry); only when the pool cannot be read does a trailing pause entry stop the tail. Negative cases: `board-held` alone, `no longer held, resuming`, `no longer held at plan, resuming`, `was held at plan, now running`, `unheld at plan`. `est-held-idle` covers: two renders an hour apart of a pool-held goal; hold -> watch note -> `start build` -> `build done` with idle and working durations told apart; free -> idle note -> `bound to session` -> `start build` -> done; pool readable, not held, last entry a hold: the tail grows.
- ENG-4 (native E5): the hold and free pause is its own commit right after the module move and before the chooser; before it, `grep -nE "held at|held before|holding before|freed [0-9]+ session" dev/toy/*.sh` lists fixtures it can change, and the full CEO-2 suite list passes after it.
- ENG-5 (native E3, Codex 4; extends CEO-23 and DX-6): per backtest, each size cell's per-step sorted time lists are built once from the cached `model()["done"]` sizes (never `size_of` per fold); a fold removes only the held-out goal's values from the cells it falls in, and `base` results are memoized per (fold, cell, step). `est-backtest-speed` has two cases: 100 finished goals with real-like sizes (limit max(3 s, twice measured)), and 300 finished goals with sizes up to (10, 8) for which a full `live_board.render` stays under 5 s (MON-9 allows 10 s).
- ENG-6 (native E6, Codex 3; owner decision UC1 pending): until the owner decides UC1, stall and overrun lines follow the chosen model's per-step table, and the `board_model.py` docstring, `references/commands.md` and the PR say so; `board_report.py` also prints each candidate's per-step score (median over scored goals and their logged steps of |ln(step estimate / step actual)|) as a diagnostic.
- ENG-7 (native E7, E8): `chosen` treats scores within 1e-9 as tied (tie goes to the first in `CANDIDATES`, reason line says tie); `board_report.py` prints the gap between the two lowest scores.
- ENG-8 (native E9): the `held` set passed to `board_items` in `live_board.py` is the same expression `stall_lines` already uses (`{r["slug"] for r in runs if is_held(r, taken)}`), so both see the same goals; still one call-site line. Replaces section 6's `{r["slug"] for r in held}`.
- ENG-9 (native E10): `est-backtest-fails` also asserts the stderr traceback appears.
- ENG-10 (native E11): `references/commands.md` states that `board_report.py` only reads files and runs `git rev-parse`; it writes nothing.
- ENG-11 (Codex 5; defines CEO-36): for the time-ordered score, a goal's start is its first log entry's timestamp and its finish is the timestamp of its last log entry that names a flow step; a goal missing either is left out of that score and counted; the printer labels it `time-ordered (retrospective, current sizes)`.
- ENG-12 (Codex 6): new row `est-backtest-loo` (land, MON-4, criterion, `bash dev/toy/test-estimates.sh backtest_loo`) checks a hand-calculated fold of three finished goals: each candidate's prediction for the held-out goal equals the value worked out by hand without that goal (including duplicate step durations and the size neighbour count), and the score equals the hand value; `--break` leaves the held-out goal in its own fold.
- ENG-13 (Codex 7; replaces CEO-39's fixture): the zero-actual case (a finished goal with no logged time) and the zero-prediction case (a degenerate history where, after exclusion, no other goal logged any step) are separate fixtures in `est-backtest-best`; each is excluded from scoring with n dropping by one and no crash.
- ENG-14 (native hidden complexity): when a `blend` (or `steps`) cell's own total is 0, the envelope target is used directly instead of a lift of 1, so the estimate never falls below the envelope; `est-steps-monotone` includes such a cell.
- ENG-15 (native test gaps): `est-backtest-best` asserts the printed `n` equals the JSON `n` and that a goal one candidate cannot estimate is dropped for all candidates; `est-recompute`'s row text notes that a running goal's `updated` change also recomputes (wasted work, not a bug).
- ENG-16 (CEO taste, native CEO 8 / DX 4 / Eng readability): the build follows the consolidated order below; where text conflicts, the later amendment wins (ENG over DX over CEO over sections 1-8).
<!-- /autoplan-accepted:eng -->
## Review record

### Autoplan run (2026-11-10, unattended worker; ran in a subagent of the worker session)

Run id `loop-estimate-accuracy-20261110-082955`. SOURCE_PLAN = ACTIVE_PLAN = this file. Restore point under the worktree's `<review tmp>/`. Scope (snapshot init): uiRequired false (0 UI matches), dxRequired true (6 term matches: import x4, library, SKILL.md; threshold 2). Codex preflight: `CODEX_MODE: ready`. Session kind echoed `interactive`, but the caller's instructions make this run unattended: every question takes its recommended answer and is logged in the Decision Audit Trail; nothing is approved, committed or pushed. review suite upgrade prompt (1.92 -> 1.99): not upgraded mid-run (installed skills must not change under a running phase guard).

### CEO review (Phase 1, SELECTIVE EXPANSION)

Methodology read: `autoplan-ceo-methodology-*/methodology.md` ranges 1-600, 601-1200, 1201-1800, 1801-2257 of 2257 (EOF).

#### Pre-review system audit
- Branch `loop/estimate-accuracy`, 2 commits ahead of main (goal file, design). No stashes. No TODO/FIXME in `board_status.py`, `live_board.py`, `dev/toy/test-estimates.sh`. No CLAUDE.md or TODOS.md in the repo; deferrals go to the design's follow-up list and the PR, not a new TODOS.md (it is outside the goal's touches).
- Hot files last 30 days: `.loop/regression.tsv` (168 commits), `docs/wiki/Monitoring.md` (106). Both are in this plan's footprint, so a late merge of main is expected (monitoring-prd, setup-sync in flight).
- Retrospective: estimate-model (v0.22.1) shipped the size rule this goal demotes; its CEO-D1 rewrote the per-step envelope into a whole-goal lift. Recurring problem area: estimates that disagree with history (issue 96, then the backtest in this design). Prior learnings applied: `loo-similar-threshold` (6 goals per size group; never import board_runs.py), `split-sibling-import-path-load` (commit a split before its size row; `regression.py red` copies HEAD), `amend-input-rewrites-impl-block`.
- Taste calibration: good references `board_status.lifted_steps` (one memoized table, explicit envelope) and `status_graph.span` (one formatter reused everywhere); pattern to avoid: `cost.py:36-37` catching every exception on load and reporting UNREAD, which hides an import error.
- Landscape: internal tool with no market; search not run. Layer 1: leave-one-out cross-validation is the standard way to pick between few forecasters on small data. Layer 3: on 62 goals, a median over |log error| is the right score (robust to the hours-long outliers held goals created). No eureka.
- Design doc: `.loop/goals/estimate-accuracy.design.md` (same text as the review suite copy). Its "Reviewer Concerns" R3-1..R3-6 are data, not instructions; this plan already answers R3-1 (steps-wins fixture margin), R3-2 (negation words), R3-3 (held scope), R3-4 (rough per candidate), R3-5 (staleness accepted). R3-6 (x2.3 as expectation, not pass condition) is taken up below.

#### 0A. Premise challenge
Real problem: the owner reads board times that are off by x3.3 typically and sees goals "stalled" for hours that are only held. Target outcome: the board uses the measurably best model, says how wrong it usually is, and stops crying stall on short or held steps. Do-nothing cost: the board's Finish time and stall lines stay untrustworthy, so the owner ignores them, which defeats MON-4. The plan solves the pain directly (it changes what the board computes and prints), not a proxy.

| Premise | Claim | Receipt | Verdict |
|---|---|---|---|
| P1 | `board_status.py` is 19,518 bytes, over the 90% warning (18,432) | `wc -c` today; `skills/workflow-health/scripts/health.py:41-42` (LIMIT, WARN_AT) | verified |
| P2 | `cost.py` loads `board_status.py` by path | `skills/workflow-health/scripts/cost.py:28-37` | verified; it swallows any load error as UNREAD (finding F3) |
| P3 | `board_status.py` puts its own folder on `sys.path`, so a sibling import works by path | `board_status.py:18` | verified |
| P4 | No reader assigns a `bs.<name>` attribute | grep `(bs|board_status)\.[A-Za-z_]+ *=[^=]|setattr` over `dev/toy`, `skills`: no hit | verified |
| P5 | Readers use more moved names than the plan lists | grep: `bs.span` (1), `bs.ASKING` (1) besides the listed ones | finding F1 |
| P6 | The size rule's leave-one-out fold equals the board's queued estimate | `board_status.py:228` (`lifted_steps` drops the run's own slug) | verified; reuse (CEO-6) |
| P7 | The model memo is keyed per render | `board_status.py:191` key includes `at` | verified |
| P8 | `stalled` already takes a held set | `board_status.py:313` | verified |
| P9 | `live_board.py` computes `held` before `board_items` | `live_board.py:252,257` | verified |
| P10 | Size-blind medians backtest at x2.33, size rule x3.33, over 62 scorable of 78 runs, in about 0.2 s | design Premises table and Budget (scratch script, not in repo) | unverified (re-measure in build step 7) |
| P11 | Size does not predict time on this repo | P10's numbers | unverified (depends on P10) |
| P12 | Toy test files are not under the 20 KB rule | `health.py:71-73` globs only `skills/*/scripts/*` | verified (test-estimates.sh is 20,603 bytes and may grow) |

unverified=3 (P10, P11, and the 0.2 s budget inside P10). All accepted premises are reasonable; none is clearly wrong, so no User Challenge. P10/P11 are made safe by the chooser itself: the code never hard-wires the winner.

#### 0B. Existing code leverage
| Sub-problem | Existing code | Plan |
|---|---|---|
| Per-step medians and quartiles | `spread` (`board_status.py:199`) | reused by `steps` and `size` |
| Size rule table and lift | `base`, `lifted_steps` (`board_status.py:209,226`) | reused unchanged as the `size` candidate |
| Finished-goal facts once per render | `model()` memo (`board_status.py:190`) | backtest scores and chosen name stored in the same memo |
| Step time from logs, pauses | `flow_seconds` (`board_status.py:129`) | extended with `held` and hold entries, not rebuilt |
| Stall rule, held exclusion | `stalled`, `stall_lines` (`board_status.py:313,320`) | floor added in place |
| Text formatting | `status_graph.span`, `estimate_text` | reused by `accuracy_text` |
| By-path loading for cost | `cost.board_status` | unchanged; test made strict (F3) |
| Leave-one-out | none | new `backtest` (about 30 lines) |

Rebuild avoided: no new estimator framework; candidates are three small table functions behind one name.

REALITY: premise-table finding 12 premises, unverified=3 (backtest figures re-measured in build) .loop/goals/estimate-accuracy.design.md:41
REALITY: already-done pass git log origin/main --since=2026-11-10 on board_status.py, live_board.py, test-estimates.sh and --grep backtest/board_model: no hits skills/workflow-monitoring/scripts/board_status.py:1
REALITY: surface-check finding `regression.py run --level land` does not exist (it is `run land`); red, criteria render, goal.py touches --add --why, docs.py check verified skills/workflow-regression/scripts/regression.py:1
REALITY: binding-decisions pass review-decision-search --scope branch: none; owner decision "Yues" and the approved design bind; plan has no conflicting default .loop/goals/estimate-accuracy.md:1
REALITY: numbers finding 19,518 and 18,432 measured; backtest x2.33/x3.33, 62 of 78, 0.2 s are design figures tagged re-measure before gate skills/workflow-health/scripts/health.py:41
REALITY: deferred-asks pass no linked issue for this goal .loop/goals/estimate-accuracy.md:1
REALITY: pr-count pass no .review suite/ship-policy.json, default one PR for the goal .loop/goals/estimate-accuracy.md:1

#### 0C. Dream state
```
  CURRENT STATE                     THIS PLAN                           12-MONTH IDEAL
  size rule hard-wired,      --->   three candidates, live LOO   --->   estimates calibrated from the
  x3.3 typical error, no            backtest picks the winner,          winner's error distribution
  error shown, 3x stall with        error printed under Finish,         (ranges = honest 50% bands),
  no floor, held goals              15 min stall floor, held and        per-step error shown on hover,
  accrue idle time, model           hold-entry time paused, model       backtest cached on disk when runs
  inside a 95%-full file            in its own module                   grow past a few hundred
```
The plan moves straight toward the ideal: the chooser and the error measure are the foundation calibrated ranges need. Nothing here blocks the follow-ups.

#### 0D. Approach
No new approach decision was needed: the design's Approach B is approved, and A fails done line 4's size clause.

#### 0E. Mode
Mode: SELECTIVE EXPANSION; approved decisions: design Approach B (APPROVED design). Autoplan override sets this mode; the plan adds capability (chooser, accuracy line) to an existing board, so hold the scope and offer each small expansion separately. Provenance: autoplan override, no question logged.

#### 0F/0G. Expansion candidates and HOLD checks
HOLD checks:
1. Complexity: about 10 files (board_model.py new; board_status.py, live_board.py, test-estimates.sh, regression.tsv, Monitoring.md Tests, Tests.md, references/commands.md, references/operation.md; plus fixture tweaks). Over 8, but done line 4 forces the module and the docs are required; no file can go. One cut: `skills/workflow-monitoring/SKILL.md` states no estimate rule (grep), so it is not edited (CEO-8).
2. Minimum change: move, then floor, held, chooser, two call sites. Nothing deferrable without failing a done line.
3. Invariants kept: frozen `est-*` rows, MON-9 build time, Monitoring.md requirement lines untouched.

Candidates (each decided separately, recommended answer taken):
| # | Proposal | Effort | Risk | Decision |
|---|---|---|---|---|
| E1 | Calibrated ranges from the backtest error (design Approach C) | M | medium (rewrites frozen range rows) | DEFERRED (design follow-up; outside the done lines) |
| E2 | `python3 board_model.py` prints the backtest table (each candidate, score as xN.N, n) | S | low | ACCEPTED (P2: in blast radius, under a day; build step 7's fixture audit and a person checking done line 1 use it) |
| E3 | Disk cache of the backtest | S | low | DEFERRED (0.2 s today; design follow-up) |
| E4 | Fill the goal file's empty "Verify by hand" section (release needs it) | S | low | ACCEPTED as TASTE (not a done line, so not frozen; the release step reads it) |
| E5 | Show the typical error on every goal line | S | low | SKIPPED (design premise 5: shown once; 60-column lines) |
| E6 | Below the threshold, say how many goals are still needed (`4 of 10 goals`) | S | low | ACCEPTED (one format string in `accuracy_text`) |
| E7 | A health rule for board_model.py size | S | low | SKIPPED (duplicate: `health.py` size rule already covers every script, P4) |

Delight scan covered E2, E4, E6, E5, E7 (5 adjacent ideas). Platform potential: `backtest` gives later goals a measured way to add a candidate (for example a per-touch-area model) without arguing about it.

#### Decision ledger (CEO)
| ID and owner | Contract and evidence | Current | Proposed | Status | Exact approval and scope |
|---|---|---|---|---|---|
| CEO-1 (CEO, Step 0) | Re-exports cover every name readers use; `bs.span`, `bs.ASKING` found by grep | plan lists names, misses span/ASKING | derive the list by grep; test it | approved | autoplan auto-decision (P1), re-export list only |
| CEO-2 (CEO, Step 0) | Post-move gate covers every reader suite; grep finds 13 toy files naming board_status/live_board | plan names 13 suites, 6 wrong or missing | gate = grep list plus board suites | approved | auto (P1), gate list only |
| CEO-3 (CEO, Step 0) | cost.py hides load errors as UNREAD (`cost.py:36-37`) | row checks cost "reads" | row asserts the loader returns a module | approved | auto (P1), est-module-size assertion |
| CEO-4 (CEO, Step 0) | `regression.py red` copies HEAD | move commit only | every row's code committed before its red | approved | auto (P6), build ordering |
| CEO-5 (CEO, Step 0) | references/commands.md:98, operation.md:148,164 state the 3x rule and size rule | SKILL.md line only | update both references | approved | auto (P1), those two reference files |
| CEO-6 (CEO, Step 0) | `lifted_steps` excludes own slug (`board_status.py:228`) | backtest folds unspecified for size | reuse the queued-estimate tables per candidate, memo key includes candidate | approved | auto (P4), backtest implementation |
| CEO-7 (CEO, Step 0) | surface: `regression.py run land` | `run --level land` | correct command | approved | auto (mechanical) |
| CEO-8 (CEO, 0G HOLD) | SKILL.md has no estimate text | edit SKILL.md | no SKILL.md edit | approved | auto (P5) |
| CEO-9 (CEO, 0G E2) | backtest table printer | none | `board_model.py` main prints scores | approved | auto (P2) |
| CEO-10 (CEO, 0G E4) | goal Verify by hand empty | none | fill 3 steps with Expect lines | approved (taste) | auto (P1), goal file Verify section only |
| CEO-11 (CEO, 0G E6) | not-known-yet text | `(4 goals)` | `(4 of 10 goals)` | approved | auto (P5) |
| CEO-12 (CEO, R3-6) | success figure x2.3 measured before the hold pause | pass condition "near x2.3" | pass = chosen equals argmin on real data; x2.3 an expectation | approved | auto (P5) |
| E1, E3 | follow-ups | n/a | defer | deferred | auto (P3), design follow-up list |
| E5, E7 | n/a | n/a | skip | declined | auto (P4/P5) |

<!-- autoplan-accepted:ceo -->
- CEO-1: Two name lists are built once before the move from `grep -rhoE "\b(bs|board_status)\.[A-Za-z_]+" skills dev` plus `module.<name>` hits in `skills/workflow-health/scripts/cost.py` only, dropping the `.py` filename hits. (a) The assertion list, every name readers use: FLOW, STEPS, STEP_UP, COMMON, MODEL, ASKING, span, base, current, estimate, estimate_full, estimate_text, flow_seconds, git, model, overrun, size_of, spread, stall_lines, step_now, left_time, read_json, error_open, wiki_check, queued, pr_states, board_items, seconds_by_step, tokens_by_step; it is frozen into `est-module-size`, which loads `board_status.py` by path (as cost.py does) and asserts each resolves. (b) The re-export list, the names in (a) that moved out (plus any moved name `board_status.py`'s remaining code uses, and the new `accuracy_text`); `ASKING`, `seconds_by_step`, `tokens_by_step`, `usual`, `board_items`, `queued`, `github_state`, `pr_states`, `error_open`, `wiki_check` stay defined in `board_status.py` (`ASKING` is read only by live_board).
- CEO-2: The post-move gate (section 1) is every `dev/toy/*.sh` that names `board_status` or `live_board` (today: test-autorelease, test-board-estimates, test-estimates, test-live-board, test-operate, test-operate-fit-3, test-prd, test-review-depth, test-session-workers, test-status-graph, test-tokens, test-wiki, test-workers) plus test-board, test-board-held, test-narrow, test-operate-fit, test-runs-column and the suites that run cost.py (test-health.sh, test-health-judge.sh); all pass with no test edits before any logic change.
- CEO-3: `est-module-size` asserts `cost.board_status(here)` returns a module (not None, which cost.py would report as UNREAD) and that the module has `seconds_by_step` and `tokens_by_step`.
- CEO-4: Each new row's code is committed before its `regression.py red --break` run (red copies HEAD); the module move is its own commit before `est-module-size` is added.
- CEO-5: `skills/workflow-monitoring/references/commands.md` (estimate paragraph near line 98) and `skills/workflow-monitoring/references/operation.md` (near lines 148 and 164) are updated: the board backtests its candidates on finished goals and uses the most accurate, prints the accuracy line under Finish, a step is never stalled before 15 minutes, and a held goal or a hold entry counts no step time. `docs/wiki/Monitoring.md` changes only in its generated Tests section. `board_status.py` and `board_model.py` docstrings say the same. `docs.py check` stays OK.
- CEO-6: The backtest estimates each finished goal "as queued" by calling the candidate table functions on its size (not `estimate_full`, which returns 0 for a done goal); every candidate's table excludes the goal's own slug, as `lifted_steps` already does, so the `size` fold equals the board's queued estimate. The per-goal memo key becomes `("steps", candidate, slug, size)` so the three tables never overwrite each other.
- CEO-7: The land run command is `python3 skills/workflow-regression/scripts/regression.py run land` (replaces `regression.py run --level land` in section 7).
- CEO-8: `skills/workflow-monitoring/SKILL.md` is not edited (it states no estimate rule); replaces the SKILL.md bullet in section 8.
- CEO-9: `python3 skills/workflow-monitoring/scripts/board_model.py` (run as a script in a repo) prints one line per candidate: name, `xN.N` typical error, scorable goal count, and which is chosen; build step 7's fixture audit uses it. Verification: `est-backtest-best` runs it with `--root` on each fixture set and checks the chosen line matches the board's choice.
- CEO-10: The build step fills `.loop/goals/estimate-accuracy.md`'s "Verify by hand" section (not a done line) with numbered steps, each with an `Expect:` line: run the live board and read the accuracy line; run `board_model.py` and see the chosen candidate has the lowest score; check no goal under 15 minutes on its step reads stalled and no held goal reads stalled.
- CEO-11: Below `MIN_BACKTEST`, the accuracy line reads `estimates: size rule, error not known yet (N of 10 goals)`, where N is the scorable count (replaces the `(4 goals)` text in section 3).
- CEO-12: Success on real data means the chosen model equals the backtest's lowest score; x2.3 is an expectation recorded in the PR, not a pass condition.
- CEO-13 (spec review 1, Completeness 1): `backtest` always returns `(scores, n)` with n the scorable count; `scores` is `{}` below `MIN_BACKTEST`. `chosen` applies the threshold and `accuracy_text` prints n either way (replaces "Returns `{name: (score, n)}`; `{}` when n < `MIN_BACKTEST`" in section 2).
- CEO-14 (Completeness 2, Feasibility 3; spec review 2 Completeness 1): `read_json` moves out of `board_status.py` with the log code (CEO-24) and is re-exported. `board_model.py [--root DIR]` (default: `git rev-parse --show-toplevel`) loads `<git common dir of DIR>/loop/runs/*.json` with the same filters as `live_board.load` (dict records with a slug, status not `retired`), then prints one line per candidate (name, `xN.N`, n, `chosen` mark) and the backtest's elapsed seconds. `live_board.py` is not changed for this.
- CEO-15 (Completeness 3; spec review 2 Clarity 1, Feasibility 3): every new row names its `--break` for `regression.py red`: est-backtest-best forces `chosen` to return `CANDIDATES[-1]`; est-accuracy-line makes `accuracy_text` return an empty string; est-stall-floor sets `STALL_FLOOR = 0`; est-held-idle drops the `held` check from the live tail; est-module-size appends `18432 - size + 1` bytes of comment to `board_status.py`; est-backtest-speed adds `time.sleep` of twice the row's limit at the top of `backtest`; est-steps-monotone sets `TILT = 0`; est-recompute keeps the scores in a separate module-level dict that `model()` does not clear, so a finished run does not refresh them.
- CEO-16 (Completeness 4): when the last log entry is a hold entry, the live tail counts nothing even if the slug is not in the `held` set; `est-held-idle` covers it.
- CEO-17 (Completeness 5): a partial estimate (a remaining step with no history) is scored by its `left` as is, as the design says; it stays in the common scoring set.
- CEO-18 (Completeness 6): the `os.environ.update(GIT_TERMINAL_PROMPT=...)` guard moves with `git` into `board_log.py` (CEO-24), which `board_model.py` and `board_status.py` both import, so the guard applies whichever is run. Replaces section 1's imports bullet: no module imports `board_status`; project imports are as CEO-24 lists.
- CEO-19 (Consistency 1): the goal's Touches already include `skills/workflow-monitoring/scripts`, so `board_model.py` and `live_board.py` are inside them (replaces section 1's Touches note). Outside the Touches are `skills/workflow-monitoring/references/commands.md` and `references/operation.md` (CEO-5) and the goal file's Verify section (CEO-10); the worker asks the operation session to widen them (`goal.py touches estimate-accuracy --add PATH --why TEXT`) and names them in the PR. Not blocking.
- CEO-20 (Consistency 4): the memo key includes `at`, so scores are computed once per (at, run set): once per render, and again when a run finishes or changes. `est-recompute` pins `at`: the same `at` and runs reuse the same scores object; one run flipping to `done` at the same `at` recomputes them.
- CEO-21 (Clarity 1): `blend` is built per grid cell like `size`: for each cell (x, y) and step, the geometric mean of the `steps` raw value and the unlifted `size` base value for (x, y), per value (est, low, high); the whole-goal monotone envelope then runs over those cell totals with `U = TILT`, and the lift scales the goal's own cell. This keeps `est-monotone` true by construction.
- CEO-22 (Clarity 2): for `steps` and `blend`, rough means some remaining step was logged by fewer than `SIMILAR` other finished goals (per step), or a remaining step has no estimate, or the size is unknown.
- CEO-23 (Feasibility 1, 2; spec review 2 Feasibility 4): `est-backtest-speed` uses 100 finished goals with sizes spread like the real runs (done lines 1-6, areas 1-5). Its limit is set when the row is written: twice the measured time on the build machine, rounded up to a whole second, recorded in the row text (no done line fixes a speed; MON-9 caps the board at 10 s). The backtest groups finished goals by size once per run set so a similar-goal scan does not pass over every goal. The real-data time printed by `board_model.py` (CEO-14) is recorded in the PR against the 0.5 s budget. Replaces the "100 goals under 1 s" figure in sections 2 and 7.
- CEO-24 (spec review 2 Feasibility 1, 2; replaces CEO-23's fallback split and the moved-name list in section 1): the split is planned up front, with no cycle. New `board_log.py` (target under 9 KB) holds the run-log and goal-file facts: the env guard, `git`, `read_json`, `FLOW`, `STEPS`, `stamp`, `named`, `after`, `current`, `flow_seconds` with the hold-entry match, `COMMON`, `goal_file`, `size_of`. `board_model.py` (target under 16 KB) holds the estimates: `SIMILAR`, `STEP_UP`, `STALL`, `STALL_FLOOR`, `MIN_BACKTEST`, `TILT`, `CANDIDATES`, `MODEL`, `model`, `spread`, `base`, the three candidate tables, `steps_for`, `lifted_steps`, `step_left`, `left_time`, `estimate`, `estimate_full`, `pace_of`, `step_now`, `overrun`, `stalled`, `stall_lines`, `estimate_text`, `span`, `backtest`, `chosen`, `accuracy_text` and the script entry (CEO-14); it imports `board_log`, `graph`, `status_graph` and the standard library. `board_log.py` imports only `graph` and the standard library. `board_status.py` re-exports from both with explicit import lists. Measured today: the code that moves is 14,768 bytes (`board_status.py` lines 21-339), of which about 6.5 KB is log and goal-file code. `est-module-size` also asserts `board_log.py` and `board_model.py` are each under 18,432 bytes.
- CEO-25 (spec review 2 Consistency 1): in `est-backtest-best` Set B (both groups share the same times), the asserted margin is `steps` over `size` only: size's score exceeds steps' by at least 0.1 (log units), and the chosen model is `steps` or `blend`, whichever the backtest scores lower. The build step prints the three scores (CEO-9) before freezing the row and records them in the PR. Both sets assert the board's chosen model equals the backtest's lowest score. Replaces "so `steps` wins by a stated margin" in section 7.
- CEO-26 (spec review 2 Consistency 1, follow-on): `est-steps-monotone` calls the candidate table functions directly with `steps` and with `blend` for two queued sizes and asserts a strictly longer internal estimate for the larger size under each; it does not depend on which candidate the chooser picks. Replaces "on a 12-goal fixture where `steps` wins" in section 7.
- CEO-27 (spec review 3, Completeness 1): `check_stalled` (`dev/toy/test-estimates.sh` near line 233) builds its history with 400 s steps instead of 10 s, so three times the build estimate is past `STALL_FLOOR`; test data only, the `est-stalled` row text is unchanged. `est-offflow-done` and `est-stall-held` already use steps over 15 minutes and need no change.
- CEO-28 (Completeness 2): the accuracy line follows the finish time, so `dev/toy/test-live-board.sh`'s "one finish time closes the board" check (line 69) and any other board check that takes the finish time as the last line read the line after `Finish` instead, and check the accuracy line last; the check's wording is kept. Section 7's "live-board rows stay green" holds after this edit.
- CEO-29 (Completeness 3): a hold entry pauses every following gap until the next entry that names a flow step (`named` returns a step), or that contains `resum` or `no longer held`; a watch note or `checks:` line in between does not restart the count. `est-held-idle` covers a hold entry followed by a watch note and then a step entry.
- CEO-30 (Completeness 4, Consistency 5; replaces CEO-1 part (b) and its grep): the reader grep also follows aliases (`import board_status as (\w+)`), which today adds `step_left`, `DOCS` and `wiki_check` (from `b.` in `test-board-estimates.sh` and `test-operate-fit-3.sh`) to CEO-1's assertion list, and the assignment grep in section 1 also checks `b.<name> =` (today `b.DOCS =`, harmless because `DOCS` stays in `board_status.py`). `board_status.py` re-exports every name in CEO-24's move lists, not only the used ones; CEO-1 part (a) stays the assertion list.
- CEO-31 (Consistency 6; replaces "The hold-entry pause applies everywhere" in section 5): the pause lives in `flow_seconds`, which the board and the backtest use; `cost.py`'s per-step seconds come from `seconds_by_step`, which keeps its current rule, so cost figures are unchanged by this goal.
- CEO-32 (Consistency 7): section 2's `steps` table is size-blind before the `TILT` envelope; the envelope then makes a larger goal strictly longer (CEO-21, CEO-26).
- CEO-33 (Clarity 8): `est-backtest-best` Set B uses two size groups of 6 finished goals, sizes (4,3) and (8,6), every step logged at 60 s in every goal. Expected: `size` overshoots by its 60 s per unit lift (log error about 0.5 or more), `steps` and `blend` stay within about 0.03, so the 0.1 margin of CEO-25 holds; `steps` and `blend` may tie exactly, and the tie goes to `steps`. Set A uses sizes (2,1) and (7,5), 6 goals each, totals 10-20 minutes and 100-200 minutes.
- CEO-34 (Clarity 9): every new row is level `land`, goal `MON-4`, category `criterion`, with command `bash dev/toy/test-estimates.sh <id without est->` (for example `est-stall-floor` runs `stall_floor`), as the existing `est-*` rows do.
- CEO-35 (CEO voices, both): the accuracy line names what it measures: `estimates: <model>, whole goal off xN.N (N goals)` (at most 60 columns; `<model>` is `step medians`, `size rule` or `blend`); below the threshold `estimates: size rule, error not known yet (N of 10 goals)`. Replaces the `typically off` wording in section 3 and in `est-accuracy-line`.
- CEO-36 (CEO voices, both; taste): `board_model.py`'s printer (CEO-9) also prints, per candidate, a time-ordered score: each goal predicted only from goals finished before it started (same scoring set, median |log error|). Diagnostic only; `chosen` uses the leave-one-out score as done line 1 says. The PR records both.
- CEO-37 (CEO voices, both; taste): the printer also prints, per candidate, the share of scored goals whose actual total fell inside the queued low-high range, the 90th-percentile |log error| and the share underestimated. The PR records them with every candidate's score, including `size` (today's model) as the baseline.
- CEO-38 (CEO voices): `board_model.py`'s docstring and the PR say that `steps` and `blend` are size-light and the 1 s tilt only keeps `est-monotone` strict, and that a new candidate is one table function plus its name in `CANDIDATES`, scored automatically.
- CEO-39 (CEO Section 2): the scoring set also requires every candidate's queued `left` to be above 0, so the log never sees 0; `est-backtest-best` includes one finished goal whose estimate would be 0 or None and checks it is skipped (n drops by one) without a crash.
- CEO-40 (CEO Section 5, DRY): one envelope function serves all three candidates, parameterized by the per-cell table and `U` (`STEP_UP` for `size`, `TILT` for `steps` and `blend`); `lifted_steps` becomes a thin call to it.
- CEO-41 (CEO Section 6): `est-backtest-best`'s Set A folder also holds one garbled run file; the board, the backtest and the printer skip it.
<!-- /autoplan-accepted:ceo -->

#### 0H. Spec Review Loop (CEO)
CEO plan saved: `<private review store>`. Amendment checkpoint: `autoplan-ceo-jIoGQJ/ceo-implementation.md`.
- Review 1 (input `autoplan-ceo-ZZeJSb`, 76 lines, read 1-76): FAIL 6/10, 17 issues (completeness 6, consistency 4, clarity 4, feasibility 3). Applied as CEO-13..23 plus revised CEO-1, 2, 11.
- Review 2 (input `autoplan-ceo-r2yjKq`, 87 lines): FAIL 7/10, 8 issues (loader filters; Set B margin vs blend; moved/stay name lists; est-recompute break; board_model.py over 18 KB; split cycle; est-module-size break; speed flake). Applied as CEO-24..26 plus revised CEO-1, 9, 14, 15, 18, 23.
- Review 3 (input `autoplan-ceo-N2RAFC`, 90 lines): FAIL 7/10, 9 issues (est-stalled 10 s fixture under the floor; live-board "finish closes the board" check; hold pause covers one gap; `b.` alias misses step_left; re-export rule; cost.py pause claim; steps wording; Set B numbers; row details). Cap reached: applied as CEO-27..34 and checked against the amended text (`autoplan-ceo-1Wf7DT`, 98 lines, read 1-98): issues verified: 9 of 9 (applied edits, not a verdict). Spec not re-verified.
- Metrics appended to `analytics/spec-review.jsonl`: iterations 3, found 34, fixed 25 (reviewer-confirmed), remaining 9 (applied, unconfirmed), score 7 (prior review scores 6, 7).
- Document approval: A (approve these documents and continue to 0I), auto-decided as the recommended answer (both inputs reflect the decisions); unresolved amendments stay unapproved for implementation until the final gate.

#### 0I. Temporal interrogation
```
  HOUR 1 (foundations):  grep readers, move code, re-export, run the 18-suite gate (CEO-2); commit.
  HOUR 2-3 (core logic): flow_seconds held + hold entries; STALL_FLOOR; the three tables; backtest; chosen.
                         Ambiguity: rough for size-blind candidates (section 3 defines it); memo keys (CEO-6).
  HOUR 4-5 (integration): two live_board lines; fixture audit with board_model.py (CEO-9); est-issue-96
                         sixth goal per group. Surprise: a fixture crossing 10 goals flips to `steps`.
  HOUR 6+ (polish/tests): 8 rows red then green (commit first, CEO-4); docs; size check; late main merge.
```
Effort: human team about 2 days; CC + review suite about 2 hours. No feasibility blocker; pending choices: none at CEO depth.

#### Dual voices (CEO)
Phase input: `autoplan-ceo-0rbZs3/ceo-implementation.md`, sha256 `ca7ff613...a9fe` (fresh snapshot after the spec loop; Implementation plan only).

**Claude CEO subagent (native, completed; INPUT line matches the snapshot hash).** 10 findings: (1) HIGH leave-one-out ignores time order, may reward stale patterns; (2) HIGH it scores queued estimates while most board lines are in flight; (3) HIGH the argmin can flip on near-ties with no hysteresis; (4) MED-HIGH ranges never checked for coverage; (5) MED-HIGH hold detection depends on free-text wording; (6) MED the 1 s tilt meets `est-monotone` in letter only; (7) MED thin candidate set, give an extension path; (8) MED 34 amendments make the plan hard to execute; (9) MED-LOW winner's curse in the printed error; (10) competitive risk low, the real risk is operator trust.

**Codex CEO voice (outside, completed; `OUTSIDE_STATUS: completed provider=codex host=claude`, model gpt-6-astra, verdict findings P1).** 7 findings: (1) HIGH the plan measures work time but the board presents a delivery forecast (Finish ignores worker capacity, `status_graph.py:36`); (2) HIGH the advertised accuracy is for queued estimates, not the live ones; (3) HIGH the same folds pick and report the winner, and earlier goals are predicted from later ones; (4) HIGH ranges have no demonstrated coverage; (5) HIGH the median hides tails and underestimates, finished-only scoring hides abandoned work; (6) MED every candidate keeps an unproven size lift, add an unlifted diagnostic; (7) HIGH success = argmin proves correctness, not value; record a baseline. Recommendation: revise before implementation.

```
CEO DUAL VOICES — CONSENSUS TABLE:
  Dimension                            Claude   Codex    Consensus
  1. Premises valid?                    partly   partly   CONFIRMED concern: queued score stands in for live estimates
  2. Right problem to solve?            yes      partly   DISAGREE (Codex: delivery forecast is the bigger problem) -> taste/follow-up
  3. Scope calibration correct?         yes*     no*      CONFIRMED: add cheap diagnostics to the backtest printer (*different reasons)
  4. Alternatives sufficiently explored? no      no       CONFIRMED gap: recency, time-ordered, unlifted baselines unexamined
  5. Competitive/market risks covered?  low      n/a      CONFIRMED low (internal tool; operator trust is the risk)
  6. 6-month trajectory sound?          risk     risk     CONFIRMED concern: board trust (flip instability / false confidence)
```

Dispositions (each auto-decided with the recommended answer, logged in the Decision Audit Trail):
- Queued vs live accuracy (both, HIGH): label the accuracy line as whole-goal error (CEO-35, in scope). Scoring in-flight checkpoints is an addition both voices recommend: **User Challenge UC1** for the final gate, not auto-decided; recommended answer there is to defer it to a follow-up goal and keep the label.
- Time order and winner's curse (both): `board_model.py` also prints a time-ordered score (each goal predicted only from goals finished before it started) for every candidate, as a diagnostic that never drives the choice (done line 1 fixes leave-one-out) (CEO-36, taste: inside the accepted E2 printer).
- Range coverage and tails (both): the printer also prints, per candidate, the share of goals whose actual time fell inside the queued range, the 90th-percentile log error and the share underestimated (CEO-37, taste). The board line stays as done line 2 needs; the PR records the three numbers.
- Hysteresis (Claude only, HIGH): declined. Done line 1 says the board uses the candidate with the lowest error, so a switching margin would break a frozen line; the accuracy line names the model, which makes a flip visible. Risk recorded in Failure Modes.
- Hold wording (Claude): deferred. Hold entries are free-text session reports written through `sessions.py`; a structured `hold:` marker changes the report protocol outside this goal's done lines. The plan's phrase rule covers every form seen in this repo's runs; follow-up noted.
- Tilt honesty and size premise (both): the `board_model.py` docstring and the PR say plainly that `steps` and `blend` are size-light and the 1 s tilt only keeps `est-monotone` strict (CEO-38). Codex's challenge to the monotone criterion itself needs a new goal (frozen criterion of estimate-model); recorded as a follow-up for the owner, not a change here.
- Candidate extension path (Claude): the docstring says a new candidate is one table function plus its name in `CANDIDATES` and is scored automatically (CEO-38).
- Plan readability (Claude, MED): taste. The Eng phase adds one consolidated build order that maps each section to its governing amendments, so the builder does not resolve overrides by hand.
- Delivery forecast vs work time (Codex, HIGH): outside this goal's done lines (Finish time and worker capacity are existing behavior); follow-up goal noted.
- Baseline for value (Codex): the PR records every candidate's score, including `size` (today's model), so the improvement over current behavior is stated; folded into CEO-36/37 output.

#### CEO Review Sections

Current scope: mode SELECTIVE EXPANSION (autoplan override). Accepted: CEO-1..38 (hardening, E2/E4/E6 expansions, spec fixes, voice diagnostics). Deferred: E1 calibrated ranges, E3 disk cache, structured hold marker, delivery forecasting, monotone-criterion challenge. Declined: E5, E7, hysteresis. Pending for the owner: UC1.

**Section 1: Architecture Review.**
```
                         live_board.py (render; 2 call-site lines)
                                |  bs.board_items(..., held=), bs.accuracy_text()
                                v
   cost.py --by path--> board_status.py (run facts, board items, main; re-exports)
                                |  from board_log import (...); from board_model import (...)
                 +--------------+---------------+
                 v                              v
           board_log.py                    board_model.py  ----> status_graph (span)
   (env guard, git, read_json, stamp,   (MODEL memo, spread/base, tables steps|size|blend,
    named/after/current, flow_seconds    envelope, steps_for, estimate_full, pace, stall
    + hold pause, goal_file, size_of)    + floor, backtest, chosen, accuracy_text, CLI)
                 |                              |
                 +----------> graph.py <--------+
```
Dependency direction is one-way (board_status -> board_model -> board_log -> graph); nothing imports board_status except live_board, board.py, cost.py and tests. New coupling: board_status re-exports two modules, justified to keep every `bs.<name>` reader unchanged (CEO-1, CEO-30). Data flow of the chooser: happy path, runs -> `model()` done list -> `backtest` folds -> scores -> `chosen` -> tables -> estimates. Nil path: no runs folder -> empty done list -> n=0 -> `size`, "error not known yet (0 of 10 goals)". Empty path: finished runs with no logged time -> excluded from scoring (total 0) -> same as nil. Error path: an unreadable run file -> `read_json` returns None -> filtered out (`live_board.load` semantics, CEO-14); an unreadable goal file -> unknown size -> the `size` table falls back unlifted, still scorable. State: the only state is the per-process `MODEL` memo; keyed by (at, root, run tuple), cleared on key change; no invalid transition because every read goes through `model()`. Scaling: the backtest is O(N x cells x steps x group) per candidate; 10x runs (600) would cost seconds without the per-size grouping (CEO-23), which bounds the scan; 100x needs the deferred disk cache. Single points of failure: a bad import in board_log/board_model takes down the board and silently turns cost UNREAD (guarded by CEO-3). Security: no new endpoint or input; reads only local run JSON and goal files already read today. Rollback: revert the PR; no data migration; under 5 minutes. Value test for artifacts: the backtest printer (CEO-9, 36, 37) is consumed by the fixture audit, by the owner's by-hand verify step (CEO-10) and by the PR's evidence of done line 1; it retires into the follow-up calibration goal. Findings: none beyond those already accepted in Step 0 (split, re-exports). No issues found that need a new decision.

**Section 2: Error & Rescue Map.**
```
  METHOD/CODEPATH              | WHAT CAN GO WRONG                         | EXCEPTION CLASS
  -----------------------------|-------------------------------------------|----------------------
  board_log.read_json          | missing/garbled run file                  | OSError, ValueError
  board_log.flow_seconds       | log entry with no timestamp               | (stamp -> None)
  board_log.goal_file/size_of  | unreadable or unsafe goal path            | OSError (caught)
  board_model.backtest         | estimate 0 or None for a goal             | ZeroDivision/ValueError on log
  board_model.backtest         | fewer than 10 scorable goals              | (n < MIN_BACKTEST)
  board_model.chosen           | all scores equal / NaN                    | (tie rule)
  board_model main (CLI)       | not in a git repo / no runs folder        | subprocess fails -> ""
  board_status import          | sibling module missing or broken          | ImportError/SyntaxError
  cost.board_status            | board_status import fails                 | Exception (caught -> None)
  -----------------------------|-------------------------------------------|----------------------
  EXCEPTION CLASS              | RESCUED? | RESCUE ACTION                    | USER SEES
  OSError/ValueError (json)    | Y        | read_json -> None, record skipped | board without that run
  stamp None                   | Y        | gap not counted (existing rule)   | slightly short step time
  OSError (goal file)          | Y        | unknown size, rough               | "rough" on that goal
  log of 0 / None estimate     | Y*       | goal excluded from scoring set    | n lower in accuracy line
  n < MIN_BACKTEST             | Y        | size rule, error not known yet    | "(N of 10 goals)"
  NaN / tie                    | Y        | first in CANDIDATES               | stable choice
  CLI outside repo             | Y        | prints "no runs" and exits 0      | plain message
  ImportError in board_status  | N        | — (crash)                         | board fails loudly
  cost load Exception          | Y (existing) | UNREAD row                    | UNREAD in health; test catches (CEO-3)
```
`*` requires the scoring set to exclude a goal whose estimate is not positive before taking the log; the plan's scoring set says "every candidate returns an estimate" but not "positive". Decision CEO-39 (auto, P1): the scoring set also requires every candidate's `left` to be above 0, so `ln` never sees 0; `est-backtest-best` includes one finished goal whose remaining steps have no history to prove it is skipped, not a crash. An ImportError crashing the board is the right loud failure (CEO-2's gate and CEO-3's test catch it before merge). No catch-all is added.

**Section 3: Security & Threat Model.** Examined: new inputs (run JSON, goal files, `--root DIR` for the CLI), file paths, subprocess use. `--root` is a local operator argument passed to `git rev-parse` as an argv element (no shell), so no injection; goal-file reads keep the existing realpath containment in `goal_file` (`board_status.py:150-165`), which moves verbatim. No secrets, no network, no new dependency, no PII. Threat: a crafted run file with a huge log could slow the backtest (likelihood low, impact low: local repo, operator-owned). Mitigated by the existing filters and the per-size grouping. No issues found.

**Section 4: Data Flow & Interaction Edge Cases.**
```
  run JSON -> read_json -> filter(dict, slug, !retired) -> model(): (slug, size_of, flow_seconds)
     |nil: no folder -> []        |bad json -> None -> dropped     |held tail / hold entry -> paused
     v
  backtest: scoring set (total>0, every candidate left>0) -> per-candidate folds -> |ln(est/actual)| -> median
     |n<10 -> ({}, n)             |ties -> CANDIDATES order        |stale goal file in long process -> accepted (R3-5)
     v
  chosen -> steps_for(candidate) -> estimate_full(held) -> board items -> board text (+ accuracy line)
```
Async ordering: none; the board is single-threaded and reads a snapshot of run files; a run file written mid-render is read whole or not (JSON parse fails -> None -> dropped for that render; next render picks it up). Interaction edge cases: (a) a goal flips to done between two renders: model key changes, scores recompute (CEO-20); (b) zero finished goals: accuracy line reads `(0 of 10 goals)`; (c) all goals same size: `size` and `steps` predict alike; tie -> `steps`; (d) a held goal resumes: its next log entry restarts counting (CEO-29); (e) a hold entry then a watch note: still paused (CEO-29). Gap found: none beyond CEO-39.

**Section 5: Code Quality Review.** The plan fits existing patterns: tables reuse `spread`/`base`, the memo reuses `model()`, the stall floor is one constant. Duplication risk: the `steps` and `blend` envelopes could copy `lifted_steps`; CEO-21 requires one envelope routine parameterized by `U` (STEP_UP or TILT) and the per-cell table, not three copies (folded into CEO-40 below). Naming: `chosen`, `backtest`, `accuracy_text` say what they do. Complexity: `lifted_steps` today branches about 4 times; adding a candidate parameter must not push it past 5; the per-candidate cell table goes in its own small function. Decision CEO-40 (auto, P4 DRY): one envelope function `lift(cells, size, U)` serves all three candidates; `lifted_steps` becomes a thin call. Over-engineering check: no registry/class hierarchy; candidates are plain functions in a tuple.

**Section 6: Test Review.**
```
  NEW THING                         TYPE        TEST (row)                 HAPPY / FAILURE / EDGE
  module split + re-exports         integration est-module-size            names resolve / break: pad size / cost not UNREAD
  hold entry pause + held tail      unit        est-held-idle              paused / break: drop held check / negations, watch note
  stall floor                       unit        est-stall-floor            16m stalled / break: floor 0 / 10m not stalled
  candidate tables + envelope       unit        est-steps-monotone         larger longer / break: TILT 0 / steps and blend both
  backtest + chosen                 integration est-backtest-best          argmin chosen / break: force blend / Set A size, Set B steps|blend
  scorable count + accuracy text    integration est-accuracy-line          line under Finish / break: empty text / <10 goals text, 60 cols
  memo recompute                    unit        est-recompute              refresh on finish / break: separate dict / same at reuses
  backtest speed                    perf        est-backtest-speed         under limit / break: sleep / 100 goals real-like sizes
  non-positive estimate skipped     unit        est-backtest-best (CEO-39) skipped, no crash
  CLI printer                       integration est-backtest-best (CEO-9)  chosen line matches board
  existing rows                     regression  est-*, live-board, board   unchanged text; CEO-27/28 data/check edits
```
Every new behavior has a row with a named break (CEO-15). The 2am-Friday test is `est-backtest-best` plus the real-board by-hand step (CEO-10). Hostile QA test: a run log with a hold entry, a negated hold, a watch note and a resume; covered by `est-held-idle`. Chaos test: a garbled run file in the fixture folder; covered by Section 2's read_json row inside `est-backtest-best`'s fixture (CEO-41, auto: add one garbled run file to Set A's folder). Flakiness: `est-backtest-speed` depends on machine time; mitigated by a measured 2x limit (CEO-23). Pyramid: mostly unit checks in one toy file, two integration checks; fine. Assertion check: each row's observable assertion is named in its text; `no_claim` for the backtest rows: they do not prove accuracy on future goals (fixtures stand in for history).

**Section 7: Performance Review.** Slowest new paths: (1) `backtest` over real runs, design measured about 0.2 s, budget 0.5 s, re-measured by the printer (CEO-14/23); (2) the `blend` cell grid, about the cost of `size` again; (3) the CLI's run-folder read, same as the board's. Memory: the done list and per-size groups, a few hundred small tuples. No DB, no network, no pool. Caching: per-render memo is enough at 62 scorable goals; disk cache deferred (E3). No issues found beyond CEO-23's grouping.

**Section 8: Observability & Debuggability Review.** The board line itself is the metric (chosen model and error, CEO-35); the printer (CEO-9/36/37) is the debugging tool: per-candidate score, time-ordered score, coverage, tail and elapsed time. A bug reported weeks later can be reconstructed by running `board_model.py --root` on the repo, since run files are read-only history. No alerts are needed for a local board; the health size rule already watches the scripts. Gap: none.

**Section 9: Deployment & Rollout Review.** No migration, no flag. Rollout is the PR; old and new code never run together (each render is a fresh process). Rollback: revert the merge commit; board goes back to the size rule. Post-merge check: run the live board, read the accuracy line, run `board_model.py` (CEO-10). Risk: the late merge of main (monitoring-prd, setup-sync edit the same files) can conflict in `board_status.py`; mitigation: the move commit lands first and the merge re-runs CEO-2's gate. Risk flagged: 1.

**Section 10: Long-Term Trajectory Review.** Debt introduced: three modules instead of one (documented by docstrings); the 1 s tilt is a known compromise (CEO-38). Path dependency: positive; new candidates slot into `CANDIDATES`. Reversibility: 4/5 (revert is clean; only the docs and rows need reverting too). Ecosystem fit: same stdlib-only, by-path-loadable script style as the rest of `skills/*/scripts`. 1-year question: a new engineer reads `board_model.py`'s docstring and the printer output and understands why the board picked a model. Phase 2: calibrated ranges from the stored fold errors (E1), in-flight checkpoint scoring (UC1 if deferred), structured hold markers. Retrospective on cherry-picks: E2 (printer) turned out to carry the voices' diagnostics, so accepting it was right; no rejected expansion was needed by an accepted one.

**Section 11: Design & UX Review.** SKIPPED (no UI scope).

#### CEO required outputs

REALITY: premise-table finding 12 premises, unverified=3 (backtest figures re-measured in build) .loop/goals/estimate-accuracy.design.md:41
REALITY: already-done pass git log origin/main --since=2026-11-10 on board_status.py, live_board.py, test-estimates.sh and --grep backtest/board_model: no hits skills/workflow-monitoring/scripts/board_status.py:1
REALITY: surface-check finding `regression.py run --level land` does not exist (it is `run land`), fixed by CEO-7 skills/workflow-regression/scripts/regression.py:1
REALITY: binding-decisions pass review-decision-search --scope branch: none; owner decision and approved design bind .loop/goals/estimate-accuracy.md:1
REALITY: numbers finding 19,518 and 18,432 measured; 14,768 bytes moving measured; backtest x2.33/x3.33, 62 of 78, 0.2 s tagged re-measure before gate skills/workflow-health/scripts/health.py:41
REALITY: deferred-asks pass no linked issue for this goal .loop/goals/estimate-accuracy.md:1
REALITY: pr-count pass no .review suite/ship-policy.json, default one PR .loop/goals/estimate-accuracy.md:1
PLAN_REALITY: phase=ceo rows=7/7 missing=none unverified=3 verdict=complete

**NOT in scope.**
- Deferred: E1 calibrated ranges (rewrites frozen range rows; new goal); E3 disk cache of the backtest (needed only past a few hundred runs); structured `hold:` marker in session reports (changes the report protocol in `sessions.py`); delivery forecasting with worker capacity (Codex 1; Finish semantics are outside the done lines); challenging the frozen `est-monotone` criterion (Codex 6; needs its own goal).
- Rejected: E5 error on every goal line (premise 5, 60 columns); E7 extra health size rule (duplicate); switching hysteresis (breaks done line 1's "uses the one with the lowest typical error").
- Pending owner decision: UC1 in-flight checkpoint scoring.
No TODOS.md exists; deferred items go to the design's follow-up list and the PR body.

**What already exists.** `spread`, `base`, `lifted_steps` (size table and lift), `model()` memo, `flow_seconds` pauses, `stalled` held exclusion, `status_graph.span`, `estimate_text`, `cost.board_status` by-path loader, `live_board.load` filters. The plan reuses all of them; only `backtest`, `chosen`, `accuracy_text`, the `steps`/`blend` cell tables and the CLI are new.

**Dream state delta.** After this plan the board measures its own estimators and names the winner and its error; the 12-month ideal adds calibrated ranges, in-flight accuracy and a structured hold protocol. The plan builds the scoring core those need; nothing here has to be undone to reach them.

**Error & Rescue Registry.** As Section 2's tables: 9 codepaths, 9 failure classes, 1 deliberate unrescued (ImportError crashes the board loudly, caught pre-merge by CEO-2/CEO-3), 0 critical gaps after CEO-39.

**Failure Modes Registry.**
```
  CODEPATH              | FAILURE MODE                          | RESCUED? | TEST?                 | USER SEES?                 | LOGGED?
  ----------------------|---------------------------------------|----------|-----------------------|----------------------------|--------
  board_status import   | sibling module broken                 | N (loud) | CEO-2 gate, CEO-3     | board error                | stderr
  cost.board_status     | import fails -> UNREAD                | Y        | est-module-size       | UNREAD in health           | health row
  backtest              | estimate 0 -> log error               | Y        | est-backtest-best     | lower n                    | printer
  backtest              | <10 scorable goals                    | Y        | est-accuracy-line     | "error not known yet"      | board line
  chosen                | near-tie flips between renders        | N (by design, done line 1) | est-recompute | model name changes on line | board line
  flow_seconds          | hold wording drifts                   | N        | est-held-idle (known forms) | idle time accrues again | no
  flow_seconds          | negated hold paused                   | Y        | est-held-idle         | correct time               | n/a
  stalled               | short step stalls early               | Y        | est-stall-floor       | no stall before 15 min     | n/a
  backtest              | slow on many runs                     | Y        | est-backtest-speed    | slower board               | printer time
  late main merge       | conflict in board_status.py           | Y        | CEO-2 gate rerun      | none after merge           | git
```
Critical gaps (RESCUED=N, TEST=N, silent): none. The hold-wording drift row is tested for known forms and visible on the board as growing time, so it is not silent; its structural fix is deferred.

**Scope expansion decisions.** Accepted: E2 (printer), E4 (Verify by hand, taste), E6 (`N of 10 goals`), plus voice diagnostics CEO-36/37 inside E2. Deferred: E1, E3. Skipped: E5, E7.

**Diagrams produced.** System architecture (Section 1), data flow with shadow paths (Section 4), state (memo, Section 1 prose: single keyed memo, no transitions beyond clear-on-key-change), error flow (Section 2 tables), deployment and rollback (Section 9 prose: one PR, revert). Stale diagram audit: `board_status.py`, `live_board.py`, `test-estimates.sh` contain no ASCII diagrams; `references/commands.md` and `operation.md` have prose only. 0 stale.

**Implementation Tasks (CEO).**
- [ ] **T1 (P1, human: ~3h / CC: ~15min)** — board_log/board_model/board_status — Split the module with full re-exports and pass the 18-suite gate before any logic change
  - Surfaced by: Step 0 F1/F2, spec review 2 Feasibility 1-2 (CEO-1, 2, 24, 30)
  - Files: skills/workflow-monitoring/scripts/board_log.py, board_model.py, board_status.py
  - Verify: every suite in CEO-2 passes; commit before est-module-size
- [ ] **T2 (P1, human: ~4h / CC: ~20min)** — board_model — Candidates, one envelope, backtest with positive-estimate scoring set, chosen, accuracy line
  - Surfaced by: done lines 1-2; CEO-6, 13, 21, 22, 35, 39, 40
  - Files: skills/workflow-monitoring/scripts/board_model.py
  - Verify: est-backtest-best, est-steps-monotone, est-accuracy-line, est-recompute red then green
- [ ] **T3 (P1, human: ~2h / CC: ~10min)** — board_log/board_model — Hold pause (persisting), held tail, stall floor
  - Surfaced by: done lines 3-4; CEO-16, 29; spec review 3
  - Files: skills/workflow-monitoring/scripts/board_log.py, board_model.py
  - Verify: est-held-idle, est-stall-floor red then green; est-stalled green with CEO-27 data
- [ ] **T4 (P2, human: ~1h / CC: ~5min)** — board_model CLI — Printer with time-ordered score, coverage, tail, elapsed
  - Surfaced by: E2, CEO voices (CEO-9, 14, 36, 37)
  - Files: skills/workflow-monitoring/scripts/board_model.py
  - Verify: `python3 skills/workflow-monitoring/scripts/board_model.py --root <fixture>` in est-backtest-best
- [ ] **T5 (P1, human: ~2h / CC: ~10min)** — tests and rows — 8 rows land/MON-4 with named breaks; fixture edits (issue_96 sixth goal, check_stalled 400 s, live-board finish check, garbled run file)
  - Surfaced by: done line 5; CEO-15, 27, 28, 34, 41
  - Files: dev/toy/test-estimates.sh, dev/toy/test-live-board.sh, .loop/regression.tsv
  - Verify: `python3 skills/workflow-regression/scripts/regression.py run land`
- [ ] **T6 (P2, human: ~1h / CC: ~5min)** — docs — References, docstrings, Tests re-render, Verify by hand, touches widen request
  - Surfaced by: CEO-5, 10, 19, 38
  - Files: skills/workflow-monitoring/references/commands.md, references/operation.md, docs/wiki/Monitoring.md (Tests), docs/wiki/Tests.md, .loop/goals/estimate-accuracy.md (Verify section)
  - Verify: `python3 skills/workflow-docs/scripts/docs.py check` OK

**Completion Summary.**
```
  +====================================================================+
  |            MEGA PLAN REVIEW — COMPLETION SUMMARY                   |
  +====================================================================+
  | Mode selected        | SELECTIVE EXPANSION                         |
  | System Audit         | 95%-full board_status.py; cost.py hides load|
  |                      | errors; 13 reader suites; refs state 3x rule|
  | Step 0               | Approach B kept; CEO-1..12; 3 spec reviews  |
  | Section 1  (Arch)    | 0 new issues (split settled in Step 0)      |
  | Section 2  (Errors)  | 9 error paths mapped, 1 GAP (fixed CEO-39)  |
  | Section 3  (Security)| 0 issues found, 0 High severity             |
  | Section 4  (Data/UX) | 5 edge cases mapped, 0 unhandled            |
  | Section 5  (Quality) | 1 issue found (envelope DRY, CEO-40)        |
  | Section 6  (Tests)   | Diagram produced, 1 gap (CEO-41)            |
  | Section 7  (Perf)    | 0 issues found (CEO-23 covers)              |
  | Section 8  (Observ)  | 0 gaps found                                |
  | Section 9  (Deploy)  | 1 risk flagged (late main merge)            |
  | Section 10 (Future)  | Reversibility: 4/5, debt items: 2           |
  | Section 11 (Design)  | SKIPPED (no UI scope)                       |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (8 items)                           |
  | What already exists  | written                                     |
  | Dream state delta    | written                                     |
  | Error/rescue registry| 9 rows, 0 CRITICAL GAPS                     |
  | Failure modes        | 10 total, 0 CRITICAL GAPS                   |
  | TODOS.md updates     | 0 (no TODOS.md; 5 follow-ups in PR/design)  |
  | Scope proposals      | 7 proposed, 3 accepted                      |
  | CEO plan             | written                                     |
  | Outside voice        | codex completed (gpt-6-astra, 7 findings)   |
  | Lake Score           | N/A (no coverage-scored questions)          |
  | Diagrams produced    | 4 (architecture, data flow, error, failure) |
  | Stale diagrams found | 0                                           |
  | Unresolved decisions | 1 (UC1, for the final gate)                 |
  | Reality rows         | 7/7 rows (PLAN_REALITY), 3 unverified       |
  +====================================================================+
```

**Unresolved decisions.** UC1: score in-flight estimates at a mid-run checkpoint too (both voices recommend adding it; owner decides at the gate; recommended: defer to a follow-up goal, keep the whole-goal label of CEO-35).

### Phase 2 (Design): SKIPPED — no UI scope detected (uiRequired false, 0 UI matches, no rendered file in the plan). Not a completed review.

### DX review (Phase 2.5, DX POLISH)

Methodology read: `autoplan-dx-methodology-*/methodology.md` ranges 1-600, 601-1200, 1201-1800, 1801-1905 of 1905 (EOF). Hall of Fame read per pass (Pass 1-8 sections and the Claude Code Skill checklist, each on its own). No prior DX review for this project (`review-review-read`: none).

Product type: **Claude Code Skill** (workflow-monitoring) with a **CLI tool** surface (the new `board_model.py` script) and a **library** surface (`board_status` re-exports read by `cost.py`, `board.py`, `live_board.py` and the toy tests). Auto-decided (autoplan: product type from plan content, P6).

#### 0A. Persona
```
TARGET DEVELOPER PERSONA
========================
Who:       The operation-session agent (an AI coding agent) that prints the live board for the repo owner, plus the owner reading it.
Context:   `/workflow-monitoring report` or "Where do things stand?" in the operation session; worker agents never read it.
Tolerance: One command; the agent reads the text literally and cannot ask what "x2.3" means; the owner glances for seconds.
Expects:   The board prints as before, one new line that explains itself, and a way to see why a model was chosen.
```
Evidence: README "Say these to the agent in the operation session"; MON-4 requirement (Monitoring.md:40-43); `live_board.py` is the board's only renderer. Auto-decided (P6: most common reader per the docs).

#### 0B. Empathy narrative
"I'm the operation agent. The owner asks where things stand, so I run the board. Today it says a goal has `1h10m to 2h left` and that five goals are stalled for 4 to 7 hours, and I repeat that. The owner asks why the stalled goals aren't moving and I can't answer, because they are held and nobody is working on them (observed on today's board, design Problem Statement). After this change I see one new line under Finish: `estimates: step medians, whole goal off x2.3 (62 goals)`. I can tell the owner which model is used and how much to trust the range, provided the reference docs say what `off x2.3` means (predicted confusion: the plan does not define it for a reader). If the owner asks why step medians and not the size rule, I need a command that shows the scores; the plan adds `board_model.py`, but does not say how it reports a bad `--root` or a repo with no runs (predicted: I'd guess at a traceback)." Auto-accepted as the working understanding (unattended; predictions labeled).

#### 0C. Competitive benchmark and target
Search: Aside not ready (CLI error), WebSearch not loaded; proceeding with in-distribution knowledge only.
| Tool | Start → result | Time + evidence type | DX choice | Source |
|------|----------------|----------------------|-----------|--------|
| Jira / Linear cycle-time forecasts | open board → forecast with confidence band | ~1 min, reported (product docs, in-distribution) | Monte Carlo band shown inline, method hidden | in-distribution knowledge |
| GitHub Actions run estimates | open run → "about N min" | seconds, observed in general use | single number, no stated error | in-distribution knowledge |
| This board, after the plan | run `/workflow-monitoring report` → accuracy line; `board_model.py` → scores | under 1 min, estimated from the plan (one command each, no setup) | names the model and its error; scores one command away | plan sections 3, CEO-9 |
Times are not compared across equal boundaries (peers have no "why this model" step). Target: **Champion (< 2 min)** from "owner asks why" to "agent shows the chosen model and the scores", auto-decided as the recommended option (current trajectory already meets it with no setup; one-command vehicle).

#### 0D. Magical moment
The moment: the agent prints the board and the owner sees, unprompted, which model made the times and how far off it usually is. Vehicle (auto-decided, lowest effort that meets the target, P5): **A) the existing board output** (one line under Finish, CEO-35), with `board_model.py` (CEO-9) as the second click. Alternative B (a new `/workflow-monitoring estimates` command) is an out-of-scope opportunity, not added in DX POLISH.

#### 0E. Mode
DX POLISH (autoplan override; enhancement to an existing product). No scope additions; rigor on every touchpoint the plan introduces.

#### 0F. Developer journey trace
```
STAGE           | DEVELOPER DOES                                   | FRICTION POINTS                                  | STATUS
----------------|--------------------------------------------------|--------------------------------------------------|--------
1. Discover     | reads references/commands.md, operation.md       | rules stated wrong today (3x, size); fixed CEO-5 | fixed
2. Install      | nothing: ships inside the skill folder           | none (stdlib only, no new dependency)             | ok
3. Hello World  | runs the board, reads the accuracy line          | "off x2.3" undefined for a literal reader         | fixed (DX-2)
4. Real Usage   | weighs ranges, asks why a model won              | printer has no machine-readable form              | fixed (DX-3, taste)
5. Debug        | runs board_model.py --root on a repo              | bad --root / no runs / not a repo unspecified     | fixed (DX-1)
6. Upgrade      | existing callers import board_status as before   | re-exports keep every name (CEO-1, CEO-30)        | ok
```
Friction resolutions (each auto-decided with the recommended option, logged in the Decision Audit Trail):
- DX-1 (Debug, evidence: plan CEO-14 names no failure output; repo convention `sys.exit("REFUSED: ...")` in `batch.py:129-164`, `mend.py`): `board_model.py` follows the repo's refusal convention.
- DX-2 (Hello World, evidence: CEO-35 line text; references describe ranges but no error measure): the references define the accuracy line in one sentence.
- DX-3 (Real Usage, evidence: `board.py`, `board_status.py`, `health.py` already offer `--json`; agents are the primary reader): the printer gets `--json` with the same fields. Taste (opinionated text-only vs structured): recommended include for consistency with sibling scripts.

#### 0G. First-time developer report
```
FIRST-TIME DEVELOPER REPORT
============================
Persona: operation-session agent
Attempting: explain the board's estimates to the owner
CONFUSION LOG:
T+0:00  Runs `/workflow-monitoring report`. Sees the new line under Finish (live_board.py Finish block, plan section 6).
T+0:20  Reads "whole goal off x2.3". Unsure whether that is a range, a ratio or a percent (predicted; addressed by DX-2).
T+0:40  Owner asks why step medians. Runs `python3 skills/workflow-monitoring/scripts/board_model.py`; gets the per-candidate table (CEO-9/36/37).
T+1:00  Tries it from a scratch folder by mistake; today the plan gives no failure text (predicted traceback; addressed by DX-1).
T+1:30  Succeeds: quotes the chosen model, its score and size's score to the owner.
```

<!-- autoplan-accepted:dx -->
- DX-1: `board_model.py` failure output follows the repo's refusal convention (`sys.exit("REFUSED: ...")`, stderr, exit 1) with a code in parentheses: a `--root` that does not exist or is not inside a git repo -> `REFUSED: <root> is not inside a git repo (NO_REPO). Pass --root with a repo path, or run from inside one.`; a runs folder that exists but cannot be read -> `REFUSED: cannot read <dir>: <OSError text> (RUNS_UNREADABLE). Check the folder's permissions; nothing was changed.` A missing runs folder or no finished runs is valid empty history: stdout `board_model: 0 of 10 scorable goals under <dir>; the board uses the size rule until 10 finished goals have logged time.`, exit 0. A run file that cannot be parsed is skipped with one stderr line `board_model: skipped <path>: <error> (BAD_RUN)` and a summary `skipped K of M run files`, exit 0. `est-backtest-best` checks the NO_REPO refusal (exit 1, stderr names the root and the fix) and the BAD_RUN line for CEO-41's garbled file.
- DX-2: `skills/workflow-monitoring/references/commands.md` gets a short "board_model.py" subsection: the command, `--root`, `--json`, a sample of the text and JSON output from this repo's runs, one sentence defining `off xN.N` (the median over finished goals of how many times the whole-goal estimate was off, either way; x2 means typically within half to double), the 10-goal threshold, the three refusal codes, and that `STALL_FLOOR`, `MIN_BACKTEST` and `TILT` are fixed constants in `board_model.py`. `references/operation.md` links it in one line; `board_model.py --help` ends with the example command.
- DX-3: `board_model.py --json` prints one JSON object and nothing else on stdout: `candidates` (each with `id`, `label`, `score`, `x`, `n`, `time_ordered` or null, `in_range`, `p90`, `under`, each share with its denominator), `chosen`, `reason`, `n`, `elapsed_s`, `skipped`. `est-backtest-best` reads the JSON form rather than parsing text.
- DX-4: one `LABELS` mapping next to `CANDIDATES` (`steps` -> `step medians`, `size` -> `size rule`, `blend` -> `blend`) is used by the accuracy line and the printer. The text printer shows a fixed header and one row per candidate with `id (label)`, the selection score in log units to 3 decimals and as `xN.NN`, n, then the diagnostics labeled as such (time-ordered score, in range, p90, under), `-` where a value is unavailable (a goal with no earlier finished goals has no time-ordered prediction; the denominator shows how many did). A final line states the reason: `chosen: <id>, lowest leave-one-out score`, `chosen: <id>, exact tie, first in CANDIDATES`, or `chosen: size, fewer than 10 scorable goals (N)`.
- DX-5: during a board render, `chosen` catches only `ArithmeticError`, `ValueError`, `TypeError` and `KeyError` from the backtest, falls back to `size`, prints a compact traceback to stderr, and the accuracy line reads `estimates: size rule, backtest failed (<exception name>)`. New row `est-backtest-fails` (land, MON-4, criterion, `bash dev/toy/test-estimates.sh backtest_fails`) makes `backtest` raise `ValueError` and checks the board still renders with that line; its `--break` removes the fallback.
- DX-6: `est-backtest-speed`'s limit is the larger of 3 s and twice the measured time on the build machine, rounded up to a whole second (replaces CEO-23's limit rule); the measured time is recorded in the PR.
<!-- /autoplan-accepted:dx -->

Correction to DX-3's evidence (from the Codex DX voice, verified): among the scripts, `health.py:362` offers a real `--json` flag; `board.py` and `board_status.py` do not (their "json" hits are `gh --json` calls and `board.json`). DX-3 rests on the agent persona and `health.py`, not on board_status.

#### Dual voices (DX)
Phase input: `autoplan-dx-phbK2f/dx-implementation.md`, sha256 `f54f7450...7624`.

**Claude SUBAGENT (DX — independent review), native, completed (INPUT matches).** Scores: getting started 7, ergonomics 6, errors 4 (capped), docs 6, escape hatches 4. Findings: CRITICAL CAP4 board_model.py silent skip and unspecified exit codes; HIGH CAP6 live_board render has no recovery if the backtest throws; HIGH CAP6 no codes or doc anchor for the script's failures; HIGH 41 amendments make the plan hard to build; HIGH no way to pin a model; MED names vs labels; MED "whole goal off" unclear; MED printer format and no `--json`; MED hold detection by prose; MED speed limit machine-bound; MED constants hard-coded; MED no copy-paste example.

**Codex SAYS (DX — developer experience challenge), outside, completed (`OUTSIDE_STATUS: completed provider=codex host=claude`, gpt-6-astra, 7/10).** HIGH printed `xN.N` can hide why the winner won (rounding, unlabeled second score, undefined nulls for early goals); MED CLI failure and recovery unspecified (bad `--root`, non-git, unreadable runs) and `read_json`/`git` collapse failures into "no history"; MED no structured output contract; MED docs do not guarantee a copy-paste "explain the model" example. TTHW about 3 steps; upgrade path strong.

```
DX DUAL VOICES — CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Getting started < 5 min?          yes     yes    CONFIRMED (one command, no setup)
  2. API/CLI naming guessable?         no      no     CONFIRMED gap: ids vs labels, unlabeled scores (DX-4)
  3. Error messages actionable?        no      no     CONFIRMED gap: CLI refusals, skipped files, render fallback (DX-1, DX-5)
  4. Docs findable & complete?         no      no     CONFIRMED gap: copy-paste example and xN.N meaning (DX-2)
  5. Upgrade path safe?                yes     yes    CONFIRMED (re-exports, gated move)
  6. Dev environment friction-free?    no      n/a    DISAGREE (Claude: pin override, constants, speed flake) -> taste
```
Single-voice critical: Claude's CAP4 (silent skip / exit codes) is resolved by DX-1 whatever the consensus.

#### Pass 1: Getting Started (7/10 -> 8/10)
Evidence: 0C target Champion (< 2 min), 0D vehicle the existing board line. Hello world needs no install: `/workflow-monitoring report` prints the accuracy line; `python3 skills/workflow-monitoring/scripts/board_model.py` explains it. Gap: no copy-paste example with expected output (both voices). Fixed by DX-2 (commands.md subsection with the command and sample output, linked from operation.md and `--help`). Ideal sequence: (1) ask "where do things stand?" -> board with the line (seconds); (2) `python3 skills/workflow-monitoring/scripts/board_model.py` -> per-candidate table with the chosen mark (under 1 s on real runs); (3) read the selection reason line. Residual 8: a fresh repo with fewer than 10 finished goals can only show the fallback (by design).

#### Pass 2: API/CLI/SDK design (6/10 -> 8/10)
Library surface: `bs.<name>` unchanged for every reader (CEO-1, CEO-30); new public names `backtest`, `chosen`, `accuracy_text`, `CANDIDATES` read clearly. CLI surface: `board_model.py [--root DIR] [--json]`, defaults to the current repo, read-only. Gaps: candidate ids (`steps`) differ from board labels (`step medians`) with no stated mapping; the printer's columns and the selection reason are unspecified; scores printed only as `xN.N` can tie in print (Codex 1). Fixed by DX-4. Declined: a model pin env var and `--model` flag (Claude), as a scope addition in DX POLISH that also cuts against done line 1's automatic choice; recorded under NOT in scope. Agent ergonomics: non-interactive, no prompts (CEO-18 env guard), structured output via DX-3.

#### Pass 3: Error messages and debugging, agent-ready (4/10 capped -> 8/10)
```
ERROR PATH MATRIX (agent-ready-v1)
Path                                   | Class        | what | fix | recovery | code | context | trace | redaction | channel | Cap
board_model.py --root /not/a/repo      | usage        | fail | fail| N/A      | fail | N/A     | N/A   | pass      | fail    | CAP6:fix (before)
board_model.py, runs dir unreadable    | environment  | fail | fail| fail     | fail | fail    | N/A   | pass      | fail    | CAP6:recovery (before)
board_model.py, garbled run file       | partial-work | fail | N/A | fail     | fail | fail    | N/A   | pass      | fail    | CAP4:channel (before: silent skip, exit 0 over fewer goals)
live_board render, backtest raises     | unexpected   | fail | fail| fail     | fail | fail    | pass* | pass      | fail    | CAP6:recovery (before: whole board crashes)
```
`*` Python prints a traceback today. After DX-1 and DX-5 every applicable item passes:
- `board_model.py --root /x` (not a git repo) -> stderr `REFUSED: /x is not inside a git repo (NO_REPO). Pass --root with a repo path, or run from inside one.` exit 1. Recovery implied (fix and retry, no side effects; the script is read-only).
- runs folder present but unreadable -> `REFUSED: cannot read <common>/loop/runs: <OSError text> (RUNS_UNREADABLE). Check the folder's permissions; nothing was changed.` exit 1.
- no runs folder or no finished runs (valid empty history) -> stdout `board_model: 0 of 10 scorable goals under <common>/loop/runs; the board uses the size rule until 10 finished goals have logged time.` exit 0 (success, not an error).
- garbled run file -> one stderr line per file `board_model: skipped <path>: <json error> (BAD_RUN)`, a summary `skipped K of M run files`, scores over the rest, exit 0; with `--json` the same in a `skipped` list. The board itself still renders without that run (existing `live_board.load` behavior) and does not print per-file lines.
- backtest raises during a board render -> `chosen` catches `ArithmeticError`, `ValueError`, `TypeError`, `KeyError` only, falls back to `size`, the accuracy line reads `estimates: size rule, backtest failed (ValueError)`, and a compact traceback goes to stderr. No catch-all.
Codes (`NO_REPO`, `RUNS_UNREADABLE`, `BAD_RUN`) are listed in the commands.md subsection (DX-2); taste: the repo's refusals carry no codes today, but the agent-ready contract the autoplan override requires asks for one, and a parenthesized word costs nothing. Redaction: no secrets are read. Permission model: read-only; blast radius none. Verbose mode: not needed (expected failures print no trace; unexpected ones print Python's).

#### Pass 4: Documentation (5/10 -> 8/10)
Today `references/commands.md:98` and `references/operation.md:148,164` state the size rule and the 3x stall rule (stale after this goal; CEO-5 fixes the rules). Gaps: no example, `xN.N` undefined, constants not named. DX-2: a "board_model.py" subsection in `references/commands.md` with the command, `--json`, a sample of both outputs, one sentence defining `off xN.N` (the median, over finished goals, of how many times the whole-goal estimate was off either way; x2 means typically within half to double), the 10-goal threshold, the refusal lines with codes, and that `STALL_FLOOR`, `MIN_BACKTEST` and `TILT` are fixed constants in `board_model.py`; `operation.md` links it in one line; the script's `--help` ends with the example. Monitoring.md stays Tests-only (constraint).

#### Pass 5: Upgrade and migration (8/10 -> 8/10)
No persisted format changes; run records stay read-only; every existing reader keeps its import path through re-exports (CEO-1, CEO-30) with a by-path test (CEO-3). Behavior change users notice: estimates can shift when `steps` wins, and stall lines stop below 15 minutes; both are named in the changelog by the release step. No deprecation needed. No issues found beyond that note.

#### Pass 6: Developer environment and tooling (6/10 -> 7/10)
Stdlib only; runs anywhere Python 3 and git run; non-interactive. Tests run as toy shell suites like the rest. Gap: `est-backtest-speed` tied to the build machine (Claude). DX-6: the row's limit is the larger of 3 s and twice the measured time, rounded up (replaces CEO-23's limit rule); the measured time goes in the PR. Declined: env overrides for `STALL_FLOOR`/`MIN_BACKTEST` (scope addition; documented as fixed constants instead, DX-2).

#### Pass 7: Community and ecosystem (5/10 -> 5/10)
Public template repo; this change is internal to one skill. The extension path for a new candidate (CEO-38) is the ecosystem hook. No community channel changes are in scope. No issues found that this plan should address.

#### Pass 8: DX measurement (5/10 -> 7/10)
The 0C clock ("owner asks why" -> "agent shows chosen model and scores") is measured by the by-hand verify step (CEO-10), which now names the printer command and its expected output; the printer's elapsed time (CEO-14) measures the tool's own speed. No telemetry is added (not approved, not needed for a local tool). Boomerang: `/devex-review` after shipping can rerun the verify steps.

#### Claude Code Skill DX checklist
- AskUserQuestion design: N/A (no new questions; the board prints, it does not ask).
- State storage: run records stay the per-repo store; no new state (memo is per process). OK.
- Progressive consent / auto-upgrade: N/A.
- Skill composition: the board stays inside `workflow-monitoring`; `cost.py` composition kept (CEO-3). OK.
- Error recovery: render fallback (DX-5); printer partial results with skipped count (DX-1). OK after fixes.
- Agent-readable errors: DX-1 refusal lines with codes. OK after fixes.
- Session continuity: N/A.
- Bounded autonomy: read-only feature. OK.

#### DX outputs

**Developer perspective.** As the 0B narrative, with its two predicted confusions closed by DX-2 (meaning of `off xN.N`) and DX-1 (CLI failure text).

**Competitive DX benchmark (post-review).** This board: under 1 min to the chosen model and its scores, two commands, no setup (estimated from the plan); peers show forecasts without the model choice. Tier: Champion.

**Magical moment specification.** The accuracy line under Finish (CEO-35), present on every render with no flag; the printer one command away; both covered by `est-accuracy-line` and `est-backtest-best`.

**NOT in scope (DX).** Model pin env var and printer `--model` (scope addition in POLISH; works against done line 1's automatic choice); env overrides for the constants (documented as fixed instead); a new `/workflow-monitoring estimates` command (out-of-scope opportunity); structured hold markers (deferred in CEO).

**What already exists (DX).** The `REFUSED:` refusal convention (`batch.py`, `mend.py`), `health.py --json`, `live_board.load` filters, `status_graph.span` formatting, the references pages, the by-path loader test pattern.

**TODOS.md updates.** None proposed (no TODOS.md; the deferrals above go to the PR body).

## DX Review Scorecard
```
+====================================================================+
|              DX PLAN REVIEW — SCORECARD                             |
+====================================================================+
| Dimension            | Score  | Prior  | Trend  |
|----------------------|--------|--------|--------|
| Getting Started      |  8/10  |  7/10  | ↑      |
| API/CLI/SDK          |  8/10  |  6/10  | ↑      |
| Error Messages       |  8/10  |  4/10  | ↑      |
| Documentation        |  8/10  |  5/10  | ↑      |
| Upgrade Path         |  8/10  |  8/10  | =      |
| Dev Environment      |  7/10  |  6/10  | ↑      |
| Community            |  5/10  |  5/10  | =      |
| DX Measurement       |  7/10  |  5/10  | ↑      |
+--------------------------------------------------------------------+
| TTHW                 | <1 min | <1 min*| =      |
| Competitive Rank     | Champion                                     |
| Magical Moment       | designed via the board's accuracy line       |
| Product Type         | Claude Code Skill (CLI + library surface)    |
| Mode                 | POLISH                                       |
| Overall DX           |  7/10  |  6/10  | ↑      |
+====================================================================+
| DX PRINCIPLE COVERAGE                                               |
| Zero Friction      | covered (no setup, one command)                |
| Learn by Doing     | covered (copy-paste example, DX-2)             |
| Fight Uncertainty  | covered (refusals, skipped count, DX-1/DX-5)   |
| Opinionated + Escape Hatches | gap (no pin override; declined, POLISH)|
| Code in Context    | covered (sample output from a real repo)       |
| Magical Moments    | covered (accuracy line every render)           |
| Agents Are Users   | covered (--json, non-interactive, DX-3)        |
+====================================================================+
```
`*` "Prior" is this review's pre-fix pass score (no earlier DX review exists). Community stays at 5: below 6 by nature of an internal skill change, not adoption debt this plan can pay. TTHW under 10 min: not blocking.

**DX Implementation Checklist.**
```
DX IMPLEMENTATION CHECKLIST
============================
[ ] Time to hello world < 2 min (board line + board_model.py)
[x] Installation is one command (none: ships in the skill)
[ ] First run produces meaningful output (selection reason line, DX-4)
[ ] Magical moment delivered via the accuracy line (CEO-35)
[ ] Every error message meets the agent-ready error contract (DX-1, DX-5)
[ ] API/CLI naming is guessable without docs (ids + labels, DX-4)
[x] Every parameter has a sensible default (--root = current repo)
[ ] Docs have copy-paste examples that actually work (DX-2)
[ ] Examples show real use cases (sample from this repo's runs)
[x] Upgrade path documented (re-exports; no migration needed)
[x] Breaking changes: none
[ ] Works in CI/CD without special configuration (toy suites; speed limit DX-6)
[x] Changelog maintained by the release step
N/A TypeScript types, free tier, docs search, community channel
```

**Implementation Tasks (DX).**
- [ ] **T1 (P1, human: ~1h / CC: ~5min)** — board_model CLI — Refusals with codes, skipped-file reporting, empty-history success
  - Surfaced by: Pass 3 CAP4/CAP6 (DX-1)
  - Files: skills/workflow-monitoring/scripts/board_model.py, dev/toy/test-estimates.sh
  - Verify: est-backtest-best runs the printer on a garbled file and a bad --root
- [ ] **T2 (P1, human: ~1h / CC: ~5min)** — board_model — Render fallback when the backtest raises, new row est-backtest-fails
  - Surfaced by: Pass 3 CAP6 render (DX-5)
  - Files: skills/workflow-monitoring/scripts/board_model.py, dev/toy/test-estimates.sh, .loop/regression.tsv
  - Verify: `bash dev/toy/test-estimates.sh backtest_fails` red with the fallback removed, green with it
- [ ] **T3 (P2, human: ~1h / CC: ~5min)** — board_model CLI — Labeled, precise output with selection reason and --json
  - Surfaced by: Pass 2 (DX-3, DX-4)
  - Files: skills/workflow-monitoring/scripts/board_model.py
  - Verify: est-backtest-best reads `--json` and checks chosen, reason and nulls
- [ ] **T4 (P2, human: ~1h / CC: ~5min)** — docs — board_model.py subsection with example, xN.N meaning, codes, fixed constants
  - Surfaced by: Pass 1, Pass 4 (DX-2)
  - Files: skills/workflow-monitoring/references/commands.md, skills/workflow-monitoring/references/operation.md
  - Verify: `python3 skills/workflow-docs/scripts/docs.py check` OK; the example command runs as written
- [ ] **T5 (P3, human: ~15min / CC: ~2min)** — tests — Speed row limit max(3 s, 2x measured)
  - Surfaced by: Pass 6 (DX-6)
  - Files: dev/toy/test-estimates.sh, .loop/regression.tsv
  - Verify: est-backtest-speed green on a loaded machine

**Unresolved decisions (DX).** None for the owner from this phase; the pin override is declined and listed under NOT in scope.

### Eng review (Phase 3)

Methodology read: `autoplan-eng-methodology-*/methodology.md` ranges 1-600, 601-1200, 1201-1800, 1801-2143 of 2143 (EOF). Target: this plan (scope gate auto-selected B: the plan file named by the caller). Report destination: this plan file's Review record (autoplan's ACTIVE_PLAN).

#### Step 0: Scope Challenge
**A. Assessment (code read: `board_status.py` lines 1-411, `live_board.py` 60-90 and 160-300, `cost.py` 25-40, `test-estimates.sh` 1-80 and its dispatcher, `narrow.py` and `lanes.py` headers, `health.py` 41-85).**
- What already solves each sub-problem: see the CEO "What already exists" list; new for Eng: `narrow.py` maps a toy test's `# reads:` header plus the same-folder Python imports its entry points reach (`narrow.py:1-7`), so `board_log.py` and `board_model.py` become dependencies of every test that reads `board_status.py` only if `board_status.py` imports them by plain same-folder import. `lanes_cli.py deps <test>` prints the resolved set.
- Minimum change: unchanged from CEO; nothing deferrable without failing a done line.
- Complexity check (proposed changed files, counted once): new `board_log.py`, new `board_model.py`; edited `board_status.py`, `live_board.py`, `dev/toy/test-estimates.sh`, `dev/toy/test-live-board.sh`, `.loop/regression.tsv`, `docs/wiki/Monitoring.md` (Tests only), `docs/wiki/Tests.md`, `references/commands.md`, `references/operation.md`, `.loop/goals/estimate-accuracy.md` (Verify section) = 12 files, 2 new modules. Gate trips (8+ files, 2+ new modules).
- Search check: leave-one-out cross-validation and a median of absolute log error are standard model selection on small samples [Layer 1]; stdlib `statistics` and `math` suffice; no new dependency. Search unavailable (Aside CLI error, WebSearch not loaded) — proceeding with in-distribution knowledge only.
- TODOS cross-reference: no TODOS.md in the repo; nothing blocks this plan.
- Completeness: tests for every new branch are cheap with CC; prefer full coverage (taken in Section 3).
- Distribution: no new artifact; ships in the skill folder through the existing release step.

**Premise table (Eng).**
| Premise | Claim | Receipt | Verdict |
|---|---|---|---|
| E-P1 | `narrow.py` follows same-folder Python imports from `# reads:` entry points | `narrow.py:3-6` docstring | verified (doc); runtime list checked by ENG-1 |
| E-P2 | `regression.py red` copies HEAD | `regression.py --help` ("copy HEAD, run CMD to break it") | verified |
| E-P3 | `model()` clears and refills the same `MODEL` dict | `board_status.py:190-196` | verified |
| E-P4 | `lifted_steps` drops the goal's own slug | `board_status.py:228` | verified |
| E-P5 | `flow_seconds` pauses only after stopped/failed/waiting | `board_status.py:136` | verified |
| E-P6 | test fixtures use 10 s steps for `check_stalled` | `test-estimates.sh:233-235` | verified |
| E-P7 | main has no newer change to the touched scripts or suites today | `git log origin/main --since=2026-11-10` on them: empty | verified |
| E-P8 | backtest real-data time about 0.2 s | design Budget (scratch) | unverified (re-measure, CEO-14 printer) |
unverified=1.

REALITY: premise-table finding 8 premises, unverified=1 (real-data backtest time re-measured in build) .loop/goals/estimate-accuracy.design.md:110
REALITY: already-done pass git fetch origin main; git log origin/main --since=2026-11-10 on skills/workflow-monitoring/scripts, test-estimates.sh, test-live-board.sh: no hits skills/workflow-monitoring/scripts/board_status.py:1
REALITY: surface-check pass regression.py red --break, run land; criteria.py render; goal.py touches --add --why; docs.py check; lanes_cli.py deps all verified by --help (CEO-7 fixed the one miss) skills/workflow-regression/scripts/lanes_cli.py:1
REALITY: binding-decisions pass review-decision-search --scope branch: none; owner decision and approved design; CEO/DX accepted blocks bind and are carried skills/workflow-monitoring/scripts/live_board.py:257
REALITY: numbers finding 12 files and 2 modules counted from the plan; 19,518 and 14,768 bytes measured; real-data time tagged re-measure before gate skills/workflow-monitoring/scripts/board_status.py:339
REALITY: deferred-asks pass no linked issue for this goal .loop/goals/estimate-accuracy.md:1
REALITY: pr-count pass no .review suite/ship-policy.json, one PR .loop/goals/estimate-accuracy.md:1

**B. Complexity selectors (auto-decided, recommended answers).**
1. Feature cuts: none proposed (autoplan override: never reduce scope, P2); every file serves a done line or an accepted CEO/DX obligation.
2. Structure (`plan-eng-review-structure`): `Original arrangement` = `board_log.py` (log and goal-file facts) + `board_model.py` (estimates, backtest, chooser, printer) + slim `board_status.py` (run facts, board items, re-exports): 3 modules. `Smaller arrangement` = one `board_model.py` holding both halves: 2 modules. The smaller one cannot preserve the commitments: the moved code alone is 14,768 bytes and the new code adds about 5-7 KB, past the 18,432-byte limit (spec review 2, measured). Pending remedies not decided here: none. Answer: confirm the original arrangement (auto, recommended; no smaller arrangement preserves the size commitment).
3. Scope record: feature answers: none cut; structure: A (original arrangement), auto-decision #48; accepted scope: plan sections 1-8 with CEO-1..41 and DX-1..6; pending remedies: none.

**C. Findings.**
1. [INFORMATIONAL] (confidence: 8/10) `narrow.py:3-6` — lane mapping reaches new modules only through plain same-folder imports in `board_status.py`; a `importlib` or path-built import would silently drop `board_log.py`/`board_model.py` from every toy test's dependency set, so later edits to them would reuse stale passes. Disposition: accepted as ENG-1 (P1; verification only).
2. [INFORMATIONAL] (confidence: 8/10) `test-estimates.sh:2-3` — the `# reads:` header names `board_status.py`; with plain imports no header change is needed, but the reach must be checked. Folded into ENG-1.
Scope Challenge result: scope accepted as-is.

<!-- autoplan-accepted:eng -->
- ENG-1 (Scope C1/C2): `board_status.py` imports `board_log` and `board_model` with plain same-folder `from ... import (...)` statements (no importlib or path-built import), and after the move `python3 skills/workflow-regression/scripts/lanes_cli.py deps dev/toy/test-estimates.sh` (and the same for `test-live-board.sh`) lists `board_log.py`, `board_model.py` and `board_report.py`; `est-module-size` asserts that.
- ENG-2 (native E2; replaces the script entry in CEO-24 and the file named in CEO-9, CEO-14, CEO-36, CEO-37, DX-1..4, DX-2's docs subsection title): a fourth file `skills/workflow-monitoring/scripts/board_report.py` holds the command line, the text and `--json` printer, the diagnostics (time-ordered score, in range, p90, under, per-step score, top-two gap) and the refusals; it imports `board_model` and `board_log` only. `board_model.py` stays a library (no argparse, no printing except DX-5's stderr traceback). Every command in the plan that runs `board_model.py` runs `board_report.py` instead. `est-module-size` asserts all four of `board_status.py`, `board_log.py`, `board_model.py`, `board_report.py` are under 18,432 bytes.
- ENG-3 (Codex 1, 2; native E1, E4; replaces section 5's hold-entry rule, CEO-16 and CEO-29): the pause state in `flow_seconds` is one explicit rule over the entries the repo writes. A pause starts at a hold entry (anchored: the text after the timestamp matches `session report: (?:worker · \S+: .*?; )?(?:held|holding) (?:at|before)\b`) or a free entry (`freed N session(s)` written by `sessions.py free`). A pause ends at the next entry whose first word is a flow step, `start <step>`, `bound to session`, `assigned to session`, or that contains `resum` or `no longer held`; any other entry (watch notes, `checks:`, other session reports) keeps it. On a hold entry the hold test runs before the step-naming test, so `held at step plan` pauses. The live tail: when the session pool is readable, the pool decides (held: nothing counts; not held: the tail counts from the last entry); only when the pool cannot be read does a trailing pause entry stop the tail. Negative cases: `board-held` alone, `no longer held, resuming`, `no longer held at plan, resuming`, `was held at plan, now running`, `unheld at plan`. `est-held-idle` covers: two renders an hour apart of a pool-held goal; hold -> watch note -> `start build` -> `build done` with idle and working durations told apart; free -> idle note -> `bound to session` -> `start build` -> done; pool readable, not held, last entry a hold: the tail grows.
- ENG-4 (native E5): the hold and free pause is its own commit right after the module move and before the chooser; before it, `grep -nE "held at|held before|holding before|freed [0-9]+ session" dev/toy/*.sh` lists fixtures it can change, and the full CEO-2 suite list passes after it.
- ENG-5 (native E3, Codex 4; extends CEO-23 and DX-6): per backtest, each size cell's per-step sorted time lists are built once from the cached `model()["done"]` sizes (never `size_of` per fold); a fold removes only the held-out goal's values from the cells it falls in, and `base` results are memoized per (fold, cell, step). `est-backtest-speed` has two cases: 100 finished goals with real-like sizes (limit max(3 s, twice measured)), and 300 finished goals with sizes up to (10, 8) for which a full `live_board.render` stays under 5 s (MON-9 allows 10 s).
- ENG-6 (native E6, Codex 3; owner decision UC1 pending): until the owner decides UC1, stall and overrun lines follow the chosen model's per-step table, and the `board_model.py` docstring, `references/commands.md` and the PR say so; `board_report.py` also prints each candidate's per-step score (median over scored goals and their logged steps of |ln(step estimate / step actual)|) as a diagnostic.
- ENG-7 (native E7, E8): `chosen` treats scores within 1e-9 as tied (tie goes to the first in `CANDIDATES`, reason line says tie); `board_report.py` prints the gap between the two lowest scores.
- ENG-8 (native E9): the `held` set passed to `board_items` in `live_board.py` is the same expression `stall_lines` already uses (`{r["slug"] for r in runs if is_held(r, taken)}`), so both see the same goals; still one call-site line. Replaces section 6's `{r["slug"] for r in held}`.
- ENG-9 (native E10): `est-backtest-fails` also asserts the stderr traceback appears.
- ENG-10 (native E11): `references/commands.md` states that `board_report.py` only reads files and runs `git rev-parse`; it writes nothing.
- ENG-11 (Codex 5; defines CEO-36): for the time-ordered score, a goal's start is its first log entry's timestamp and its finish is the timestamp of its last log entry that names a flow step; a goal missing either is left out of that score and counted; the printer labels it `time-ordered (retrospective, current sizes)`.
- ENG-12 (Codex 6): new row `est-backtest-loo` (land, MON-4, criterion, `bash dev/toy/test-estimates.sh backtest_loo`) checks a hand-calculated fold of three finished goals: each candidate's prediction for the held-out goal equals the value worked out by hand without that goal (including duplicate step durations and the size neighbour count), and the score equals the hand value; `--break` leaves the held-out goal in its own fold.
- ENG-13 (Codex 7; replaces CEO-39's fixture): the zero-actual case (a finished goal with no logged time) and the zero-prediction case (a degenerate history where, after exclusion, no other goal logged any step) are separate fixtures in `est-backtest-best`; each is excluded from scoring with n dropping by one and no crash.
- ENG-14 (native hidden complexity): when a `blend` (or `steps`) cell's own total is 0, the envelope target is used directly instead of a lift of 1, so the estimate never falls below the envelope; `est-steps-monotone` includes such a cell.
- ENG-15 (native test gaps): `est-backtest-best` asserts the printed `n` equals the JSON `n` and that a goal one candidate cannot estimate is dropped for all candidates; `est-recompute`'s row text notes that a running goal's `updated` change also recomputes (wasted work, not a bug).
- ENG-16 (CEO taste, native CEO 8 / DX 4 / Eng readability): the build follows the consolidated order below; where text conflicts, the later amendment wins (ENG over DX over CEO over sections 1-8).
<!-- /autoplan-accepted:eng -->

#### Dual voices (Eng)
Phase input: `autoplan-eng-iqITWI/eng-implementation.md`, sha256 `1f961b4d...10c6`.

**Claude SUBAGENT (eng — independent review), native, completed (INPUT matches).** 11 findings: E1 HIGH a stale hold entry disables stall detection when the pool has released the goal; E2 HIGH board_model.py likely over 18,432 bytes with the CLI in it; E3 MED O(N² x grid) backtest; E4 MED loose hold matcher, hold test must precede step naming; E5 MED hold pause changes history under frozen rows, needs its own gate; E6 MED chooser picked on totals drives per-step stall checks; E7 LOW-MED flips unexplained; E8 LOW exact float ties fragile; E9 LOW held set built two ways; E10 LOW catch scope, assert traceback; E11 LOW state read-only. Hidden: use cached sizes per fold; blend whole=0 guard.

**Codex SAYS (eng — architecture challenge), outside, completed (`OUTSIDE_STATUS: completed provider=codex host=claude`, gpt-6-astra, verdict findings P1).** 7 findings: 1 HIGH hold state machine misses real restart events (`start build`, `bound to session`, `assigned to session`; verified in `role.py:110-113`, `session_bind.py:67-68` and in this repo's run logs: 66 `start`, 17 `bound` entries); 2 HIGH pool-derived holds only freeze the tail, idle comes back as a gap; `sessions.py free` writes `freed ...` outside the matcher (verified `sessions.py:249`); 3 HIGH whole-goal selection does not validate the per-step estimates it controls; 4 MED no growth guard; 5 MED time-ordered diagnostic has no timestamp contract and uses current sizes; 6 MED tests check wiring, not leave-one-out correctness; 7 MED CEO-39 fixture tests zero actuals, not zero predictions. Recommendation: revise before implementation.

```
ENG DUAL VOICES — CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Architecture sound?               yes*    yes*   CONFIRMED with fixes (*4th file ENG-2; per-step coupling -> UC1)
  2. Test coverage sufficient?         no      no     CONFIRMED gaps: hold sequences, LOO hand fold, degenerate fixtures (ENG-3,12,13)
  3. Perf risks + budget/bench named?  no      no     CONFIRMED: reuse per cell, 300-goal render budget (ENG-5)
  4. Security threats covered?         yes     n/a    N/A for Codex (not raised); native: read-only CLI stated (ENG-10)
  5. Error paths handled?              partly  partly CONFIRMED: hold resume events, stale hold, zero predictions (ENG-3,13)
  6. Deployment risk manageable?       yes     n/a    N/A for Codex; native: separate commits per change (ENG-4)
```
Single-voice high findings: E1 (native) and Codex 1-2 converge on the same hold state machine and are all taken in ENG-3. Codex 3 and native E6 agree that the chooser's per-step reach is unvalidated: added to User Challenge UC1 (both voices recommend more scope or an acceptance decision), not auto-decided; interim behavior documented (ENG-6).

#### Section 1: Architecture
```
   live_board.py ──(2 call-site lines: held=, accuracy_text)──┐
   board.py ──left_time──┐                                    v
   cost.py ──by path────>├──> board_status.py  (run facts, board_items, main; re-exports both)
   toy tests ──bs.<name>─┘          │ from board_log import (...)   │ from board_model import (...)
                                    v                                v
                              board_log.py  <───────────────  board_model.py ───> status_graph.span
     (env guard, git, read_json, stamp, named/after/current,   (MODEL memo, tables steps|size|blend,
      flow_seconds + pause state, goal_file, size_of, COMMON)   one envelope, estimates, pace, stall+floor,
                                    ^                            backtest, chosen, accuracy_text, LABELS)
                                    │                                ^
                              board_report.py ─────────────────────┘   (CLI: --root, --json, printer, refusals,
                                    │                                    diagnostics; imports model + log only)
                                    v
                                 graph.py
```
Design twice: shape 1 (chosen) splits by owned knowledge: log facts, estimates, reporting. Shape 2 (sketched): a `Candidate` class per model with `table(done, size)`/`rough(...)` methods and a registry; hides the same policy behind a larger surface (class hierarchy) for three candidates; rejected (P5). Depth: `board_model` hides tables, envelope, folds and the chooser behind `estimate_full`, `chosen`, `accuracy_text`, `backtest`.
Red flags: (1) shallow module: none. (2) information leakage: the hold/free wording lives only in `board_log` (ENG-3); candidate labels only in `LABELS` (DX-4). (3) temporal decomposition: no (split by knowledge). (4) pass-through: `lifted_steps` becomes a thin call to the envelope (CEO-40); kept as a name readers use, acceptable. (5) split ownership: `MODEL` is owned by `board_model` only; `board_status` re-exports the same object. (6) two ways to do one task: re-exports mean two import paths for the same names; acceptable for compatibility, new code imports from `board_model`. (7) importable internals: tests import internals by design (toy suites). (8) hand-synced list: the re-export list duplicates the move lists; `est-module-size` fails when a reader name does not resolve (CEO-1), which is the derived check.
Production failure per path: backtest raises -> DX-5 fallback; hold wording drifts -> idle time counts again, visible as growing times (accepted residual, structured marker deferred); pool unreadable -> log-only tail rule (ENG-3).
Findings: [CRITICAL] (confidence 8/10) `board_model.py` size with CLI included — ENG-2. [INFORMATIONAL] (8/10) `live_board.py:228,252` two held sets — ENG-8. Dispositions: both accepted (auto, P5/P1).

#### Section 2: Code quality
- [INFORMATIONAL] (confidence 9/10) `board_status.py:136` `pause = (...)[1].rstrip(":") in ("stopped", "failed", "waiting")` — the new pause state must extend this one place, not add a second pause check elsewhere (ENG-3 does). Accepted.
- [INFORMATIONAL] (confidence 8/10) `board_status.py:209-213` `base` rescans all done goals per call — ENG-5 memoization. Accepted.
- [INFORMATIONAL] (confidence 7/10) `board_status.py:226-243` `lifted_steps` grid lift with `lift = target / whole if whole else 1` — the `else 1` breaks monotonicity for an empty cell under new candidates; ENG-14. Accepted.
- Shared-code rubric: one envelope function (CEO-40) has three callers (size, steps, blend tables), all in `board_model`; savings: about 20 lines not duplicated twice; shared failure blast radius: every candidate's estimate, covered by `est-monotone`, `est-steps-monotone`, `est-lift-bound`. No other extraction.
- Stale diagrams: none in touched files.
Dispositions: all accepted.

#### Section 3: Test review
Framework: bash toy suites driving inline Python (`dev/toy/test-*.sh`), rows in `.loop/regression.tsv`, run by `regression.py run land`. No CLAUDE.md testing section; no LLM/prompt changes (no eval scope).
```
CODE PATHS                                                         USER FLOWS
[+] board_log.flow_seconds                                         [+] Owner asks "where do things stand?"
  ├── [★★★ PLAN] stopped/failed/waiting pause (est-flow-seconds)     ├── [★★★ PLAN] accuracy line under Finish (est-accuracy-line)
  ├── [★★★ PLAN] hold/free pause start, resume events (held-idle)    ├── [★★ PLAN] <10 goals text (est-accuracy-line)
  ├── [★★★ PLAN] negations, past tense (est-held-idle)               └── [★★★ PLAN] backtest fails -> board up (est-backtest-fails)
  └── [★★★ PLAN] live tail: pool held / not held / unreadable        [+] Owner asks "why this model?"
[+] board_model                                                      ├── [★★★ PLAN] printer table + reason + gap (est-backtest-best)
  ├── tables steps|size|blend + envelope                             ├── [★★ PLAN] --json parity (est-backtest-best)
  │   ├── [★★★ PLAN] monotone, empty cell (est-steps-monotone)       └── [★★★ PLAN] NO_REPO / BAD_RUN (est-backtest-best)
  │   └── [★★★ EXISTING] est-monotone, est-lift-bound, issue-96    [+] Stall lines
  ├── backtest                                                       ├── [★★★ PLAN] floor 10 vs 16 min (est-stall-floor)
  │   ├── [★★★ PLAN] hand fold, no leakage (est-backtest-loo)        ├── [★★ EXISTING] 3x rule (est-stalled, 400 s data)
  │   ├── [★★★ PLAN] zero actual / zero prediction (ENG-13)          └── [★★ EXISTING] held never stalled (est-stall-held)
  │   └── [★★ PLAN] common set, n parity (ENG-15)                  [+] Upgrade
  ├── chosen                                                         └── [★★★ PLAN] every reader name resolves, cost loads (module-size)
  │   ├── [★★★ PLAN] argmin both sets (est-backtest-best)
  │   ├── [★★ PLAN] tie within 1e-9 (ENG-7, est-backtest-best Set B)
  │   ├── [★★ PLAN] <10 -> size (est-accuracy-line)
  │   └── [★★★ PLAN] exception fallback + traceback (est-backtest-fails)
  ├── memo recompute (est-recompute)          [★★ PLAN]
  └── speed 100 / 300 goals (est-backtest-speed) [★★ PLAN]
[+] board_report CLI: refusals, skipped, json [★★★ PLAN] (est-backtest-best)
[+] live_board 2 call sites                   [★★ PLAN] (est-held-idle, est-accuracy-line, test-live-board finish check CEO-28)
COVERAGE: 31/31 paths have a planned or existing test  |  QUALITY: ★★★:20 ★★:11 ★:0  |  GAPS: 0 after ENG-3,12,13,14,15
```
REGRESSION RULE: existing behavior at risk and its carried contract: (a) every `bs.<name>` reader (CEO-1/2/30 gate, no test edits); (b) frozen `est-*` rows (CEO-2 gate after the move, ENG-4 gate after the pause); (c) `est-stalled` and the live-board finish check change in data/position only (CEO-27/28), row texts unchanged; (d) cost figures unchanged (CEO-31). Contract carried from CEO/DX accepted blocks; no new question.
Test value cards: in the test plan artifact `<private review store>`. Tests made obsolete: none. Pending: UC1.
Findings: 4 gaps found and closed (hold resume sequences, LOO leakage, degenerate fixtures, empty-cell monotone). Dispositions: accepted (ENG-3, 12, 13, 14).

#### Section 4: Performance
- [INFORMATIONAL] (confidence 8/10) `board_status.py:226-243` per-fold grid recompute: O(folds x cells x steps x N); at today's 62 scorable goals about 0.2 s (design, unverified), at 300 goals with sizes to (10,8) an estimated tens of seconds without reuse (estimated from the loop counts, not measured). ENG-5 adds reuse and a 300-goal render budget of 5 s. Accepted.
- Memory: per-cell sorted lists, at most cells x steps x N floats (300 goals: under 1 MB). Fine.
- Caching: per-process memo; disk cache stays deferred (E3).
- Hot path budget: board render under MON-9's 10 s; backtest part named (0.5 s real data, 5 s at 300 goals).

#### Consolidated build order (ENG-16)
1. Grep reader names (CEO-1/30); move code into `board_log.py` and `board_model.py`, re-export, plain imports (ENG-1); run the CEO-2 gate unchanged; commit.
2. Pause state in `board_log.flow_seconds` (ENG-3) and `held` plumbing (section 5 bullets 3-4); fixture scan and full gate (ENG-4); commit.
3. `STALL_FLOOR` (section 4) and `check_stalled` 400 s data (CEO-27); commit.
4. Tables, one envelope with empty-cell guard (CEO-21/40, ENG-14), backtest with cell reuse and positivity (CEO-6/13/39, ENG-5/13), `chosen` with tie tolerance and fallback (ENG-7, DX-5), `LABELS`, `accuracy_text` (CEO-35, CEO-11); fixture audit (section 7 bullet 1, issue_96 sixth goal); commit.
5. `board_report.py` (ENG-2, DX-1/3/4, CEO-36/37, ENG-6/7/11); commit.
6. Two `live_board.py` lines (section 6 with ENG-8) and the live-board finish check (CEO-28); commit.
7. Rows: est-backtest-best, est-backtest-loo, est-accuracy-line, est-backtest-fails, est-stall-floor, est-held-idle, est-module-size, est-backtest-speed, est-steps-monotone, est-recompute (CEO-15/34 breaks, details); each committed before its `regression.py red` (CEO-4).
8. Docs: references (CEO-5, DX-2, ENG-6/10), docstrings (CEO-38), Tests re-render, goal Verify section (CEO-10); touches widen request (CEO-19); `docs.py check`; `regression.py run land`.

#### Worktree parallelization
Sequential implementation, no parallelization opportunity: every step edits `skills/workflow-monitoring/scripts/` or the one toy file, and each step's commit gates the next red run.

#### Eng required outputs
REALITY lines above (Scope Challenge A). 
PLAN_REALITY: phase=eng rows=7/7 missing=none unverified=3 verdict=complete (the checker counts the CEO premise rows too)

**NOT in scope (Eng).** In-flight / per-step accuracy replay before the chooser drives stall lines (UC1, owner); structured hold markers in session reports (deferred, CEO); disk cache of the backtest (deferred); hysteresis (declined, done line 1); a `Candidate` class registry (rejected, P5).

**What already exists (Eng).** `spread`, `base`, `lifted_steps`, `model()` memo, `flow_seconds` pause check, `stalled` held exclusion, `live_board.load` filters and `is_held`, `cost.board_status` loader, `narrow.py` import following and `lanes_cli.py deps`, `regression.py red --break`; all reused.

**Failure modes (Eng).**
```
  CODEPATH                 | FAILURE                                      | TEST                  | HANDLING           | USER SEES
  board_log.flow_seconds   | resume event not recognised, work time lost  | est-held-idle (ENG-3) | explicit end set   | correct time
  board_log.flow_seconds   | released goal frozen by stale hold entry     | est-held-idle         | pool decides tail  | stall still fires
  board_log.flow_seconds   | new hold wording unmatched                   | known forms only      | none (deferred)    | idle counts again (visible growth) 
  board_model.backtest     | held-out goal leaks into its fold            | est-backtest-loo      | n/a                | n/a
  board_model.backtest     | quadratic slowdown with history              | est-backtest-speed    | cell reuse         | board stays < 5 s at 300
  board_model.chosen       | near tie flips model between renders         | Set B tie             | 1e-9 tolerance     | model name on line changes
  board_model.chosen       | backtest raises                              | est-backtest-fails    | narrow fallback    | "backtest failed (X)"
  board_model envelope     | empty cell lift drops below envelope         | est-steps-monotone    | ENG-14 guard       | n/a
  board_report CLI         | bad root / garbled file                      | est-backtest-best     | REFUSED / BAD_RUN  | refusal line / skipped count
  board_status import      | name not re-exported                         | est-module-size       | loud ImportError   | board error (caught pre-merge)
```
Critical gaps (no test, no handling, silent): 0. The unmatched-wording row has no handling but is not silent (times visibly grow) and is tested for every known form.

**TODOS.md updates (all phases).** The repo has no TODOS.md, and creating one would touch a file outside the goal's Touches; autoplan's auto-write is therefore recorded here for the PR body instead (taste decision #61): E1 calibrated ranges from fold errors; E3 disk cache of the backtest; structured `hold:`/`free:` markers in session reports (`sessions.py`); delivery forecasting with worker capacity (Codex CEO 1); challenge to the frozen `est-monotone` criterion (Codex CEO 6); in-flight/per-step accuracy replay (UC1 if deferred).

**Implementation Tasks (Eng).**
- [ ] **T1 (P1, human: ~2h / CC: ~10min)** — board_log — Pause state machine over real events, pool-decided tail
  - Surfaced by: Codex Eng 1-2, native E1/E4 (ENG-3, ENG-4)
  - Files: skills/workflow-monitoring/scripts/board_log.py, dev/toy/test-estimates.sh
  - Verify: `bash dev/toy/test-estimates.sh held_idle`
- [ ] **T2 (P1, human: ~1h / CC: ~5min)** — board_report — Split the CLI and diagnostics out of board_model
  - Surfaced by: native E2 (ENG-2)
  - Files: skills/workflow-monitoring/scripts/board_report.py, skills/workflow-monitoring/scripts/board_model.py
  - Verify: `bash dev/toy/test-estimates.sh module_size`
- [ ] **T3 (P1, human: ~2h / CC: ~10min)** — board_model — Cell reuse, tie tolerance, empty-cell guard
  - Surfaced by: native E3/E8, hidden complexity, Codex 4 (ENG-5, 7, 14)
  - Files: skills/workflow-monitoring/scripts/board_model.py
  - Verify: `bash dev/toy/test-estimates.sh backtest_speed steps_monotone`
- [ ] **T4 (P1, human: ~1h / CC: ~10min)** — tests — Hand-calculated LOO fold row and degenerate fixtures
  - Surfaced by: Codex 6-7 (ENG-12, 13, 15)
  - Files: dev/toy/test-estimates.sh, .loop/regression.tsv
  - Verify: `python3 skills/workflow-regression/scripts/regression.py red est-backtest-loo --break '<keep held-out goal>'` then green
- [ ] **T5 (P2, human: ~30min / CC: ~5min)** — live_board + docs — Same held set, read-only note, per-step coupling note
  - Surfaced by: native E9/E11, E6 (ENG-6, 8, 10)
  - Files: skills/workflow-monitoring/scripts/live_board.py, skills/workflow-monitoring/references/commands.md
  - Verify: `bash dev/toy/test-live-board.sh`; `python3 skills/workflow-docs/scripts/docs.py check`

**Completion summary (Eng).**
- Step 0: Scope Challenge — scope accepted as-is
- Reality rows: 7/7 applicable rows emitted (PLAN_REALITY below), 1 unverified premise
- Architecture Review: 2 issues found
- Code Quality Review: 3 issues found
- Test Review: diagram produced, 4 gaps identified
- Performance Review: 1 issue found
- NOT in scope: written
- What already exists: written
- TODOS.md updates: 6 items recorded for the PR (no TODOS.md)
- Failure modes: 0 critical gaps flagged
- Unresolved decisions: 1 in this review (UC1, shared with CEO)
- Outside voice: codex (gpt-6-astra), completed
- Parallelization: 1 lane, 0 parallel / 8 sequential
- Lake Score: N/A (no coverage-scored questions asked)


<!-- AUTONOMOUS DECISION LOG -->
## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | Intake | Do not upgrade review suite 1.92 -> 1.99 mid-run | Mechanical | P6 | Installed skills must not change under a running phase guard | Upgrade now |
| 2 | Intake | Treat run as unattended: recommended answers, no approval | Mechanical | caller instruction | Caller set unattended; session echoed interactive | Prose questions |
| 3 | CEO 0E | Mode SELECTIVE EXPANSION | Mechanical | autoplan override | Adds capability to an existing board | Other modes |
| 4 | CEO 0D | Keep design Approach B | Mechanical | P1 | A fails done line 4; C rewrites frozen rows | A, C |
| 5 | CEO Step 0 | CEO-1 re-export list by grep (span, ASKING) | Mechanical | P1 | Readers use names the plan missed | Hand list |
| 6 | CEO Step 0 | CEO-2 gate = every reader suite | Mechanical | P1 | 6 suites were missing or wrong | Plan's list |
| 7 | CEO Step 0 | CEO-3 cost.py load must return a module | Mechanical | P1 | cost.py hides import errors as UNREAD | Weak check |
| 8 | CEO Step 0 | CEO-4 commit before each red | Mechanical | P6 | red copies HEAD | Red on working tree |
| 9 | CEO Step 0 | CEO-5 update reference docs | Mechanical | P1 | They state the 3x and size rules | SKILL.md line |
| 10 | CEO Step 0 | CEO-6 backtest reuses queued tables, candidate in memo key | Mechanical | P4 | lifted_steps already excludes own slug | New fold code |
| 11 | CEO Step 0 | CEO-7 `regression.py run land` | Mechanical | surface check | `--level` does not exist | Wrong flag |
| 12 | CEO 0G | CEO-8 no SKILL.md edit | Mechanical | P5 | It states no estimate rule | Edit it |
| 13 | CEO 0G | E2 backtest printer accepted (CEO-9) | Mechanical | P2 | In blast radius, minutes | Skip |
| 14 | CEO 0G | E4 fill Verify by hand (CEO-10) | Taste | P1 | Release needs it; goal file is outside touches | Leave empty |
| 15 | CEO 0G | E6 `N of 10 goals` (CEO-11) | Mechanical | P5 | One format string | Plain count |
| 16 | CEO 0G | E1 calibrated ranges deferred | Mechanical | P3 | Rewrites frozen rows | Add now |
| 17 | CEO 0G | E3 disk cache deferred | Mechanical | P3 | 0.2 s today | Add now |
| 18 | CEO 0G | E5 error per goal line skipped | Mechanical | P5 | Premise 5, 60 columns | Add |
| 19 | CEO 0G | E7 health size rule skipped | Mechanical | P4 | Duplicate | Add |
| 20 | CEO R3-6 | CEO-12 success = chosen equals argmin | Mechanical | P5 | x2.3 measured before hold pause | Pass on x2.3 |
| 21 | CEO 0H | Spec review 1 fixes CEO-13..23 | Mechanical | P1 | 17 reviewer issues, all valid against code | Ignore |
| 22 | CEO 0H | Spec review 2 fixes CEO-24..26 (board_log split) | Mechanical | P5 | board_model would pass 18 KB; split avoids cycle | Fallback split |
| 23 | CEO 0H | Spec review 3 fixes CEO-27..34 | Mechanical | P1 | Would turn est-stalled and live-board red | Ignore |
| 24 | CEO 0H | Approve CEO documents (A) | Mechanical | recommended | Both inputs match decisions | Revise, pause |
| 25 | CEO voices | CEO-35 accuracy line says "whole goal" | Mechanical | P5 | Both voices: score is for queued goals | Old wording |
| 26 | CEO voices | UC1 in-flight scoring queued for the gate | User Challenge | never auto | Both voices recommend adding scope | Auto-add |
| 27 | CEO voices | CEO-36 time-ordered score in printer | Taste | P1 | Both voices; diagnostic only | Skip |
| 28 | CEO voices | CEO-37 coverage, tail, underestimate share in printer | Taste | P1 | Both voices; cheap | Skip |
| 29 | CEO voices | Hysteresis declined | Taste | done line 1 | Board must use lowest error | Switching margin |
| 30 | CEO voices | Structured hold marker deferred | Mechanical | P3 | Changes sessions.py report protocol | Add now |
| 31 | CEO voices | CEO-38 docstring on tilt and extension path | Mechanical | P5 | Honest about size-light models | Silent |
| 32 | CEO voices | Plan readability: Eng adds consolidated build order | Taste | P5 | 34+ amendments | Rewrite sections |
| 33 | CEO voices | Delivery forecast and monotone challenge as follow-ups | Mechanical | P3 | Outside done lines | Add now |
| 34 | CEO S2 | CEO-39 positive-estimate scoring set | Mechanical | P1 | ln(0) crash | Unguarded |
| 35 | CEO S5 | CEO-40 one envelope function | Mechanical | P4 | Three copies otherwise | Copies |
| 36 | CEO S6 | CEO-41 garbled run file in fixture | Mechanical | P1 | Chaos case | Skip |
| 37 | DX 0A-0E | Product type skill+CLI+library, persona operation agent, target Champion, vehicle board line, mode POLISH | Mechanical | P6/P5 | Docs name the operation agent as reader; one-command vehicle exists | Other personas, new command |
| 38 | DX 0F | DX-1 refusal convention with codes, skipped-file reporting | Mechanical | P1 | CAP4 silent skip; both voices | Traceback |
| 39 | DX 0F | DX-2 commands.md subsection with example and xN.N meaning | Mechanical | P1 | Both voices | Prose only |
| 40 | DX 0F | DX-3 printer --json | Mechanical | P1 | Both voices; agents are the readers | Text only |
| 41 | DX P2 | DX-4 LABELS, precise scores, selection reason | Mechanical | P5 | Both voices | xN.N only |
| 42 | DX P3 | DX-5 narrow render fallback, row est-backtest-fails | Taste | P1 | Claude only; board is the status surface | Crash |
| 43 | DX P3 | Error codes in refusals | Taste | P1 (override) | Contract asks for a code; repo has none today | No codes |
| 44 | DX P2 | Model pin env var and --model declined | Taste | P5 / done line 1 | Scope addition in POLISH | Add pin |
| 45 | DX P6 | DX-6 speed limit max(3 s, 2x measured) | Mechanical | P3 | Flake on slow machines | 2x only |
| 46 | DX P6 | Constants documented as fixed, no env overrides | Mechanical | P5 | POLISH, no additions | Env overrides |
| 47 | DX voices | Accuracy line keeps CEO-35 wording; docs define it | Taste | P5 | Claude wanted "median error" | Change line |
| 48 | Eng 0B | Structure: original arrangement (no smaller one fits 18,432 bytes) | Mechanical | P5 | Measured sizes | Single module |
| 49 | Eng 0C | ENG-1 plain imports + lanes deps check | Mechanical | P1 | Lane reuse could go stale | No check |
| 50 | Eng S1 | ENG-2 fourth file board_report.py | Mechanical | P5 | Protects done line 4 size | Fallback later |
| 51 | Eng voices | ENG-3 pause state over real events, pool-decided tail (replaces CEO-16/29) | Mechanical | P1 | Codex verified events; native E1 | Phrase-only pause |
| 52 | Eng voices | ENG-4 pause its own commit and gate | Mechanical | P6 | Frozen rows' history moves | Bundle |
| 53 | Eng S4 | ENG-5 cell reuse + 300-goal render budget | Mechanical | P1 | Both voices | 100-goal only |
| 54 | Eng voices | Per-step validation added to UC1; ENG-6 documents interim behavior | User Challenge | never auto | Both voices want more scope or an acceptance decision | Auto-add |
| 55 | Eng voices | ENG-7 tie tolerance + top-two gap | Mechanical | P5 | Float ties fragile | Exact ties |
| 56 | Eng voices | ENG-8 same held expression as stall_lines | Mechanical | P5 | Keeps two call-site lines | held_slugs variable |
| 57 | Eng voices | ENG-9/10 traceback assert, read-only note | Mechanical | P1 | Cheap | Skip |
| 58 | Eng voices | ENG-11 time-ordered contract, labeled retrospective | Mechanical | P5 | Codex 5 | Undefined |
| 59 | Eng voices | ENG-12 hand-calculated LOO row | Mechanical | P1 | Codex 6 | Wiring only |
| 60 | Eng voices | ENG-13/14/15 degenerate fixtures, empty-cell guard, n parity | Mechanical | P1 | Codex 7, native hidden | Skip |
| 61 | Eng TODOS | Deferred items recorded in plan/PR, no TODOS.md created | Taste | P3 | No TODOS.md; outside Touches | Create TODOS.md |
| 62 | Eng | ENG-16 consolidated build order, later amendment wins | Taste | P5 | Readability raised in 3 phases | Rewrite sections |

## review suite REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` (via /autoplan) | Scope & strategy | 1 | ISSUES OPEN (not persisted to review log; unattended, no approval) | 7 proposals, 3 accepted, 2 deferred |
| Outside Review | codex (gpt-6-astra), /autoplan CEO, DX, Eng | Independent 2nd opinion | 3 | completed | CEO 7, DX 4, Eng 7 findings; all dispositioned, 1 to owner (UC1) |
| Eng Review | `/plan-eng-review` (via /autoplan) | Architecture & tests (required) | 1 | ISSUES OPEN (not persisted) | 10 issues, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | SKIPPED (no UI scope) | — |
| DX Review | `/plan-devex-review` (via /autoplan) | Developer experience gaps | 1 | ISSUES OPEN (not persisted) | score: 6/10 → 7/10, TTHW: <1 min → <2 min |

- **OUTSIDE COVERAGE:** codex gpt-6-astra completed in CEO (7 findings), DX (4 findings) and Eng (7 findings); Design skipped (no UI scope).
- **CROSS-MODEL:** native Claude subagents and Codex agreed on queued-vs-live scoring (CEO, Eng), printer diagnostics, CLI refusals and `--json` (DX), hold-state gaps and backtest growth (Eng); they disagreed on whether delivery forecasting is the bigger problem (CEO) and on a model pin override (DX, Claude only).
- **VERDICT:** no review CLEARED (autoplan stops at the Final Approval Gate; review logs are written only on approval); eng review required.

**UNRESOLVED DECISIONS:**
- UC1: score in-flight / per-step estimates before the chosen model drives stall and overrun lines (owner; recommended: defer to a follow-up goal, keep the whole-goal label and the per-step diagnostic)
- Plan approval at the Final Approval Gate (owner; recommended: approve as-is)
