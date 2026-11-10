# Template updates flow both ways, every repo has a self-describing entry point, and every agent gets the same loop in its own format (owner, 2026-11-10: "Approve 1, 2, 3.")

- Slug: setup-sync
- Touches: skills/workflow-setup, skills/workflow-monitoring/scripts/board_status.py, skills/workflow-docs, skills/loop-files.md, dev/toy, .loop/regression.tsv, docs/wiki/Setup.md, README.md, skills/workflow-delivery, skills/workflow-monitoring/scripts/watch.py, skills/workflow-monitoring/scripts/live_board.py, dev/package.py, listing.json, docs/wiki/Delivery.md, docs/wiki/Monitoring.md, CLAUDE.md, AGENTS.md, .loop/START.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. SET-4: update --check shows what is new in a newer template version and update applies it keeping the repo's config, pages, rules and local settings; the operation board flags any governed repo on an older template version; a template-worthy fix in an adopted repo is proposed back to the template as an issue
2. SET-5: every adopted repo has one generated entry point, built from its PRD pages and settings, explaining how the loop, release, operation and workers, docs, regression, health and settings fit together and listing every feature and how to use it; the docs check fails when it is stale
3. SET-10: setup wires the same skills into each agent's entry files (CLAUDE.md and AGENTS.md), so Claude Code and Codex run the same loop the same way
4. Each requirement above has a regression row seen failing then passing, listed in the Setup Tests table
5. Issue 47 is decided and done: the package works without the private skill suite through its built-in default flow (owner-approved issue mapping 2026-11-10)

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. In this repo, open `.loop/START.md`.
   Expect: a "First five minutes" list, one part each for Loop, Release, Operation and workers, Docs, Regression, Health and Settings, a Features table naming all seven feature pages (Home is not one) with how to use each, and a Settings table with every repo setting and its value.
2. Open `CLAUDE.md` and `AGENTS.md` side by side.
   Expect: the same `<!-- workflow-loop -->` block in both, telling a session to read `.loop/START.md` first and listing the seven workflow skills.
3. Change one Usage bullet's first sentence in `docs/wiki/Setup.md`, then run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: `STALE .loop/START.md: ... (ENTRY_STALE)` and exit 1; `python3 skills/workflow-docs/scripts/docs.py audit` rewrites it, and the check is back to `DOCS OK`. Undo the edit.
4. Run `bash dev/toy/test-sync.sh update` and `bash dev/toy/test-sync.sh board`.
   Expect: `ALL PASS (update)` (check shows what is new, apply lands `workflow-update-v1.1.0` and keeps the repo's data) and `ALL PASS (board)` (the live board lists `oldharbor runs template v1.0.0, older than v1.1.0`).
5. Run `bash dev/toy/test-sync.sh builtin`.
   Expect: `ALL PASS (builtin)`: a goal with a flow file whose steps are all `built-in` and no probe runs every step through delivery's own routine.

## Closes

Closes #47
