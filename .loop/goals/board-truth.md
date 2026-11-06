# Make the board's runs tell the truth about pull requests and keep paths short

- Slug: board-truth
- Level: standard
- Touches: skills/workflow-monitoring/scripts/board.py, dev/toy/test-board.sh

## Done lines

Frozen. A wrong done line needs a new goal.

1. board.py reads each goal's pull request state with gh, shows open, merged or closed in Runs and Finished today, and shows unknown when gh cannot answer
2. Waiting on you shows the repo name and goal, not a long worktree path, and still says exactly where to type
3. dev/toy/test-board.sh proves both with a fake gh, and board.py stays under 20 KB
4. The repo checks pass

## Verify by hand

1. Run `python3 skills/workflow-monitoring/scripts/board.py board --out /tmp/bt` in a repo with a finished run whose `pr` is a real GitHub PR URL, then open `/tmp/bt/board.html`.
   Expect: that run's pull request shows `(open)`, `(merged)` or `(closed)` in Runs and Finished today.
2. Run the same command with `gh` not on PATH (`PATH=/usr/bin:/bin`).
   Expect: every pull request shows `(unknown)`.
3. Make a run wait on you and read Waiting on you.
   Expect: it says `the governing session, which owns <repo>/<goal>`, with no worktree path, and the exact words to type.

## Design

For each run with a `pr`, board.py asks `gh pr view <url> --json state` from the repo and keeps open, merged or closed; any failure, timeout or odd answer becomes `unknown`. The state rides in the run row, Finished today, the HTML cells and the CHANGE diff. Waiting on you swaps the worktree path for `<repo>/<slug>`, which names the session as the sessions are named. Risk: the 20 KB cap (trimmed docstring) and a slow gh (20 s timeout per run).

## Plan

1. Add `pr_state` and the `prstate` field to board.py (done line 1; proved by the fake-gh test in test-board.sh).
2. Change the waiting `where` text to repo/slug (done line 2; proved by the test's `where` and handoff asserts).
3. Test with a fake gh, a no-gh run, and the existing 20 KB loop (done line 3).
4. Run `goal.py check` (done line 4).
