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
- `/workflow-regression run land --reuse` reuses the branch's last recorded run and reruns only the rows a change can affect; it opens no issue. Delivery's qa step runs it once per goal, and ship and the pull request reuse that run. Each run records every row's time and the total in the branch's lane record, which health's test-time rule reads.
- A reusing run reruns a row only when a file it reads changed. A test script declares what it runs in `# reads:` lines in its top comment block (`skills/` keeps it wide), and the mapping follows those files without widening to folders. A row whose header can't be worked out, or whose script runs tools on the repo's own files, runs on every change; a deleted file means a full run; `LANES_WIDE=1` brings back the wide mapping. Ask the agent to check the test headers (each problem comes with a fix line), which rows a change to a file reruns, or why a row reads a file; a nightly row traces each run's Python reads against what its header declares.
- `/workflow-regression sync` lists criteria with no row and rows never seen failing; `/workflow-regression workflow` writes the GitHub Actions workflow. It runs each row in its own process group with a 15-minute limit, inside a 90-minute job: a row starts only if its full limit still fits, one that doesn't is skipped and fails with an issue, each result is saved as its row ends, and rows run with no GitHub token and none of the runner's own files (the run summary, env, outputs) in their environment, nor a token in the checkout's git config; rows run as the same user, so this stops accidents such as a toy test writing into the summary, not a hostile row.
- `/workflow-regression list` lists every test in one fixed format, grouped by feature (the page holding the requirement it guards, then Other): its kind, what it guards (requirement ID and words, or issue link and state), what it checks, when it runs, its last result and date, and when it was seen failing. The GitHub run summary (one header with totals and run time, then one table per feature), these Tests lines and the health report use the same format; `/workflow-regression issues` records each defect test's issue or pull request state, keeping a state's date until it changes; if `gh` can't sign in it writes nothing, and a link it can't read keeps its last state (only this command writes them, so commit them with the re-rendered Tests); the GitHub run refreshes them for its summary for at most a minute, and only in the time its job has left.
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

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| [refused-unmet](Tests#t-refused-unmet) | requirement | REG-1 | Given a criterion with no test, when a release is cut, then it is refused. | PASS 2026-11-09 |
| [defect-owed](Tests#t-defect-owed) | requirement | REG-1 | Given a goal that fixes an issue, when it opens its pull request without a defect test seen failing, then it is refused. | PASS 2026-11-09 |
| [defect-known](Tests#t-defect-known) | requirement | REG-1 | Given issues 35 and 58 and the two worker defects, when the tests are listed, then defect tests exist for each. | PASS 2026-11-09 |
| [prd-readers](Tests#t-prd-readers) | requirement | REG-1 | Given pages under the Requirements heading or the old Criteria heading, when the release, regression, health and docs readers run, then they all find the same requirement IDs and the release refuses an unmet one. | PASS 2026-11-09 |
| [unproven-blocks](Tests#t-unproven-blocks) | requirement | REG-2 | Given a test never seen failing, when the run happens, then the run is blocked. | PASS 2026-11-09 |
| [tests-seen-failing](Tests#t-tests-seen-failing) | requirement | REG-2 | Given a test that cannot fail, when it is checked, then it stays unproven. | PASS 2026-11-09 |
| [one-link](Tests#t-one-link) | requirement | REG-2 | Given a test linked to no criterion, when the check runs, then the check fails. | PASS 2026-11-09 |
| [run-ledger](Tests#t-run-ledger) | requirement | REG-2 | Given a test run, when it ends, then each test's result and date are recorded. | PASS 2026-11-09 |
| [tests-table-columns](Tests#t-tests-table-columns) | requirement | REG-2 | Given a requirement with a test row, when the Tests are rendered, then its table row carries the test link, its Given/When/Then words and its last result. | PASS 2026-11-10 |
| [tests-row-shape](Tests#t-tests-row-shape) | requirement | REG-2 | Given a test row, when the full Tests page is rendered, then the row carries its anchor, result, date, run and seen-failing date. | PASS 2026-11-10 |
| [describe-needed](Tests#t-describe-needed) | requirement | REG-2 | Given a test row with no description, when the check runs, then it is flagged. | PASS 2026-11-09 |
| [keeps-seen-red](Tests#t-keeps-seen-red) | requirement | REG-2 | Given a row with a seen-failing date, when a description is added, then the date is kept. | PASS 2026-11-09 |
| [every-row-described](Tests#t-every-row-described) | requirement | REG-2 | Given this repo's test rows, when they are checked, then every row has a plain one-line description. | PASS 2026-11-10 |
| [defect-categories](Tests#t-defect-categories) | requirement | REG-2 | Given the test rows, when they are checked, then every row has a category, defect rows link their issue, and the page shows defect tests apart. | PASS 2026-11-10 |
| [summary-groups](Tests#t-summary-groups) | requirement | REG-2 | Given tests guarding requirements on two wiki pages and one guarding none, when they are listed, then they come grouped by feature in page order, then Other. | PASS 2026-11-10 |
| [summary-fields](Tests#t-summary-fields) | requirement | REG-2 | Given requirement and defect tests, when they are listed, then each shows its kind, what it guards (requirement ID and words, or issue link and state), what it checks, when it runs, its last result and date, and seen failing. | PASS 2026-11-10 |
| [summary-escapes](Tests#t-summary-escapes) | requirement | REG-2 | Given a description with a pipe and a backtick, when tests are listed as tables, then the pipe cannot split a column. | PASS 2026-11-10 |
| [summary-header](Tests#t-summary-header) | requirement | REG-2 | Given a run's results, when the run summary is written, then it has one header with totals and the run time, then one table per feature with each test's name, kind, guards, checks and result. | PASS 2026-11-10 |
| [summary-step](Tests#t-summary-step) | requirement | REG-2 | Given the written workflow, when its summary step runs after the rows, then the grouped summary reaches the run summary. | PASS 2026-11-10 |
| [summary-fallback](Tests#t-summary-fallback) | requirement | REG-2 | Given the grouped summary cannot be written, when the summary step runs, then each row's plain result still reaches the run summary. | PASS 2026-11-10 |
| [summary-refuses](Tests#t-summary-refuses) | requirement | REG-2 | Given a malformed results file or run time, when the run summary is asked for, then it is refused with the line to fix. | PASS 2026-11-10 |
| [issue-states](Tests#t-issue-states) | requirement | REG-2 | Given defect tests linked to an issue and a pull request, when their states are read, then each state is recorded with its date, and nothing is written when gh cannot read them. | PASS 2026-11-10 |
| [health-lists-tests](Tests#t-health-lists-tests) | requirement | REG-2 | Given a repo's tests, when the health check runs, then its report lists the tests grouped by feature in the same format, before its verdict. | PASS 2026-11-10 |
| [reg2-wording](Tests#t-reg2-wording) | requirement | REG-2 | Given the owner's REG-2 wording approved in chat on 2026-11-08, when the Regression page is read, then REG-2 says it word for word and is Reviewed 2026-11-08. | PASS 2026-11-10 |
| [issue-keeps-state](Tests#t-issue-keeps-state) | requirement | REG-2 | Given a defect test's link gh cannot read, when issue states are read, then its last recorded state is kept. | PASS 2026-11-10 |
| [summary-no-results](Tests#t-summary-no-results) | requirement | REG-2 | Given the rows never ran, when the summary step runs under the GitHub shell, then the run summary still says the grouped summary could not be written. | PASS 2026-11-10 |
| [summary-render-guard](Tests#t-summary-render-guard) | requirement | REG-2 | Given tests.py holds text GitHub Actions would evaluate, when the workflow is written, then it is refused. | PASS 2026-11-10 |
| [tests-py-missing](Tests#t-tests-py-missing) | requirement | REG-2 | Given tests.py is not installed, when health and the wiki render run, then each says so and keeps working. | PASS 2026-11-10 |
| [list-tsv-raw](Tests#t-list-tsv-raw) | requirement | REG-2 | Given a description with a pipe, when tests are listed as TSV, then the pipe stays raw and the feature comes first. | PASS 2026-11-10 |
| [list-no-tests](Tests#t-list-no-tests) | requirement | REG-2 | Given a repo with no test rows, when tests are listed, then it says NO TESTS. | PASS 2026-11-10 |
| [summary-unknown-row](Tests#t-summary-unknown-row) | requirement | REG-2 | Given a run result for a test no longer in the rows, when the summary is written, then it shows under Other. | PASS 2026-11-10 |
| [issues-no-rows](Tests#t-issues-no-rows) | requirement | REG-2 | Given no test rows can be read, when issue states are refreshed, then the recorded states are kept. | PASS 2026-11-10 |
| [health-tests-error](Tests#t-health-tests-error) | requirement | REG-2 | Given tests.py fails, when the health check runs, then its TESTS block shows the error and the verdict stays last. | PASS 2026-11-10 |
| [health-group-no-tests](Tests#t-health-group-no-tests) | requirement | REG-2 | Given a health check of one group, when it runs, then no TESTS block is printed. | PASS 2026-11-10 |
| [workflow-same-as-run](Tests#t-workflow-same-as-run) | requirement | REG-3 | Given the same tests, when the workflow runs and regression.py runs locally, then both end the same way and open the same issues. | PASS 2026-11-09 |
| [local-row-env](Tests#t-local-row-env) | requirement | REG-3 | Given a local run with GH_TOKEN and a run summary file set, when a row runs, then it sees neither. | PASS 2026-11-10 |
| [ci-summary](Tests#t-ci-summary) | requirement | REG-4 | Given the nightly run, when it ends, then it writes a results table to the job summary. | PASS 2026-11-09 |
| [schedule-setting](Tests#t-schedule-setting) | requirement | REG-4 | Given a changed schedule setting, when the workflow is rewritten, then the Actions schedule changes. | PASS 2026-11-09 |
| [bad-schedule-refused](Tests#t-bad-schedule-refused) | requirement | REG-4 | Given a schedule setting that is not a cron time, when it is applied, then it is refused. | PASS 2026-11-09 |
| [known-no-block](Tests#t-known-no-block) | requirement | REG-5 | Given a known failure, when the run happens, then it does not block the run or open an issue. | PASS 2026-11-09 |
| [no-token-dry-run](Tests#t-no-token-dry-run) | requirement | REG-5 | Given no GitHub token, when a run happens, then it only prints what it would do. | PASS 2026-11-09 |
| [one-issue](Tests#t-one-issue) | requirement | REG-5 | Given a failing test, when the run reports it, then one GitHub issue is opened. | PASS 2026-11-09 |
| [known-recorded](Tests#t-known-recorded) | requirement | REG-5 | Given a known failure, when the GitHub run runs it, then its result is recorded KNOWN, not FAIL. | PASS 2026-11-10 |
| [lanes-reuse](Tests#t-lanes-reuse) | requirement | REG-6 | Given a first run on unchanged content, when a second run happens, then it reuses the first and runs no test. | PASS 2026-11-09 |
| [lanes-affected](Tests#t-lanes-affected) | requirement | REG-6 | Given a change, when tests run again, then only the tests that read the changed files run. | PASS 2026-11-09 |
| [lanes-failing](Tests#t-lanes-failing) | requirement | REG-6 | Given a run with a failing test, when a later run happens, then it is never reused. | PASS 2026-11-09 |
| [lanes-missing](Tests#t-lanes-missing) | requirement | REG-6 | Given no recorded run, when tests run, then every test runs. | PASS 2026-11-09 |
| [lanes-ship-reuses](Tests#t-lanes-ship-reuses) | requirement | REG-6 | Given nothing changed since the qa run, when ship runs, then it reuses the qa run. | PASS 2026-11-09 |
| [lanes-qa-record](Tests#t-lanes-qa-record) | requirement | REG-6 | Given the qa step, when it runs the tests, then it records the run with the exact command ship checks. | PASS 2026-11-09 |
| [lanes-pr-affected](Tests#t-lanes-pr-affected) | requirement | REG-6 | Given the base merged before the pull request, when tests run, then only the affected tests rerun. | PASS 2026-11-09 |
| [lanes-headers](Tests#t-lanes-headers) | requirement | REG-6 | Given the repo's test scripts, when their # reads: headers are checked, then every script a row names has a valid header. | PASS 2026-11-10 |
| [lanes-declared](Tests#t-lanes-declared) | requirement | REG-6 | Given scripts that declare the files they run, when one skill's file changes, then only the rows whose closure reaches it rerun. | PASS 2026-11-10 |
| [lanes-folder-var](Tests#t-lanes-folder-var) | requirement | REG-6 | Given a file run through a folder variable set in another file, when that file changes, then its row still reruns. | PASS 2026-11-10 |
| [lanes-always](Tests#t-lanes-always) | requirement | REG-6 | Given a row whose declaration cannot be resolved, when an unrelated mapped file changes, then the row still reruns. | PASS 2026-11-10 |
| [lanes-narrow-wide](Tests#t-lanes-narrow-wide) | requirement | REG-6 | Given declared rows, when a change reaches only some of them, then only those rerun, and a change every row reaches reruns them all. | PASS 2026-11-10 |
| [lanes-repo-narrow](Tests#t-lanes-repo-narrow) | requirement | REG-6 | Given this repo's table, when one skill script changes, then fewer than half the land rows rerun and every row whose script declares it does. | PASS 2026-11-10 |
| [lanes-glob](Tests#t-lanes-glob) | requirement | REG-6 | Given a script that globs a skill folder, when its header declares only a file in it, then the check refuses it until the folder is declared. | PASS 2026-11-10 |
| [lanes-deleted](Tests#t-lanes-deleted) | requirement | REG-6 | Given a deleted skill file, when a reusing run happens, then every row runs even when a broad row maps the file. | PASS 2026-11-10 |
| [lanes-check](Tests#t-lanes-check) | requirement | REG-6 | Given a header problem, when lanes_cli.py check runs, then it names the code, the file and line, and the line to fix. | PASS 2026-11-10 |
| [lanes-wide-parity](Tests#t-lanes-wide-parity) | requirement | REG-6 | Given scripts with no header, when affected runs, then the mapping is the same as the wide one, and LANES_WIDE=1 forces it everywhere. | PASS 2026-11-10 |
| [lanes-trace-check](Tests#t-lanes-trace-check) | requirement | REG-6 | Given a row whose run reads a skill file outside its closure, when check-reads runs, then that row fails with the line to add. | PASS 2026-11-10 |
| [lanes-trace](Tests#t-lanes-trace) | requirement | REG-6 | Given every land row, when check-reads traces their runs, then each run's skill reads are inside its closure. | not run |
| [lanes-table](Tests#t-lanes-table) | requirement | REG-6 | Given an edit to one row of the table, when a reusing run happens, then only that row and the rows that read this repo's table rerun. | PASS 2026-11-10 |
| [summary-only-real-rows](Tests#t-summary-only-real-rows) | defect | [#92](https://github.com/jcl2018/agent-workflow-template/issues/92) open (2026-11-09) | Given a row that writes to the run summary, env or outputs like a toy test, when the GitHub run runs it, then nothing it writes reaches the real summary, env or outputs. | PASS 2026-11-10 |
