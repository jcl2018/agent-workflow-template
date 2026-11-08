# Design: status-graph

Status: shaped by office-hours with the recommended answer at every question. Nothing approved, merged or pushed.
The goal's done lines are frozen; this design meets them. Delivery fills in the done lines' met marks and Verify by hand.

## Problem

The status block (`board_status.py`) prints Needs you, Now, Next, Roadmap, Goals. Roadmap is a per-feature count and
milestone bars; nothing shows which goal waits on which, and nothing gives a time for the whole queue. The board
(`board_map.py` / `board_page.py`) already draws lanes and dependency arrows but has no merged/running/queued marks
and no total. Separately, the step label lies: `goal.py record` sets `state["step"] = args.step` after a flow step
has finished, so a finished step shows as the current one until the next `step`/`check`.

## Premises (taken as agreed)

1. The planner's dependencies are the source: `graph.parse`, `graph.unmet` and `graph.merged` in `graph.py`. No second parser.
2. The estimate source is unchanged: median of other finished runs, read from their logs (`board_status.usual`). A node with no history says "no estimate yet", never 0.
3. Total = longest chain of estimates through the dependency graph (critical path), not the sum. Done (merged) goals contribute 0; a running goal contributes its remaining estimate; a queued goal its full estimate.
4. Scripts are near the 20 KB cap (`goal.py` 19.2 KB, `watch.py` 17.3 KB, `board.py` 16.4 KB), so new logic goes into new small modules and `goal.py` must not grow.

## Approach (recommended, taken): one graph module feeding both surfaces

1. **MON-4 wording** (line 1): first edit, before any code. Unreview MON-4, rewrite it in `docs/wiki/Monitoring.md` word for word as the goal says, then `criteria.py review --user` for MON-4 only, dated 2026-11-08 (Reviewed locks wording by hash). Then `criteria.py render` so the generated MON-4 rows follow; the existing MON-4 regression rows stay linked, with the status-order row's text updated to the new template.
2. **`status_graph.py`** (new, in `skills/workflow-monitoring/scripts/`, line 2): pure functions over run records plus queue lines.
   - `nodes(runs, queue)`: every non-retired run and every queued goal; each node has slug, mark (`merged`, `running`, `waiting`, `failed`, `queued`; a done-but-unmerged run reads `awaiting merge`), `depends`, stage n of 8 from `STEPS`, remaining and full estimate.
   - `levels(nodes)`: topological depth, so parallel goals share a level and chained goals sit deeper. A dependency on an unknown goal becomes a visible `? slug` node; a cycle is cut with one `cycle:` note, never an infinite loop.
   - `total(nodes)`: longest path of remaining estimates over the DAG; if any node on the longest path has no estimate the line reads `at least <t> (n goals without estimate)`.
   - `render_text(...)`: one block, a line per node: `[mark] slug  stage 4 of 8  [####------]  ~12m  <- waits on a, b`, grouped by level with `level 1`, `level 2` headers and `-->` edges listed on the dependent. Running nodes keep today's per-step est/actual lines indented underneath, so the existing estimate rows stay true.
   - `render_data(...)`: marks + total as plain fields for the board.
3. **Status block** (`board_status.py`): `TITLES` becomes `Needs you, Roadmap, Total, Goals` in that fixed order. Now and Next are absorbed into the graph's nodes (a running node carries its step, a waiting-to-merge node its pull request). The old per-feature merged counts and milestone bars stay as lines at the end of Roadmap. Needs you is unchanged and still first. `--html` fragment unchanged in shape. `board_status.py` shrinks as `queued`, `nxt` and `step_lines` move behind the module; keep it under 20 KB.
4. **Board**: `board_map.py` `Map.result()` adds `mark` per lane and `total` to the map document; `board_page.py` draws the mark as a class/label on each lane and a Total line under the map. Arrows already come from `waiters`; unchanged. `board_map.py` calls the same `status_graph.total` so the text and the page can never disagree.
5. **Live step label** (line 3): label changes when a step starts.
   - `role.py` (3.2 KB) gains `begin(slug, step)`: rewrites the run record's `step` and appends a log entry `<ts> start <step>`. `flow.py start` calls it before launching the agent. `goal.py check` already sets `checks` before running; `goal.py step` already sets at start; `pr` likewise.
   - `goal.py record` stops setting `state["step"]` to the step just finished (removing the line also frees bytes). The label is left at the started step and `record` advances it to the next entry in `STEPS` only on a recorded done/skipped, so the board, block and graph never show a finished step as current.
   - `seconds_by_step` credits the gap before an entry to that entry's step word. A start entry uses the word `start`, which is not in `STEPS`, so the gap before it is ignored and the gap start-to-record is credited to the step. Estimates stay correct; no history migration (old logs read as before).
6. **Toy test** (line 4): `dev/toy/test-status-graph.sh`, no model. Made-up queue: `a` and `b` parallel roots, `c` depends on both, `d` depends on `c`, `e` standalone; seeded run records (`a` merged, `b` running at stage 3, history medians known so estimates are fixed numbers). Asserts: graph lines present with correct `waits on`; marks merged/running/queued; total equals the longest chain (assert it differs from the sum of estimates); an unknown dependency shows; a no-history node gives the `at least` form; board JSON carries the same marks and total. Live label: run `flow.py` start with a stand-in agent and read the run record before `record` (step = the new step) and after (advanced), and render the block at both points. Update the existing assertions in `test-workers.sh` and `test-operate.sh` that name the five old sections. Add the test to the repo checks and regression rows tied to MON-4.
7. **Docs**: `references/operation.md`, `commands.md` and `docs/wiki/Monitoring.md` describe the new template; `docs.py check` and `criteria.py render --check` must pass. Wiki change is delivered through the existing wiki flow (`docs/wiki`), as the goal's `Touches` says.

## Alternatives considered

- **A. Minimal**: add an ASCII tree to `board_status.py` only. Busts the size cap, leaves the board without marks or total, and does not fix the step label. Rejected.
- **B. Recommended** (above): `status_graph.py` shared by block and board; label fix in `role.py` + `flow.py`.
- **C. Replace the board's lane map with the new graph**: more consistent but rewrites `board_page.py` for no done-line gain. Deferred.

## Risks

- Existing tests assert the old five titles (`test-workers.sh` lines ~84 and ~92, `test-operate.sh` ~86-92); they change with the template, and the regression rows in `.loop/regression.tsv` must be re-pointed rather than deleted.
- `record` advancing the label is a guess at "next"; if the flow skips a step the label may name a step that is skipped. Mitigation: advance only past steps still pending in `state["flow"]`.
- Critical path with partial estimates can understate; hence the explicit `at least` wording.
- `goal.py` is at 19.2 KB; the net edit there must be negative or zero. Check sizes after each edit.

## Order

MON-4 wording and review → `role.begin` + `flow.py` + `goal.py record` (label) → `status_graph.py` → `board_status.py` → `board_map.py` / `board_page.py` → toy test and updated old assertions → docs. Run `docs.py check`, `criteria.py render --check`, the regression suite and the repo checks at the end.
