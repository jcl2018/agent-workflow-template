<!-- workflow-docs -->
# Delivery

## Summary

The last step, the release step, checks and updates the goal's wiki pages before the merge and publishes the wiki after it.

Skill: `workflow-delivery`. Takes one sentence to a pull request by running your own skill suite's flow unattended:
your idea, plan, review, test and ship skills, with frozen done lines, the repo's checks, a 3-try stop and a manual
verify section around them. There is one flow, and no levels.

Delivery needs a configured skill suite. A private file outside the repo, `~/.workflow-loop/flow.json`, names your skill
for each step, the command that runs them, the environment that puts them in their own unattended mode and a probe that
proves it. With no flow file, every command refuses with one line saying how to set it. The repo never names the
skills.

A step runs only after the probe proves the unattended mode, because a ship skill run by a person's rules could push.
Each step takes its skill's recommended answers. Anything the skill leaves for the owner waits under Waiting on you;
nothing is approved for the owner. The ship step never pushes, so delivery's own `pr` pushes and opens the pull request.

In an operation session, `go` is not run in that session: it is put in a batch (see Monitoring) and runs in a background
agent. On Agensi, the file contract `loop-files.md` is under `shared/` in the pack, and `workflow-monitoring` is a sibling
skill the agent loads by name.

**This repo runs with no gates.** Its `.loop/config.json` turns off `require_checks`, with an empty `checks` list, and
turns on `auto_approve` and `auto_merge`. A pull request opens without any check passing. What the skills leave for the
owner is approved automatically and logged as auto-approved, in the goal's log and on the board. The release step then
merges the pull request into `main` by itself. The skills' own built-in refusals still apply, and the private-name leak
scan still guards every commit. The risk is plain: a broken or wrong change can reach `main` with nobody looking, and
the only check left is the regression workflow on GitHub, which reports and never blocks. A repo set up from this
template keeps every gate until its owner turns one off.

Commands, flows and how-tos: `skills/workflow-delivery/references/commands.md`.

## Criteria

- DEL-5: **Unreviewed** Every goal starts from done lines that can't change once it starts.
- DEL-6: **Unreviewed** Every goal runs the owner's own idea, plan, review, test and ship skills in their unattended mode, and nothing starts without them.
- DEL-7: **Unreviewed** What the skills leave for the owner waits on the owner, unless the repo turns on auto_approve, as this one does: then it is approved and logged as auto-approved.
- DEL-8: **Unreviewed** A goal that keeps failing stops and says why.
- DEL-9: **Unreviewed** No script merges but the release step, and it merges only where the repo turns on auto_merge, as this one does.
- DEL-10: **Unreviewed** Scripts refuse rather than wait when no terminal is attached.

## Tests

| Criterion | Test | Last run |
|---|---|---|
| DEL-5 | [DEL-1](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DEL-5 | [frozen-done-lines](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DEL-6 | [DEL-2](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DEL-6 | [starts-at-idea](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DEL-6 | [steps-through-flow](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DEL-7 | [DEL-3](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DEL-7 | [DEL-4](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DEL-7 | [auto-approved](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DEL-8 | [stop-after-3-tries](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DEL-9 | [never-merges](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DEL-10 | [DEL-10](../../.loop/regression.tsv) | PASS 2026-11-07 |
