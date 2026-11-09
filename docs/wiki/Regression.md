<!-- workflow-docs -->
# Regression

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/7

Review: **Unreviewed**

## Problem

Skill: `workflow-regression`. Keeps tests visible and enforced. Rows live in `.loop/regression.tsv`: a row tests code, not a delivery level, and is a criterion test or a defect test (`category`, with a `link` to the issue or finding for a defect). The `goal` column names the one criterion a row proves, and `-` marks a row that proves none yet.

## Usage

- `/workflow-regression add ID --level land --command "cmd" --goal DEL-1` adds a test row; `--category defect --link URL` makes it a defect test.
- `/workflow-regression red ID --break "cmd"` records that the test fails on broken code.
- `/workflow-regression run land` runs the rows and opens, updates or closes one issue per failing row.
- `/workflow-regression run land --reuse` reuses the branch's last recorded run and reruns only the rows a change can affect; it opens no issue. Delivery's qa step runs it once per goal, and ship and the pull request reuse that run.
- `/workflow-regression sync` lists criteria with no row and rows never seen failing; `/workflow-regression workflow` writes the GitHub Actions workflow.

## Requirements

- REG-1: **Reviewed 2026-11-08** Two kinds of tests. The suite has two categories: criteria tests, which prove each Reviewed criterion, and defect tests, one for every finding, issue or bug that gets fixed, which prove it stays fixed. A criterion with no passing test shows as not enforced, and a fix isn't finished until its defect test exists and passes. <!-- reviewed 43753494 -->
- REG-2: **Reviewed 2026-11-08** Test format. Every test is listed in one fixed format: its category (criterion or defect), what it guards (the criterion's words, or a link to the finding or issue it came from), what it checks in one plain line, when it runs, its last result and date, and whether it has been seen failing once. <!-- reviewed 22465066 -->
- REG-3: **Reviewed 2026-11-08** One command runs it, the same way for me, the loop and GitHub. <!-- reviewed fccc7d92 -->
- REG-4: **Reviewed 2026-11-08** Runs in GitHub Actions: the routine run lives in GitHub Actions, not a session, on every push and nightly, with the schedule as a setting I can change (e.g. hourly). <!-- reviewed 9fce961f -->
- REG-5: **Reviewed 2026-11-08** Failures go to GitHub: one issue per failing test, updated, closed on pass; known failures don't block; no token = preview only. <!-- reviewed 8074710d -->
- REG-6: **Reviewed 2026-11-09** Temporary, until the PRD format replaces the criteria pages: a goal runs the full suite once, in qa; ship and release reuse qa's recorded run when no code changed since it, and otherwise run only the rows for the files changed after it. <!-- reviewed 8a250f7d -->

## Non-goals

- The owner never writes or manages tests; the loop does.
- A known failure does not block a run.
- The routine run needs no session: it lives in GitHub Actions.

## Success metrics

- Every test row has been seen failing once and passes now, or shows as unproven.
- Each failing test has exactly one open GitHub issue, closed when it passes.
- A run in GitHub Actions and a local run of the same rows end the same way.

## Tests

#### REG-1

Two kinds of tests. The suite has two categories: criteria tests, which prove each Reviewed criterion, and defect tests, one for every finding, issue or bug that gets fixed, which prove it stays fixed. A criterion with no passing test shows as not enforced, and a fix isn't finished until its defect test exists and passes.

- Given a criterion with no test, when a release is cut, then it is refused. — [refused-unmet](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a goal that fixes an issue, when it opens its pull request without a defect test seen failing, then it is refused. — [defect-owed](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given issues 35 and 58 and the two worker defects, when the tests are listed, then defect tests exist for each. — [defect-known](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given pages under the Requirements heading or the old Criteria heading, when the release, regression, health and docs readers run, then they all find the same requirement IDs and the release refuses an unmet one. — [prd-readers](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing no

#### REG-2

Test format. Every test is listed in one fixed format: its category (criterion or defect), what it guards (the criterion's words, or a link to the finding or issue it came from), what it checks in one plain line, when it runs, its last result and date, and whether it has been seen failing once.

- Given a test never seen failing, when the run happens, then the run is blocked. — [unproven-blocks](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a test that cannot fail, when it is checked, then it stays unproven. — [tests-seen-failing](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a test linked to no criterion, when the check runs, then the check fails. — [one-link](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a test run, when it ends, then each test's result and date are recorded. — [run-ledger](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a requirement with a test row, when the Tests are rendered, then the row's line carries the test, when it runs, its last result and when it was seen failing. — [tests-table-columns](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing no
- Given a test row with a description, when the Tests are rendered, then it appears under its requirement's heading and words as a Given/When/Then scenario with its result and seen-failing date. — [tests-row-shape](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing no
- Given a test row with no description, when the check runs, then it is flagged. — [describe-needed](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given a row with a seen-failing date, when a description is added, then the date is kept. — [keeps-seen-red](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given this repo's test rows, when they are checked, then every row has a description. — [every-row-described](../../.loop/regression.tsv), both, FAIL 2026-11-09, seen failing 2026-11-08
- Given the test rows, when they are checked, then every row has a category, defect rows link their issue, and the page shows defect tests apart. — [defect-categories](../../.loop/regression.tsv), both, FAIL 2026-11-09, seen failing 2026-11-08

#### REG-3

One command runs it, the same way for me, the loop and GitHub.

- Given the same tests, when the workflow runs and regression.py runs locally, then both end the same way and open the same issues. — [workflow-same-as-run](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08

#### REG-4

Runs in GitHub Actions: the routine run lives in GitHub Actions, not a session, on every push and nightly, with the schedule as a setting I can change (e.g. hourly).

- Given the nightly run, when it ends, then it writes a results table to the job summary. — [ci-summary](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a changed schedule setting, when the workflow is rewritten, then the Actions schedule changes. — [schedule-setting](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given a schedule setting that is not a cron time, when it is applied, then it is refused. — [bad-schedule-refused](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08

#### REG-5

Failures go to GitHub: one issue per failing test, updated, closed on pass; known failures don't block; no token = preview only.

- Given a known failure, when the run happens, then it does not block the run or open an issue. — [known-no-block](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given no GitHub token, when a run happens, then it only prints what it would do. — [no-token-dry-run](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a failing test, when the run reports it, then one GitHub issue is opened. — [one-issue](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07

#### REG-6

Temporary, until the PRD format replaces the criteria pages: a goal runs the full suite once, in qa; ship and release reuse qa's recorded run when no code changed since it, and otherwise run only the rows for the files changed after it.

- Given a first run on unchanged content, when a second run happens, then it reuses the first and runs no test. — [lanes-reuse](../../.loop/regression.tsv), both, not run, seen failing 2026-11-09
- Given a change, when tests run again, then only the tests that read the changed files run. — [lanes-affected](../../.loop/regression.tsv), both, not run, seen failing 2026-11-09
- Given a run with a failing test, when a later run happens, then it is never reused. — [lanes-failing](../../.loop/regression.tsv), both, not run, seen failing 2026-11-09
- Given no recorded run, when tests run, then every test runs. — [lanes-missing](../../.loop/regression.tsv), both, not run, seen failing 2026-11-09
- Given nothing changed since the qa run, when ship runs, then it reuses the qa run. — [lanes-ship-reuses](../../.loop/regression.tsv), both, not run, seen failing 2026-11-09
- Given the qa step, when it runs the tests, then it records the run with the exact command ship checks. — [lanes-qa-record](../../.loop/regression.tsv), both, not run, seen failing 2026-11-09
- Given the base merged before the pull request, when tests run, then only the affected tests rerun. — [lanes-pr-affected](../../.loop/regression.tsv), both, not run, seen failing 2026-11-09
- **not enforced**: no passing test
