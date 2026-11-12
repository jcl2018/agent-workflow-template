# Design: pr-body-file

## Problem
`goal.py pr` and `merge.py` pass the whole PR body as one `--body` argument to `gh`. On native Windows the command
line is capped near 32,767 characters, so a long body crashes with WinError 206. Health and regression do the same for
issue bodies and comments. Release notes already use `--notes-file`.

## Approaches
1. **Per-call-site temp files.** Each site writes a temp file and passes `--body-file`. Cost: the same ten lines
   repeated in a dozen places; several files sit within 15 bytes of the 20,480-byte script cap (goal.py, merge.py).
2. **A `body=` keyword on each module's existing gh wrapper** (`rounds.gh`, `file.run`, `runs.gh`, `actions.write`,
   `autorelease.sh`, `fit`). The wrapper writes the temp file, appends `--body-file PATH`, runs gh and removes the file.
   Call sites change one argument each. No new file (skills/ is at the 99-file cap).

## Chosen
Approach 2. It is the smallest diff per site, one tested place per module, and shrinks goal.py/merge.py instead of
growing them. The temp file is UTF-8, removed in `finally`, on every platform (no Windows-only branch).

## Done line
- `goal.py pr` with a body over 32,000 chars: the body goes through `--body-file`, so the command line stays short.
- No gh call in skills/ passes a body or notes text as an argument: every `--body` text argument in skills/ becomes
  `body=` on a wrapper (issue create/edit/comment, pr create), release notes stay `--notes-file`.
- Toy fakes (fakegh, release-gh.py, stubs in test-automation*.sh, test-regression.sh, test-milestones.sh) read
  `--body-file`. Bash toy tests skip on Windows, so a Python test of the wrappers and a long-body check run here.

## Open questions
None the owner must decide.
