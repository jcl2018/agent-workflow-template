<!-- workflow-docs -->
# Release

## Summary

Skill: `workflow-release`. After a goal has a pull request. With `auto_merge` on, `merge`
refuses while a wiki page the goal's changed paths map to is stale, runs the owner's `routines` from `.loop/config.json`
(refusing if one fails), merges the pull request into `main`, bumps the version once, writes the CHANGELOG entry, creates a
published GitHub release and publishes the wiki. It asks nothing, even for a breaking change. Any failure is recorded
on the goal as `release_error` and shows under Needs you. `ask`, `cut` and `leave` stay as the manual path.

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
- REL-5: **Unreviewed** Every merged goal bumps the version once and gets a CHANGELOG entry and a published GitHub release, with no draft and no question; it merges only where the repo turns on auto_merge.
- REL-6: **Unreviewed** An unattended goal cuts a release only if the owner turned that on or said so.
- REL-7: **Unreviewed** A release is refused while a criterion is unmet.
- REL-8: **Unreviewed** A breaking change releases with no question (major, or minor while the version is 0.x), and a failed routine, merge or release is recorded and shown under Needs you.
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
