# Design: health-docs-size

## Problem
The goal lists seven open health findings (#1399 #1400 #1401 #1406 #1407 stale pages, #1402 and #1403 size) and
three README findings (#343 #344 #345). Measured on origin/main (v0.27.41): `docs.py check` says DOCS OK (9 pages),
issues #1399 #1400 #1401 #1403 #1406 #1407 and #343-#345 are already closed, and `render.py` still compares nothing
as a number (its cadence is `str(e.get("cadence")) != "off"`). What is left is #1402: render.py is 19,994 bytes,
97% of the 20,480 cap, so health's size rule warns.

## Approaches
1. **Trim render.py in place** (shorten comments and docstrings). Cheap, but it needs about 1,600 bytes cut and
   renders the file harder to read; the next goal that touches it hits the cap again.
2. **Move the Automation-block code (BUILT_IN, config_of, entries, automation_block, about 2.9 KB) from render.py to
   counting.py**, which already holds render's `cadence()` and `live()` ("moved here unchanged") and is the only
   other caller of `entries`. render.py falls to about 17 KB (83%), counting.py rises to about 16 KB (78%). No new
   file (skills/ is at the 99-file cap).

## Chosen
Approach 2. A pure move: the page output is byte for byte the same, so no wiki page changes and the Monitoring page
(Usage and Success metrics locked for the owner) is not touched.

## What each done line needs
- "workflow-health check reports no docs or size finding" is read as: no docs finding, and no size finding on any
  workflow-docs file. Other near-cap scripts in delivery, setup, monitoring and regression are separate findings and
  not this goal's files; pageformat.py (18,864, 92%) is the other workflow-docs file the size rule warns on and is
  trimmed too if the move leaves room to do it without changing behaviour; otherwise it is named, not touched.
- "issues ... are closed": only #1402 is open. Closing it needs the owner's words (`health.py triage --close`), or
  health's own round closes it once the finding is gone; the goal reports that, it does not close issues itself.
- Guard: a row proves render.py and counting.py stay under 18,432 bytes and the Automation block output is unchanged.

## Open questions
None the owner must decide; the issue close after merge is noted above.
