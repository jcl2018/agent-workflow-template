# Plan: health-docs-size

Checked against the code: render.py defines BUILT_IN (line ~292), config_of (246), entries (300) and automation_block
(315); settings_block and refresh/stale_blocks call config_of, automation_block; counting.py:216 calls
`render.entries` (a back-import) and already holds `cadence()`. Nothing outside workflow-docs/scripts calls these.

## Build steps
1. counting.py: add `config_of`, `BUILT_IN`, `entries` and `automation_block` after `cadence()`, unchanged except
   `counting.cadence(...)` becomes `cadence(...)` and `pageformat` is already imported; `live()` calls `entries`.
2. render.py: delete the four definitions; call `counting.config_of` / `counting.automation_block` where used.
3. Measure: render.py and counting.py both under 18,432 LF bytes; if room, trim pageformat.py by moving nothing
   (comments only) or leave it named.
4. Row `docs-block-split`: renders the Automation and Settings blocks for a toy config before and after (golden
   text) and checks both scripts stay under 18,432 bytes; seen red by restoring render.py from the base.
5. Wiki: the Documentation page gets nothing new unless docs.py check calls it stale after the move.

## Tests per done line
Done line "no docs or size finding" → the new row (block output unchanged, sizes under 90%) plus
`docs.py check` = DOCS OK and `health.py check --group size` shows no workflow-docs script. The row is red on the
base (render.py is 19,994 bytes).

## Could break
An import cycle (counting imports render today; after the move counting no longer imports render at all);
`render.entries` kept as an alias only if something outside calls it (nothing does).

## Out of scope
Closing issues (#1402 needs the owner's `triage --close` or health's own round after merge); other scripts near the
cap; the Monitoring page (locked).
