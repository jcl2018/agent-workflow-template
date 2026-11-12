# Design: settings-render-windows

## Problem

On this PC a lane left README.md and Home.md with an older Settings block (no `automation` row, the shorter
`regression_runs` text), so `docs.py check` printed `STALE Settings` and `LANE_DIRTY: a row left README.md`. The render is
not platform-dependent: a fresh worktree at main renders the same text as the Mac. The cause is that the lane's prep
(`criteria.py render`) also rewrites the Settings, Automation and README blocks, using the settings reference of whichever
checkout's scripts ran it. When those scripts are older than the page (a worker started from an older worktree), the lane
commits the older blocks over the newer page. It reproduces on any OS: `criteria.py render` from the win-posix-rest or
operator-setup worktree's scripts, run in a worktree at main, rewrites Home.md and README.md.

## Approaches

1. Re-render the Settings block and commit it whenever a lane finds it stale. Hides the symptom, and the next lane run
   from older scripts writes it back. Rejected.
2. A lane renders only what it measures, the Tests tables: `criteria.py render --tables` skips the block refresh, and the
   three lane callers (lane prep, the pull-request step's results commit, the merge mender) pass it. Small, no new state.

## Chosen

Approach 2. `render` without the flag still refreshes the blocks, so `/workflow-docs render` and `docs.py` behave as before.

## What the done line needs

- `docs.py check` prints no STALE Settings line: row `settings-render-fresh` (and the page is fresh at the merged head).
- A lane that renders leaves README.md and Home.md unchanged: row `settings-render-tables` makes both stale, runs
  `render --tables`, and checks neither changed; a plain render still repairs them.

## Open questions

None.
