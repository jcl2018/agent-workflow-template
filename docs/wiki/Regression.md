<!-- workflow-docs -->
# Regression

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/7

Review: **Unreviewed**

## Problem

Skill: `workflow-regression`. Keeps tests visible and enforced. Rows live in `.loop/regression.tsv`: a row tests code, not a delivery level, and is a criterion test or a defect test (`category`, with a `link` to the issue or finding for a defect). The `goal` column names the one criterion a row proves, and `-` marks a row that proves none yet.

## Usage

- `/workflow-regression add ID --level land --command "cmd" --goal DEL-1` adds a test row; `--category defect --link URL` makes it a defect test.
- `/workflow-regression red ID --break "cmd"` records that the test fails on broken code. Only a real date counts as seen failing; `-` or any other text counts as never.
- `/workflow-regression run land` runs the rows and opens, updates or closes one issue per failing row. A row whose suite takes 20 seconds or more is `nightly`, so it runs only in the nightly and full runs.
- `/workflow-regression run land --reuse` reuses the branch's last recorded run and reruns only the rows a change can affect; it opens no issue. Delivery's qa step runs it once per goal, and ship and the pull request reuse that run.
- `/workflow-regression sync` lists criteria with no row and rows never seen failing; `/workflow-regression workflow` writes the GitHub Actions workflow. It runs each row in its own process group with a 15-minute limit, inside a 90-minute job: a row starts only if its full limit still fits, one that doesn't is skipped and fails with an issue, each result is saved as its row ends, and rows run with no GitHub token and none of the runner's own files (the run summary, env, outputs) in their environment, nor a token in the checkout's git config.
- `/workflow-regression list` lists every test in one fixed format, grouped by feature (the page holding the requirement it guards, then Other): its kind, what it guards (requirement ID and words, or issue link and state), what it checks, when it runs, its last result and date, and when it was seen failing. The GitHub run summary (one header with totals and run time, then one table per feature), these Tests lines and the health report use the same format; `/workflow-regression issues` records each defect test's issue state.
- To give a slow repo's GitHub run more time, ask for the workflow step's `REGRESSION_ROW_SECONDS` (each row's limit, 900 by default) or `REGRESSION_JOB_SECONDS` (the job's budget, 88 minutes by default) to be raised; a budget past 88 minutes also needs the job's 90-minute limit raised, a value that isn't a positive whole number keeps the default, and writing the workflow again resets both.

## Requirements

- REG-1: **Reviewed 2026-11-08** Two kinds of tests. The suite has two categories: criteria tests, which prove each Reviewed criterion, and defect tests, one for every finding, issue or bug that gets fixed, which prove it stays fixed. A criterion with no passing test shows as not enforced, and a fix isn't finished until its defect test exists and passes. <!-- reviewed 43753494 -->
- REG-2: **Reviewed 2026-11-08** Test format. Every test is listed in one fixed format, grouped by feature, wherever tests are shown (the wiki, the GitHub run summary, the health report): its category (requirement or defect); what it guards (the requirement's ID and words, or a link to the issue or finding it came from, with that issue's state); what it checks in one plain line; when it runs; its last result and date; and whether it has been seen failing once. <!-- reviewed e1571cd8 -->
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

- Given a criterion with no test, when a release is cut, then it is refused. — [refused-unmet](../../.loop/regression.tsv), requirement, guards REG-1, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a goal that fixes an issue, when it opens its pull request without a defect test seen failing, then it is refused. — [defect-owed](../../.loop/regression.tsv), requirement, guards REG-1, both, PASS 2026-11-09, seen failing 2026-11-08
- Given issues 35 and 58 and the two worker defects, when the tests are listed, then defect tests exist for each. — [defect-known](../../.loop/regression.tsv), requirement, guards REG-1, both, PASS 2026-11-09, seen failing 2026-11-08
- Given pages under the Requirements heading or the old Criteria heading, when the release, regression, health and docs readers run, then they all find the same requirement IDs and the release refuses an unmet one. — [prd-readers](../../.loop/regression.tsv), requirement, guards REG-1, both, PASS 2026-11-09, seen failing 2026-11-09

#### REG-2

Test format. Every test is listed in one fixed format, grouped by feature, wherever tests are shown (the wiki, the GitHub run summary, the health report): its category (requirement or defect); what it guards (the requirement's ID and words, or a link to the issue or finding it came from, with that issue's state); what it checks in one plain line; when it runs; its last result and date; and whether it has been seen failing once.

