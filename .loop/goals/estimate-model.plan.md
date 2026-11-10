<!-- /autoplan restore point: "<review tmp>/loop-estimate-model-autoplan-restore-20261110-010426.md" -->
# Plan: estimate-model

Goal: `.loop/goals/estimate-model.md` (6 frozen done lines). Design: `.loop/goals/estimate-model.design.md` (Approach A, nearest-size medians).

## URGENT, outside this plan

None.

## Implementation plan

### 1. Goal size (done line 1)
- `skills/workflow-monitoring/scripts/graph.py`: add `area(path)` and `size(done, touches)`.
  - `area(path)`: a path under `skills/` folds to its first two parts (`skills/workflow-monitoring/scripts/x.py` -> `skills/workflow-monitoring`); any other path with a folder folds to its first part (`dev/toy/t.sh` -> `dev`, `.github/workflows/x.yml` -> `.github`, `docs/wiki/Home.md` -> `docs`, `.loop/docs.tsv` -> `.loop`); a root file is its own area (`README.md`).
  - `size(done, touches)` returns `(d, a)`: the done-line count and the count of distinct areas; `None` when either list is missing or empty.
- `skills/workflow-monitoring/scripts/board_status.py`: `size_of(run, root)` resolves a goal's size with one precedence for every state: the goal file wins (`.loop/goals/<slug>.md` in the run's worktree, then in the main checkout: its numbered Done lines and its `- Touches:` line), then the queue line (`graph.parse`), then the run record's `touches` with the goal file's done lines. Measured 2026-11-10: 57 of 57 finished runs resolve both counts.

### 2. Estimate model in `board_status.py` (done lines 1, 2, 3)
- **Similar goals** for a size `(d, a)`: finished runs (status `done`, other slug, known size) with `|d_i - d| <= 1` and `|a_i - a| <= 1`. The goal-level similar count is the number of such runs for the goal's own size.
- **Per step**, with `s = d + a`:
  1. Rates: for each similar goal that logged the step (time > 0 from `seconds_by_step`), `rate_i = t_i / s_i`. If none, the rates of every finished goal of known size that logged the step (scaled fallback).
  2. `raw(d, a) = s x median(rates)`; `low = s x q25`, `high = s x q75` with `statistics.quantiles(rates, n=4, method="inclusive")`; with one rate, low = high = raw.
  3. Monotone envelope: `est(d, a) = max over d' <= d, a' <= a, d' + a' >= 1 of raw(d', a') x s / (d' + a')`. Grid points with no rates are skipped; a step with no rates at any size has no estimate. Strictly larger for a componentwise larger size whenever the step's estimate is positive.
  4. Monotonicity wins over the similar range: `high` widens to `est` when the envelope lifts it; `low` narrows to `est` if needed, so `low <= est <= high` always.
  5. Unknown size: unscaled median, q25 and q75 of the step's times over all finished goals; always rough.
- **Goal estimate**: the sum over the steps still to run of each step's (est, low, high). Finished steps add zero. `left_time` keeps returning the summed estimate in seconds, so the Finish line and status graph keep working; a new `estimate(run, runs, at, root)` returns `(left, low, high, rough)`.
- **Rough**: similar count under 5, or unknown size.
- **Pace (running goals)**: pace = sum of actual times / sum of estimates over finished steps that had an estimate; 1 with none; clamped to 0.5..2. It multiplies est, low and high of the current step (before it overruns) and of every remaining step. Past its pace-adjusted estimate, the current step uses `step_left`'s re-estimate as today.
- **Text**: `estimate_text(left, low, high, rough)` returns `"<low> to <high> left"` with `status_graph.span` on each end (for example `20m to 45m left`), a single `"<x> left"` when low and high round to the same span, plus `", rough"`; `"no estimate yet"` when there is no estimate.
- Cache: the board computes per-step rates once per render (a dict keyed by step and size) so the envelope grid stays cheap.

### 3. Stalled (done line 4, issue 37)
- `board_status.stalled(run, runs, at, root)` returns `(step, spent, estimate)` when a running goal's current step has run more than 3 times its pace-adjusted estimate (taken before any `step_left` re-estimate). A step with no estimate is never stalled.

### 4. Board call sites: `skills/workflow-monitoring/scripts/live_board.py` (about 4 lines; approved by the operation session 2026-11-10)
- The running-goal bar and the queued-goal line call `bs.estimate_text(...)` instead of formatting `left` themselves.
- `issues(...)` appends, for each stalled run, `- <slug> is stalled: <step> has run <spent> (estimate <est>)` and `    fix: check its worker session; stop and resume the goal if it is stuck`.
- The PR's touches note names `live_board.py` as outside the goal's touches, approved.

### 5. Tests: new `dev/toy/test-estimates.sh` (done lines 1-5)
- Fixture runs in a throwaway common dir (`loop/runs/*.json` with logs giving step times) and goal files, so `board_status` reads them as on a real repo; a `# reads:` header naming `skills/workflow-monitoring/scripts/`.
- Checks: area folding examples; size precedence (goal file over queue line); similar set selection; scaled fallback gives different estimates for sizes 3 and 12 when nothing is similar; one-rate range; monotone envelope (larger size strictly longer); range text and `rough` under 5 similar and not at 5; pace refinement shrinks and grows the estimate within 0.5..2; stalled at more than 3x and not at 3x, never without an estimate; the issue 96 defect case: two queued goals of sizes 3 (2 done lines, 1 area) and 12 (7 done lines, 5 areas) get different estimates, each between the min and max of its similar goals' scaled times.
- Regression rows in `.loop/regression.tsv` for each check, MON-4 for the requirement rows and `#96` / `#37` for the defect rows; each seen failing once with `regression.py red --break`.

### 6. Docs (done line 6)
- `docs/wiki/Monitoring.md`: Given/When/Then scenarios under MON-4 linked to the rows, and the Tests section re-rendered with `criteria.py render`. The requirement lines themselves (MON-1..) are not edited (re-approved by the owner 2026-11-10); conflicts with the monitoring-prd goal stay small because only the MON-4 scenarios and the generated Tests change.
- `skills/workflow-monitoring/SKILL.md` / references: one line on how estimates are made; `docs.py check` stays OK.


