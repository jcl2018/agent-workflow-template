# Design: regression rows for SET-6/7/9 and GRD-1..10

## Problem
Health files "requirements SET-6/7/9 rows" (#338 #339 #341, already closed) and "requirements GRD-1..10 rows" (#815-#824, open)
for requirements with no regression row seen red. `regression.py sync` today shows SET-6/7/9 already have rows (seen red
2026-11-12); only GRD-1..GRD-10 are gaps. The goal also names two rows as missing: `del8-session-tokens` (DEL-8, a
session-run step is stopped past `token_budget`) and a GRD-3 hook-bypass row (a commit or push that skips hooks).

## Approaches
1. One row per GRD bullet that wraps existing toy tests (grep a PASS line, as the del8-* rows do). Cheap and low risk; rows
   cover only what is built today. Bullets marked "new" (not built) cannot have a passing row.
2. Build every "new" guardrail (hook-bypass refusal, session token stop, branch protection read, CI cancel...) so every bullet
   has a real test. Weeks of work across seven features, high risk, and the GRD page says each is built by its owner's own goal.

## Choice
Approach 1. Add `grd<N>-<part>` rows (category criterion, goal GRD-N, level land, or nightly when the test is slow) that run
the existing proof of each built part (DEL-8 step/test/prep budgets and board OVER line; private-name scan hooks
test-guard-enforce.sh; MON-7 govern hook test-govern.sh; goal-worker role refusals test-guards.sh; HLT-4 preview-by-default;
REG-8 lane minutes; MON-8 silent worker; HLT-2 controls). Each new row is run once for real, then `regression.py red` with a
break command that removes the behaviour on a copy, which records `seen_red`. Where the only way to cover a "new" bullet is to
build it, the row's description says which part it proves and the part left is written in the PR as not enforced (the Tests
table already reads "not enforced" until a row passes). Then add `del8-session-tokens` and the GRD-3 hook-bypass row with a
small test only if the behaviour exists; if it does not, the row stays `draft` with the missing part named, and that is
reported rather than faked. Issues #815-#824 are closed by the pull request ("fixes") once rows exist.

## What each done line needs
Done line 1: a row with `seen_red` for each of SET-6, SET-7, SET-9 (present) and GRD-1..10 (to add, plus the two named rows);
`regression.py sync` shows no GAP for them. The issues #815-#824 are closed by the merge; #338 #339 #341 are closed.

## Open questions
- Whether the lane can run on Windows now (win-posix-calls #1396 is open): running and `red` for new rows wait for it.
- Which "new" GRD bullets have no built behaviour yet: found while planning, each reported, none built here.
