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
- `/workflow-regression sync` lists criteria with no row and rows never seen failing; `/workflow-regression workflow` writes the GitHub Actions workflow. It runs each row in its own process group with a 15-minute limit, inside a 90-minute job: a row starts only if its full limit still fits, one that doesn't is skipped and fails with an issue, results reach the summary as each row ends, and rows run with no GitHub token in their environment or in the checkout's git config.
- To give a slow repo's GitHub run more time, ask for the workflow step's `REGRESSION_ROW_SECONDS` (each row's limit, 900 by default) or `REGRESSION_JOB_SECONDS` (the job's budget, 88 minutes by default) to be raised; a budget past 88 minutes also needs the job's 90-minute limit raised, a value that isn't a positive whole number keeps the default, and writing the workflow again resets both.

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
- Given pages under the Requirements heading or the old Criteria heading, when the release, regression, health and docs readers run, then they all find the same requirement IDs and the release refuses an unmet one. — [prd-readers](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09

#### REG-2

Test format. Every test is listed in one fixed format: its category (criterion or defect), what it guards (the criterion's words, or a link to the finding or issue it came from), what it checks in one plain line, when it runs, its last result and date, and whether it has been seen failing once.

- Given a test never seen failing, when the run happens, then the run is blocked. — [unproven-blocks](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a test that cannot fail, when it is checked, then it stays unproven. — [tests-seen-failing](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a test linked to no criterion, when the check runs, then the check fails. — [one-link](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a test run, when it ends, then each test's result and date are recorded. — [run-ledger](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a requirement with a test row, when the Tests are rendered, then the row's line carries the test, when it runs, its last result and when it was seen failing. — [tests-table-columns](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09
- Given a test row with a description, when the Tests are rendered, then it appears under its requirement's heading and words as a Given/When/Then scenario with its result and seen-failing date. — [tests-row-shape](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09
- Given a test row with no description, when the check runs, then it is flagged. — [describe-needed](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given a row with a seen-failing date, when a description is added, then the date is kept. — [keeps-seen-red](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given this repo's test rows, when they are checked, then every row has a description. — [every-row-described](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given the test rows, when they are checked, then every row has a category, defect rows link their issue, and the page shows defect tests apart. — [defect-categories](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08

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

- Given a first run on unchanged content, when a second run happens, then it reuses the first and runs no test. — [lanes-reuse](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09
- Given a change, when tests run again, then only the tests that read the changed files run. — [lanes-affected](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09
- Given a run with a failing test, when a later run happens, then it is never reused. — [lanes-failing](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09
- Given no recorded run, when tests run, then every test runs. — [lanes-missing](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09
- Given nothing changed since the qa run, when ship runs, then it reuses the qa run. — [lanes-ship-reuses](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09
- Given the qa step, when it runs the tests, then it records the run with the exact command ship checks. — [lanes-qa-record](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09
- Given the base merged before the pull request, when tests run, then only the affected tests rerun. — [lanes-pr-affected](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09
- Given the repo's test scripts, when their # reads: headers are checked, then every script a row names has a valid header. — [lanes-headers](../../.loop/regression.tsv), both, PASS 2026-11-10, seen failing 2026-11-10
- Given scripts that declare the files they run, when one skill's file changes, then only the rows whose closure reaches it rerun. — [lanes-declared](../../.loop/regression.tsv), both, PASS 2026-11-10, seen failing 2026-11-10
- Given a file run through a folder variable set in another file, when that file changes, then its row still reruns. — [lanes-folder-var](../../.loop/regression.tsv), both, PASS 2026-11-10, seen failing 2026-11-10
- Given a row whose declaration cannot be resolved, when an unrelated mapped file changes, then the row still reruns. — [lanes-always](../../.loop/regression.tsv), both, PASS 2026-11-10, seen failing 2026-11-10
- Given declared rows, when a change reaches only some of them, then only those rerun, and a change every row reaches reruns them all. — [lanes-narrow-wide](../../.loop/regression.tsv), both, PASS 2026-11-10, seen failing 2026-11-10
- Given this repo's table, when one skill script changes, then fewer than half the land rows rerun and every row whose script declares it does. — [lanes-repo-narrow](../../.loop/regression.tsv), both, PASS 2026-11-10, seen failing 2026-11-10
- Given a script that globs a skill folder, when its header declares only a file in it, then the check refuses it until the folder is declared. — [lanes-glob](../../.loop/regression.tsv), both, PASS 2026-11-10, seen failing 2026-11-10
- Given a deleted skill file, when a reusing run happens, then every row runs even when a broad row maps the file. — [lanes-deleted](../../.loop/regression.tsv), both, PASS 2026-11-10, seen failing 2026-11-10
- Given a header problem, when lanes_cli.py check runs, then it names the code, the file and line, and the line to fix. — [lanes-check](../../.loop/regression.tsv), both, PASS 2026-11-10, seen failing 2026-11-10
- Given scripts with no header, when affected runs, then the mapping is the same as the wide one, and LANES_WIDE=1 forces it everywhere. — [lanes-wide-parity](../../.loop/regression.tsv), both, PASS 2026-11-10, seen failing 2026-11-10
- Given a row whose run reads a skill file outside its closure, when check-reads runs, then that row fails with the line to add. — [lanes-trace-check](../../.loop/regression.tsv), both, PASS 2026-11-10, seen failing 2026-11-10
- Given every land row, when check-reads traces their runs, then each run's skill reads are inside its closure. — [lanes-trace](../../.loop/regression.tsv), nightly, not run, seen failing 2026-11-10
