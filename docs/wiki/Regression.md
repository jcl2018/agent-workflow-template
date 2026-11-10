<!-- workflow-docs -->
# Regression

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/7

Review: **Reviewed 2026-11-10** <!-- prd P=14b68802 R=73faed5f N=f86bd012 M=bdcf897b U=53ff20fc -->

## Problem
- I can't trust a requirement or a fix unless a test proves it, and every fix I've ever shipped should stay fixed without me re-checking it.
- Running every test on every change is too slow, but skipping tests lets breakage slip through; I need fast checks in the loop and the full suite somewhere I can see it, like GitHub Actions.
- I need failures to reach me as GitHub issues, every test shown in one format, and control over what runs when.

## Usage

- `/workflow-regression add ID --level land --command "cmd" --goal DEL-1` — Adds or replaces a regression row. Prints `ROW <id> <level>: <command>`. Refuses (exit 1) `REFUSED: bad id. Fix: letters, digits, dots, dashes.`, `REFUSED: a defect row links to its issue or finding. Fix: add --link URL or finding:SLUG.` and `REFUSED: a row can't hold a tab or new line. Fix: use a script.`
- `/workflow-regression red ID --break "cmd"` — Copies HEAD, runs the break command on the copy, and records that the row's test fails there. Prints `SEEN RED <id> on <YYYY-MM-DD>`, or `STILL GREEN <id>: the test passed on broken code, so it proves nothing.` with exit 1. Refuses (exit 1) `REFUSED: no row <id>. Fix: add it first.` and `REFUSED: the break command failed: ...`
- `/workflow-regression run land` — Runs the land rows, records each result, and opens, updates or closes one issue per failing row. Prints `PASS <id>`, `FAIL <id>` or `KNOWN <id> (<reason>)` per row, `OPENED issue for <id>` or `WOULD open or update the issue for <id>`, and `RESULT <n> passed, <n> known, <n> failed, <n> unproven`. Refuses (exit 1) `REFUSED: no row or level called <target>.`, and `NO ROWS: run add first` when there are none.
- `/workflow-regression sync` — Lists done lines and criteria with no row, plus draft, never-seen-failing and undescribed rows. Prints `GAP <slug>:<n> <line>`, `DRAFT <id>: ...`, `UNPROVEN <id>: never seen failing. Run red.`, `NODESC <id>: ...`, or `SYNC OK: <n> rows`. Refuses nothing.
- `/workflow-regression workflow` — Writes the GitHub Actions regression workflow on the schedule in regression_cron. Prints `WROTE <repo>/.github/workflows/regression.yml`. Refuses (exit 1) `REFUSED: regression_cron is not five cron fields. ...`, `REFUSED: <path> exists, and this tool didn't write it. Fix: merge by hand.` and `REFUSED: tests.py contains <token>, which the workflow can't carry. ...`
- `/workflow-regression list` — Lists every regression test from the recorded runs, grouped by feature. Prints `FEATURE <title>`, then `<test> | <kind> | <guards> | <checks> | <runs> | <last result> | seen failing <date|no>` per test, or `NO TESTS`. Refuses nothing.
- `/workflow-regression issues` — Reads each defect test's issue or pull request state from GitHub and records it. Prints `ISSUE <link> <state>`. Refuses (exit 1) `ISSUES: cannot read issues (gh: <cause>). Fix: gh auth login, or set GH_TOKEN`

## Requirements

### Functional
- REG-1: **Reviewed 2026-11-10** Three kinds of tests <!-- reviewed a26a0b86 -->
  - Requirement tests: one or more for every Reviewed requirement, functional and non-functional alike.
  - Workflow tests: end-to-end runs of a whole flow on a toy repo (for example a goal from freeze to release), proving the steps work together.
  - Defect tests: one for every issue, finding or bug that gets fixed, proving it stays fixed.
  - A requirement with no passing test shows as not enforced; a fix isn't finished until its defect test exists and passes.
- REG-2: **Reviewed 2026-11-10** Test format <!-- reviewed cb11400e -->
  - Every test is listed in one fixed format, grouped by feature, wherever tests are shown (the wiki, the GitHub run summary, the health report): its kind, what it guards (the requirement, the workflow, or the issue with its state), what it checks in one plain line, when it runs, its last result and date, and whether it has been seen failing once.
- REG-3: **Reviewed 2026-11-10** One command, three places <!-- reviewed 6fb19e03 -->
  - One command runs the suite the same way for me, the loop and GitHub Actions.
