<!-- workflow-docs -->
# Delivery

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/1

## Summary

Skill: `workflow-delivery`, with `workflow-release` as its last step. Takes one sentence to a pull request by running your own skill suite's flow unattended, with frozen done lines, a 3-try stop and a manual verify section, then the release step refuses while a touched page is stale, runs the `routines` in `.loop/config.json`, merges where the repo allows it, bumps the version once, writes the CHANGELOG entry and a published GitHub release, and publishes the wiki. A failure is recorded as `release_error` and shows under Needs you. A pull request body says none ran when the repo has no checks.

Delivery needs a configured skill suite: a private file outside the repo, `~/.workflow-loop/flow.json`, names your skills and proves their unattended mode, and the repo never names them. The ship step never pushes, so delivery's own `pr` does. In an operation session `go` runs in a background agent, not in that session. Commands, flows and how-tos: `skills/workflow-delivery/references/commands.md` and `skills/workflow-release/references/commands.md`.

**This repo runs with no gates.** Its `.loop/config.json` turns off `require_checks`, with an empty `checks` list, and
turns on `auto_approve` and `auto_merge`. A pull request opens without any check passing. What the skills leave for the
owner is approved automatically and logged as auto-approved, in the goal's log and on the board. The release step then
merges the pull request into `main` by itself. The skills' own built-in refusals still apply, and the private-name leak
scan still guards every commit. The risk is plain: a broken or wrong change can reach `main` with nobody looking, and
the only check left is the regression workflow on GitHub, which reports and never blocks. A repo set up from this
template keeps every gate until its owner turns one off.

## Criteria

- DEL-1: **Reviewed 2026-11-08** I give one sentence and the done lines, and a worker runs my own skill flow unattended from idea to merge; it won't start without the flow set up, and stops and says why after 3 failed tries. <!-- reviewed 3adf4097 -->
- DEL-2: **Reviewed 2026-11-08** The done lines are frozen once the goal starts; changing one means a new goal. <!-- reviewed 7eb4f867 -->
- DEL-3: **Reviewed 2026-11-08** A decision left for me waits under Needs you, or, where the repo allows it, is auto-approved and logged. <!-- reviewed c76ab2fe -->
- DEL-4: **Reviewed 2026-11-08** Every pull request carries the done lines, the plan, how to verify it by hand, and each step's result. <!-- reviewed 85dc7a9a -->
- DEL-5: **Reviewed 2026-11-08** Release is the last step, fully automatic: every goal ends with release, which bumps the version, writes the release note, brings the docs up to date with the docs command (DOC-4) and refuses to merge while a page is stale, runs my own routines, then merges where the repo allows it and publishes the wiki. No draft step and no question, even for a breaking change. Anything that fails shows under Needs you. <!-- reviewed c2490e55 -->

## Tests

| Criterion | Test | Last run |
|---|---|---|
| DEL-1 | [no-done-line-refused](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DEL-1 | [no-flow-refused](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DEL-1 | [stop-after-3-tries](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DEL-1 | [pr-needs-flow](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DEL-1 | [starts-at-idea](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DEL-1 | [steps-through-flow](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DEL-2 | [frozen-done-lines](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DEL-3 | [pending-waits](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DEL-3 | [auto-approved](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DEL-4 | **not enforced** | |
| DEL-5 | [never-merges](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DEL-5 | [wiki-release](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DEL-5 | [auto-release](../../.loop/regression.tsv) | PASS 2026-11-08 |
