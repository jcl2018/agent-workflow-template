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

| Criterion | Test | What it checks | Runs | Last result | Seen failing |
|---|---|---|---|---|---|
| **REG-1** Every criterion is enforced: every Reviewed criterion has at least one test; no passing test = not enforced; release refused while one is unmet. | [refused-unmet](../../.loop/regression.tsv) | A release is refused while a criterion has no test. | both | PASS 2026-11-08 | 2026-11-07 |
| **REG-2** Test format: each test listed in one fixed format: name, the criterion it proves with its words, what it checks in one plain line, when it runs (push, nightly, both), last result and date, seen failing once. | [unproven-blocks](../../.loop/regression.tsv) | A test never seen failing blocks the run. | both | PASS 2026-11-08 | 2026-11-07 |
| **REG-2** Test format: each test listed in one fixed format: name, the criterion it proves with its words, what it checks in one plain line, when it runs (push, nightly, both), last result and date, seen failing once. | [tests-seen-failing](../../.loop/regression.tsv) | A test that cannot fail stays unproven. | both | PASS 2026-11-08 | 2026-11-07 |
| **REG-2** Test format: each test listed in one fixed format: name, the criterion it proves with its words, what it checks in one plain line, when it runs (push, nightly, both), last result and date, seen failing once. | [one-link](../../.loop/regression.tsv) | A test linked to no criterion fails the check. | both | PASS 2026-11-08 | 2026-11-07 |
| **REG-2** Test format: each test listed in one fixed format: name, the criterion it proves with its words, what it checks in one plain line, when it runs (push, nightly, both), last result and date, seen failing once. | [run-ledger](../../.loop/regression.tsv) | A run records each test's result and date. | both | PASS 2026-11-08 | 2026-11-07 |
| **REG-2** Test format: each test listed in one fixed format: name, the criterion it proves with its words, what it checks in one plain line, when it runs (push, nightly, both), last result and date, seen failing once. | [tests-table-columns](../../.loop/regression.tsv) | The Tests table has columns for the test, its description, when it runs, last result and seen failing. | both | PASS 2026-11-08 | 2026-11-08 |
| **REG-2** Test format: each test listed in one fixed format: name, the criterion it proves with its words, what it checks in one plain line, when it runs (push, nightly, both), last result and date, seen failing once. | [tests-row-shape](../../.loop/regression.tsv) | A Tests row shows the criterion's words, the description, when it runs, the result and the date seen failing. | both | PASS 2026-11-08 | 2026-11-08 |
| **REG-2** Test format: each test listed in one fixed format: name, the criterion it proves with its words, what it checks in one plain line, when it runs (push, nightly, both), last result and date, seen failing once. | [describe-needed](../../.loop/regression.tsv) | A test row with no description is flagged. | both | PASS 2026-11-08 | 2026-11-08 |
| **REG-2** Test format: each test listed in one fixed format: name, the criterion it proves with its words, what it checks in one plain line, when it runs (push, nightly, both), last result and date, seen failing once. | [keeps-seen-red](../../.loop/regression.tsv) | Adding a description to a row does not lose its seen-failing date. | both | PASS 2026-11-08 | 2026-11-08 |
| **REG-2** Test format: each test listed in one fixed format: name, the criterion it proves with its words, what it checks in one plain line, when it runs (push, nightly, both), last result and date, seen failing once. | [every-row-described](../../.loop/regression.tsv) | Every test row in this repo has a description. | both | PASS 2026-11-08 | 2026-11-08 |
| **REG-3** One command runs it, the same way for me, the loop and GitHub. | **not enforced** | | | | |
| **REG-4** Runs in GitHub Actions: the routine run lives in GitHub Actions, not a session, on every push and nightly, with the schedule as a setting I can change (e.g. hourly). | [ci-summary](../../.loop/regression.tsv) | The nightly run writes a results table to the job summary. | both | PASS 2026-11-08 | 2026-11-07 |
| **REG-4** Runs in GitHub Actions: the routine run lives in GitHub Actions, not a session, on every push and nightly, with the schedule as a setting I can change (e.g. hourly). | [schedule-setting](../../.loop/regression.tsv) | Changing the schedule setting and rewriting the workflow changes the Actions schedule. | both | PASS 2026-11-08 | 2026-11-08 |
| **REG-4** Runs in GitHub Actions: the routine run lives in GitHub Actions, not a session, on every push and nightly, with the schedule as a setting I can change (e.g. hourly). | [bad-schedule-refused](../../.loop/regression.tsv) | A schedule setting that is not a cron time is refused. | both | PASS 2026-11-08 | 2026-11-08 |
| **REG-5** Failures go to GitHub: one issue per failing test, updated, closed on pass; known failures don't block; no token = preview only. | [known-no-block](../../.loop/regression.tsv) | A known failure does not block the run or open an issue. | both | PASS 2026-11-08 | 2026-11-07 |
| **REG-5** Failures go to GitHub: one issue per failing test, updated, closed on pass; known failures don't block; no token = preview only. | [no-token-dry-run](../../.loop/regression.tsv) | With no GitHub token, a run only prints what it would do. | both | PASS 2026-11-08 | 2026-11-07 |
| **REG-5** Failures go to GitHub: one issue per failing test, updated, closed on pass; known failures don't block; no token = preview only. | [one-issue](../../.loop/regression.tsv) | A failing test opens one GitHub issue. | both | PASS 2026-11-08 | 2026-11-07 |