- REG-4: **Reviewed 2026-11-10** When tests run <!-- reviewed b1a6fd25 -->
  - In the loop, each goal runs only the rows affected by its changes plus its own new rows, at qa; ship and release reuse that run when no code changed since.
  - Before a pull request merges, the affected rows run again on the merged result.
  - The full suite (every requirement, workflow and defect test) runs in GitHub Actions on the Automation schedule (every few hours by default) and on every release, never on every goal.
  - I can run the full suite or any part of it at any time.
- REG-5: **Reviewed 2026-11-10** Failures go to GitHub <!-- reviewed b2d968db -->
  - One labeled issue per failing test, updated while it fails and closed when it passes; known failures don't block; with no token it only previews.
- REG-6: **Reviewed 2026-11-10** Every fixed issue leaves a test <!-- reviewed 9f5b8594 -->
  - A goal that fixes an issue adds that issue's defect test, seen failing on the old code and passing on the fix, before the issue closes.
  - Each release note lists the issues it fixed, each with its defect test, so every version carries the regressions for what it fixed.
  - A reopened issue's test is marked failing until it passes again.

### Non-functional
- REG-7: **Reviewed 2026-11-10** Fast in the loop <!-- reviewed 0643c29e -->
  - A goal's affected-rows run finishes in under 10 minutes; the full suite finishes in under 30 minutes; health flags either when it doesn't.
- REG-8: **Reviewed 2026-11-10** Controllable <!-- reviewed e39ec809 -->
  - Which levels run where, the GitHub schedule, the time limits and how many test lanes run at once are settings.
  - Lanes running side by side never share files or ports or time each other out, and a lane over its limit says so.
- REG-9: **Reviewed 2026-11-10** Honest results <!-- reviewed 194b357d -->
  - Every test has been seen failing once, or shows as unproven.
  - A test that fails then passes on the same commit is marked flaky, never silently retried.

## Non-goals
- The owner never writes or manages tests; the loop does.
- The loop never runs the full suite on every goal.
- A known failure does not block a run.

## Success metrics
- No goal's test run in the loop takes over 10 minutes, and the nightly full suite runs green or every failure has its issue.
- Every closed issue fixed by a goal has a passing defect test listed in its release note.
- A GitHub run and a local run of the same rows end the same way.

