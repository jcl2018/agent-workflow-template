# Plan: routine-runbooks

Goal: `.loop/goals/routine-runbooks.md`. Design: `.loop/goals/routine-runbooks.design.md`.

1. `skills/workflow-docs/references/template.md`: rules block gains `runbook_section`, `runbook_fields` and `runbook` in `format`; layout text and a Runbook entry (DOC-16).
2. `skills/workflow-docs/scripts/deployments.py` (`rules()`), `pageformat.py` (`runbook`, `owed`, CHECKS), `criteria.py` (section order, call sites), `prd.py` and `render.py` (the optional section is not a PRD section).
3. `.loop/routines.tsv`: the registry (health-round, regression-round).
4. `docs/wiki/Health.md`, `Regression.md`: the two runbooks; `Documentation.md` DOC-16 and `Automation.md` AUT-8, Unreviewed.
5. `dev/toy/test-runbook.sh` (good, refused, registry, locked, repo) and five regression rows, each seen failing against a real break.
6. Checks: docs check, docs toy tests, package check (99 files, scripts under 20 KB), lane.

Out of scope: the README and Home Automation section (settings-table), an automation prompt in another repo, a `docs.py runbook` command.
