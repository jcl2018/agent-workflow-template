<!-- workflow-docs -->
# Regression

## Summary

Skill: `workflow-regression`. Keeps tests visible and enforced. Rows live in `.loop/regression.tsv`. A row tests code, not a delivery level: delivery has one flow. Like every script, it refuses rather than waits when no terminal is attached.

Commands, flows and how-tos: `skills/workflow-regression/references/commands.md`.

## Criteria

- REG-4: **Unreviewed** A test counts only after it has been seen failing.
- REG-5: **Unreviewed** A failure already known doesn't block work or open an issue.
- REG-6: **Unreviewed** Without a GitHub token, nothing reaches GitHub.
- REG-7: **Unreviewed** A failing test keeps one issue until it passes.
- REG-8: **Unreviewed** Every test belongs to exactly one criterion.
- REG-9: **Unreviewed** Every run records each test's last status and date, and the regression workflow on GitHub runs them all and shows them.

## Tests

| Criterion | Test | Last run |
|---|---|---|
| REG-4 | [REG-1](../../.loop/regression.tsv) | PASS 2026-11-07 |
| REG-4 | [tests-seen-failing](../../.loop/regression.tsv) | PASS 2026-11-07 |
| REG-5 | [REG-2](../../.loop/regression.tsv) | PASS 2026-11-07 |
| REG-6 | [REG-3](../../.loop/regression.tsv) | PASS 2026-11-07 |
| REG-7 | [one-issue](../../.loop/regression.tsv) | PASS 2026-11-07 |
| REG-8 | [one-link](../../.loop/regression.tsv) | PASS 2026-11-07 |
| REG-9 | [run-ledger](../../.loop/regression.tsv) | PASS 2026-11-07 |
| REG-9 | [ci-summary](../../.loop/regression.tsv) | PASS 2026-11-07 |
