# Any repo adds its own routines beside health and regression, and every routine's scheduled prompt points to its Runbook in the repo

- Slug: automation-routines
- Touches: skills/workflow-health/scripts, skills/workflow-docs/scripts, skills/workflow-setup/scripts, docs/wiki/Automation.md, DECISIONS.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A routine added to the config registry gets a schedule row, a required Runbook and a generated one-line prompt that points to the repo's Runbook; health warns on a prompt that holds steps

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Run `python3 dev/toy/test-automation-routines.py` from the repo root.
   Expect: every line starts with `PASS:`.
2. Run `python3 skills/workflow-docs/scripts/docs.py prompts`.
   Expect: one `PROMPT <routine>: In <repo>, fast-forward to origin/main, then read docs/wiki/<Page>.md's Runbook section <routine> and follow it exactly.` line for health-round and regression-round.
3. Add an entry such as `{"name": "site-deploy", "cadence": "0 6 * * *", "runs": "claude:site-deploy", "page": "Health"}` to `automation` in `.loop/config.json`, then run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: a finding says Health needs a `### site-deploy` Runbook; add it and the finding goes; `docs.py prompts` now prints a line for site-deploy.

