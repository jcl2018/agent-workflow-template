# Template updates flow both ways, every repo has a self-describing entry point, and every agent gets the same loop in its own format (owner, 2026-11-10: "Approve 1, 2, 3.")

- Slug: setup-sync
- Touches: skills/workflow-setup, skills/workflow-monitoring/scripts/board_status.py, skills/workflow-docs, skills/loop-files.md, dev/toy, .loop/regression.tsv, docs/wiki/Setup.md, README.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. SET-4: update --check shows what is new in a newer template version and update applies it keeping the repo's config, pages, rules and local settings; the operation board flags any governed repo on an older template version; a template-worthy fix in an adopted repo is proposed back to the template as an issue
2. SET-5: every adopted repo has one generated entry point, built from its PRD pages and settings, explaining how the loop, release, operation and workers, docs, regression, health and settings fit together and listing every feature and how to use it; the docs check fails when it is stale
3. SET-10: setup wires the same skills into each agent's entry files (CLAUDE.md and AGENTS.md), so Claude Code and Codex run the same loop the same way
4. Each requirement above has a regression row seen failing then passing, listed in the Setup Tests table
5. Issue 47 is decided and done: the package works without the private skill suite through its built-in default flow (owner-approved issue mapping 2026-11-10)

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
