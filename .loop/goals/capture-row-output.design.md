# capture-row-output: design

## Problem
A failing row's regression issue (#3773, #3784, #3133, defect #3789) has an empty output block. Each of those rows ends in
`| grep -q "PASS: ..."`, which prints nothing, so the row's log is empty and both filers (the workflow's inline block and
`runs.execute` on the Mac tick) copy that empty log into the body.

## Approaches
1. Rewrite every row so it prints before it filters. Cost: 700+ rows, each a risk, and every new row can slip back.
   Risk: high churn, no guard.
2. Fix the filers. A failing row that printed nothing runs once more with each `| grep -q PATTERN` made `| cat`; the
   issue body takes the last 40 lines of that text, or a line saying the row printed nothing. Cost: one small module,
   embedded in the workflow the way tests.py is. Risk: a rerun of a failing row (only failing, only silent ones).

## Chosen
Approach 2: `rowtail.py` (`again`, `shown`), used by `runs.py` and embedded in the workflow by `actions.py`
(`@ROWTAIL@`). The verdict, exit code and state of the first run are never changed by the rerun.

## Done line
"A failing row's issue body holds the row's last 40 output lines, never an empty block": the toy
`dev/toy/test-row-output.py` checks the Mac path and the workflow's block with gh stubbed; two defect rows
(`capture-row-mac`, `capture-row-ci`) are seen red against the old code.

## Open questions
None. The size cap (20,480 bytes) holds: actions.py 20,217, runs.py 15,184, rowtail.py 974.
