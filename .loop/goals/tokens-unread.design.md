# Design: tokens-unread

## Problem
A goal that never recorded a token count shows `0` tokens on the board budget line and `spent 0 tokens` in the pull request
body, which reads as "free" instead of "not measured". GRD-2 says to record unknown and show "tokens unread" (#2615).

## Approaches
1. Store `"unknown"` in the run record's `tokens`. Touches every reader (`flow.py` budget compare, `cost.py`, `judge.py`)
   that does arithmetic on it; high risk.
2. Keep the record as is (no count = nothing recorded) and decide at display time: `fit.tokens_text(run)` returns
   "N tokens" or "tokens unread"; the board line and the PR body use it. Zero risk to the budget arithmetic.

## Choice
Approach 2. A count of 0 counts as unread too. fit.py is already over the script cap on main (merge result); this adds a
few lines and the owner should split it separately.

## Done lines
A goal with no count shows "tokens unread" on the board and in the PR body; one with a count shows the number. Proved by
`dev/toy/test-tokens-unread.py`.

## Open questions
- Reply for "report": the PR body and the board line are the two places a total is shown; health's cost rows already say
  "no tokens recorded". Recommended: leave them.
DEPTH: condensed
