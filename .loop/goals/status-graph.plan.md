# Plan: status-graph

Goal: `.loop/goals/status-graph.md` (done lines and Verify by hand are frozen and belong to delivery; not restated or reopened here).
Design: `.loop/goals/status-graph.design.md`. Reviewed by /autoplan (unattended; no UI or developer-tool scope). Every question took the recommended answer.

## Implementation plan

Order: MON-4 wording and review, then label fix, then `status_graph.py`, then `board_status.py`, then board, then toy test and old assertions, then docs.

1. **MON-4 wording (done line 1).** Unreview MON-4, rewrite it in `docs/wiki/Monitoring.md` word for word as the goal says, run `criteria.py review --user` for MON-4 only dated 2026-11-08, then `criteria.py render`. Existing MON-4 regression rows stay linked; the status-order row's text follows the new template.
2. **Live step label (done line 3).** `role.py` gains `begin(slug, step)`: rewrite the run record's `step` and append a log entry `<ts> start <step>`. `flow.py start` calls it before launching the agent. `goal.py record` stops setting `state["step"]` to the finished step and instead advances the label to the next step still pending in `state["flow"]`, only on a recorded done or skipped. `seconds_by_step` ignores the `start` word (not in `STEPS`) so estimates stay correct; no history migration. `goal.py` (19.2 KB) must not grow.
3. **`status_graph.py` (done line 2)**, new, in `skills/workflow-monitoring/scripts/`: pure functions `nodes`, `levels`, `total`, `render_text`, `render_data`. Dependencies come from `graph.parse`, `graph.unmet`, `graph.merged`; estimates from `board_status.usual` (median of other finished runs; none means "no estimate yet", never 0). Marks: merged, running, waiting, failed, queued, awaiting merge. Unknown dependency shows as a `? slug` node; a cycle is cut with one `cycle:` note. Total is the longest chain of remaining estimates (merged 0, running remaining, queued full), not the sum; with a missing estimate on the longest path it reads `at least <t> (n goals without estimate)`.
4. **Status block.** `board_status.py` titles become Needs you, Roadmap, Total, Goals in that order; Now and Next fold into graph nodes; per-feature counts and milestone bars stay at the end of Roadmap; `--html` fragment shape unchanged; file stays under 20 KB.
5. **Board.** `board_map.py` `Map.result()` adds `mark` per lane and `total`, calling the same `status_graph.total`; `board_page.py` shows the mark on each lane and a Total line under the map.
6. **Toy test (done line 4).** `dev/toy/test-status-graph.sh`, no model: queue with parallel roots a and b, c waits on both, d on c, e standalone; a merged, b running at stage 3; fixed medians. Asserts graph lines and `waits on`, marks, total equals the longest chain and differs from the sum, an unknown dependency shows, no-history node gives the `at least` form, board JSON carries the same marks and total, and the live label before and after `record` via a stand-in agent. Update the old five-title assertions in `test-workers.sh` and `test-operate.sh`; re-point (never delete) `.loop/regression.tsv` rows and add rows for MON-4.
7. **Docs.** `references/operation.md`, `references/commands.md`, `docs/wiki/Monitoring.md`; `docs.py check` and `criteria.py render --check` pass.

## Failure modes

| Step | Failure | Handling |
|---|---|---|
| 2 | `record` advances the label to a skipped step | advance only past steps still pending in `state["flow"]` |
| 3 | Partial estimates understate the total | explicit `at least` wording |
| 3 | Dependency cycle or unknown goal | `cycle:` note and `? slug` node, no loop |
| 4 | Scripts near the 20 KB cap | new logic in new modules; check sizes after each edit |
| 6 | Old tests name the five old titles | updated in the same change |

## Review record
