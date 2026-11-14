# Plan: migration-v1

Checked: `defects.migration_gaps` (line 260) composes `gaps_version/files/settings/blocks` and `enforce.automation_gaps/checks_gaps/docs_gaps/task_gaps/wiki_gaps`; `lines()` prints; `migration()` is health's rule; `setup.HOOKS` and `controls.CONTROLS` exist; `dev/toy/test-migration.sh` is the existing toy.

## Build steps
1. `enforce.py`: `format_gaps(root, cfg, g)` for Usage section, health-rules.json, Backlog milestones, routine pointers, each active only when the installed template carries the feature; `hook_gaps` (each hook once, no duplicate); `owner_steps(root, cfg)` returning `(kind, name, instruction)` for gh sign-in, connectors, smoke cell, milestone approval.
2. `defects.py`: call them from `migration_gaps` (as `gaps`) and print `OWNER STEP <kind> <name>: <instruction>` lines plus `installed N, adapted N, owner steps N` in CHECKED; health's `migration` rule turns owner steps into INFO rows.
3. `dev/toy/test-migration-v1.py`-style toy (Python, in `test-migration.sh` or a new toy script): a clean toy exits 0 and a toy missing each feature exits 1 naming code, fix or owner step.
4. Regression rows `migration-v1-gaps`, `migration-v1-clean` seen red; docs: draft SET-16 / SET-11 wording in DECISIONS.md.
5. Merge origin/main as the format goals land; run the full toy.

## Tests per done line
`migration-v1-gaps` (toy missing each feature: names it, fix or owner step, exit 1) and `migration-v1-clean` (all present: exit 0), each seen failing on HEAD without the change.

## Could break
Script caps: defects.py has about 1 KB of room, enforce.py about 4.9 KB; the new code stays inside them. A check gated on the template carrying a feature must not fire on an older template.

## Out of scope
Making the format changes themselves; editing Reviewed requirements; merging (hold before merge.py).
