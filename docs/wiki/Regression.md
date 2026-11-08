<!-- workflow-docs -->
# Regression

## Summary

Skill: `workflow-regression`. Keeps tests visible and enforced. Rows live in `.loop/regression.tsv`: a row tests code, not a delivery level. The `goal` column names the one criterion a row proves, and `-` marks a row that proves none yet.

Commands, flows and how-tos: `skills/workflow-regression/references/commands.md`.

## Criteria

- REG-1: **Reviewed 2026-11-08** Every criterion is enforced: every Reviewed criterion has at least one test; no passing test = not enforced; release refused while one is unmet. <!-- reviewed 732c2385 -->
- REG-2: **Reviewed 2026-11-08** Test format: each test listed in one fixed format: name, the criterion it proves with its words, what it checks in one plain line, when it runs (push, nightly, both), last result and date, seen failing once. <!-- reviewed bb7597fb -->
- REG-3: **Reviewed 2026-11-08** One command runs it, the same way for me, the loop and GitHub. <!-- reviewed fccc7d92 -->
- REG-4: **Reviewed 2026-11-08** Runs in GitHub Actions: the routine run lives in GitHub Actions, not a session, on every push and nightly, with the schedule as a setting I can change (e.g. hourly). <!-- reviewed 9fce961f -->
- REG-5: **Reviewed 2026-11-08** Failures go to GitHub: one issue per failing test, updated, closed on pass; known failures don't block; no token = preview only. <!-- reviewed 8074710d -->

## Tests

| Criterion | Test | Last run |
|---|---|---|
| REG-1 | [refused-unmet](../../.loop/regression.tsv) | PASS 2026-11-08 |
| REG-2 | [unproven-blocks](../../.loop/regression.tsv) | PASS 2026-11-08 |
| REG-2 | [tests-seen-failing](../../.loop/regression.tsv) | PASS 2026-11-08 |
| REG-2 | [one-link](../../.loop/regression.tsv) | PASS 2026-11-08 |
| REG-2 | [run-ledger](../../.loop/regression.tsv) | PASS 2026-11-08 |
| REG-3 | **not enforced** | |
| REG-4 | [ci-summary](../../.loop/regression.tsv) | PASS 2026-11-08 |
| REG-5 | [known-no-block](../../.loop/regression.tsv) | PASS 2026-11-08 |
| REG-5 | [no-token-dry-run](../../.loop/regression.tsv) | PASS 2026-11-08 |
| REG-5 | [one-issue](../../.loop/regression.tsv) | PASS 2026-11-08 |
