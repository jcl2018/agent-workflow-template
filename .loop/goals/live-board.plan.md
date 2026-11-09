# Plan: live-board

Goal: `.loop/goals/live-board.md` (done lines and Verify by hand are frozen and belong to delivery; not restated or reopened here).
Design: the idea step's design doc (approach B). No UI scope (text board plus an existing generated HTML fragment); no developer-tool scope.

## Implementation plan

Order: MON-4/MON-5 wording, then `live_board.py`, then callers (`board_status.py`, `operate.py`, `board.py`, `board_page.py`/`board_map.py`), then toy test and old assertions, then docs.

1. **MON-4/MON-5 wording.** Unreview MON-4 and MON-5, rewrite both in `docs/wiki/Monitoring.md` word for word as the goal says, run `criteria.py review --user` for those two only dated 2026-11-08, then `criteria.py render`. Existing MON-4/MON-5 regression rows stay linked; rows that assert old sections or the one-line mode are re-pointed to the new text (never deleted without a replacement).
2. **`live_board.py` (new, `skills/workflow-monitoring/scripts/`).** `render(root, at)` returns the text; a fragment wrapper returns the HTML form. Header `LIVE BOARD  <repo>  <local time>  v<VERSION>  health: <ok|N findings|unknown>` (health via a cheap, time-boxed workflow-health call, `unknown` on error or timeout). Sections in fixed order: Issues (open only, stuck worker pinned first, `(none)` when empty, each fix in plain words with the exact answer words), Running (10-cell bar, percent, time left or `no estimate yet`; step flow idea > plan > build > review > qa > ship > pr > release with done steps ticked and the current step in brackets; one-line `next:`), Queued (with `waits on`), Dependencies (arrows `dep --> slug`, running and queued only, `(none)` if no edges), Finish (one time from the longest chain, `status_graph.total`). It reuses `status_graph` (CELLS, chain/total), `graph` (clock, localize, flow) and the existing estimates helpers; no second copy of the logic.
3. **Plain-words fixes.** A sanitizer strips absolute and home paths (absolute, home and .git paths) from any fix text to the basename or drops them; applied inside `live_board.py` so every surface gets it.
4. **Callers.** `board_status.py` `sections/text/fragment` delegate to `live_board`; dead helpers (milestones, wiki extras, token tables, goal_lines, merged_line, done-line lists) are deleted. `operate.py` always prints the full board each pass and drops the `NO_CHANGE` and quiet branch. `board.py` drops the `NO_CHANGE` print and its handoff wording, keeps `DIGEST`/`CHANGED`/`NEXT_DELAY` for the report-at-once trigger, and `cadence_of` fallback and the stored default move from 10 to 30 minutes. `board_page.py` and the artifact page embed the same fragment, so the page and the text agree.
5. **Size.** `board.py` is 17.3 KB and `board_status.py` 15.8 KB of the 20 KB cap; deleting the old code must shrink them, and `live_board.py` splits (for example a separate sanitizer/health helper) before it nears 20 KB. Check sizes after each edit.
6. **Toy test (done line 5).** `dev/toy/test-live-board.sh`, no model: toy repo with 2 running, 2 queued, one chain and one open issue (a stuck worker); asserts every board line against the format (header fields, bar cells and percent, flow ticks and brackets, arrows, `(none)` forms, finish line), no local paths, none of Merged/closed/milestone/token/done-line text, no `NO_CHANGE`. Update the existing assertions that name the old sections or the quiet mode (`test-status-graph.sh`, `test-operate.sh`, `test-operate-fit*.sh`, `test-monitoring.sh`, `test-tokens.sh`, `test-workers.sh`, `test-wiki.sh`, `test-autorelease.sh` where they touch the board) and add regression rows tied to MON-4/MON-5.
7. **Docs.** `references/operation.md`, `references/commands.md`, `SKILL.md`, `docs/wiki/Monitoring.md`; `docs.py check` and `criteria.py render --check` pass; run the full toy suite and repo checks at the end.

## Failure modes

| Step | Failure | Handling |
|---|---|---|
| 2 | Health call slow or failing | time-box it; print `health: unknown`, never block the board |
| 2 | Goal with no estimate | `no estimate yet` and an `at least` finish, never 0 |
| 2 | Dependency on an unknown or cycle goal | keep status_graph's `? slug` node and `cycle:` note, no loop |
| 3 | A fix text carries a local path | sanitizer drops it; toy test asserts none appear |
| 4 | Scripts near the 20 KB cap | delete dead code first; split modules; size check |
| 4 | Removing `NO_CHANGE` breaks a worker-report wake path | keep `DIGEST`/`CHANGED`; `operate-wakes-on-report` regression row must stay green |
| 6 | Old tests and regression rows assert old sections | updated in the same change, re-pointed not deleted |

## Review record
