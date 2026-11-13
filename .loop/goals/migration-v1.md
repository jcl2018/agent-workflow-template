# migration-check and adoption list every template feature as installed, adapted or an owner step with its exact instruction, including tonight's format changes

- Slug: migration-v1
- Touches: skills/workflow-setup/scripts, skills/workflow-health/scripts, dev/toy, docs/wiki/Setup.md, DECISIONS.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. On a toy repo missing a template feature, migration-check names it with its fix or owner step and exits nonzero; with all present it exits 0

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
1. In a repo whose `package.json` holds `"engines": {"node": ">=99"}`, run `python3 skills/workflow-setup/scripts/setup.py migration-check --offline`.
   Expect: an `OWNER STEP toolchain node: needs node 99 (... here): <install command for this platform>` line, a `CHECKLIST:` line, and the exit code unchanged by the owner step.
2. In a repo with the reply hook listed twice in `.claude/settings.local.json`, run the same command.
   Expect: `GAP MIG_HOOKS reply_hook.py: is installed 2 times. Fix: remove the duplicate entry` and exit 1.
3. Run `bash dev/toy/test-migration-v1.sh`.
   Expect: 13 `PASS` lines and `ALL PASS`.
