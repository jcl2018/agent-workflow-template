# Design: skill-governs-line

## Problem
Rows skill-says-governs (MON-1, #3773) and skill-kept (SET-3, #3785) fail on the Mac's scheduled run. Both grep the
delivery SKILL.md for the literal "governance only". Commit 5bd0ad83 (the v0.27.34 health review findings) reworded the
line to "**One session governs, and the others build.** ... the operation session assigns and watches, and never runs
`go`", so the phrase is gone while the meaning is kept. The rows are bash, so they are skipped on native Windows and no
Windows lane saw it. The same toy (test-batch.sh) also has two checks pinned to the old Tests list format
(" — [id]("), which the DOC-9 table format replaced; they fail the toy but not the rows.

## Approaches
1. Put "governance only" back into SKILL.md. Rejected: the reword was a reviewed fix, and the SKILL.md is capped at 150
   lines (skill-size row) and its wording is the page's.
2. Make the checks read the line as it is now: accept "One session governs" (the new line) beside "governance only" (the
   other two files still use it) and keep the second half ("runs neither" or "never runs") as is. Chosen. The check
   still fails when the line is removed, and still needs the "never runs" half, so it is not weaker.

## What each done line needs
"pass on main": test-batch.sh's delivery-SKILL check and test-defect.sh skill-kept accept the current line, and the two
Tests-list checks match the table rows. "seen red when the governance line is removed": both rows fail with the line
deleted from SKILL.md. Both are bash rows, so the proof on this machine is under a Linux shim; the real proof is owed
off-platform (the Mac).

## Open questions
None.
