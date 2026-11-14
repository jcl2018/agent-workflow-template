# Design: migration-v1

Branch: loop/migration-v1, cut from origin/main v0.28.9. The done line (frozen): on a toy repo missing a template feature, migration-check names it with its fix or owner step and exits nonzero; with all present it exits 0.

## Problem

`migration-check` (SET-16) already judges a repo against the template, but it checks a fixed set of kinds. Format changes landing after it (no Usage section on feature pages, the Backlog milestones, `.loop/health-rules.json`, one-line Runbook routine prompts, the budget settings `max_merge_rounds`, `max_active_goals`, `plan_pause_percent`) would pass as "migrated" on a repo that lacks them. And a new machine's adopter gets gaps but not one list of what they must do themselves (sign in to gh, run a smoke cell, approve the milestones), so a feature is silently dropped.

## Approaches

1. **Keep adding hand-written codes.** Cheap per item, but every new template feature needs someone to remember to add a check: the same silent drop, one level up.
2. **One checklist derived from the template (chosen).** `checklist(root)` returns `(kind, name, state, instruction)` rows, `state` one of `installed`, `adapted`, `OWNER STEP`. The rows come from what the installed template defines, not from a list in the checker:
   - settings: the settings table (already derived, so the three budget settings are caught the day they land);
   - hooks: `setup.HOOKS` (installed in the repo's machine-local settings, once each);
   - guardrails: `controls.CONTROLS`;
   - routines: the `automation` entries and their Runbook pointer;
   - feature pages: each page in `docs.tsv` holds the current sections and no Usage section;
   - format files: `.loop/health-rules.json`, the Backlog milestones, active only when the installed template carries the feature, so the check never fails a repo for something its template cannot yet write;
   - owner steps: gh signed in, connectors (SET-14), the platform smoke cell, approving the Backlog milestones. Never done by the check; each prints the exact instruction.
3. A new `checklist.py` file. Rejected: the package is already at 103 files against a cap of 99 on main, so no file is added.

## Where it lives

The engine is `migration_gaps` in workflow-health `defects.py` (19.4 KB of 20.48 KB), so the new gap helpers go in `enforce.py` (15.6 KB), which already holds `automation_gaps`, `checks_gaps`, `docs_gaps`. `defects.py` gains only the printing of `OWNER STEP` lines and a map from the new codes. Health's Adoption `migration` rule already maps each gap to a row, so it reads the same list; `OWNER STEP` rows are INFO there (they need a person, not a PR).

## Exit rule

Exit 0 only when every item is installed, adapted or has an owner step. A missing item with no owner step is a GAP (exit 1). An item with an owner step prints the instruction and does not by itself fail the PR-closable check (`--pr`).

## Dependencies

The format goals (drop-usage, backlog-milestones, health-repo-rules, automation-routines, budget-enforce) land overnight. This goal merges origin/main as they do and merges after them; until then their checks are gated on the template carrying the feature, and the toy test builds the feature in the toy's own template copy.

## Open questions (none for the owner)

Naming of the smoke-cell row convention and the SET-16/SET-11 wording are drafted in DECISIONS.md for the owner; SET-16 and SET-11 are Reviewed, so wording is proposed, not edited.
