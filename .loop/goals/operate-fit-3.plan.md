# Plan: operate-fit-3

Goal: `.loop/goals/operate-fit-3.md` (done lines and Verify by hand are frozen and belong to delivery; not restated or reopened here).
No design doc exists for this goal; the goal file's four done lines are the design. Reviewed by /autoplan (unattended; no UI or developer-tool scope). Every question took the recommended answer.

## Implementation plan

Order: `graph.py` helpers, then `board_status.py` (wiki line, flow chart, localized total), then `operate.py` (local times), then the toy test, then docs.
Everything stays inside the goal's Touches. `status_graph.py` and `board.py` are not in Touches and stay unchanged; their UTC or zone-less times are fixed at the print boundary instead.

1. **Time and flow helpers in `graph.py`.**
   - `clock(at)`: `at.astimezone().strftime("%H:%M %Z")`; if the platform gives an empty zone name, `"%H:%M UTC%z"`.
   - `localize(text)`: rewrites `HH:MM UTC` (dated as today in UTC) and `YYYY-MM-DDTHH:MM:SSZ` stamps into local time followed by the zone name; text with neither passes through unchanged.
   - `flow(nodes)`: pure; nodes are `slug`, `mark`, `depends`. Returns `[]` when no node has a dependency, else a `flow (arrow = must finish before):` line plus one line per goal that others wait on: `[running] a --> [queued] b, [queued] c`. One line per source, not per path, so a wide graph cannot blow up. A dependency that is no goal here is drawn as `[? not a goal here]`, and a cycle is printed once, not followed.
2. **Wiki line (done line 1), `board_status.py`.** New `wiki_check(root)` runs `docs.py check` from the sibling `workflow-docs` skill (`../../workflow-docs/scripts/docs.py` next to this script), `cwd=root`, 60 s cap, and returns the reported pages as `[(kind, page)]`, or `None` when the check could not judge (script missing, timeout, exit other than 0 or 1, or `NO PAGES`). Exit 0 is the empty list. Output lines `KIND Page: detail` are parsed with `^([A-Z]+) (\S+): `.
   - Needs you gets at most one wiki line, built every pass from the current check: `- wiki (docs check): Documentation stale, Home missing. Fix: python3 <docs.py> audit`.
   - Saved `wiki_error` records no longer print one line per goal. A saved error is judged by `page <Name>` at its start: dropped when the check ran and no longer reports that page, folded into the one line when the page is still reported, and, when it names no page or the check could not judge, kept in the same line as `saved: <text>` under the existing `error_open` merged and published rules. No publish is needed to clear it.
   - `release_error` lines are unchanged.
3. **Flow chart and ending (done line 2), `board_status.py`.** Roadmap = `status_graph.render_text(live, under)`, then `graph.flow(live + unknown deps)`, then the merged and closed lines and milestones, then last a `longest path:` line. That line is `status_graph.total(live, at)` with its `finish about HH:MM` swapped for `graph.clock(at + longest seconds)`, so the zone name shows without editing `status_graph.py`. The Total section prints the same line. It is always last in Roadmap, with no finish time only when the total has none ("no estimate yet", "nothing left").
4. **Local times (done line 3), `operate.py`.** Every line `operate` prints (the block, the quiet "Next check-in" line, watch output, changes) goes through `graph.localize`. `board_page.py` output is a file path and needs nothing. `board.py` and `board_map.py` keep emitting UTC to their own consumers and tests.
5. **Toy test (done line 4).** New `dev/toy/test-operate-fit-3.sh`, same harness shape as `test-operate-fit.sh`, with `TZ=Asia/Kolkata` (a fixed non-UTC offset). Seeds: unmerged goals with old `wiki_error` for a page the docs check no longer reports and for a page it still reports; a repo whose pages are written, so `docs.py check` is clean, then one page made stale by a commit to a mapped path; queued goals chained `a <- b <- c` plus a branch `d` that waits on `a`. Assertions: with a clean check Needs you has no wiki line; with a stale page exactly one wiki line names that page and the fix and the old error of the clean page is gone; the Roadmap holds arrow lines for the chain and ends with `longest path:` carrying `finish about HH:MM IST`; no `UTC` in any `operate.py run --once` output; the quiet pass prints one line with `IST`. The same script adds direct assertions for the branches the integration run cannot reach: `wiki_check` returning `None` (no `docs.py`, `NO PAGES`), a saved error naming no page, an unknown dependency and a cycle in `graph.flow`, and `graph.localize` on a plain line, and it checks that two passes with an unchanged check print one line (reported pages sorted). The existing `test-operate-fit.sh` assertions on the per-goal `late (wiki not published)` lines move to the one-line format; `test-operate.sh`, `test-monitoring.sh`, `test-board.sh`, `test-status-graph.sh` and `test-docs.sh` stay green unchanged.
6. **Docs.** `skills/workflow-monitoring/references/operation.md` and `docs/wiki/Monitoring.md` describe the single wiki line from the current check, the flow chart and closing longest-path line, and local times; `docs.py check` passes; every script stays under 20 KB (`board_status.py` 13.9 KB now, about 1.5 KB added; `graph.py` 3.3 KB, about 2 KB added).

## Failure modes

| Step | Failure | Handling |
|---|---|---|
| 2 | `docs.py` missing, slow or odd exit | check judged `None`: saved errors fall back to the old per-goal rule, folded into the one line; nothing is hidden |
| 2 | A real publish failure that names no page | kept as `saved: ...` in the one line; never silently dropped |
| 2 | `docs.py check` costs git calls on every pass | one call per pass, 60 s cap; the quiet-pass line stays one line |
| 3 | Dependency on a closed or unknown goal | drawn as `[? not a goal here]`, as the graph already does |
| 3 | A cycle in `depends` | flow prints each edge once; `status_graph` already cuts the cycle in the total |
| 4 | `HH:MM UTC` has no date, so a day boundary shifts | dated as today in UTC; only the clock and zone are shown |
| 4 | Platform returns an empty zone name | fall back to `UTC+hhmm` offset text, still not bare "UTC" |
| 5 | Zone-dependent assertions flake | the test pins `TZ` and never compares to the host zone |

## Review record

<!-- autoplan-accepted:ceo -->
- Keep the change on the read and print side and inside Touches: `status_graph.py`, `board.py`, `board_map.py` and `docs.py` stay unchanged; the wiki line comes from running `docs.py check`, and UTC times are rewritten at `operate.py`'s print boundary.
<!-- /autoplan-accepted:ceo -->
<!-- autoplan-accepted:eng -->
- `wiki_check` returns `None` rather than an empty list when the check cannot judge, so a missing or broken `docs.py` never hides a saved error.
- The new toy test pins `TZ` and asserts each of the four done lines; no existing toy test other than the per-goal wiki assertions in `test-operate-fit.sh` changes.
<!-- /autoplan-accepted:eng -->
