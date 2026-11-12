# pending-none: design

Status: APPROVED (condensed; a small fix with a known cause).

## Problem
A step reply that says `PENDING: none`, `PENDING: nothing` or an empty `PENDING:` line makes `goal.py record` park the goal as waiting on the owner (seen three times on other goals, each costing an operation round trip).

## Cause
`goal.py cmd_record` reads items with `re.findall(r"^\W*PENDING:\s*(.+)$", text, re.M)`:
- `\s*` also matches a newline, so an empty `PENDING:` line captures the NEXT line (the DEPTH or STEP line) as an item;
- "none" and "nothing" are taken literally as an item.
Any item makes `pending` non-empty, so the goal waits (or, with auto_approve, is "auto-approved: none").

## Decision
One helper, `guards.pending_items(text)`, used by `cmd_record`: items are matched on one line only (`[ \t]*`), and an item that is empty or only says none, nothing, n/a or no decisions (case-insensitive, trailing punctuation ignored) is dropped. A real item still waits exactly as before. `role.need_lane` keeps its own PENDING test for the failed-step exception; it uses the same helper so a `PENDING: none` does not defeat a `STEP: failed`. Regression row plus a toy test: a toy goal replying `PENDING: none`, `PENDING: nothing` and `PENDING:` records and goes on; a real PENDING item still waits.

## Out of scope
The flow.py prompt text, the monitoring and release scripts.
