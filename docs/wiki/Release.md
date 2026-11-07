<!-- workflow-docs -->
# Release

## Summary

Skill: `workflow-release`. After a goal has a pull request. For now it merges and keeps the wiki current: with `auto_merge` on, `merge`
refuses while a wiki page the goal's changed paths map to is stale, merges the pull request into `main`, then publishes the
wiki to GitHub by itself. It cuts no version. Its skill file tells the agent the order: prepare, rewrite, commit, merge. `ask`, `cut` and `leave` stay for the owner's
own routines before a release later.

**This repo runs with no gates.** Its `.loop/config.json` turns off `require_checks`, with an empty `checks` list, and
turns on `auto_approve` and `auto_merge`. A pull request opens without any check passing. What the skills leave for the
owner is approved automatically and logged as auto-approved, in the goal's log and on the board. The release step then
merges the pull request into `main` by itself. The skills' own built-in refusals still apply, and the private-name leak
scan still guards every commit. The risk is plain: a broken or wrong change can reach `main` with nobody looking, and
the only check left is the regression workflow on GitHub, which reports and never blocks. A repo set up from this
template keeps every gate until its owner turns one off.

Commands, flows and how-tos: `skills/workflow-release/references/commands.md`.

## Criteria

- REL-4: **Unreviewed** Every release says how to verify it by hand.
- REL-5: **Unreviewed** A release is only ever a draft, and it merges only where the repo turns on auto_merge.
- REL-6: **Unreviewed** An unattended goal cuts a release only if the owner turned that on or said so.
- REL-7: **Unreviewed** A release is refused while a criterion is unmet.
- REL-8: **Unreviewed** A breaking change always asks the owner, and docs-only work never releases.
- REL-9: **Unreviewed** The release step updates the wiki pages a goal's changed paths map to before the merge, and publishes the wiki after it; a refused publish names the page and shows under Needs you.

## Tests

| Criterion | Test | Last run |
|---|---|---|
| REL-4 | [REL-1](../../.loop/regression.tsv) | PASS 2026-11-07 |
| REL-5 | [REL-2](../../.loop/regression.tsv) | PASS 2026-11-07 |
| REL-6 | [REL-3](../../.loop/regression.tsv) | PASS 2026-11-07 |
| REL-7 | [refused-unmet](../../.loop/regression.tsv) | PASS 2026-11-07 |
| REL-8 | [breaking-asks](../../.loop/regression.tsv) | PASS 2026-11-07 |
| REL-8 | [docs-only](../../.loop/regression.tsv) | PASS 2026-11-07 |
| REL-9 | [wiki-release](../../.loop/regression.tsv) | PASS 2026-11-07 |