- Given a test never seen failing, when the run happens, then the run is blocked. — [unproven-blocks](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a test that cannot fail, when it is checked, then it stays unproven. — [tests-seen-failing](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a test linked to no criterion, when the check runs, then the check fails. — [one-link](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a test run, when it ends, then each test's result and date are recorded. — [run-ledger](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a requirement with a test row, when the Tests are rendered, then the row's line carries the test, when it runs, its last result and when it was seen failing. — [tests-table-columns](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-09
- Given a test row with a description, when the Tests are rendered, then it appears under its requirement's heading and words as a Given/When/Then scenario with its result and seen-failing date. — [tests-row-shape](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-09
- Given a test row with no description, when the check runs, then it is flagged. — [describe-needed](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-09, seen failing 2026-11-08
- Given a row with a seen-failing date, when a description is added, then the date is kept. — [keeps-seen-red](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-09, seen failing 2026-11-08
- Given this repo's test rows, when they are checked, then every row has a plain one-line description. — [every-row-described](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given the test rows, when they are checked, then every row has a category, defect rows link their issue, and the page shows defect tests apart. — [defect-categories](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-09, seen failing 2026-11-08
- Given tests guarding requirements on two wiki pages and one guarding none, when they are listed, then they come grouped by feature in page order, then Other. — [summary-groups](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given requirement and defect tests, when they are listed, then each shows its kind, what it guards (requirement ID and words, or issue link and state), what it checks, when it runs, its last result and date, and seen failing. — [summary-fields](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a description with a pipe and a backtick, when tests are listed as tables, then the pipe cannot split a column. — [summary-escapes](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a run's results, when the run summary is written, then it has one header with totals and the run time, then one table per feature with each test's name, kind, guards, checks and result. — [summary-header](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given the written workflow, when its summary step runs after the rows, then the grouped summary reaches the run summary. — [summary-step](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given the grouped summary cannot be written, when the summary step runs, then each row's plain result still reaches the run summary. — [summary-fallback](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a malformed results file or run time, when the run summary is asked for, then it is refused with the line to fix. — [summary-refuses](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given defect tests linked to an issue and a pull request, when their states are read, then each state is recorded with its date, and nothing is written when gh cannot read them. — [issue-states](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a repo's tests, when the health check runs, then its report lists the tests grouped by feature in the same format, before its verdict. — [health-lists-tests](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given the owner's REG-2 wording approved in chat on 2026-11-08, when the Regression page is read, then REG-2 says it word for word and is Reviewed 2026-11-08. — [reg2-wording](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a defect test's link gh cannot read, when issue states are read, then its last recorded state is kept. — [issue-keeps-state](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given the rows never ran, when the summary step runs under the GitHub shell, then the run summary still says the grouped summary could not be written. — [summary-no-results](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given tests.py holds text GitHub Actions would evaluate, when the workflow is written, then it is refused. — [summary-render-guard](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given tests.py is not installed, when health and the wiki render run, then each says so and keeps working. — [tests-py-missing](../../.loop/regression.tsv), requirement, guards REG-2, both, PASS 2026-11-10, seen failing 2026-11-10

#### REG-3

One command runs it, the same way for me, the loop and GitHub.

- Given the same tests, when the workflow runs and regression.py runs locally, then both end the same way and open the same issues. — [workflow-same-as-run](../../.loop/regression.tsv), requirement, guards REG-3, both, PASS 2026-11-09, seen failing 2026-11-08

#### REG-4

Runs in GitHub Actions: the routine run lives in GitHub Actions, not a session, on every push and nightly, with the schedule as a setting I can change (e.g. hourly).

- Given the nightly run, when it ends, then it writes a results table to the job summary. — [ci-summary](../../.loop/regression.tsv), requirement, guards REG-4, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a changed schedule setting, when the workflow is rewritten, then the Actions schedule changes. — [schedule-setting](../../.loop/regression.tsv), requirement, guards REG-4, both, PASS 2026-11-09, seen failing 2026-11-08
- Given a schedule setting that is not a cron time, when it is applied, then it is refused. — [bad-schedule-refused](../../.loop/regression.tsv), requirement, guards REG-4, both, PASS 2026-11-09, seen failing 2026-11-08

#### REG-5

Failures go to GitHub: one issue per failing test, updated, closed on pass; known failures don't block; no token = preview only.

- Given a known failure, when the run happens, then it does not block the run or open an issue. — [known-no-block](../../.loop/regression.tsv), requirement, guards REG-5, both, PASS 2026-11-09, seen failing 2026-11-07
- Given no GitHub token, when a run happens, then it only prints what it would do. — [no-token-dry-run](../../.loop/regression.tsv), requirement, guards REG-5, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a failing test, when the run reports it, then one GitHub issue is opened. — [one-issue](../../.loop/regression.tsv), requirement, guards REG-5, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a known failure, when the GitHub run runs it, then its result is recorded KNOWN, not FAIL. — [known-recorded](../../.loop/regression.tsv), requirement, guards REG-5, both, PASS 2026-11-10, seen failing 2026-11-10

#### REG-6

Temporary, until the PRD format replaces the criteria pages: a goal runs the full suite once, in qa; ship and release reuse qa's recorded run when no code changed since it, and otherwise run only the rows for the files changed after it.

- Given a first run on unchanged content, when a second run happens, then it reuses the first and runs no test. — [lanes-reuse](../../.loop/regression.tsv), requirement, guards REG-6, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a change, when tests run again, then only the tests that read the changed files run. — [lanes-affected](../../.loop/regression.tsv), requirement, guards REG-6, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a run with a failing test, when a later run happens, then it is never reused. — [lanes-failing](../../.loop/regression.tsv), requirement, guards REG-6, both, PASS 2026-11-09, seen failing 2026-11-09
- Given no recorded run, when tests run, then every test runs. — [lanes-missing](../../.loop/regression.tsv), requirement, guards REG-6, both, PASS 2026-11-09, seen failing 2026-11-09
- Given nothing changed since the qa run, when ship runs, then it reuses the qa run. — [lanes-ship-reuses](../../.loop/regression.tsv), requirement, guards REG-6, both, PASS 2026-11-09, seen failing 2026-11-09
- Given the qa step, when it runs the tests, then it records the run with the exact command ship checks. — [lanes-qa-record](../../.loop/regression.tsv), requirement, guards REG-6, both, PASS 2026-11-09, seen failing 2026-11-09
- Given the base merged before the pull request, when tests run, then only the affected tests rerun. — [lanes-pr-affected](../../.loop/regression.tsv), requirement, guards REG-6, both, PASS 2026-11-09, seen failing 2026-11-09

### Defect tests

- Given a row that writes to the run summary, env or outputs like a toy test, when the GitHub run runs it, then nothing it writes reaches the real summary, env or outputs. — [summary-only-real-rows](../../.loop/regression.tsv), defect, guards [#92](https://github.com/jcl2018/agent-workflow-template/issues/92) open (2026-11-09), both, PASS 2026-11-10, seen failing 2026-11-10
