# The Settings block renders the same on native Windows as on the Mac: the automation row and the full regression_runs text appear, so docs.py check is clean on Windows (#3777)

- Slug: settings-render-windows
- Touches: skills/workflow-docs/scripts, README.md, docs/wiki

## Done lines

Frozen. A wrong done line needs a new goal.

1. On native Windows at the merged head, docs.py check prints no STALE Settings line and a lane that renders leaves README.md and Home.md unchanged

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. In a worktree at main, run `python3 skills/workflow-docs/scripts/docs.py check`. Expect: no line starting STALE.
2. Run `python3 dev/render_tables_check.py`. Expect: `OK: render --tables left README.md and Home.md alone; a plain render repaired them`.
