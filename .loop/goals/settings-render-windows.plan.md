# Plan: settings-render-windows

Checked against the code: `render.render` in skills/workflow-docs/scripts/render.py calls `refresh(root, args.check)`, which
writes the Settings, Automation and README blocks; `criteria.py` `cmd_render` passes its args through; the lane callers are
`lanekit.prep`, `role.py` (the pull-request results commit) and `private.py` (the Tests.md mender).

## Build steps

1. `criteria.py render --tables` (argument in criteria.py) and `render.render` skips `refresh` when it is set.
2. `lanekit.py`, `role.py` and `private.py` pass `--tables`.
3. Document the flag in criteria.py's header and workflow-docs SKILL.md.
4. `dev/render_tables_check.py`: copies the repo to a scratch git repo, makes the Settings block stale on Home and README,
   checks `render --tables` leaves both unchanged and a plain render repairs them.

## Tests

- `settings-render-tables` (goal 1): seen red with the flag's guard removed, green with it.
- `settings-render-fresh` (goal 1): `docs.py check` prints no STALE line; seen red with Home's automation row deleted.

## What could break

- A caller that relied on a lane's render to refresh the blocks: none (lanes only commit Tests paths).
- `/workflow-docs render` and `docs.py` still refresh the blocks; unchanged.

## Out of scope

Why a worker ran older scripts than its worktree (a stale session started from an older checkout); the backslash in the
printed `WROTE docs/wiki\Home.md` paths.
