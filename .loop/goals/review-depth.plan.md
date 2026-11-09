# Plan: review-depth

Source: `.loop/goals/review-depth.design.md` (spec review PASS). Done lines: `.loop/goals/review-depth.md`.

## Implementation plan

1. `skills/workflow-delivery/scripts/role.py`
   - `depth_of(cfg)`: `"condensed"` when `cfg.get("review_depth") == "condensed"`, otherwise `"full"`.
   - `check_depth(text, step, setting, markers)` returns `(depth, error)`:
     - `DEPTH:` is read from the text before the last `STEP:` line, and the last match wins. A missing or malformed
       line is an error in every step.
     - For plan and review: claiming `condensed` under `full` is an error.
     - For plan and review claiming `full`, under either setting: each configured marker must appear in the text before
       `STEP:`, case-insensitive, excluding the `DEPTH:` line. A missing marker is an error that names it.
     - Markers that aren't a list of strings are ignored, with a `NOTE:` line.
2. `skills/workflow-delivery/scripts/goal.py` `cmd_record`: one call to `role.check_depth`. The setting comes from
   `config()` and the markers from the private flow file (`full_markers`). An error goes to `failed_try` with the
   reason. On success the flow entry is stamped `(depth X)` and `state["depth"][step] = X` is saved. goal.py must stay
   under 20 KB.
3. `skills/workflow-delivery/scripts/flow.py` `PROMPT`:
   - The depth rule for plan and review, from the setting: full is "run the skill's full pipeline, every phase and
     pass; never condense it"; condensed is "a condensed run is allowed; say so".
   - The `DEPTH:` line rule for every step.
   - The headless and IN SESSION paths share it.
4. `skills/workflow-monitoring/scripts/live_board.py` `worker_of`: appends
   `· depth: <step> <depth>, ... (setting <s>)` from `state["depth"]` and the config.
5. `skills/workflow-setup/scripts/settings.py`:
   - `TABLE` rows: `review_depth` (repo, `"full"`, one line) and `full_markers` (private, `{}`).
   - `fill-repo` refuses an unknown `review_depth` and writes `"_help": {"review_depth": ...}` when missing.
   - `setup.py` `merged()` writes the same `_help`.
   - Regenerate `references/settings.md`.
6. `.loop/config.json`: `"review_depth": "full"`. Docs: `skills/loop-files.md`, `docs/wiki/Delivery.md`, the delivery
   SKILL.md step text.
7. `dev/toy/test-review-depth.sh`: the cases in design rule 10, plus a check that the repo config loaders
   (`watch.config`, `goal.config`, `flow.repo_config`, `live_board`/`board_status`) load a config containing `_help`.
   Regression rows link each case to the goal's done lines, and each row is seen red.
8. Existing toy tests whose stand-in replies lack a `DEPTH:` line are updated to include it (`make.sh`'s stand-in flow
   reply and `flow-done.sh`).

## Review record

The plan review ran at full depth, unattended, through the review driver. It covered the strategy (CEO), developer
experience (DX) and engineering (Eng) phases. Each phase had a native reviewer. The outside voice was unavailable in
every phase: the configured outside model is not supported for the account. Findings: CEO 11, DX 14, Eng 13
(1 Critical, 7 High across phases). The run stopped at its final gate (gate_rev 1), which this step never approves:
- **d1:** reframe depth as control through a per-depth skill invocation. Recommended: keep the stated direction.
- **d2:** a per-goal override. Recommended: keep the stated direction.
- **p1:** plan approval.

### Build obligations taken from the findings

1. **Gate placement (Eng F1 Critical, F2 High, CEO F4).** The depth check runs only in the two branches of
   `cmd_record` that advance a step: auto-approve and done/skipped. A failed reply, a reply with no STEP line, or a
   time-limit kill keeps its real reason. A pending reply under `auto_approve` is checked before it is approved.
2. **Size (CEO F3, DX, Eng F3).** goal.py has about 500 bytes left under the 19,500-byte toy limit. The check, the
   stamp and the `state["depth"]` write live in one `role.record_depth(...)` function, and goal.py makes one call.
3. **Stamp position (DX, Eng).** `(depth X)` goes at the end of the flow entry, after the existing truncation, so the
   `startswith("done")` checks still hold.
4. **DEPTH line (DX F4, CEO F5).** Format: the same forms the STEP check accepts (`^\W*DEPTH:\s*(full|condensed)\b`,
   any case). It is required in every step that advances: frozen done line 2 needs every recorded result to say which
   depth ran. A missing line is a failed try whose reason gives the exact line to add, so the re-run costs one step.
   The reviewers' softer "(depth not stated)" for idea, qa and ship is not taken, because it would break done line 2.
5. **Marker hygiene (DX F1, Eng).**
   - The missing-marker error never prints the marker; it says "a configured full_markers evidence string for review
     is missing".
   - `full_markers` that isn't a map, or a marker that is empty or not a string, is ignored with a NOTE, never a
     crash.
   - Markers are read from `$LOOP_FLOW` or `~/.workflow-loop/flow.json`.
   - `full_markers` goes into `FLOW_KEYS`, so `fill-private` writes it with its help line.
6. **Error context (DX F3).** "condensed under full" names `review_depth` in `.loop/config.json` and the fix (rerun
   the step at full, or set `condensed`).
7. **A skipped step under full (Eng Low)** is stamped `(depth full, skipped)`: no full run is claimed beyond the
   skip.
8. **Board.** Depth gets its own line under the worker line: `depth: idea full, plan full, review full (setting full)`.
9. **Toy tests.** Every toy test whose stand-in plan or review reply lacks a DEPTH line is updated: make.sh's flow,
   flow-done.sh, and any test that checks exact strings, such as test-session-workers' "done in session". The
   auto-approved condensed review under full case is added.
10. **Unknown value.** `fill-repo` refuses an unknown `review_depth` (case-sensitive `full` or `condensed`).
11. **PR body.** The PR lists the behavior changes: DEPTH lines, `_help` in config, and goals in flight may lose one
    try.

Not taken: d1 and d2 (direction changes; the recommendation is to keep the direction), and the step-time and budget
interaction (CEO F8), which goes into the PR as a known limit.

Result: stopped at the final gate, pending. Artifacts are in the run directory (not committed).
