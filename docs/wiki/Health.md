<!-- workflow-docs -->
# Health

## Summary

Skill: `workflow-health`. A check of the repo's health with fixed rules, so the same repo always gets the same answer. `check` is
read-only; `run` files what it finds as issues. It runs `workflow-docs` and `workflow-regression` and reports on what they say, and adds the checks they
don't make: script size, old findings, stuck runs and merged branches.

Scripts here refuse rather than wait when no terminal is attached.

On Agensi, a script can't reach its siblings, so the criteria and docs rules print `UNREAD`, and the verdict says so.

Commands, flows and how-tos: `skills/workflow-health/references/commands.md`.

## Criteria

- HLT-1: **Unreviewed** Running the check twice on a repo that hasn't changed prints exactly the same lines.
- HLT-2: **Unreviewed** A script over 20 KB is a failure, and one at 90 percent of that or more is a warning, each with a line saying how to fix it.
- HLT-3: **Unreviewed** A stale or missing wiki page, or a criterion with no regression test, shows up as a line naming it.
- HLT-5: **Unreviewed** When a rule can't read what it needs, it says so and the verdict is never green.
- HLT-6: **Unreviewed** The check changes nothing: no file, commit, branch or stash.
- HLT-7: **Unreviewed** Each health finding is filed as one issue: a repeat updates it, a fix closes it, a return reopens it, and a check that did not run or could not read its data closes nothing.

## Tests

| Criterion | Test | Last run |
|---|---|---|
| HLT-1 | [HLT-1](../../.loop/regression.tsv) | not run |
| HLT-1 | **not enforced** | |
| HLT-2 | [HLT-2](../../.loop/regression.tsv) | not run |
| HLT-2 | **not enforced** | |
| HLT-3 | [HLT-3](../../.loop/regression.tsv) | not run |
| HLT-3 | [HLT-3b](../../.loop/regression.tsv) | not run |
| HLT-3 | **not enforced** | |
| HLT-5 | [HLT-5](../../.loop/regression.tsv) | not run |
| HLT-5 | **not enforced** | |
| HLT-6 | [HLT-6](../../.loop/regression.tsv) | not run |
| HLT-6 | **not enforced** | |
| HLT-7 | [HLT-7b](../../.loop/regression.tsv) | not run |
| HLT-7 | [HLT-7](../../.loop/regression.tsv) | not run |
| HLT-7 | [HLT-7c](../../.loop/regression.tsv) | not run |
| HLT-7 | **not enforced** | |
