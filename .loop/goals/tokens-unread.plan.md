# Plan: tokens-unread
1. fit.py: add `tokens_text(run)` ("N tokens" or "tokens unread"; a zero count is unread); the PR body's Budget line uses it.
2. board_lines.py `line()`: when unread, the tokens part reads "tokens unread" instead of "0 of N tokens".
3. dev/toy/test-tokens-unread.py: bare, zero, counted and worker-total runs against both displays.
4. Regression row for the done line; wiki Tests table re-rendered by docs audit.
Risk: fit.py is already over the 20 KB cap on main; the change adds about 300 bytes. Owner's call to split.
DEPTH: condensed
