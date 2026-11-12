# package-cap-3: main packages again

## Problem
dev/package.py fails on main: 103 files against the 99-file cap and `automation` missing from `listing.json` commands.
`lanes_cli.py check` fails (`LANES-DECL-FOLDER-UNBACKED` on test-settings-table.sh). Eleven regression rows are marked
KNOWN because of these (plus a stale Tests table and two size rows). Added by the operation session after the freeze:
adopt-set-3, adopt-set-4 and adopt-set-5 fail with "v1 package refused" for the same reasons, so they must pass and
lose their KNOWN entries too.

## Approach
1. Files: portlock.py exists once per skill (four identical 42-line copies, because a skill imports only its own
   scripts). Fold each copy into an existing module of the same skill with no new file: slots.py (regression),
   lanekit.py (delivery; guards.py and lane.py take `lanekit.fcntl`), session_bind.py (monitoring; sessions.py imports it
   from there, keeping sessions.py under its 19800-byte row budget) and update.py (setup). The shim is the same msvcrt
   byte-range lock, behaviour unchanged. Result: 99 files.
2. Scripts stay under 20 KB: lanekit.py, update.py and slots.py absorb the shim, so wording in their docstrings is
   tightened; no code changes there.
3. Listing: add `automation` (a docs.py subcommand) to `listing.json` commands.
4. Lanes check: test-settings-table.sh declares the files it runs instead of `skills/`; fixing the false dependency
   that dev/toy/reap.sh created (a comment naming test-guard-enforce.sh) makes every row narrow again, which exposes five
   tests that read whole folders without declaring them: declare them.
5. Rows: defect-categories (the toy copy of the repo lacks `.github`, so its Automation block looked stale: copy it),
   skill-size (workflow-docs SKILL.md 158 lines: the automation registry and audit detail move to references/commands.md),
   plan-sizes and pods-size (lanes.py and sessions.py ceilings) pass again; their KNOWN entries are removed.
6. Test: no test covered the Windows fallback, so add dev/toy/test-portlock.sh (fake msvcrt, fcntl hidden) with a row,
   and a row for dev/package.py passing; both seen failing under a planted break.

## Not done here
size-140 (skills/workflow-docs/scripts/docs.py at 91% of the cap) belongs behind render-readme-guard, which owns docs.py,
render.py and seed.py; its KNOWN entry stays, handed to the operation session.

## Risks
Wider docstring edits in lanekit.py: the COPIED functions are untouched (test-lane-control compares them).
