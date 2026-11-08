# Plan: queue-key

Goal: `.loop/goals/queue-key.md` (done lines and Verify by hand belong to delivery; not restated or reopened here).
Design: `.loop/goals/queue-key.design.md`, approach A. Reviewed by /autoplan (unattended; no UI or developer-tool scope; CEO + Eng
read from the repo, no outside voice). Every question took the recommended answer.

## Findings from reading the repo

- **Premise 1 holds.** `graph.parse` (`skills/workflow-monitoring/scripts/graph.py:24`) is the only parser of queue lines. `board.py:176`,
  `monitor.py:112`, `watch.py:160` and `board_status.py:132` all call it. `batch.py`, `watch.py` and `goal.py` only write `depends-on:` and
  validate the `--depends-on` flag, which is unchanged.
- **Root cause.** `parse` matches only `key == "depends-on"`, so `depends:` falls through and the line gets `depends = []`.
- **Overwrite hazard.** The current branch assigns `item["depends"] = [...]`, so a second key on the same line would replace the first.
  The fix must extend, which also gives the union for a line with both keys.
- **Toy fixture.** `dev/toy/test-status-graph.sh:42-45` appends queue lines `c`, `d`, `e`, `f`; the existing "waits on" check reads them
  through `board_status`. A new line with `depends:` fits beside them without disturbing the level assertions if it is a leaf.

## Steps

1. **Parser.** In `graph.parse`, accept `"depends"` and `"depends-on"` as one key and extend `item["depends"]` (skip repeats, keep order).
   Keep `touches` handling as is. Update the module docstring to name both spellings and say `depends-on:` is the one written.
2. **Doc.** In `skills/loop-files.md` (~line 65) show `depends-on: a, b` and its alias `depends: a, b`.
3. **Toy test** (`dev/toy/test-status-graph.sh`).
   - Add queue line `g` with `depends: a` (a is merged, so `g` is ready) and one with `depends: b` (b is running, so it waits); assert the
     board block shows `<- waits on b` for the second.
   - Add direct `graph.parse` assertions: `depends:` alone, `depends-on:` alone, both on one line (union, no duplicates), and neither.
   - Keep the new lines at levels that do not change the existing level-order assertion, or extend that assertion.
4. **Verify.** `bash dev/toy/test-status-graph.sh`, then the repo checks and `regression.py run land` if the repo has them.

## Failure modes

| Step | Failure | Handling |
|---|---|---|
| 1 | Both keys on one line, second overwrites first | Extend, not assign; asserted in step 3 |
| 1 | Same slug in both keys | Skip repeats so `waits on` does not print it twice |
| 3 | New fixture lines shift level numbering | Place as leaves or update the level assertion |

## Not in scope

- Warning on unknown keys (approach C): a different goal; the parser ignores unknown keys by design.
- Rewriting `queue.md` (approach B), or changing what the tools write or the `--depends-on` flag.
- Touching `batch.py`, `watch.py`, `goal.py`: they only write the long spelling.

## What already exists

`graph.parse` and its four callers, the `board_status` toy harness in `test-status-graph.sh`, and the `depends-on` doc line. Nothing new
is built.

## Decision audit

| # | Decision | Class | Principle |
|---|---|---|---|
| 1 | Approach A (alias on read) over rewrite or warn | Mechanical | P3, P5 |
| 2 | Union with de-duplication for a line with both keys | Mechanical | P1, least surprise |
| 3 | `depends-on:` stays the written spelling | Mechanical | P4, no churn in writers |
| 4 | Add direct `graph.parse` assertions as well as the board check | Mechanical | P1 |