<!-- autoplan-accepted:ceo -->
- CEO-D1 (replaces section 2 steps 1-4 and the Rough bullet's meaning of "similar"): per step, the base estimate is `s x median(rates)` over the similar goals that logged the step when the goal-level similar count is at least 5; with fewer than 5 similar goals (rough), it is `s x median(rates)` over every finished goal of known size that logged the step (done line 1's fallback to all finished goals). A step that none of 5+ similar goals logged also uses the pooled rates. Unknown size keeps section 2 step 5 (unscaled, always rough, no lift). low and high are `s x q25` and `s x q75` of the same rate set (`statistics.quantiles(n=4, method="inclusive")`; one rate gives low = high = raw).
- CEO-D1 (replaces section 2 step 3's per-step rescaled envelope): monotonicity is applied to the whole-goal total. `total(d, a)` = sum over all seven steps of the base estimate. `lifted(d, a) = max(total(d, a), lifted(d-1, a) + U, lifted(d, a-1) + U)` over d, a >= 0 with d + a >= 1 (memoized; out-of-range neighbours skipped), where `U` = sum over steps of the q25 of every finished goal's per-unit rate (one size unit's worth of time). `lift = lifted / total` (1 when total is 0). Every step's est, low and high for that goal are multiplied by `lift`, so low <= est <= high holds and per-step estimates stay available to pace and the stall check. A componentwise larger size always gets a strictly larger whole-goal estimate when U > 0.
- CEO-D1 verification: the toy test asserts (a) for sizes (2,1) < (4,2) < (7,5) the queued estimates strictly increase; (b) with fixtures where lift is 1, the issue 96 sizes 3 and 12 each sit between the min and max of their similar goals' scaled times; (c) a fixture where a small size has a high per-unit rate shows the large size's estimate under 3x its unlifted total (no runaway envelope); (d) with 4 similar goals the estimate equals the pooled-rate estimate and reads rough, with 5 it uses the similar set and does not.
- CEO-D2: a queued goal's size comes from its queue line: `live_board.py` passes the parsed queue item (`dict(g, status="queued")`) and `root` for queued and freezing goals, and `size_of` reads `done` and `touches` from the run dict when no goal file exists (precedence stays goal file, then queue line, then run record touches with goal-file done lines). The items' `left` that feeds the Finish line comes from the same `estimate(...)` as the shown range. `left_time(run, runs, at, root=None)` stays backward compatible for `board.py`. Verification: the issue 96 defect test drives `live_board.render` on a fixture repo with two queued lines (sizes 3 and 12) and asserts their two rendered estimates differ and the Finish line uses the larger chain.
- CEO-E1: a running goal whose step is outside STEPS (checks, release) is estimated and stall-checked from its last known flow step: `live_board` passes `current(run)`'s index to `estimate`/`stalled`; board_status does not duplicate that logic. Verification: toy check that a goal at `checks` after build is not estimated as if at idea.
- CEO-D3: existing board toy tests whose assertions pin the old estimate text (`dev/toy/test-live-board.sh:61`, `dev/toy/test-status-graph.sh:66`, `dev/toy/test-workers.sh:129`, `dev/toy/test-board-estimates.sh:42,51`) are updated to the new text (range or single value, optional `, rough`) without weakening what they check; all board toy tests (test-board, test-board-held, test-board-estimates, test-live-board, test-status-graph, test-workers, test-narrow, test-operate-fit) pass, and no board line exceeds 60 columns.
- CEO-D4: the PR body carries `Closes #96` and `Closes #37`.
- CEO-SR1 (spec review round 1, Completeness 1 and CEO-E1): at an off-flow step (checks, release) the time since the last log entry counts toward the last known flow step, so `spent` for the stall check and pace is that flow step's logged time plus the off-flow gap. Verification: toy checks that a goal at `checks` after build is estimated from review onward, and that one sitting at `checks` past 3x build's estimate shows as stalled naming build.
- CEO-SR2 (Completeness 2, Consistency 2; done line 5): the issue 96 defect fixture gives each of the two sizes (3 = 2 done lines + 1 area; 12 = 7 done lines + 5 areas) at least 5 finished goals of exactly that size and no finished goal of a neighbouring size, so the similar set is used (not pooled), scaled times equal actual times, and lift is 1 by construction; the test asserts each rendered estimate lies between the min and max of its similar goals' actual times, and that the two differ. The lifted case is covered separately by CEO-D1 check (c).
- CEO-SR3 (Completeness 3): a freezing goal with no queue line, or any goal with no goal file, no queue line and no run touches, is unknown size: unscaled, rough, no lift.
- CEO-SR4 (Consistency 3; done line 2): `estimate_text` always prints both ends, `"<low> to <high> left"` (for example `30m to 30m left` when they round equal), plus `", rough"` when rough; this replaces section 2's single-value collapse.
- CEO-SR5 (Consistency 4): section 2's Cache bullet now reads: once per render, cache each finished run's size and `seconds_by_step`, the rate sets per (step, size) and the `lifted(d, a)` memo. Section 5's "monotone envelope" check now reads "whole-goal running max: a componentwise larger size gets a strictly longer queued estimate".
- CEO-SR6 (Clarity 1, 2): every grid point `(d', a')` in `lifted` uses its own similar count (>= 5: similar rates, else pooled); the goal itself is excluded from similar sets, pooled rates and `U` (other slugs only). Pace and the stall threshold use the lifted per-step estimates (pace-adjusted for the stall threshold).
- CEO-SR7 (Clarity 3): final signatures: `estimate(run, runs, at, root=None, here=None)` returns `(left, low, high, rough)` or `None` when no step has an estimate; `stalled(run, runs, at, root=None, here=None)` returns `(step, spent, est)` or `None`; `left_time(run, runs, at, root=None, here=None)` returns `estimate(...)[0]` (or `None`, or 0 when done); `here` is the flow index from `live_board.current`, defaulting to today's rule when omitted (board.py).
- CEO-SR8 (Scope 2): the PR's touches note names every file outside the goal's Touches line: `live_board.py` (approved call sites), `.loop/regression.tsv`, `docs/wiki/Monitoring.md`, and the workflow-monitoring SKILL.md or reference edited.
- CEO-SR9 (Feasibility 1): all logic stays in `board_status.py`; `live_board.py` gets call-site edits only, and after the build both scripts are under 20 KB (`workflow-health check` script-size rule passes).
- CEO-SR10 (round 2, Completeness 1): `overrun()` (the flow line's "over by") uses the same lifted, pace-adjusted per-step estimate and the same `here` as `estimate` and `stalled`, so the board shows one model.
- CEO-SR11 (Completeness 2): `here` 7 (release) or a done goal has no steps left: `estimate` returns `(0, 0, 0, False)` and `estimate_text` prints today's `<1m left` for a zero estimate (the only single-value case; no range for nothing left).
- CEO-SR12 (Completeness 3; extends CEO-D3): every `dev/toy/test-*.sh` passes after the change, not only the board tests named in CEO-D3; any other test that pins the old estimate or over-by text is updated the same way.
- CEO-SR13 (Completeness 4, Consistency 1; replaces CEO-SR1's verification wording): off-flow time belongs to the last known flow step: every log gap after the last flow-step entry, whatever off-flow words (checks, lane names) it is logged under, plus the gap since the last entry, counts toward that flow step. A new helper in `board_status.py` computes this on top of `seconds_by_step`, which stays unchanged for `workflow-health/scripts/cost.py`. So a goal at `checks` after build keeps build as its current step (re-estimated by `step_left` once over) and is estimated as build plus review onward, never from idea; it is stalled naming build when build's counted time passes 3x build's pace-adjusted estimate. Pace and stall use this same rule.
- CEO-SR14 (Consistency 2; replaces section 4's "about 4 lines"): the `live_board.py` call-site edits are about 9 lines (items' left and `here` for running, queued and freezing goals; bar and queued text through `estimate_text`; the stall lines in `issues`). This exceeds the operation session's "about 4 lines" approval and is an owner decision at the final gate. If `live_board.py` would pass 20 KB, the stall lines' formatting moves into a `board_status` helper so `issues` adds one line.
- CEO-SR15 (Consistency 3): the estimate model's reading of done line 1 is the scaled median: per-unit rates (time / size) of similar goals, times this goal's size, falling back to the same over all finished goals. It equals the median actual time when sizes match and is what makes a larger goal longer; the PR body states this reading. Tests claim "inside the similar goals' actual range" only for the exact-size fixture of CEO-SR2.
- CEO-SR16 (Clarity 1): the defect test asserts the Finish line's time equals `at + max(left_3, left_12)` (the two queued goals are independent), using the same seconds the two rendered ranges come from.
- CEO-SR17 (Clarity 2): known sizes have d >= 1 and a >= 1 (`size` returns None otherwise), so the `lifted` grid starts at (1, 1); neighbours with d = 0 or a = 0 are skipped; `lifted(1, 1) = total(1, 1)`.
- CEO-SR18 (Clarity 3): a step with no rates in either the similar or the pooled set has no estimate; lift scales only existing estimates and never creates one; such a step is never stalled.
- CEO-SR19 (Scope 1, 2): CEO-E1 and CEO-SR13 (off-flow handling) are autoplan expansions in the blast radius of `left_time`, listed for the owner at the final gate. `.loop/regression.tsv` and `docs/wiki/Monitoring.md` are required by done line 6 itself. The PR's touches note also says `board_runs.py` (named in Touches) was not changed.
- CEO-SR20 (round 3, Completeness 1): the gap since the last log entry counts only while the goal's status is `running` (as `seconds_by_step` does today); pace and the stall check run only for `running` goals, so a `waiting`, failed or stopped goal is never stalled. Toy check: a `waiting` goal sitting far past 3x its step estimate is not under Issues as stalled.
- CEO-SR21 (Completeness 2): `U` sums, over the steps that have pooled rates, the q25 of those rates; a step with no pooled rates adds nothing; a step with one rate adds that rate.
- CEO-SR22 (Completeness 3): held goals pass `current(run)` as `here` and their queue/run dict, like running goals.
- CEO-SR23 (Consistency 1; refines CEO-SR13): the flow step that off-flow time counts toward is `FLOW[here]` from `live_board.current` (one source for the bar, the estimate, the over-by and the stall line); with `here` omitted (board.py), the last flow-step entry in the log.
- CEO-SR24 (Consistency 2; clarifies section 1 precedence): done lines come from the goal file when it exists, else the queue line's `done`; touches come from the goal file's `- Touches:` line when present, else the queue line's `touches`, else the run record's `touches`.
- CEO-SR25 (Clarity 1): CEO-D1 check (d) uses a fixture whose lift is 1 (no smaller size with a higher total).
- CEO-SR26 (Clarity 2): the stall line prints `(estimate <est>)` as the pace-adjusted lifted step estimate, the same number the 3x test uses, via `status_graph.span`.
- CEO-SR27 (Clarity 3; replaces CEO-SR9's "passes"): both scripts stay under 20,480 bytes (no FAIL on the script-size rule). `live_board.py` is already over the 90% WARN line (18,646 bytes) before this goal; WARN is accepted, FAIL is not.
- CEO-V1 (dual voices + backtest; replaces CEO-D1's base estimate and CEO-SR15's scaled-median reading): the per-step base estimate is the plain median of the actual step times of the similar goals that logged the step when the goal-level similar count is at least 5, else of every finished goal that logged it (done line 1 read literally). low and high are the q25 and q75 of the same times (one time: low = high). The goal-level running max of CEO-D1 (`lifted`, `U`, `lift`, grid from (1, 1)) is unchanged and is what makes a larger goal longer. CEO-SR2's fixture then needs no exact-size trick for the range claim, but keeps it so lift is 1. Measured leave-one-out on 56 finished runs (median absolute log error of the whole-goal estimate): today's size-blind median x2.43, scaled base x2.94, scaled + lift x3.67, plain-median base + lift x3.49; this variant is the most accurate of the ones that meet done line 1.
- CEO-V2: the PR body reports that backtest (old vs new median error and the q25-q75 coverage, about 24 of 56) so the owner sees that the size rule costs accuracy on this repo's history; the docs line in section 6 says the range is the summed per-step quartiles, not a calibrated interval.
- CEO-V3: an estimate is also rough when any remaining step has no estimate (missing history), in addition to fewer than 5 similar goals or unknown size.
- CEO-V4: the stall lines' formatting lives in a `board_status` helper from the start (not only as a size fallback), so `live_board.issues` adds one call; a stalled goal that is also quiet shows both lines (slow and silent are different facts).
- CEO-V5: the defect test's fixture leaves `parallel` unset (unlimited), so the Finish line's `at + max(left_3, left_12)` holds; the Finish line's slot-blind assumption is unchanged (pre-existing, NOT in scope).
- CEO-S1 (Sections 2, 3): `size_of` builds a goal-file path only for a slug matching `graph.SLUG`, catches only `OSError` and parse misses (no catch-all), and falls through the precedence to unknown size; toy check: an unreadable goal file and a slug with `..` both give a rough unknown-size estimate while the board still renders.
- CEO-S2 (Section 5): the model splits into `step_estimates(size, model)` (per-step est/low/high for a size) and `estimate(...)` (remaining steps, pace, overrun, off-flow), each with at most 5 branches.
- CEO-S3 (Section 7): `board_status.py` wall time on this repo is measured before and after (stated in the PR); the change adds under 0.5 s per render.
<!-- /autoplan-accepted:ceo -->

<!-- autoplan-accepted:eng -->
- ENG-1 (Step 0): goal-file done lines are the top-level `N. ` lines between `## Done lines` and the next `## ` heading, outside code fences (numbered `## Verify by hand` steps never count); the Touches line is `- Touches:` split on commas. Verification: a toy goal file with 3 done lines, 4 numbered verify steps and a fenced numbered list counts d = 3; a goal file with no Done section gives unknown size.
- ENG-2 (Step 0): the per-render model is keyed by content (`at`, `root`, and each run's slug, status and `updated`), never by `id(runs)`. Verification: two renders in one process with a changed finished run give different estimates.
- ENG-3 (native 6): `graph.area` normalizes a Touches entry first: strip backticks, a leading `./` and a trailing `/`; a path segment containing `*` ends the fold before it (`skills/*/SKILL.md` -> `skills`, `dev/toy/test-*.sh` -> `dev`); `skills/README.md` (two parts) folds to `skills`. Verification: these cases in the area checks.
- ENG-4 (native 3, 4; Codex 7; replaces CEO-E1's index passing, CEO-SR7's `here` parameter, CEO-SR22 and CEO-SR23): `FLOW` and `current(run)` move into `board_status.py` (`live_board.py` keeps `FLOW = bs.FLOW` and `current = bs.current`), so there is one list and one position rule for the bar, the flow line, the estimate, the over-by and the stall line, in both `live_board` and `board.py`. `estimate`, `stalled`, `overrun` and `left_time` take `(run, runs, at, root=None)` and find the position themselves; a queued or freezing goal needs every step. `current` resolves an off-flow step from the newest timestamped evidence (report `at` or log entry time) naming a flow step, then the flow record; a stale older report never overrides a newer log entry. Verification: toy checks for a stale build report with a later review log entry at `checks` (position review), a queued goal (all steps), and the existing held-off-flow row still passing.
- ENG-5 (native 5): `stalled` skips held runs (the board's held goals already get their own Issue); the stall helper takes the held set from `live_board.issues`. Verification: a held goal far past 3x is not listed as stalled.
- ENG-6 (Codex 3): the estimator uses one accounting rule for history and live runs, `flow_seconds(run, at)` in `board_status.py`: each log gap counts toward the flow step in force (the last step started or named), including gaps that end in off-flow entries (reports, checks, session notes); gaps that start at a `stopped:`, `failed:` or `waiting:` entry are not counted until the next entry; the gap since the last entry counts only while running. `seconds_by_step` stays unchanged for `cost.py`. The backtest in the PR (CEO-V2) is re-run with this rule. Verification: toy logs with a mid-build report (full build time counted), an off-flow `checks` entry, and a stop/resume pause.
- ENG-7 (Codex 1; replaces the `U` increment of CEO-D1 and the "lift is 1" claims of CEO-D1 check (b), CEO-SR2 and CEO-SR25): the strictness increment is a named constant `STEP_UP = 60` seconds per extra done line or area: `lifted(d, a) = max(total(d, a), lifted(d-1, a) + STEP_UP, lifted(d, a-1) + STEP_UP)`. The issue 96 fixture gives each size at least 5 similar goals with actual totals spread at least 20 minutes (small goals 10-30m, large goals 90-150m) and asserts each rendered estimate lies within its similar goals' actual min and max; the test computes these bounds from the fixture, not from constants.
- ENG-8 (native 2; replaces CEO-D1 check (c)): the lift bound is a property: `lifted(d, a) <= max over grid points (d', a') <= (d, a) of total(d', a') + (d + a - 2) x STEP_UP`. Verification: a fixture with a high-total small size checks this bound for a large size.
- ENG-9 (Codex 2): ranges under overrun: before the current step passes its pace-adjusted estimate it contributes `(est - spent, max(0, low - spent), max(0, high - spent))`, with low clipped to at most left; once past it, it contributes `step_left`'s re-estimate `r` as left, low and high; remaining steps keep their ranges. `0 <= low <= left <= high` holds at every moment. Verification: one goal sampled before, at and after its step boundary checks the ordering each time.
- ENG-10 (Codex 5): a goal whose remaining steps include one with no estimate makes the Finish line read "at least finish about ...", like a goal with no estimate today; the partial flag travels with the item (`board_status` builds the items' `left` and `partial` in a helper). Verification: a partially estimated goal on the critical path gives "at least".
- ENG-11 (Codex 6, native 8): `lifted` is computed iteratively (no recursion) over d in 1..D and a in 1..A, with D and A clamped to the largest finished size plus 1; a larger goal uses the clamped corner plus `STEP_UP` per extra unit and is rough. Verification: a queue line with 60 done lines and 15 areas renders in under 1 s in the toy repo.
- ENG-12 (native 10, 11, 13): `statistics.quantiles` is called only with 2 or more values (one value: itself; none: no estimate), including inside the pooled-rate step sets; every stall and pace test passes a fixed `at` and checks 3x minus 1 s (not stalled) against 3x plus 1 s (stalled); each new regression row names its break command for `regression.py red --break` (for most rows: restore `board_status.py` from `origin/main`).
- ENG-13 (native 12, 14, 16): toy checks also cover the longest range text on a long slug staying within 60 columns after wrap; `size_of` reads a goal file only under the run's `worktree` when that is an existing directory under the repo's git common dir `loop/worktrees`, else under `root`, using `os.path.realpath` to refuse a path that leaves `.loop/goals`; the PR notes that the over-by marker moves with the new model.
- ENG-14 (native 15, Codex 5; extends CEO-SR14 and CEO-V4): `live_board.render`'s three item comprehensions become one `bs.board_items(...)` call returning slug, mark, depends, stage, left, low, high, rough and partial, so `live_board.py` shrinks instead of growing. The `live_board.py` edits are then: the items call, the bar and queued text via `estimate_text`, one stall-helper call in `issues`, the Finish `missing` test using `partial`, and the `FLOW`/`current` aliases (about 8 changed lines, about 15 removed); still an owner gate item since it exceeds "about 4 lines".
- ENG-15 (native 1, consolidates the amendments; later bullets in the CEO block that this list replaces are void): the final model, in one place:
  1. Size: `size_of(run, root)` -> `(d, a)` or None (CEO-SR24 precedence, ENG-1, ENG-3, ENG-13, CEO-S1).
  2. History: finished runs (status done, other slug, known size); per-step times from `flow_seconds` (ENG-6).
  3. Base per step: plain median, q25, q75 of the actual times of the similar goals (|d_i - d| <= 1, |a_i - a| <= 1) that logged the step when there are at least 5 similar goals, else of every finished goal that logged it (CEO-V1, ENG-12); unknown size: all finished goals, rough, no lift.
  4. Lift: `total` = sum of base medians over the seven steps; `lifted` by ENG-7 (iterative, ENG-11); `lift = lifted / total` multiplies every step's est, low and high.
  5. Running goals: position from `current` (ENG-4); spent from `flow_seconds`; pace over finished steps with an estimate, clamped 0.5..2, multiplies the current and remaining steps; overrun and ranges by ENG-9; `overrun()` uses the same numbers (CEO-SR10).
  6. Output: `estimate(...)` -> `(left, low, high, rough)` or None; `(0, 0, 0, False)` when nothing is left; rough when fewer than 5 similar goals, unknown size, or a remaining step has no estimate (CEO-V3); `estimate_text` prints `<low> to <high> left[, rough]`, `<1m left` for zero, `no estimate yet` for None (CEO-SR4, SR11).
  7. Stall: running, not held, current step's spent > 3 x its pace-adjusted lifted estimate; printed estimate is that number (CEO-SR20, SR26, ENG-5).
<!-- /autoplan-accepted:eng -->
## Review record


### Autoplan run (2026-11-10, unattended worker; ran in a subagent of the worker session)

Phase 0: UI scope no (0 UI matches), DX scope no (1 term match `SKILL.md`, threshold 2; not a developer tool, not agent-primary). CODEX_MODE: ready. Methodology loaded: CEO `autoplan-ceo-methodology-MEV2LO/methodology.md` ranges 1-600, 601-1200, 1201-1800, 1801-2257 (2257 lines, EOF).

### CEO review (Phase 1, SELECTIVE EXPANSION)

**Pre-review system audit.** Branch `loop/estimate-model` is 2 commits ahead of `origin/main` (goal + design only; no code yet). No stash. No TODOS.md in this repo (deferrals go to the NOT in scope list and the owner's issue tracker). Most-touched files in 30 days: `.loop/regression.tsv` (147), `docs/wiki/Monitoring.md` (92). Prior related work: board-estimates (v0.19.1, issue 93) added `step_left` and the over-by re-estimate in `board_status.py`; this plan builds on it. Retrospective: board-estimates' review noted its goal file's `Touches:` line omitted `live_board.py`; the same pattern recurs here (approved call-site edits in `live_board.py`), so the PR touches note is required again.

**Taste calibration.** Good references: `board_status.step_left` (one docstring, one rule, small) and `status_graph.chain` (pure function, memoized). Avoid: `live_board.render`'s long lambda chains (hard to extend; adding range fields there must stay one-line call-site edits).

**Landscape check.** Web search skipped (estimating from a repo's own run history needs no outside research). [Layer 1] Reference-class forecasting: estimate from the actual outcomes of similar past items, report a range, not a point. [Layer 3] On this repo's data, size does not predict time (see 0A premise P2'), so the "larger goal takes longer" rule is a product requirement imposed on top of the data, not something the data supplies. The model must satisfy it without inflating estimates.

#### 0A. Premise challenge

Real problem: queued goals all read about 15m (issue 96), so the board's queue and finish time are useless for planning; stuck goals hide (issue 37). Do-nothing cost: the owner keeps ignoring the board's times. The plan addresses the pain directly (estimate per goal, range, stall line), not a proxy.

| Premise | Claim | Receipt | Verdict |
|---|---|---|---|
| P1 | Today every queued goal gets the same estimate | `board_status.py:84-94` `left_time` sums `usual()` over steps, independent of the goal | verified |
| P2 | Size (done lines + areas) resolves for all finished runs | measured 2026-11-10 by scratch script over `.git/loop/runs/*.json`: 57 of 57 status-done runs resolve d and a | verified [measured: 57 runs] |
| P2' | Larger goals take longer | measured: Pearson correlation of per-step time vs s = d + a is -0.01 to -0.07 for all 7 steps (57 runs). Median ship time: 29.3m for s <= 5 (n=4), 13.5m for s >= 9 (n=25) | **REALITY: false on this data.** Done line 1 still requires it, so the model must impose it without inflating |
| P3 | The plan's monotone envelope only lifts in rare cases | design step 4 says it lifts "only when a smaller size has a higher per-unit rate"; measured per-unit ship rate is 8.89 min/unit at s <= 5 vs 1.29 at s >= 9 | **false**: it lifts almost always. Measured totals with the plan's per-step rescaled envelope: (4,2) 14m raw -> 88m, (6,3) 31m -> 158m, (10,6) 35m -> 327m |
| P4 | Queued goals carry size into the estimate | `live_board.py:270` passes `{"slug", "status": "queued"}` (no done or touches) and `left_time` has no root | **false**: as written, every queued goal on the real board would be unknown size, rough and unscaled; issue 96 stays unfixed on the board while a toy test calling `estimate` directly passes |
| P5 | Off-flow steps are handled | `board_status.py:89` maps a step not in STEPS (checks, release) to index 0 (idea); 1 running goal is at `checks` now | **false** (existing bug in the function this plan rewrites) |
| P6 | Changing the text format breaks nothing | `dev/toy/test-live-board.sh:61` anchors `[0-9]+m left$`; `test-status-graph.sh:66` pins `51m left`, `1h01m left`; `test-workers.sh:129`; `test-board-estimates.sh:42,51` | **false**: these rows (estimates-shown, status-graph-marks, live-board-*) must be updated in this goal |
| P7 | No new dependency; scripts under 20 KB | `board_status.py` 7277 B, `live_board.py` 18646 B (limit 20480) | verified; `live_board.py` has 1.8 KB headroom |

unverified=0.

#### 0B. Existing code leverage

| Sub-problem | Existing code | Reuse |
|---|---|---|
| Per-step times | `board_status.seconds_by_step` (`board_status.py:52`) | reuse as is |
| Over-estimate re-estimate | `board_status.step_left` (`:72`) | reuse as is |
| Queue line parsing | `graph.parse` (`graph.py:17`): `done`, `touches` lists | reuse; size of a queued goal comes straight from it |
| Off-flow step index | `live_board.current` (`live_board.py:103`) | reuse by passing its index into the estimate (no duplicate in board_status) |
| Duration text | `status_graph.span` (`status_graph.py:18`) | reuse for both range ends |
| Finish line | `status_graph.chain` over items' `left` | reuse; items' `left` must come from the new estimate |
| Quantiles | stdlib `statistics.quantiles(method="inclusive")`, `median` | reuse |
| Regression rows, red proof, Tests render | `regression.py add/red`, `criteria.py render` | reuse |

No rebuild.

REALITY: premise-table finding 7 premises, 4 false (P2', P3, P4, P5, P6 counted as findings; P2', P3 measured) skills/workflow-monitoring/scripts/board_status.py:84
REALITY: already-done pass `git log origin/main --since=2026-11-08` on board_status.py, graph.py, live_board.py shows only board-estimates/board-held work; no size-aware estimate or stall line exists skills/workflow-monitoring/scripts/board_status.py:84
REALITY: surface-check pass `regression.py add/red --break`, `criteria.py render`, `docs.py check` verified with --help; `status_graph.span` exists skills/workflow-regression/scripts/regression.py:13
REALITY: binding-decisions pass `review-decision-search --scope branch --recent 50` returned nothing; the plan's constraints (live_board.py ~4 lines approved, MON-1.. requirement text frozen) are honored .loop/goals/estimate-model.design.md:30
REALITY: numbers finding the resolve-size count was re-measured by <scratchpad>/sim.py:28 [measured]; the envelope inflation was re-measured by <scratchpad>/sim.py:52 [measured]; the backtest errors come from <scratchpad>/loo.py:44 [measured]; the 29-minute median is quoted from issue 96 [estimated, not re-derived] skills/workflow-monitoring/scripts/board_status.py:66
REALITY: deferred-asks pass issue 96 asks for size- and history-aware estimates (covered); issue 37 asks to flag a goal with no change, which the frozen done line narrows (covered as frozen) .loop/goals/estimate-model.md:12
REALITY: pr-count pass no `.review suite/ship-policy.json`; one PR (default) .loop/goals/estimate-model.md:1

#### 0C. Dream state

```
  CURRENT STATE                    THIS PLAN                           12-MONTH IDEAL
  every queued goal ~15m;   --->   per-goal range from similar   --->  estimates calibrated against
  stuck goals hidden in            finished goals, rough flag,          their own outcomes (estimate vs
  flow lines                       pace refinement, stall Issue         actual tracked), owner-wait time
                                                                        excluded, Finish line trustworthy
```

Moves toward the ideal: yes. Gaps left: no calibration record (estimate vs actual), owner-wait time still inside step times.

#### 0D. Approach decision (CEO-D1, auto-decided)

| Commitment | Source | Current (plan) | A: keep plan | B: lifted similar medians (recommended) | C: no envelope |
|---|---|---|---|---|---|
| Base per-step estimate | done line 1 | s x median(similar rates), any similar count | same | s x median(similar rates) when >= 5 similar; else s x median(all finished rates) (done line 1's fallback) | as B |
| Larger goal -> longer | done line 1 | per-step rescaled max envelope | same (measured up to 9x inflation) | goal-level running max with a one-unit increment, applied to the whole-goal total, then every step scaled by the same lift factor | none (fails done line 1 when data contradicts) |
| Range | done line 2 | per-step q25/q75 summed | same | same, both ends scaled by the lift factor | same |
| Coverage | | 7/10 | 7/10 | 10/10 | 3/10 |

Auto-decided B (P1 completeness, P5 explicit). Measured on 57 runs: (4,2) 14m -> 42m, (10,6) 35m -> 88m, versus the plan's 88m and 327m. Classified TASTE (close approaches; surfaced at the gate).

#### 0E. Mode

Mode: SELECTIVE EXPANSION (autoplan override). Planned changed files: `board_status.py`, `graph.py`, `live_board.py`, new `dev/toy/test-estimates.sh`, existing board toy tests (up to 4), `.loop/regression.tsv`, `docs/wiki/Monitoring.md`, `skills/workflow-monitoring/SKILL.md` or a reference: about 10 [estimated]. Added capability, under 15 files.

#### 0F/0G. Expansion candidates and HOLD checks

HOLD checks: complexity 10 files, no new classes (functions only): acceptable. Minimum changes: graph size + estimate model + 3 call-site groups + tests + docs. Invariants kept: done lines 1-6 frozen, MON-1.. text frozen.

| # | Proposal | Effort | Decision | Reason |
|---|---|---|---|---|
| E1 | Off-flow steps (checks, release) use the last known flow step in the estimate and the stall check (pass `live_board.current`'s index) | S | ACCEPTED (P2, in blast radius, 1 file) | today a goal at checks is estimated as if at idea |
| E2 | `board.py` (multi-repo board) passes queue lines too, so its queued estimates are size-aware | S | DEFERRED | outside the goal's touches and the approved call-site list |
| E3 | Exclude owner-wait time from step times | M | DEFERRED | design Open Question; needs new run-record events |
| E4 | Record each goal's estimate at freeze time and report estimate vs actual (calibration) | M | DEFERRED | needs a `board_runs.py` field and a health rule; separate goal |
| E5 | `board_status.py --explain SLUG` per-step breakdown | S | DEFERRED | new CLI surface with docs and tests; not needed by the done lines |
| E6 | Show the similar count on the board ("rough, 3 similar") | S | SKIPPED | 60-column width; "rough" already carries it |

#### 0I. Temporal interrogation

```
  HOUR 1 (foundations):  area()/size() in graph.py; size_of precedence; where a queued goal's
                         size comes from (its queue line dict)  [human ~2h / CC ~10min]
  HOUR 2-3 (core logic): similar set, >=5 gate with pooled fallback, quantiles with 1 rate,
                         goal-level lift, pace clamp, stalled before step_left
                         [human ~6h / CC ~30min]
  HOUR 4-5 (integration):live_board call sites: items' left from estimate (Finish line), bar and
                         queued text, issues stall line, current() index; existing board tests'
                         text assertions  [human ~3h / CC ~20min]
  HOUR 6+ (tests/docs):  fixture repo with >=5 similar goals per size, red proofs, MON-4
                         scenarios, criteria render, docs check  [human ~4h / CC ~30min]
```
Surprises to plan for: anchored test regexes break on ", rough"; the bar line wraps past 60 columns; `left_time` is also called by `board.py` (signature must stay compatible).

#### Decision ledger (CEO)

| ID and owner | Contract and evidence | Current | Proposed | Status | Exact approval and scope |
|---|---|---|---|---|---|
| CEO-D1 (CEO 0D) | done line 1 monotone clause; P2', P3 measured | per-step rescaled envelope | B: lifted similar medians | approved (auto) | autoplan unattended auto-decide, recommended option; TASTE surfaced at gate |
| CEO-D2 (CEO 0A) | P4 | queued goals pass slug only | queued items pass the queue-line dict and root; items' left uses the same estimate | approved (auto) | mechanical, P1 |
| CEO-E1 | P5 | step not in STEPS -> idea | flow index from `live_board.current` | approved (auto) | P2 blast radius |
| CEO-D3 (CEO 0A) | P6 | not planned | update existing board tests' estimate-text assertions | approved (auto) | mechanical, required by P6 |
| CEO-D4 | done lines 4, 5 | not planned | PR body carries `Closes #96` and `Closes #37` | approved (auto) | mechanical |
| CEO-E2..E5 | 0G | — | deferred | deferred | P3 outside blast radius |
| CEO-E6 | 0G | — | skipped | declined | width |

<!-- autoplan-accepted:ceo -->
- CEO-D1 (replaces section 2 steps 1-4 and the Rough bullet's meaning of "similar"): per step, the base estimate is `s x median(rates)` over the similar goals that logged the step when the goal-level similar count is at least 5; with fewer than 5 similar goals (rough), it is `s x median(rates)` over every finished goal of known size that logged the step (done line 1's fallback to all finished goals). A step that none of 5+ similar goals logged also uses the pooled rates. Unknown size keeps section 2 step 5 (unscaled, always rough, no lift). low and high are `s x q25` and `s x q75` of the same rate set (`statistics.quantiles(n=4, method="inclusive")`; one rate gives low = high = raw).
- CEO-D1 (replaces section 2 step 3's per-step rescaled envelope): monotonicity is applied to the whole-goal total. `total(d, a)` = sum over all seven steps of the base estimate. `lifted(d, a) = max(total(d, a), lifted(d-1, a) + U, lifted(d, a-1) + U)` over d, a >= 0 with d + a >= 1 (memoized; out-of-range neighbours skipped), where `U` = sum over steps of the q25 of every finished goal's per-unit rate (one size unit's worth of time). `lift = lifted / total` (1 when total is 0). Every step's est, low and high for that goal are multiplied by `lift`, so low <= est <= high holds and per-step estimates stay available to pace and the stall check. A componentwise larger size always gets a strictly larger whole-goal estimate when U > 0.
- CEO-D1 verification: the toy test asserts (a) for sizes (2,1) < (4,2) < (7,5) the queued estimates strictly increase; (b) with fixtures where lift is 1, the issue 96 sizes 3 and 12 each sit between the min and max of their similar goals' scaled times; (c) a fixture where a small size has a high per-unit rate shows the large size's estimate under 3x its unlifted total (no runaway envelope); (d) with 4 similar goals the estimate equals the pooled-rate estimate and reads rough, with 5 it uses the similar set and does not.
- CEO-D2: a queued goal's size comes from its queue line: `live_board.py` passes the parsed queue item (`dict(g, status="queued")`) and `root` for queued and freezing goals, and `size_of` reads `done` and `touches` from the run dict when no goal file exists (precedence stays goal file, then queue line, then run record touches with goal-file done lines). The items' `left` that feeds the Finish line comes from the same `estimate(...)` as the shown range. `left_time(run, runs, at, root=None)` stays backward compatible for `board.py`. Verification: the issue 96 defect test drives `live_board.render` on a fixture repo with two queued lines (sizes 3 and 12) and asserts their two rendered estimates differ and the Finish line uses the larger chain.
- CEO-E1: a running goal whose step is outside STEPS (checks, release) is estimated and stall-checked from its last known flow step: `live_board` passes `current(run)`'s index to `estimate`/`stalled`; board_status does not duplicate that logic. Verification: toy check that a goal at `checks` after build is not estimated as if at idea.
- CEO-D3: existing board toy tests whose assertions pin the old estimate text (`dev/toy/test-live-board.sh:61`, `dev/toy/test-status-graph.sh:66`, `dev/toy/test-workers.sh:129`, `dev/toy/test-board-estimates.sh:42,51`) are updated to the new text (range or single value, optional `, rough`) without weakening what they check; all board toy tests (test-board, test-board-held, test-board-estimates, test-live-board, test-status-graph, test-workers, test-narrow, test-operate-fit) pass, and no board line exceeds 60 columns.
- CEO-D4: the PR body carries `Closes #96` and `Closes #37`.
- CEO-SR1 (spec review round 1, Completeness 1 and CEO-E1): at an off-flow step (checks, release) the time since the last log entry counts toward the last known flow step, so `spent` for the stall check and pace is that flow step's logged time plus the off-flow gap. Verification: toy checks that a goal at `checks` after build is estimated from review onward, and that one sitting at `checks` past 3x build's estimate shows as stalled naming build.
- CEO-SR2 (Completeness 2, Consistency 2; done line 5): the issue 96 defect fixture gives each of the two sizes (3 = 2 done lines + 1 area; 12 = 7 done lines + 5 areas) at least 5 finished goals of exactly that size and no finished goal of a neighbouring size, so the similar set is used (not pooled), scaled times equal actual times, and lift is 1 by construction; the test asserts each rendered estimate lies between the min and max of its similar goals' actual times, and that the two differ. The lifted case is covered separately by CEO-D1 check (c).
- CEO-SR3 (Completeness 3): a freezing goal with no queue line, or any goal with no goal file, no queue line and no run touches, is unknown size: unscaled, rough, no lift.
- CEO-SR4 (Consistency 3; done line 2): `estimate_text` always prints both ends, `"<low> to <high> left"` (for example `30m to 30m left` when they round equal), plus `", rough"` when rough; this replaces section 2's single-value collapse.
- CEO-SR5 (Consistency 4): section 2's Cache bullet now reads: once per render, cache each finished run's size and `seconds_by_step`, the rate sets per (step, size) and the `lifted(d, a)` memo. Section 5's "monotone envelope" check now reads "whole-goal running max: a componentwise larger size gets a strictly longer queued estimate".
- CEO-SR6 (Clarity 1, 2): every grid point `(d', a')` in `lifted` uses its own similar count (>= 5: similar rates, else pooled); the goal itself is excluded from similar sets, pooled rates and `U` (other slugs only). Pace and the stall threshold use the lifted per-step estimates (pace-adjusted for the stall threshold).
- CEO-SR7 (Clarity 3): final signatures: `estimate(run, runs, at, root=None, here=None)` returns `(left, low, high, rough)` or `None` when no step has an estimate; `stalled(run, runs, at, root=None, here=None)` returns `(step, spent, est)` or `None`; `left_time(run, runs, at, root=None, here=None)` returns `estimate(...)[0]` (or `None`, or 0 when done); `here` is the flow index from `live_board.current`, defaulting to today's rule when omitted (board.py).
- CEO-SR8 (Scope 2): the PR's touches note names every file outside the goal's Touches line: `live_board.py` (approved call sites), `.loop/regression.tsv`, `docs/wiki/Monitoring.md`, and the workflow-monitoring SKILL.md or reference edited.
- CEO-SR9 (Feasibility 1): all logic stays in `board_status.py`; `live_board.py` gets call-site edits only, and after the build both scripts are under 20 KB (`workflow-health check` script-size rule passes).
- CEO-SR10 (round 2, Completeness 1): `overrun()` (the flow line's "over by") uses the same lifted, pace-adjusted per-step estimate and the same `here` as `estimate` and `stalled`, so the board shows one model.
- CEO-SR11 (Completeness 2): `here` 7 (release) or a done goal has no steps left: `estimate` returns `(0, 0, 0, False)` and `estimate_text` prints today's `<1m left` for a zero estimate (the only single-value case; no range for nothing left).
- CEO-SR12 (Completeness 3; extends CEO-D3): every `dev/toy/test-*.sh` passes after the change, not only the board tests named in CEO-D3; any other test that pins the old estimate or over-by text is updated the same way.
- CEO-SR13 (Completeness 4, Consistency 1; replaces CEO-SR1's verification wording): off-flow time belongs to the last known flow step: every log gap after the last flow-step entry, whatever off-flow words (checks, lane names) it is logged under, plus the gap since the last entry, counts toward that flow step. A new helper in `board_status.py` computes this on top of `seconds_by_step`, which stays unchanged for `workflow-health/scripts/cost.py`. So a goal at `checks` after build keeps build as its current step (re-estimated by `step_left` once over) and is estimated as build plus review onward, never from idea; it is stalled naming build when build's counted time passes 3x build's pace-adjusted estimate. Pace and stall use this same rule.
- CEO-SR14 (Consistency 2; replaces section 4's "about 4 lines"): the `live_board.py` call-site edits are about 9 lines (items' left and `here` for running, queued and freezing goals; bar and queued text through `estimate_text`; the stall lines in `issues`). This exceeds the operation session's "about 4 lines" approval and is an owner decision at the final gate. If `live_board.py` would pass 20 KB, the stall lines' formatting moves into a `board_status` helper so `issues` adds one line.
- CEO-SR15 (Consistency 3): the estimate model's reading of done line 1 is the scaled median: per-unit rates (time / size) of similar goals, times this goal's size, falling back to the same over all finished goals. It equals the median actual time when sizes match and is what makes a larger goal longer; the PR body states this reading. Tests claim "inside the similar goals' actual range" only for the exact-size fixture of CEO-SR2.
- CEO-SR16 (Clarity 1): the defect test asserts the Finish line's time equals `at + max(left_3, left_12)` (the two queued goals are independent), using the same seconds the two rendered ranges come from.
- CEO-SR17 (Clarity 2): known sizes have d >= 1 and a >= 1 (`size` returns None otherwise), so the `lifted` grid starts at (1, 1); neighbours with d = 0 or a = 0 are skipped; `lifted(1, 1) = total(1, 1)`.
- CEO-SR18 (Clarity 3): a step with no rates in either the similar or the pooled set has no estimate; lift scales only existing estimates and never creates one; such a step is never stalled.
- CEO-SR19 (Scope 1, 2): CEO-E1 and CEO-SR13 (off-flow handling) are autoplan expansions in the blast radius of `left_time`, listed for the owner at the final gate. `.loop/regression.tsv` and `docs/wiki/Monitoring.md` are required by done line 6 itself. The PR's touches note also says `board_runs.py` (named in Touches) was not changed.
- CEO-SR20 (round 3, Completeness 1): the gap since the last log entry counts only while the goal's status is `running` (as `seconds_by_step` does today); pace and the stall check run only for `running` goals, so a `waiting`, failed or stopped goal is never stalled. Toy check: a `waiting` goal sitting far past 3x its step estimate is not under Issues as stalled.
- CEO-SR21 (Completeness 2): `U` sums, over the steps that have pooled rates, the q25 of those rates; a step with no pooled rates adds nothing; a step with one rate adds that rate.
- CEO-SR22 (Completeness 3): held goals pass `current(run)` as `here` and their queue/run dict, like running goals.
- CEO-SR23 (Consistency 1; refines CEO-SR13): the flow step that off-flow time counts toward is `FLOW[here]` from `live_board.current` (one source for the bar, the estimate, the over-by and the stall line); with `here` omitted (board.py), the last flow-step entry in the log.
- CEO-SR24 (Consistency 2; clarifies section 1 precedence): done lines come from the goal file when it exists, else the queue line's `done`; touches come from the goal file's `- Touches:` line when present, else the queue line's `touches`, else the run record's `touches`.
- CEO-SR25 (Clarity 1): CEO-D1 check (d) uses a fixture whose lift is 1 (no smaller size with a higher total).
- CEO-SR26 (Clarity 2): the stall line prints `(estimate <est>)` as the pace-adjusted lifted step estimate, the same number the 3x test uses, via `status_graph.span`.
- CEO-SR27 (Clarity 3; replaces CEO-SR9's "passes"): both scripts stay under 20,480 bytes (no FAIL on the script-size rule). `live_board.py` is already over the 90% WARN line (18,646 bytes) before this goal; WARN is accepted, FAIL is not.
- CEO-V1 (dual voices + backtest; replaces CEO-D1's base estimate and CEO-SR15's scaled-median reading): the per-step base estimate is the plain median of the actual step times of the similar goals that logged the step when the goal-level similar count is at least 5, else of every finished goal that logged it (done line 1 read literally). low and high are the q25 and q75 of the same times (one time: low = high). The goal-level running max of CEO-D1 (`lifted`, `U`, `lift`, grid from (1, 1)) is unchanged and is what makes a larger goal longer. CEO-SR2's fixture then needs no exact-size trick for the range claim, but keeps it so lift is 1. Measured leave-one-out on 56 finished runs (median absolute log error of the whole-goal estimate): today's size-blind median x2.43, scaled base x2.94, scaled + lift x3.67, plain-median base + lift x3.49; this variant is the most accurate of the ones that meet done line 1.
- CEO-V2: the PR body reports that backtest (old vs new median error and the q25-q75 coverage, about 24 of 56) so the owner sees that the size rule costs accuracy on this repo's history; the docs line in section 6 says the range is the summed per-step quartiles, not a calibrated interval.
- CEO-V3: an estimate is also rough when any remaining step has no estimate (missing history), in addition to fewer than 5 similar goals or unknown size.
- CEO-V4: the stall lines' formatting lives in a `board_status` helper from the start (not only as a size fallback), so `live_board.issues` adds one call; a stalled goal that is also quiet shows both lines (slow and silent are different facts).
- CEO-V5: the defect test's fixture leaves `parallel` unset (unlimited), so the Finish line's `at + max(left_3, left_12)` holds; the Finish line's slot-blind assumption is unchanged (pre-existing, NOT in scope).
- CEO-S1 (Sections 2, 3): `size_of` builds a goal-file path only for a slug matching `graph.SLUG`, catches only `OSError` and parse misses (no catch-all), and falls through the precedence to unknown size; toy check: an unreadable goal file and a slug with `..` both give a rough unknown-size estimate while the board still renders.
- CEO-S2 (Section 5): the model splits into `step_estimates(size, model)` (per-step est/low/high for a size) and `estimate(...)` (remaining steps, pace, overrun, off-flow), each with at most 5 branches.
- CEO-S3 (Section 7): `board_status.py` wall time on this repo is measured before and after (stated in the PR); the change adds under 0.5 s per render.
<!-- /autoplan-accepted:ceo -->

#### 0H. Spec Review Loop (CEO)

Inputs: CEO scope summary `<private review store>` and the amend-input export of the working plan. Three reviewer launches (cap): round 1 score 6/10, 15 issues (fixed as CEO-SR1..SR9); round 2 score 6/10, 13 issues, mostly new (fixed as CEO-SR10..SR19); round 3 score 7/10, 8 issues, Scope and Feasibility PASS (fixed as CEO-SR20..SR27; issues verified: 8 of 8 against the amended text; spec not re-verified, launch cap). Metrics appended to `analytics/spec-review.jsonl` (iterations 3, found 36, fixed 28, remaining 8, score 7). Document approval: auto-decided A (approve these documents and continue to 0I); unattended run, recommended option.

#### Dual voices (CEO)

Input: `autoplan-ceo-UGddcY/ceo-implementation.md`, sha256 fe82577a... (fresh snapshot after the Spec Review Loop).

**Claude CEO subagent** (native, completed; INPUT line matched the snapshot hash). Findings: (1) critical: no check that size predicts time; (2) high: proportional scaling with no fixed cost, suggests `t = a + b*s` per step; (3) high: the similar branch may rarely run; (4) high: stall inherits estimate error, suggests q75 or absolute thresholds and shipping #37 separately; (5) medium-high: the spec is patched by about 30 amendments; (6) medium: live_board.py size and scope growth (E1, about 9 lines); (7) medium: `30m to 30m` text and rough-by-default; (8) medium: alternatives not backtested; (9) medium-low: competition is the owner's time.

**Codex CEO voice** (outside, completed: `OUTSIDE_STATUS: completed provider=codex host=claude`, model gpt-6-astra, VERDICT findings P1). Findings: (1) high: success is "different numbers", not better predictions; require a backtest; (2) high: done-line count and area count are proxies, monotonicity forces them; (3) high: stalled (slow) is not "no change" (silent); the board already has a session-silence Issue (`live_board.py:221-230`); (4) high: Finish ignores slot limits (`graph.py:105` vs `status_graph.py:36`); (5) high: summed quartiles times a lift are not calibrated; rough should reflect step coverage; (6) high: "actual time" mixes PR-waiting and log-gap artefacts; (7) medium: cold start and recency. Recommendation: revise before implementation because the tests prove arithmetic, not accuracy.

**Evidence run in response** (scratch scripts over `.git/loop/runs/*.json`, 2026-11-10): leave-one-out on 56 finished runs, median absolute log error of the whole-goal estimate: old size-blind median x2.43; plan's scaled base x2.94; scaled + lift x3.67; plain-median base + lift x3.49. q25-q75 coverage 22-25 of 56. Rough (fewer than 5 similar): 9 of 56, so native finding 3 is refuted (the similar branch runs for 47 of 56). Per-step time vs size correlation -0.01 to -0.07.

```
CEO DUAL VOICES — CONSENSUS TABLE:
  Dimension                            Claude        Codex          Consensus
  1. Premises valid?                    no (size)     no (proxies)   CONFIRMED: not valid (measured: size does not predict time)
  2. Right problem to solve?            yes           partly         DISAGREE (Codex: Finish and stall/silence are the real question)
  3. Scope calibration correct?         over-scoped   under on Finish DISAGREE
  4. Alternatives sufficiently explored? no           no             CONFIRMED (backtest now run)
  5. Competitive/market risks covered?  low risk      cold start     DISAGREE (minor)
  6. 6-month trajectory sound?          patched spec  uncalibrated   CONFIRMED concern
```

Dispositions (auto-decided; P = principle):
| Finding | Disposition |
|---|---|
| Size does not predict time (both) | Confirmed by backtest. The done lines are frozen (delivery), so the plan keeps the size rule, picks the most accurate compliant variant (CEO-V1) and reports the accuracy cost in the PR (CEO-V2). Not an owner decision here; recorded in the brief as evidence. |
| Linear fit `a + b*s` (Claude) | Rejected: the design rejected a fitted model (Approach B) and done line 1 names medians of similar goals; with correlation near 0 the slope clamps to 0 and gives no ordering. TASTE disagreement logged. |
| Similar branch rarely runs (Claude) | Refuted: 47 of 56 runs have 5+ similar goals. |
| Stall separate / absolute fallback / split #37 into its own PR (Claude) | Rejected: done line 4 fixes the 3x-estimate rule and the done lines put #37 in this goal. Silence is already covered by the quiet-session Issue (Codex 3). CEO-V4 keeps both lines. |
| Spec patched by amendments (Claude) | TASTE: keep the amendment blocks (autoplan's record) and rely on "later bullet wins"; the Eng phase restates the final model in one place. |
| live_board.py size and scope (Claude) | CEO-V4 moves stall formatting into board_status now; line count and E1 remain owner gate items. |
| `30m to 30m` and rough wording (Claude) | Keep both ends (done line 2 says a range); rough is 9 of 56, not the default. TASTE noted. |
| Backtest alternatives (both) | Done (numbers above); CEO-V1 picks the best compliant variant. |
| Finish ignores slot limits (Codex) | Pre-existing, outside the done lines: NOT in scope; CEO-V5 keeps the test valid. |
| Range calibration, rough from coverage (Codex) | CEO-V2 (say it is summed quartiles, report coverage) and CEO-V3 (rough when a step has no estimate). |
| Outcome definition, cold start, recency (Codex) | Deferred (NOT in scope); cold start keeps "no estimate yet" as today. |

#### CEO Review Sections

Current scope: mode SELECTIVE EXPANSION (autoplan override, recorded at 0E). Accepted: CEO-D1 (as revised by CEO-V1), D2, D3, D4, E1, SR1-SR27, V1-V5. Deferred: E2-E5. Skipped: E6. Pending for the owner at the gate: live_board.py call-site growth (about 9 lines vs about 4 approved), E1/SR13 off-flow expansion.

**Section 1: Architecture.**
```
  queue.md ──graph.parse──┐                      .loop/goals/<slug>.md (worktree, then main)
                          v                                  │
  loop/runs/*.json ──> board_status.size_of(run, root) <─────┘     graph.area / graph.size
          │                     │ (d, a) or None
          │                     v
          ├──seconds_by_step──> model cache (per render): sizes, step times, similar sets,
          │                     per-step median/q25/q75, U, lifted(d,a) memo
          │                     │
          │        live_board.current(run) ──here──┐
          │                     v                  v
          │              estimate(run, runs, at, root, here) -> (left, low, high, rough)
          │              stalled(...) -> (step, spent, est)    overrun(...) (same model)
          v                     │
  live_board.render: items' left (Finish via status_graph.chain), bar/queued text via
                     estimate_text, issues + stall lines (board_status helper)
  board.py (unchanged): left_time(run, records, at) -> estimate(...)[0], here/root default
```
New coupling: `live_board` passes `current(run)` into `board_status` (one integer, justified by DRY: the flow-step rule lives once). `board_status` reads goal files from disk (new read path). Scaling: 57 finished runs today; the grid is at most about 15 x 15 per render, memoized; 10x runs (570) keeps it linear in runs per (step, size) set. Single point of failure: a malformed goal file or run record; handled by unknown size (rough). Rollback: revert the PR; no persisted state changes (read-only model). Findings: P4 (queued size lost) and P5 (off-flow) fixed by D2 and E1; P3 (envelope inflation) fixed by D1/V1. Value test: no artifact about the work is added; the board is product observability.

**Section 2: Error & Rescue Map.**
```
  CODEPATH                       | WHAT CAN GO WRONG                      | CLASS
  size_of: read goal file        | missing, unreadable, no Done/Touches   | OSError / parse miss
  size_of: slug -> path          | slug with path characters              | traversal
  graph.size                     | empty done or touches                  | None result
  model: quantiles               | 0 or 1 values                          | StatisticsError
  model: lift                    | total 0                                | ZeroDivisionError
  estimate: here 7 / done        | no steps left                          | empty sum
  seconds_by_step stamps         | unparsable log stamp                   | ValueError (already caught: stamp() -> None)
  live_board render              | any exception kills the whole board    | uncaught

  CLASS               | RESCUED? | RESCUE ACTION                                | USER SEES
  OSError/parse miss  | Y        | fall through the precedence; else None size  | estimate marked rough
  traversal           | Y        | slug must match graph.SLUG before path join  | unknown size, rough
  None size           | Y        | unknown-size path (unscaled, rough, no lift) | rough range
  StatisticsError     | Y        | 0 values: no estimate; 1 value: low=high     | "no estimate yet" or a 2-end range
  ZeroDivisionError   | Y        | lift = 1 when total is 0 (CEO-D1)            | normal text
  empty sum           | Y        | (0,0,0,False) -> "<1m left" (CEO-SR11)       | today's text
  uncaught render     | N <- GAP | catch OSError/ValueError at size_of only; no catch-all | (no new crash path if the above hold)
```
Gap closed by obligation: size_of catches only OSError and parse misses and validates the slug (added below as CEO-S1); no catch-all.

**Section 3: Security.** No new endpoints, inputs or secrets. New file reads: `.loop/goals/<slug>.md` keyed by slugs from run records and queue lines; a slug with `/` or `..` could read outside `.loop/goals` (likelihood Low, impact Low: read-only, parsed for counts only). Mitigation: CEO-S1 (slug must match `graph.SLUG`). No dependency change (stdlib only). No PII. No LLM prompts.

**Section 4: Data flow and edge cases.**
```
  INPUT (run/queue dict) -> VALIDATE (slug regex) -> SIZE (goal file > queue line > run touches)
     -> MODEL (similar >= 5 ? similar times : all times; quartiles; lift) -> PACE (0.5..2)
     -> OUTPUT (range text, Finish seconds, stall line)
  shadow: nil size -> rough unscaled | empty history -> "no estimate yet" | 1 run -> low=high
          | malformed log stamp -> step time skipped (existing) | off-flow step -> FLOW[here]
          | waiting/failed goal -> no gap added, never stalled (CEO-SR20) | done -> "<1m left"
```
Interaction edge cases: board re-render mid-step (estimate shrinks as time passes, then step_left grows it: existing behavior); a goal re-queued after retire (retired runs are excluded by `load`); two goals with the same slug (impossible: run files keyed by slug). Async ordering: none (single-process read-only render). All mapped cases are handled by accepted obligations; 0 unhandled.

**Section 5: Code quality.** Fits existing patterns (pure functions in board_status, call sites in live_board). DRY: off-flow rule reused from `live_board.current` (E1/SR23), not duplicated. Risk: `estimate` branches (unknown size, rough, pace, overrun, off-flow) exceed 5; obligation CEO-S2 splits it into `step_estimates(...)` (per-step est/low/high for a size) and `estimate(...)` (remaining steps, pace, overrun), each under 5 branches. Naming: `estimate`, `stalled`, `estimate_text`, `size_of` say what they do.

**Section 6: Tests.**
```
  NEW CODEPATH                     | TEST TYPE    | HAPPY                         | FAILURE / EDGE
  graph.area / size                | unit (toy)   | folding examples              | empty lists -> None
  size_of precedence               | toy repo     | goal file wins                | no goal file -> queue line; bad slug -> None
  similar >= 5 vs pooled           | toy repo     | 5 similar -> not rough        | 4 similar -> pooled, rough
  quartiles                        | toy repo     | range from 5 times            | 1 time -> low = high
  lift                             | toy repo     | (2,1)<(4,2)<(7,5) strictly    | high-rate small size: large < 3x unlifted
  pace                             | toy repo     | slow history grows estimate   | clamp at 0.5 and 2
  off-flow (E1/SR13/SR23)          | toy repo     | checks after build -> build+  | not estimated from idea
  stalled                          | toy repo     | > 3x -> Issues line           | = 3x no; no estimate no; waiting no
  render call sites (D2)           | toy repo     | queued 3 vs 12 differ         | Finish = at + max
  issue 96 defect                  | toy repo     | ranges inside similar actuals | seen failing on old code
  existing board tests (D3/SR12)   | toy repo     | all dev/toy tests pass        | no line > 60 columns
```
2am-Friday test: the issue 96 defect test through `live_board.render`. Hostile QA: a goal file with a `Touches:` line of only root files, a slug with `..`, a log with one entry. Chaos: an unreadable goal file mid-render (permission denied) -> unknown size, board still renders (CEO-S1 test). Flakiness: tests compare HH:MM text; pin `TZ=UTC` (prior learning toy-test-local-tz applied) and pass a fixed `at`. No LLM changes.

**Section 7: Performance.** Today `usual()` re-parses every run's log per goal per step (O(goals x steps x runs)). The model cache (CEO-SR5) parses each run once per render. Grid memo at most d x a (under 15 x 15). Goal-file reads: 57 small files per render. Obligation CEO-S3: measure `board_status.py` wall time on this repo before and after; the change adds under 0.5 s.

**Section 8: Observability.** The board itself is the observability surface. New signals: range, rough, stall line. Debuggability gap: no way to see why an estimate is what it is (E5 deferred). The stall line names step, time spent and estimate, enough to act. Runbook: the stall fix line points at the worker session (stop and resume). No metrics or alerts beyond the board (none exist for this tool).

**Section 9: Deployment.** No migration, no persisted format change, no flag. Old and new code never run together on one board render. Rollback: revert the merge commit; board falls back to the size-blind median. Post-merge check: run `python3 skills/workflow-monitoring/scripts/board_status.py` on this repo and see different ranges for queued goals of different sizes (design success criterion).

**Section 10: Long-term trajectory.** Debt: a model tuned to 57 runs whose accuracy is lower than the old median on backtest (CEO-V2 makes it visible); the patched plan text (TASTE). Reversibility 5/5 (read-only model, one revert). Path dependency: E4 (calibration record) is the natural next goal and fits this model's cache. 1-year question: obvious if the docs line explains similar >= 5, pooled fallback, lift and pace in four sentences.

**Section 11: Design.** SKIPPED (no UI scope).

#### CEO required outputs

PLAN_REALITY: phase=ceo rows=7/7 missing=none verdict=complete

**NOT in scope (CEO).**
Deferred (each for the owner to file as an issue if wanted; this repo has no TODOS.md):
- E2: `board.py` multi-repo board passes queue lines (its queued estimates stay size-blind and rough). Reason: outside touches.
- E3: owner-wait time excluded from step times. Reason: needs new run-record events.
- E4: estimate-at-freeze record and an estimate-vs-actual health rule (calibration). Reason: new field and rule; the natural next goal given the backtest.
- E5: `board_status.py --explain SLUG`. Reason: new CLI surface.
- Finish line slot-awareness (Codex 4): pre-existing, outside the done lines.
- Outcome definition (PR-waiting time inside "done" runs), cold start and recency weighting (Codex 6, 7).
Rejected:
- E6 (similar count on the board): width.
- Linear fit `a + b*s` (Claude 2): design rejected a fitted model; done line 1 names medians.
- Splitting #37 into its own PR (Claude 4): the frozen done lines put it in this goal.

**What already exists.** See 0B: `seconds_by_step`, `step_left`, `graph.parse`, `live_board.current`, `status_graph.span` and `chain`, the regression and criteria tools; all reused. The quiet-session Issue (`live_board.py:221-230`) already covers silent workers; the stall line covers slow ones.

**Dream state delta.** After this plan: per-goal ranges, rough flag, pace, stall line, honest accuracy note. Still short of the ideal: no calibration loop (E4), owner-wait time inside step times (E3), slot-blind Finish. Backtest says the size rule costs accuracy today (x2.43 -> x3.49); the ideal needs E4's data to tune it.

**Error & Rescue Registry.** As in Section 2 (8 rows; the one GAP closed by CEO-S1).

**Failure Modes Registry.**
```
  CODEPATH            | FAILURE MODE                         | RESCUED? | TEST? | USER SEES?            | LOGGED?
  size_of             | unreadable goal file / bad slug      | Y (S1)   | Y     | rough estimate        | n/a (board text)
  queued items        | size lost at call site (P4)          | Y (D2)   | Y     | different ranges      | n/a
  model               | 0 or 1 history values                | Y        | Y     | no estimate / 2 ends  | n/a
  lift                | runaway inflation (P3)               | Y (D1)   | Y (c) | bounded lift          | n/a
  off-flow step       | estimated from idea (P5)             | Y (E1)   | Y     | build + rest          | n/a
  stalled             | waiting goal flagged                 | Y (SR20) | Y     | no false stall        | n/a
  stalled             | step with no estimate never flagged  | partial  | Y     | quiet-session Issue   | n/a
  render              | old text assertions break (P6)       | Y (D3)   | Y     | n/a                   | n/a
  accuracy            | size rule less accurate than median  | disclosed (V2) | backtest | rough/ranges | PR body
```
CRITICAL GAPS: 0 (no row is unrescued, untested and silent).

**Diagrams produced:** system architecture (Section 1), data flow with shadow paths (Section 4), error flow (Section 2 tables), dream state (0C), temporal sequence (0I). State machine: none new (no new stateful object). Deployment/rollback: single revert (Section 9), no diagram needed.

**Stale diagram audit.** Files touched: `board_status.py`, `graph.py`, `live_board.py`: no ASCII diagrams in them. `docs/wiki/Monitoring.md`: no diagram on estimates. None stale.

**Implementation Tasks (CEO).**
- [ ] **T1 (P1, human: ~3h / CC: ~15min)** — board_status/graph — size, size_of with slug check and per-field precedence
  - Surfaced by: 0A P4, Sections 2-3 (CEO-D2, S1, SR24)
  - Files: skills/workflow-monitoring/scripts/graph.py, skills/workflow-monitoring/scripts/board_status.py
  - Verify: bash dev/toy/test-estimates.sh (size checks)
- [ ] **T2 (P1, human: ~6h / CC: ~30min)** — board_status — plain-median similar/pooled model, quartiles, lift, pace, off-flow, stalled, overrun
  - Surfaced by: 0A P3/P5, dual voices backtest (CEO-D1, V1, V3, E1, SR10-SR23, S2)
  - Files: skills/workflow-monitoring/scripts/board_status.py
  - Verify: bash dev/toy/test-estimates.sh
- [ ] **T3 (P1, human: ~2h / CC: ~10min)** — live_board — call sites (items' left with here and root, estimate_text, stall helper call)
  - Surfaced by: 0A P4 (CEO-D2, SR14, V4)
  - Files: skills/workflow-monitoring/scripts/live_board.py
  - Verify: issue 96 defect check through live_board.render; wc -c under 20480
- [ ] **T4 (P1, human: ~4h / CC: ~25min)** — tests — new toy test, defect fixture, red proofs, existing assertions updated
  - Surfaced by: Section 6, 0A P6 (CEO-D3, SR2, SR12, SR16, V5)
  - Files: dev/toy/test-estimates.sh, dev/toy/test-live-board.sh, dev/toy/test-status-graph.sh, dev/toy/test-workers.sh, dev/toy/test-board-estimates.sh, .loop/regression.tsv
  - Verify: every dev/toy/test-*.sh passes; regression.py red for each new row
- [ ] **T5 (P2, human: ~1h / CC: ~10min)** — docs/PR — MON-4 scenarios, Tests render, docs line, PR body backtest and Closes lines, touches note, timing
  - Surfaced by: 0A, dual voices (CEO-D4, V2, SR8, SR19, S3)
  - Files: docs/wiki/Monitoring.md, skills/workflow-monitoring/SKILL.md or a reference
  - Verify: criteria.py render --check; docs.py check
_No new tasks from Sections 3, 8, 9 beyond those above._

**Completion Summary (CEO).**
```
  +====================================================================+
  |            MEGA PLAN REVIEW — COMPLETION SUMMARY                   |
  +====================================================================+
  | Mode selected        | SELECTIVE EXPANSION                         |
  | System Audit         | size does not predict time (corr ~0); plan  |
  |                      | envelope inflates 3-9x; queued size lost    |
  | Step 0               | D1 lifted model (V1 plain medians), D2, E1  |
  | Section 1  (Arch)    | 3 issues found (P3, P4, P5)                 |
  | Section 2  (Errors)  | 8 error paths mapped, 1 GAP (closed by S1)  |
  | Section 3  (Security)| 1 issue found, 0 High severity              |
  | Section 4  (Data/UX) | 9 edge cases mapped, 0 unhandled            |
  | Section 5  (Quality) | 1 issue found (branching, S2)               |
  | Section 6  (Tests)   | Diagram produced, 0 gaps                    |
  | Section 7  (Perf)    | 1 issue found (per-goal log reparse, S3)    |
  | Section 8  (Observ)  | 1 gap found (no explain; E5 deferred)       |
  | Section 9  (Deploy)  | 0 risks flagged                             |
  | Section 10 (Future)  | Reversibility: 5/5, debt items: 2           |
  | Section 11 (Design)  | SKIPPED (no UI scope)                       |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (9 items)                           |
  | What already exists  | written                                     |
  | Dream state delta    | written                                     |
  | Error/rescue registry| 8 rows, 0 CRITICAL GAPS                     |
  | Failure modes        | 9 total, 0 CRITICAL GAPS                    |
  | TODOS.md updates     | 0 items (no TODOS.md; 6 deferrals listed)   |
  | Scope proposals      | 6 proposed, 1 accepted (EXP + SEL)          |
  | CEO plan             | written (~/.review suite/.../ceo-plans/2026-11-10-estimate-model.md) |
  | Outside voice        | codex completed (gpt-6-astra, P1 findings)  |
  | Lake Score           | 1/1 recommendations chose complete option   |
  | Diagrams produced    | 5 (arch, data flow, error, dream, temporal) |
  | Stale diagrams found | 0                                           |
  | Unresolved decisions | 2 (owner gate: live_board lines, E1/SR13)   |
  | Reality rows         | 7/7 rows (PLAN_REALITY complete), 0 unverified |
  +====================================================================+
```
Approval readiness: PASS (rows CEO-D1/V1, D2, D3, D4, E1, SR1-SR27, V2-V5, S1-S3: autoplan unattended auto-decisions, recommended options; CEO-E2..E5 deferred, E6 declined; owner gate items pending).


### Phase 2 (Design): SKIPPED — no UI scope detected (scope uiRequired false, 0 UI matches). Not a completed review.

### Phase 2.5 (DX): SKIPPED — no developer-facing scope detected (1 term match, threshold 2; not a developer tool, not agent-primary). Not a completed review.

### Eng review (Phase 3)

Methodology loaded: Eng `autoplan-eng-methodology-NI3ds6/methodology.md` ranges 1-600, 601-1200, 1201-1800, 1801-2143 (2143 lines, EOF). Scope gate: target is this plan file (user-named in the dispatch). Design doc: `.loop/goals/estimate-model.design.md`; CEO plan: `<private review store>` (accepted D1/V1, D2, E1, D3, D4; deferred E2-E5).

#### Step 0: Scope Challenge

**What already solves each sub-problem.** See CEO 0B (all reused). Additional code read for Eng: `live_board.current` (`live_board.py:103-114`: done -> release index 7; off-flow -> newest report naming a FLOW step, else furthest flow-record step), `live_board.flow_lines` (`:117-133`, takes `over` from `bs.overrun`), `live_board.render` item construction (`:267-272`), `graph.SLUG` (`graph.py:13`), `board.py:201,216` (second `left_time` caller), `workflow-health/scripts/cost.py:71` (`seconds_by_step` caller, must stay unchanged).

**Minimum changes.** graph (2 small functions), board_status (size, model, estimate, stalled, text, stall lines), live_board call sites, one new toy test plus assertion updates, rows, docs. Nothing deferrable without failing a done line, except E1/SR13 (off-flow), which is an expansion already at the owner gate.

**Complexity check.** Planned changed files: graph.py, board_status.py, live_board.py, dev/toy/test-estimates.sh (new), dev/toy/test-live-board.sh, test-status-graph.sh, test-workers.sh, test-board-estimates.sh, .loop/regression.tsv, docs/wiki/Monitoring.md, a workflow-monitoring doc: 11 [estimated]. New classes/services: 0. At 8+ files the complexity gate trips: structure question auto-decided (plan-eng-review-structure): Original arrangement (11 files: logic in board_status, call sites in live_board, tests in dev/toy, docs) vs Smaller arrangement (no smaller arrangement keeps the approved features: the 4 test-file edits are forced by CEO-D3, the doc files by done line 6). Decision: Original arrangement; feature answers: none cut (P2: never reduce); pending remedies: none. Scope record: `feature answers: none; structure: A (auto-decided, recommended); accepted scope: CEO-accepted plan; pending remedies: none`.

**Search check.** No new architectural pattern, infrastructure or concurrency (stdlib statistics, functions, an in-process cache). Search skipped: in-distribution. [Layer 1] memoize per render; median/quartiles from stdlib.

**TODOS cross-reference.** No TODOS.md in this repo.

**Distribution.** No new artifact; existing release path.

| Premise | Claim | Receipt | Verdict |
|---|---|---|---|
| E-P1 | `here` index lines up with STEPS | `live_board.py:32` FLOW = STEPS + release; `board_status.py:23` STEPS | true today, but two hand-synced lists (red flag 8) |
| E-P2 | a per-render cache can key on the runs list | `live_board.py:268` passes the same `runs` list per call | risky: id-keyed caches can go stale across renders |
| E-P3 | goal-file done lines are the numbered list | `.loop/goals/board-estimates.md:6` `## Done lines`; goal files also have numbered `## Verify by hand` steps | parser must stop at the next `## ` heading |
| E-P4 | `left_time` has one caller | `board.py:201,216` also calls it | two callers; signature must stay compatible (CEO-SR7) |
| E-P5 | `seconds_by_step` may change | `workflow-health/scripts/cost.py:71` uses it | must stay unchanged (CEO-SR13 keeps it) |

unverified=0.

REALITY: premise-table finding 5 premises, 3 findings (E-P1 hand-synced lists, E-P2 cache key, E-P3 parser bound) skills/workflow-monitoring/scripts/live_board.py:32
REALITY: already-done pass origin/main since 2026-11-08 has no size-aware estimate or stall line in board_status.py or live_board.py (last estimate change c9093df, the over-by re-estimate) skills/workflow-monitoring/scripts/board_status.py:72
REALITY: surface-check pass named helpers exist: `live_board.current` (live_board.py:103), `status_graph.span` (status_graph.py:18), `graph.SLUG` (graph.py:13); `regression.py red --break` and `criteria.py render --check` per --help skills/workflow-regression/scripts/regression.py:13
REALITY: binding-decisions pass no branch decisions logged; CEO accepted blocks and the operation-session constraints are honored .loop/goals/estimate-model.design.md:30
REALITY: numbers pass the file sizes come from `wc -c` on the scripts (live_board.py, board_status.py) [measured]; the leave-one-out errors come from <scratchpad>/loo.py:44 [measured]; the 11-file count is an estimate [estimated] skills/workflow-monitoring/scripts/live_board.py:1
REALITY: deferred-asks pass issue 96 and issue 37 asks are covered by done lines 1-5 (frozen) .loop/goals/estimate-model.md:12
REALITY: pr-count pass one PR, no ship policy file .loop/goals/estimate-model.md:1

Scope Challenge result: scope accepted as-is. Findings (Step 0): [INFORMATIONAL] (confidence: 9/10) `live_board.py:32` / `board_status.py:23` — FLOW and STEPS are hand-synced; passing an index couples them. [INFORMATIONAL] (confidence: 7/10) `live_board.py:268` — a cache keyed on the list object can go stale. [INFORMATIONAL] (confidence: 9/10) `.loop/goals/board-estimates.md` — numbered Verify-by-hand steps would be miscounted as done lines. Dispositions: ENG-1, ENG-2, ENG-3 accepted (auto, P5).

<!-- autoplan-accepted:eng -->
- ENG-1 (Step 0): goal-file done lines are the top-level `N. ` lines between `## Done lines` and the next `## ` heading, outside code fences (numbered `## Verify by hand` steps never count); the Touches line is `- Touches:` split on commas. Verification: a toy goal file with 3 done lines, 4 numbered verify steps and a fenced numbered list counts d = 3; a goal file with no Done section gives unknown size.
- ENG-2 (Step 0): the per-render model is keyed by content (`at`, `root`, and each run's slug, status and `updated`), never by `id(runs)`. Verification: two renders in one process with a changed finished run give different estimates.
- ENG-3 (native 6): `graph.area` normalizes a Touches entry first: strip backticks, a leading `./` and a trailing `/`; a path segment containing `*` ends the fold before it (`skills/*/SKILL.md` -> `skills`, `dev/toy/test-*.sh` -> `dev`); `skills/README.md` (two parts) folds to `skills`. Verification: these cases in the area checks.
- ENG-4 (native 3, 4; Codex 7; replaces CEO-E1's index passing, CEO-SR7's `here` parameter, CEO-SR22 and CEO-SR23): `FLOW` and `current(run)` move into `board_status.py` (`live_board.py` keeps `FLOW = bs.FLOW` and `current = bs.current`), so there is one list and one position rule for the bar, the flow line, the estimate, the over-by and the stall line, in both `live_board` and `board.py`. `estimate`, `stalled`, `overrun` and `left_time` take `(run, runs, at, root=None)` and find the position themselves; a queued or freezing goal needs every step. `current` resolves an off-flow step from the newest timestamped evidence (report `at` or log entry time) naming a flow step, then the flow record; a stale older report never overrides a newer log entry. Verification: toy checks for a stale build report with a later review log entry at `checks` (position review), a queued goal (all steps), and the existing held-off-flow row still passing.
- ENG-5 (native 5): `stalled` skips held runs (the board's held goals already get their own Issue); the stall helper takes the held set from `live_board.issues`. Verification: a held goal far past 3x is not listed as stalled.
- ENG-6 (Codex 3): the estimator uses one accounting rule for history and live runs, `flow_seconds(run, at)` in `board_status.py`: each log gap counts toward the flow step in force (the last step started or named), including gaps that end in off-flow entries (reports, checks, session notes); gaps that start at a `stopped:`, `failed:` or `waiting:` entry are not counted until the next entry; the gap since the last entry counts only while running. `seconds_by_step` stays unchanged for `cost.py`. The backtest in the PR (CEO-V2) is re-run with this rule. Verification: toy logs with a mid-build report (full build time counted), an off-flow `checks` entry, and a stop/resume pause.
- ENG-7 (Codex 1; replaces the `U` increment of CEO-D1 and the "lift is 1" claims of CEO-D1 check (b), CEO-SR2 and CEO-SR25): the strictness increment is a named constant `STEP_UP = 60` seconds per extra done line or area: `lifted(d, a) = max(total(d, a), lifted(d-1, a) + STEP_UP, lifted(d, a-1) + STEP_UP)`. The issue 96 fixture gives each size at least 5 similar goals with actual totals spread at least 20 minutes (small goals 10-30m, large goals 90-150m) and asserts each rendered estimate lies within its similar goals' actual min and max; the test computes these bounds from the fixture, not from constants.
- ENG-8 (native 2; replaces CEO-D1 check (c)): the lift bound is a property: `lifted(d, a) <= max over grid points (d', a') <= (d, a) of total(d', a') + (d + a - 2) x STEP_UP`. Verification: a fixture with a high-total small size checks this bound for a large size.
- ENG-9 (Codex 2): ranges under overrun: before the current step passes its pace-adjusted estimate it contributes `(est - spent, max(0, low - spent), max(0, high - spent))`, with low clipped to at most left; once past it, it contributes `step_left`'s re-estimate `r` as left, low and high; remaining steps keep their ranges. `0 <= low <= left <= high` holds at every moment. Verification: one goal sampled before, at and after its step boundary checks the ordering each time.
- ENG-10 (Codex 5): a goal whose remaining steps include one with no estimate makes the Finish line read "at least finish about ...", like a goal with no estimate today; the partial flag travels with the item (`board_status` builds the items' `left` and `partial` in a helper). Verification: a partially estimated goal on the critical path gives "at least".
- ENG-11 (Codex 6, native 8): `lifted` is computed iteratively (no recursion) over d in 1..D and a in 1..A, with D and A clamped to the largest finished size plus 1; a larger goal uses the clamped corner plus `STEP_UP` per extra unit and is rough. Verification: a queue line with 60 done lines and 15 areas renders in under 1 s in the toy repo.
- ENG-12 (native 10, 11, 13): `statistics.quantiles` is called only with 2 or more values (one value: itself; none: no estimate), including inside the pooled-rate step sets; every stall and pace test passes a fixed `at` and checks 3x minus 1 s (not stalled) against 3x plus 1 s (stalled); each new regression row names its break command for `regression.py red --break` (for most rows: restore `board_status.py` from `origin/main`).
- ENG-13 (native 12, 14, 16): toy checks also cover the longest range text on a long slug staying within 60 columns after wrap; `size_of` reads a goal file only under the run's `worktree` when that is an existing directory under the repo's git common dir `loop/worktrees`, else under `root`, using `os.path.realpath` to refuse a path that leaves `.loop/goals`; the PR notes that the over-by marker moves with the new model.
- ENG-14 (native 15, Codex 5; extends CEO-SR14 and CEO-V4): `live_board.render`'s three item comprehensions become one `bs.board_items(...)` call returning slug, mark, depends, stage, left, low, high, rough and partial, so `live_board.py` shrinks instead of growing. The `live_board.py` edits are then: the items call, the bar and queued text via `estimate_text`, one stall-helper call in `issues`, the Finish `missing` test using `partial`, and the `FLOW`/`current` aliases (about 8 changed lines, about 15 removed); still an owner gate item since it exceeds "about 4 lines".
- ENG-15 (native 1, consolidates the amendments; later bullets in the CEO block that this list replaces are void): the final model, in one place:
  1. Size: `size_of(run, root)` -> `(d, a)` or None (CEO-SR24 precedence, ENG-1, ENG-3, ENG-13, CEO-S1).
  2. History: finished runs (status done, other slug, known size); per-step times from `flow_seconds` (ENG-6).
  3. Base per step: plain median, q25, q75 of the actual times of the similar goals (|d_i - d| <= 1, |a_i - a| <= 1) that logged the step when there are at least 5 similar goals, else of every finished goal that logged it (CEO-V1, ENG-12); unknown size: all finished goals, rough, no lift.
  4. Lift: `total` = sum of base medians over the seven steps; `lifted` by ENG-7 (iterative, ENG-11); `lift = lifted / total` multiplies every step's est, low and high.
  5. Running goals: position from `current` (ENG-4); spent from `flow_seconds`; pace over finished steps with an estimate, clamped 0.5..2, multiplies the current and remaining steps; overrun and ranges by ENG-9; `overrun()` uses the same numbers (CEO-SR10).
  6. Output: `estimate(...)` -> `(left, low, high, rough)` or None; `(0, 0, 0, False)` when nothing is left; rough when fewer than 5 similar goals, unknown size, or a remaining step has no estimate (CEO-V3); `estimate_text` prints `<low> to <high> left[, rough]`, `<1m left` for zero, `no estimate yet` for None (CEO-SR4, SR11).
  7. Stall: running, not held, current step's spent > 3 x its pace-adjusted lifted estimate; printed estimate is that number (CEO-SR20, SR26, ENG-5).
<!-- /autoplan-accepted:eng -->

#### Dual voices (Eng)

Input: `autoplan-eng-evKwOg/eng-implementation.md`, sha256 8d43d341... (the plan as closed by CEO; Eng Step 0 obligations ENG-1..3 were recorded after it and do not change its findings).

**Claude SUBAGENT (eng — independent review)**, native, completed, INPUT matched. 17 findings: (1) high: spec is a stack of amendments; (2) high: `U` from per-unit rates does not fit V1's plain medians, check (c) is a fixture property; (3) medium: `here` meanings differ (STEPS vs FLOW) and queued goals are unspecified; (4) medium: board.py and live_board can disagree; (5) high: held goals would be flagged stalled; (6) medium: area folding with globs, backticks, `./`; (7) medium: done-line parser contract; (8) low: large grids; (9) low: estimate jumps at the rough threshold; (10) low: quantiles with fewer than 2 points incl. inside U; (11) medium: stall tests need a fixed clock; (12) medium: missing tests (held, queued, cross-board, globs, cost.py, 60 columns); (13) low: name each red break; (14) low: worktree path validation; (15) medium: live_board 20 KB margin, move items building into board_status; (16) low: over-by moves; (17) low: `30m to 30m` reads like a bug.

**Codex SAYS (eng — architecture challenge)**, outside, completed (`OUTSIDE_STATUS: completed provider=codex host=claude`, gpt-6-astra, VERDICT findings P1). 7 findings: (1) high: "lift is 1" is impossible under V1 plus `U` (reproduced: a small goal estimate 800 s outside its actual range 600 s); (2) high: ranges have no defined overrun transformation (10/20/30 after 25 min becomes 12.5/12.5/5); (3) high: history uses `seconds_by_step` (drops gaps that end in off-flow entries; reproduced: a 10-minute build with a report at minute 9 records 1 minute) while live time uses new off-flow accounting; (4) medium: board.py stays a second, inconsistent integration; (5) medium: partial estimates lose incompleteness at Finish; (6) medium: memoization does not bound the grid, recursion depth; (7) medium: `current` prefers a stale report over newer evidence. Recommendation: revise before implementation.

```
ENG DUAL VOICES — CONSENSUS TABLE:
  Dimension                            Claude            Codex             Consensus
  1. Architecture sound?                no (spec, here)   no (accounting)   CONFIRMED: needs revision (fixed by ENG-4, ENG-6, ENG-15)
  2. Test coverage sufficient?          no (6 gaps)       no (fixture math) CONFIRMED: gaps (fixed by ENG-7, ENG-12, ENG-13, test plan)
  3. Perf risks + budget/bench named?   low (grid)        medium (grid)     CONFIRMED (ENG-11 budget: 60x15 under 1 s)
  4. Security threats covered?          low (worktree)    not raised        DISAGREE (single voice, low; ENG-13 accepted)
  5. Error paths handled?               held/quantiles    overrun ranges    CONFIRMED gaps (ENG-5, ENG-9, ENG-12)
  6. Deployment risk manageable?        yes (20 KB note)  board.py drift    DISAGREE (board.py stays deferred E2; ENG-4 shares the position rule)
```
Single-voice criticals: none rated critical; Codex 1-3 high, each verified by its reproduction or by code (`board_status.py:52-63`, `:77`).

Dispositions (auto-decided):
| Finding | Disposition |
|---|---|
| Claude 1 spec stack | ENG-15 restates the final model in one place (resolves CEO taste item 15) |
| Claude 2 / Codex 1 U and lift-is-1 | ENG-7 (`STEP_UP = 60` s) and fixture spreads; ENG-8 bound replaces check (c) |
| Claude 3, 4 / Codex 7 `here`, position rule | ENG-4 moves FLOW and `current` into board_status with timestamp precedence |
| Claude 5 held goals | ENG-5 |
| Claude 6, 7 parsing | ENG-1, ENG-3 |
| Claude 8 / Codex 6 grid | ENG-11 |
| Claude 9 threshold jump | documented in the docs line (accepted behavior) |
| Claude 10, 11, 13 | ENG-12 |
| Claude 12, 14, 16 | ENG-13 and the test plan |
| Claude 15 live_board size | ENG-14 (`bs.board_items`) |
| Claude 17 two equal ends | kept (done line 2 says a range); TASTE carried to the gate |
| Codex 2 overrun ranges | ENG-9 |
| Codex 3 accounting | ENG-6 |
| Codex 4 board.py | deferred (E2, outside touches); ENG-4 removes the position disagreement |
| Codex 5 partial Finish | ENG-10 |

#### Section 1: Architecture

```
                    graph.py                      board_status.py (owns the model)
  queue.md ──> parse(line) ─┐            ┌─> FLOW, current(run)  <── moved from live_board (ENG-4)
                area(path) ─┼─ size() ──>│   size_of(run, root)    goal file > queue line > run touches
                            │            │   flow_seconds(run, at) one accounting rule (ENG-6)
  loop/runs/*.json ─────────┘            │   model(runs, at, root)  content-keyed per render (ENG-2):
  .loop/goals/<slug>.md ────────────────>│      similar >=5 ? similar times : pooled; q25/median/q75;
                                         │      lifted grid, iterative, clamped (ENG-7, ENG-11)
                                         │   estimate / stalled / overrun / left_time (run, runs, at, root)
                                         │   estimate_text, stall_lines(held), board_items(...)
                                         └───────────────┬───────────────────────────────────────
                                                         v
  live_board.py: FLOW = bs.FLOW; current = bs.current; items = bs.board_items(...);
                 bar/queued text = bs.estimate_text(...); issues += bs.stall_lines(...);
                 Finish "at least" when any item is partial
  board.py (unchanged): bs.left_time(run, records, at)   status_graph.chain (unchanged)
  workflow-health/cost.py (unchanged): bs.seconds_by_step
```
Coupling: live_board depends on board_status for FLOW/current (it already imports it); no new cycle (board_status imports live_board only inside `main`). Scaling: model cost O(D x A x runs x steps) with D, A clamped (about 16 x 12 x 57 x 7, about 77k operations). Production failure per path: a malformed goal file (unknown size, rough); a stale report (resolved by timestamps); an unreadable runs dir (existing: empty list, "no estimate yet").

**Design-twice.** New public surface: board_status's model functions. Shape A (chosen): module functions with a hidden content-keyed cache; callers pass `(run, runs, at, root)`. Shape B: a `Model` object built once per render (`m = bs.Model(runs, at, root)`; `m.estimate(run)`), explicit lifetime, no hidden cache. Depth: A hides the cache and the position rule behind the same four-argument calls the board already makes (smaller surface for live_board and board.py); B makes the lifetime explicit but every caller (board.py included, outside touches) must build and thread it. Pick A. Red flags: (1) shallow module: no. (2) information leakage: FLOW/current lived in live_board while estimates needed them; fixed by ENG-4. (4) pass-through: `left_time` becomes `estimate(...)[0]` for board.py; kept for compatibility, documented. (6) two ways: `seconds_by_step` (cost) and `flow_seconds` (estimates) are two accountings; kept deliberately (cost.py contract), named for their uses in docstrings. (8) hand-synced list: FLOW vs STEPS; fixed by deriving `FLOW = STEPS + ("release",)` in board_status. Other flags: none.

Findings: [INFORMATIONAL] (confidence: 9/10) `live_board.py:32` — FLOW hand-synced with STEPS (ENG-4). [INFORMATIONAL] (confidence: 8/10) `live_board.py:103-114` — `current` prefers any newest flow report over newer log evidence (Codex 7; ENG-4). Dispositions: accepted.

#### Section 2: Code quality

Findings: [INFORMATIONAL] (confidence: 9/10) `board_status.py:52-63` — `seconds_by_step` drops gaps that end in off-flow entries ("start plan", reports, checks), so history undercounts (Codex 3 reproduced; ENG-6). [INFORMATIONAL] (confidence: 8/10) plan CEO block — superseded amendments (ENG-15). [INFORMATIONAL] (confidence: 7/10) estimate branching (CEO-S2 split kept). Shared code: `current` is reused by both boards after ENG-4 (two verified callers: `live_board.py:124` flow_lines and the new estimate path; board.py via `left_time`); helper contract `current(run) -> FLOW index`, existing tests held-off-flow and live-board-flow cover it; implementation lines moved about 12 (out of live_board) and about 12 in (board_status), net about 0, plus aliases. Error handling: CEO-S1 narrow catches; ENG-12 quantile guard. Touched-file diagrams: none in these files. Dispositions: accepted.

#### Section 3: Test review

Framework: no CLAUDE.md testing section; repo tests are bash toy repos under `dev/toy/test-*.sh` run by `.loop/regression.tsv` rows (`regression.py run`). Code read for tracing: `board_status.py` (all), `live_board.py:100-135, 200-330`, `graph.py:17-31`, `status_graph.py:18-60`, `dev/toy/test-board-estimates.sh:1-51`.

```
CODE PATHS                                              USER FLOWS
[+] graph.py                                            [+] Owner reads the live board
  ├── area()  [GAP->planned ★★★] folding+globs+root     ├── [GAP->planned ★★★] queued 3 vs 12 differ (issue 96, defect row)
  └── size()  [GAP->planned ★★] empty -> None           ├── [GAP->planned ★★★] running goal range + pace
[+] board_status.py                                     ├── [GAP->planned ★★★] stalled line under Issues (issue 37)
  ├── size_of()      [GAP->planned ★★★] precedence,     ├── [GAP->planned ★★]  off-flow goal placed right
  │                  bad slug, unreadable, no Done       └── [★★ TESTED, update] existing board text rows
  ├── flow_seconds() [GAP->planned ★★★] report gap,         (test-live-board:61, test-status-graph:66,
  │                  off-flow, pause                         test-workers:129, test-board-estimates:42,51)
  ├── current()      [★★ TESTED held-off-flow] + [GAP->planned] stale report
  ├── model()        [GAP->planned ★★★] >=5 vs 4, one value, cache key, big grid
  ├── lifted         [GAP->planned ★★★] strict order, bound
  ├── estimate()     [GAP->planned ★★★] queued all steps, done 0, partial, ranges before/at/after overrun
  ├── stalled()      [GAP->planned ★★★] 3x±1s, no estimate, waiting, held
  ├── overrun()      [★★ TESTED board-estimates-overrun, update]
  ├── estimate_text()[GAP->planned ★★] two ends, rough, <1m, none
  └── board_items()  [GAP->planned ★★] partial -> "at least"
[+] live_board.py call sites  [→E2E via render] covered by the issue 96 and stall render checks
[+] cost.py (unchanged seconds_by_step)  [★★ TESTED existing cost/health tests]

LLM integration: none (no prompt changes).
COVERAGE (planned): 20/20 paths with a planned ★★ or ★★★ test  |  existing: 3/20
QUALITY (planned): ★★★:13 ★★:7  |  GAPS after plan: 0
```
Regression rule: the rewrite puts existing board behavior at risk (MON-4 rows estimates-shown, status-graph-marks, live-board-*, board-estimates-overrun, held-off-flow). Approved regression contract (CEO-D3, CEO-SR12): every `dev/toy/test-*.sh` passes; assertions change only in estimate text, not in what they check. Test plan artifact: `<private review store>` (written). Tests made obsolete: none. Findings: Codex 1 (fixture impossible) and Claude 11/12 (clock, missing tests): accepted as ENG-7, ENG-12, ENG-13.

#### Section 4: Performance

Hot path: every board render (each check-in and each operate wake). Today `left_time` calls `usual` per step, which reparses every run's log: O(goals x steps x runs) log parses per render. New: the content-keyed model parses each run once per render and evaluates the clamped grid iteratively (ENG-2, ENG-11). Goal-file reads: one per finished run per render (57 small files today) [measured count: 57 runs]. Budget: the change adds under 0.5 s per render on this repo (CEO-S3) and a 60 x 15 queue line renders under 1 s (ENG-11). Memory: grid at most (largest finished size + 1)^2 floats. No queries, no network. Findings: [INFORMATIONAL] (confidence: 8/10) `board_status.py:66-69` — per-goal reparse of all logs (fixed by the cache). Dispositions: accepted.

#### Eng required outputs

**NOT in scope (Eng).** `board.py` size-aware queued estimates (E2, Codex 4); Finish slot-awareness (CEO); a repo TODOS.md (this repo tracks follow-ups as GitHub issues; the deferred items are listed for the owner instead of creating a new file in the goal's diff); prediction calibration (E4); owner-wait exclusion beyond stopped/failed/waiting pauses (E3).

**What already exists.** `seconds_by_step` (kept for cost.py), `step_left` (reused for overrun), `graph.parse` (queue size), `live_board.current` (moved, reused by both boards), `status_graph.span` and `chain` (reused), `fit` (wraps the longer text), regression/criteria tools (rows, red, render).

**Failure modes (Eng).**
| Path | Realistic failure | Test | Handling | User sees |
|---|---|---|---|---|
| flow_seconds | log vocabulary changes (new entry words) | ENG-6 checks | gaps go to the step in force | slightly different times, never a crash |
| current | stale report vs newer log | ENG-4 check | timestamp precedence | right step |
| model cache | stale across renders | ENG-2 check | content key | fresh estimates |
| lifted | huge queue line | ENG-11 check | clamp, rough | rough range |
| estimate ranges | overrun breaks order | ENG-9 check | defined transform | ordered range |
| stall | held or waiting goal | ENG-5, SR20 checks | skipped | no false Issue |
| Finish | partial estimate | ENG-10 check | "at least" | honest Finish |
| live_board size | passes 20,480 bytes | wc -c in build | board_items helper | n/a |
Critical gaps: 0.

**Worktree parallelization strategy.** Sequential implementation, no parallelization opportunity (one primary module, `board_status.py`, with the call sites and tests depending on it).

**Implementation Tasks (Eng).**
- [ ] **T6 (P1, human: ~3h / CC: ~15min)** — board_status — move FLOW and current with timestamp precedence; flow_seconds accounting
  - Surfaced by: Codex 3, 7; Claude 3, 4 (ENG-4, ENG-6)
  - Files: skills/workflow-monitoring/scripts/board_status.py, skills/workflow-monitoring/scripts/live_board.py
  - Verify: bash dev/toy/test-board-held.sh (held-off-flow) and the new stale-report and accounting checks
- [ ] **T7 (P1, human: ~4h / CC: ~20min)** — board_status — STEP_UP lift (iterative, clamped), overrun ranges, partial flag, board_items, stall_lines with held set
  - Surfaced by: Codex 1, 2, 5, 6; Claude 2, 5, 8, 15 (ENG-5, ENG-7..11, ENG-14)
  - Files: skills/workflow-monitoring/scripts/board_status.py, skills/workflow-monitoring/scripts/live_board.py
  - Verify: bash dev/toy/test-estimates.sh; wc -c skills/workflow-monitoring/scripts/live_board.py under 20480
- [ ] **T8 (P1, human: ~3h / CC: ~15min)** — tests — fixture spreads, fixed clock, 3x±1s, parser/area/cache/grid/60-column checks, named red breaks
  - Surfaced by: Section 3; Claude 11-13; Codex 1 (ENG-1..3, ENG-12, ENG-13)
  - Files: dev/toy/test-estimates.sh, .loop/regression.tsv
  - Verify: every dev/toy/test-*.sh passes; regression.py red for each new row
_No new tasks from Section 4 beyond T7's cache and grid._

**Completion summary (Eng).**
- Step 0: Scope Challenge — scope accepted as-is
- Reality rows: 7/7 applicable rows emitted (PLAN_REALITY: phase=eng rows=7/7 missing=none verdict=complete), 0 unverified premises
- Architecture Review: 2 issues found
- Code Quality Review: 3 issues found
- Test Review: diagram produced, 17 gaps identified (all planned)
- Performance Review: 1 issue found
- NOT in scope: written
- What already exists: written
- TODOS.md updates: 0 items written (no TODOS.md in this repo; 6 deferrals listed for the owner)
- Failure modes: 0 critical gaps flagged
- Unresolved decisions: 2 (owner gate: live_board.py edit size; off-flow expansion)
- Outside voice: codex completed (gpt-6-astra), 7 findings, all dispositioned
- Parallelization: 1 lane, 0 parallel / 1 sequential
- Lake Score: N/A (no coverage-scored questions asked)

Approval readiness: PASS (ENG-1..ENG-15: autoplan unattended auto-decisions on reviewer findings; owner gate items pending).

<!-- AUTONOMOUS DECISION LOG -->
## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | CEO | Mode SELECTIVE EXPANSION | Mechanical | override | autoplan rule | other modes |
| 2 | CEO | Replace per-step rescaled envelope with goal-level lift (CEO-D1) | Taste | P1, P5 | measured 3-9x inflation on 57 runs | keep plan envelope; no envelope |
| 3 | CEO | Queued goals pass queue-line dict and root (CEO-D2) | Mechanical | P1 | P4: queued size lost at call site | slug-only dicts |
| 4 | CEO | Accept E1 off-flow steps use live_board.current | Taste (owner gate) | P2, P4 | checks estimated as idea today | duplicate logic in board_status |
| 5 | CEO | Update existing board tests' text assertions (CEO-D3, SR12) | Mechanical | P1 | P6 anchored regexes break | leave tests failing |
| 6 | CEO | PR body Closes #96 and #37 (CEO-D4) | Mechanical | P1 | done lines 4, 5 | — |
| 7 | CEO | Defer E2-E5, skip E6 | Mechanical | P3 | outside touches / width | include |
| 8 | CEO | Spec review fixes SR1-SR27 | Mechanical | P1, P5 | reviewer findings, 3 rounds | — |
| 9 | CEO | 0H document approval A | Mechanical | P6 | recommended | revise, pause |
| 10 | CEO | Base estimate = plain medians of similar actual times (CEO-V1) | Taste | P5, P1 | best backtest among compliant variants (x3.49 vs x3.67), literal done line 1 | scaled rates; linear fit |
| 11 | CEO | Report backtest in PR, say range is summed quartiles (CEO-V2) | Mechanical | P1 | both voices: differentiation is not accuracy | silence |
| 12 | CEO | Rough also when a remaining step has no estimate (CEO-V3) | Taste | P1 | Codex 5: rough should reflect coverage | done-line-only rough |
| 13 | CEO | Stall formatting in board_status helper now (CEO-V4) | Mechanical | P5 | live_board 1.8 KB headroom | fallback only |
| 14 | CEO | Reject linear fit and splitting #37 | Mechanical | P4, frozen done lines | design rejected fitted model; done lines | adopt |
| 15 | CEO | Keep amendment blocks, Eng restates final model | Taste | P6 | autoplan record; avoid churn | fold now |
| 16 | CEO | Keep two-end range text | Taste | done line 2 | "range" literal | collapse equal ends |
| 17 | CEO | Slug check, narrow catches, branch split, timing (S1-S3) | Mechanical | P1, P5 | Sections 2, 3, 5, 7 | — |
| 18 | Eng | Structure: original arrangement, no cuts | Mechanical | P2 | no smaller arrangement keeps the approved features | smaller arrangement |
| 19 | Eng | Parser bound, cache key, area normalization (ENG-1..3) | Mechanical | P5 | Step 0 and native 6, 7 | — |
| 20 | Eng | Move FLOW and current into board_status with timestamp precedence (ENG-4) | Taste (owner gate) | P4, P5 | one position rule; fixes stale reports and hand-synced lists | pass index or name from live_board |
| 21 | Eng | Held goals never stalled (ENG-5) | Mechanical | P1 | native 5 | — |
| 22 | Eng | One accounting rule flow_seconds (ENG-6) | Mechanical | P1 | Codex 3 reproduced undercount | keep seconds_by_step for history |
| 23 | Eng | STEP_UP 60 s replaces U; fixture spreads (ENG-7, ENG-8) | Taste | P5 | Codex 1: lift-is-1 impossible | keep U; cap lift |
| 24 | Eng | Overrun range transform (ENG-9) | Mechanical | P1 | Codex 2 | leave ranges undefined |
| 25 | Eng | Partial estimates make Finish "at least" (ENG-10) | Mechanical | P1 | Codex 5 | — |
| 26 | Eng | Iterative clamped grid (ENG-11) | Mechanical | P5 | Codex 6, native 8 | recursive memo |
| 27 | Eng | Quantile guard, fixed clock, named breaks, path checks (ENG-12, ENG-13) | Mechanical | P1 | native 10-14 | — |
| 28 | Eng | board_items helper shrinks live_board (ENG-14) | Taste (owner gate) | P3 | 1.8 KB headroom | grow live_board |
| 29 | Eng | Consolidated final model (ENG-15) | Mechanical | P5 | both natives: patched spec | leave amendments only |
| 30 | Eng | No TODOS.md created; deferrals listed for owner | Mechanical | P3 | repo tracks issues, file outside touches | write TODOS.md |
| 31 | Eng | board.py stays deferred (E2) | Mechanical | P3 | outside touches | wire board.py |

