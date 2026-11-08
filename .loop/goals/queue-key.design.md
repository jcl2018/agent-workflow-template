# Design: accept both depends: and depends-on: in queue lines

Status: APPROVED (recommended answers taken; owner approves nothing yet, the PR is the gate)

## Problem

A queue line such as `- slug: c | depends: a | goal: C | done: c` is silently read as having no dependencies, so goal
`c` starts before `a` is merged. Only the spelling `depends-on:` is recognised. People and agents write `depends:` too
(the parsed field is already called `depends`).

## Premises

1. The bug is in one place. `graph.parse` (skills/workflow-monitoring/scripts/graph.py:24) is the only parser of queue
   lines; board.py, monitor.py, watch.py and board_status.py all call it. No other reader needs to change.
2. `depends-on:` stays the spelling the tools write (watch.py, batch.py, goal.py all emit it), and the flag stays
   `--depends-on`. `depends:` is accepted on read only.
3. No new behaviour for a line that has both keys: the union is the least surprising result.

## Approaches

- A (recommended, minimal): in `parse`, treat `"depends"` and `"depends-on"` as the same key, extending (not
  overwriting) `item["depends"]`, so a line with both gets the union. Three lines of code.
- B: normalise `depends:` to `depends-on:` by rewriting queue.md. Rejected: mutates a user file for a read-side problem.
- C: warn on unknown keys. Useful but a different goal; the parser silently ignores unknown keys today by design.

Recommendation: A.

## Changes

1. `skills/workflow-monitoring/scripts/graph.py`: accept both keys in `parse`; update the module docstring to name both.
2. `skills/loop-files.md` (line ~65): show the key as `depends-on: a, b` (alias `depends: a, b`), so the doc shows
   both spellings. Done line 1 requires the doc to show the key.
3. `dev/toy/test-status-graph.sh`: add a queue line using `depends:` beside the existing `depends-on:` lines, and assert it
   produces the same "waits on" result. A direct `graph.parse` assertion on both spellings, and on a line with both,
   is the proof for done line 2.

## Risks

Low. Parsing is additive; no existing line changes meaning. `batch.py`/`watch.py` validation of unknown dependencies
only runs on the flag path, which is unchanged.

## Files touched vs the goal's Touches

graph.py, loop-files.md, dev/toy (test-status-graph.sh) match the declared list.

## The Assignment

Implement approach A and the toy test; run `bash dev/toy/test-status-graph.sh`.
