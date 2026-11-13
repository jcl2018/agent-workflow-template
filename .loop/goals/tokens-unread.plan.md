# Plan: tokens-unread
1. fit.py: add `tokens_text(run)` ("N tokens" or "tokens unread"; a zero count is unread); the PR body's Budget line uses it.
2. board_lines.py `line()`: when unread, the tokens part reads "tokens unread" instead of "0 of N tokens".
3. dev/toy/test-tokens-unread.py: bare, zero, counted and worker-total runs against both displays.
4. Regression row for the done line; wiki Tests table re-rendered by docs audit.
Risk: fit.py is already over the 20 KB cap on main; the change adds about 300 bytes. Owner's call to split.
DEPTH: condensed

## Full pass
- Scope check: touches are monitoring/scripts, delivery/scripts, dev/toy; the change stays inside them (plus the regression row and generated wiki tables).
- Readers of `tokens`: `fit.spent_tokens` stays numeric for `flow.py` budget compares, so budgets are unchanged; `cost.py`/`judge.py` read the record directly and already say "no tokens recorded".
- Edge cases: `tokens` missing, not a dict, `{}`, `{"build": 0}`, bool values, worker `{"total": N}`; each tested or covered by the isinstance guard.
- Failure mode: `board_lines.fit` is None (no fit): `line()` returns '' before the new code runs.
- Tests: Python toy `test-tokens-unread.py`; regression row `tokens-unread-shown` seen red by running the toy against main's fit.py.
