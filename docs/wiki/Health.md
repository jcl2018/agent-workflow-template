<!-- workflow-docs -->
# Health

## Summary

Skill: `workflow-health`. A check of the repo's health with fixed rules, so the same repo always gets the same answer. `check` is read-only; `run` files what it finds as issues on the Backlog milestone. It runs `workflow-docs` and `workflow-regression` and reports on what they say, and adds script size, old findings, stuck runs and merged branches. A Mine group runs the owner's own rules from a private setting outside the repo. `check` prints one fixed report ending in one `HEALTH:` line. `suggest` is a separate, advisory step that lists overlapping criteria and ranked next steps. On Agensi a script can't reach its siblings, so the criteria and docs rules print `UNREAD`, and the verdict says so.

Commands, flows and how-tos: `skills/workflow-health/references/commands.md`.

## Criteria

- HLT-1: **Reviewed 2026-11-08** One command, run by group; fixed rules; same answer twice; changes nothing. <!-- reviewed ea097218 -->
- HLT-2: **Reviewed 2026-11-08** The rules: Size (scripts under 20 KB, warn from 90%); Criteria (each criterion has a test seen failing once and passing now; done lines with no test warn); Docs (required docs match template and code; stale warns, other gaps fail); Hygiene (<=5 open findings, nothing waiting on me >24h, no leftover merged branches); Mine (my own rules, e.g. an outside code-quality command, named in a private setting). Adding a rule means retiring one or raising the cap on purpose; a rule may run an existing command to get its data. <!-- reviewed b8ae0aee -->
- HLT-3: **Reviewed 2026-11-08** One printout template like the status block: groups, findings pass/warn/fail/unread, fix line each, one verdict; unread never green. <!-- reviewed d67b7618 -->
- HLT-4: **Reviewed 2026-11-08** Findings go to the Backlog: one issue each on the Backlog milestone; repeat updates, fix closes, return reopens; no token = preview. <!-- reviewed e8e3261e -->
- HLT-5: **Reviewed 2026-11-08** Next-step tracker: separate suggestions section: conflicting/overlapping criteria, features missing a criterion, ranked next steps from warnings and failures. <!-- reviewed cca14989 -->

## Tests

| Criterion | Test | Last run |
|---|---|---|
| HLT-1 | [same-lines](../../.loop/regression.tsv) | PASS 2026-11-07 |
| HLT-1 | [check-writes-nothing](../../.loop/regression.tsv) | PASS 2026-11-07 |
| HLT-2 | [size-fail](../../.loop/regression.tsv) | PASS 2026-11-07 |
| HLT-2 | [stale-page-row](../../.loop/regression.tsv) | PASS 2026-11-07 |
| HLT-2 | [no-row-fail](../../.loop/regression.tsv) | PASS 2026-11-07 |
| HLT-3 | [unread-not-green](../../.loop/regression.tsv) | PASS 2026-11-07 |
| HLT-4 | [no-token-would](../../.loop/regression.tsv) | PASS 2026-11-07 |
| HLT-4 | [update-in-place](../../.loop/regression.tsv) | PASS 2026-11-07 |
| HLT-4 | [fixed-closes](../../.loop/regression.tsv) | PASS 2026-11-07 |
| HLT-4 | [repeat-no-second](../../.loop/regression.tsv) | PASS 2026-11-07 |
| HLT-4 | [unread-closes-none](../../.loop/regression.tsv) | PASS 2026-11-07 |
| HLT-5 | **not enforced** | |