## Tests

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| [refused-unmet](Tests#t-refused-unmet) | requirement | REG-1 | Given a criterion with no test, when a release is cut, then it is refused. | PASS 2026-11-10 |
| [defect-owed](Tests#t-defect-owed) | requirement | REG-1 | Given a goal that fixes an issue, when it opens its pull request without a defect test seen failing, then it is refused. | PASS 2026-11-10 |
| [defect-known](Tests#t-defect-known) | requirement | REG-1 | Given issues 35 and 58 and the two worker defects, when the tests are listed, then defect tests exist for each. | PASS 2026-11-10 |
| [prd-readers](Tests#t-prd-readers) | requirement | REG-1 | Given pages under the Requirements heading or the old Criteria heading, when the release, regression, health and docs readers run, then they all find the same requirement IDs and the release refuses an unmet one. | PASS 2026-11-10 |
| [unproven-blocks](Tests#t-unproven-blocks) | requirement | REG-2 | Given a test never seen failing, when the run happens, then the run is blocked. | PASS 2026-11-10 |
| [tests-seen-failing](Tests#t-tests-seen-failing) | requirement | REG-2 | Given a test that cannot fail, when it is checked, then it stays unproven. | PASS 2026-11-10 |
| [one-link](Tests#t-one-link) | requirement | REG-2 | Given a test linked to no criterion, when the check runs, then the check fails. | PASS 2026-11-10 |
| [run-ledger](Tests#t-run-ledger) | requirement | REG-2 | Given a test run, when it ends, then each test's result and date are recorded. | PASS 2026-11-10 |
| [tests-table-columns](Tests#t-tests-table-columns) | requirement | REG-2 | Given a requirement with a test row, when the Tests are rendered, then its table row carries the test link, its Given/When/Then words and its last result. | PASS 2026-11-10 |
| [tests-row-shape](Tests#t-tests-row-shape) | requirement | REG-2 | Given a test row, when the full Tests page is rendered, then the row carries its anchor, result, date, run and seen-failing date. | PASS 2026-11-10 |
| [describe-needed](Tests#t-describe-needed) | requirement | REG-2 | Given a test row with no description, when the check runs, then it is flagged. | PASS 2026-11-10 |
| [keeps-seen-red](Tests#t-keeps-seen-red) | requirement | REG-2 | Given a row with a seen-failing date, when a description is added, then the date is kept. | PASS 2026-11-10 |
| [every-row-described](Tests#t-every-row-described) | requirement | REG-2 | Given this repo's test rows, when they are checked, then every row has a plain one-line description. | PASS 2026-11-10 |
| [defect-categories](Tests#t-defect-categories) | requirement | REG-2 | Given the test rows, when they are checked, then every row has a category, defect rows link their issue, and the page shows defect tests apart. | FAIL 2026-11-10 |
| [summary-groups](Tests#t-summary-groups) | requirement | REG-2 | Given tests guarding requirements on two wiki pages and one guarding none, when they are listed, then they come grouped by feature in page order, then Other. | PASS 2026-11-10 |
| [summary-fields](Tests#t-summary-fields) | requirement | REG-2 | Given requirement and defect tests, when they are listed, then each shows its kind, what it guards (requirement ID and words, or issue link and state), what it checks, when it runs, its last result and date, and seen failing. | PASS 2026-11-10 |
| [summary-escapes](Tests#t-summary-escapes) | requirement | REG-2 | Given a description with a pipe and a backtick, when tests are listed as tables, then the pipe cannot split a column. | PASS 2026-11-10 |
| [summary-header](Tests#t-summary-header) | requirement | REG-2 | Given a run's results, when the run summary is written, then it has one header with totals and the run time, then one table per feature with each test's name, kind, guards, checks and result. | PASS 2026-11-10 |
| [summary-step](Tests#t-summary-step) | requirement | REG-2 | Given the written workflow, when its summary step runs after the rows, then the grouped summary reaches the run summary. | PASS 2026-11-10 |
| [summary-fallback](Tests#t-summary-fallback) | requirement | REG-2 | Given the grouped summary cannot be written, when the summary step runs, then each row's plain result still reaches the run summary. | PASS 2026-11-10 |
| [summary-refuses](Tests#t-summary-refuses) | requirement | REG-2 | Given a malformed results file or run time, when the run summary is asked for, then it is refused with the line to fix. | PASS 2026-11-10 |
| [issue-states](Tests#t-issue-states) | requirement | REG-2 | Given defect tests linked to an issue and a pull request, when their states are read, then each state is recorded with its date, and nothing is written when gh cannot read them. | PASS 2026-11-10 |
| [health-lists-tests](Tests#t-health-lists-tests) | requirement | REG-2 | Given a repo's tests, when the health check runs, then its report lists the tests grouped by feature in the same format, before its verdict. | PASS 2026-11-10 |
| [reg2-wording](Tests#t-reg2-wording) | requirement | REG-2 | Given the owner's REG-2 wording approved in the operation session on 2026-11-10, when the Regression page is read, then REG-2 carries it, Reviewed 2026-11-10 and sealed. | FAIL 2026-11-10 |
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
| [workflow-same-as-run](Tests#t-workflow-same-as-run) | requirement | REG-3 | Given the same tests, when the workflow runs and regression.py runs locally, then both end the same way and open the same issues. | PASS 2026-11-10 |
| [local-row-env](Tests#t-local-row-env) | requirement | REG-3 | Given a local run with GH_TOKEN and a run summary file set, when a row runs, then it sees neither. | PASS 2026-11-10 |
| [lanes-reuse](Tests#t-lanes-reuse) | requirement | REG-4 | Given a first run on unchanged content, when a second run happens, then it reuses the first and runs no test. | PASS 2026-11-10 |
| [lanes-affected](Tests#t-lanes-affected) | requirement | REG-4 | Given a change, when tests run again, then only the tests that read the changed files run. | PASS 2026-11-10 |
| [lanes-failing](Tests#t-lanes-failing) | requirement | REG-4 | Given a run with a failing test, when a later run happens, then it is never reused. | PASS 2026-11-10 |
| [lanes-missing](Tests#t-lanes-missing) | requirement | REG-4 | Given no recorded run, when tests run, then every test runs. | PASS 2026-11-10 |
| [lanes-ship-reuses](Tests#t-lanes-ship-reuses) | requirement | REG-4 | Given nothing changed since the qa run, when ship runs, then it reuses the qa run. | PASS 2026-11-10 |
| [lanes-qa-record](Tests#t-lanes-qa-record) | requirement | REG-4 | Given the qa step, when it runs the tests, then it records the run with the exact command ship checks. | PASS 2026-11-10 |
| [lanes-pr-affected](Tests#t-lanes-pr-affected) | requirement | REG-4 | Given the base merged before the pull request, when tests run, then only the affected tests rerun. | PASS 2026-11-10 |
| [lanes-headers](Tests#t-lanes-headers) | requirement | REG-4 | Given the repo's test scripts, when their # reads: headers are checked, then every script a row names has a valid header. | FAIL 2026-11-10 |
| [lanes-declared](Tests#t-lanes-declared) | requirement | REG-4 | Given scripts that declare the files they run, when one skill's file changes, then only the rows whose closure reaches it rerun. | PASS 2026-11-10 |
| [lanes-folder-var](Tests#t-lanes-folder-var) | requirement | REG-4 | Given a file run through a folder variable set in another file, when that file changes, then its row still reruns. | PASS 2026-11-10 |
| [lanes-always](Tests#t-lanes-always) | requirement | REG-4 | Given a row whose declaration cannot be resolved, when an unrelated mapped file changes, then the row still reruns. | PASS 2026-11-10 |
| [lanes-narrow-wide](Tests#t-lanes-narrow-wide) | requirement | REG-4 | Given declared rows, when a change reaches only some of them, then only those rerun, and a change every row reaches reruns them all. | PASS 2026-11-10 |
| [lanes-repo-narrow](Tests#t-lanes-repo-narrow) | requirement | REG-4 | Given this repo's table, when one skill script changes, then fewer than half the land rows rerun and every row whose script declares it does. | PASS 2026-11-10 |
| [lanes-glob](Tests#t-lanes-glob) | requirement | REG-4 | Given a script that globs a skill folder, when its header declares only a file in it, then the check refuses it until the folder is declared. | PASS 2026-11-10 |
| [lanes-deleted](Tests#t-lanes-deleted) | requirement | REG-4 | Given a deleted skill file, when a reusing run happens, then every row runs even when a broad row maps the file. | PASS 2026-11-10 |
| [lanes-check](Tests#t-lanes-check) | requirement | REG-4 | Given a header problem, when lanes_cli.py check runs, then it names the code, the file and line, and the line to fix. | PASS 2026-11-10 |
| [lanes-wide-parity](Tests#t-lanes-wide-parity) | requirement | REG-4 | Given scripts with no header, when affected runs, then the mapping is the same as the wide one, and LANES_WIDE=1 forces it everywhere. | PASS 2026-11-10 |
| [lanes-trace-check](Tests#t-lanes-trace-check) | requirement | REG-4 | Given a row whose run reads a skill file outside its closure, when check-reads runs, then that row fails with the line to add. | PASS 2026-11-10 |
| [lanes-trace](Tests#t-lanes-trace) | requirement | REG-4 | Given every land row, when check-reads traces their runs, then each run's skill reads are inside its closure. | FAIL 2026-11-10 |
| [lanes-table](Tests#t-lanes-table) | requirement | REG-4 | Given an edit to one row of the table, when a reusing run happens, then only that row and the rows that read this repo's table rerun. | PASS 2026-11-10 |
| [reg-same-env](Tests#t-reg-same-env) | requirement | REG-4 | Given the same test, when it runs locally, in the loop or in GitHub Actions, then it gets the same environment from the same command. | PASS 2026-11-10 |
| [known-no-block](Tests#t-known-no-block) | requirement | REG-5 | Given a known failure, when the run happens, then it does not block the run or open an issue. | PASS 2026-11-10 |
| [no-token-dry-run](Tests#t-no-token-dry-run) | requirement | REG-5 | Given no GitHub token, when a run happens, then it only prints what it would do. | PASS 2026-11-10 |
| [one-issue](Tests#t-one-issue) | requirement | REG-5 | Given a failing test, when the run reports it, then one GitHub issue is opened. | PASS 2026-11-10 |
| [known-recorded](Tests#t-known-recorded) | requirement | REG-5 | Given a known failure, when the GitHub run runs it, then its result is recorded KNOWN, not FAIL. | PASS 2026-11-10 |
| [reg-defect-label](Tests#t-reg-defect-label) | requirement | REG-5 | Given a failing test, when a local live run reports it, then its issue is labelled defect. | PASS 2026-11-10 |
| [reg-local-relabel](Tests#t-reg-local-relabel) | requirement | REG-5 | Given an older open issue for a failing test, when a local live run reports it, then the issue gains the defect label. | PASS 2026-11-10 |
| - | requirement | REG-6 | no passing test | not enforced |
| - | requirement | REG-7 | no passing test | not enforced |
| - | requirement | REG-8 | no passing test | not enforced |
| - | requirement | REG-9 | no passing test | not enforced |
| [summary-only-real-rows](Tests#t-summary-only-real-rows) | defect | [#92](https://github.com/jcl2018/agent-workflow-template/issues/92) closed (2026-11-10) | Given a row that writes to the run summary, env or outputs like a toy test, when the GitHub run runs it, then nothing it writes reaches the real summary, env or outputs. | PASS 2026-11-10 |
| [toy-no-leftovers](Tests#t-toy-no-leftovers) | defect | [#100](https://github.com/jcl2018/agent-workflow-template/issues/100) state unknown | Given a toy test that starts stand-in agents, when it passes, fails, is interrupted or its pipe closes, then no process it started is left running. | not run |
