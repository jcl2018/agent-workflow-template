<!-- workflow-docs -->
# Health

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/4

Review: **Unreviewed**

## Problem

Skill: `workflow-health`. A check of the repo's health with fixed rules, so the same repo always gets the same answer. `check` is read-only and prints one formal report; `preview` lists the issues it would file and writes nothing; `file --group NAME` files only the named groups as issues on the Backlog milestone, each tagged `health:<group>`. It runs `workflow-docs` and `workflow-regression` and reports on what they say, and adds closed issues and findings with no defect test, script size, old findings, stuck runs, merged branches and goals over their time or token budget (the performance group). It keeps itself honest: every rule has a negative control, a throwaway repo made to break it, and a rule that no longer fires on its control is reported as one that cannot fire (a rule with no control stops health from loading). It keeps the repo lean: the land test lane over `test_budget_seconds` is a warning naming the slowest rows to move to nightly, and stale loop worktrees and local branches on no remote are listed with the commands that remove them, which it never runs and never files. A control that breaks, or whose rule cannot read on it, is `UNREAD`, never "cannot fire"; test time is judged only from this branch's own lane record (another branch's is shown as information); and a live goal's worktree or branch, a queued one included, is never listed (a run record that cannot be read makes both rules `UNREAD`). The controls are shown and never filed. The merged-branch warning's fix is `worker.py cleanup`. A Mine group runs the owner's own rules from a private setting outside the repo. `check` prints a header naming the groups run and skipped, every rule of each group with its state and a fix on each non-pass line, and one `HEALTH:` line; the Cost rule is shown as performance. `judge` prints that report, then a separate judge section of suggestions on criteria quality, test quality and performance (test time, from the land lane's total and slowest rows, and tokens), with ranked next steps; it never changes the verdict. Like the other scripts, the health modules never wait on a terminal prompt. On Agensi a script can't reach its siblings, so the criteria and docs rules print `UNREAD`, and the verdict says so; a lone `health.py` prints the bare rows and verdict without the formal report, and `preview` and `file` refuse unless `file.py` is beside it. A filed Mine issue names only the rule and its state; the rule's output stays local.

## Usage

- `/workflow-health check` prints the formal report ending in a `HEALTH:` line; "check only the docs health" limits it to one group. The full report also lists every test just before the verdict, under `TESTS`, grouped by feature in workflow-regression's one test format; it never changes the verdict, and a single group or `--json` leaves it out.
- `/workflow-health preview` lists each issue it would open, update, close or reopen, with its tag, and writes nothing.
- `/workflow-health file --group docs` writes only the named groups as issues on the Backlog; with no group it refuses.
- `/workflow-health judge` adds the judge section of suggestions and ranked next steps; it never changes the verdict. Name `performance` to preview or file to include the judge's savings.

## Requirements

- HLT-1: **Reviewed 2026-11-08** One command, run by group; fixed rules; same answer twice; changes nothing. <!-- reviewed ea097218 -->
- HLT-2: **Reviewed 2026-11-08** The rules. Health checks exactly these rules: Size (every script stays under 20 KB, with a warning from 90%); Criteria (every criterion has a test seen failing once and passing now; done lines with no test are a warning); Docs (every required doc matches the template and the code; a stale page is a warning, any other gap fails); Hygiene (no more than 5 open findings, no goal waiting on me over 24 hours, no leftover merged branches); Cost (a goal over its time or token budget is a warning, naming the slowest or costliest steps); Mine (any rules I add of my own, named in a private setting). Adding a rule means retiring one or raising the cap on purpose. A rule may run an existing command to get its data. <!-- reviewed ec941e9a -->
- HLT-3: **Reviewed 2026-11-08** Formal report. Health prints one formal report: a header listing every rule group it ran (and any skipped), then each group in a fixed order with every rule it checked, marked pass, warn, fail or unread, each non-pass line with its fix, then one verdict. A rule that can't read its data is never shown as passing. <!-- reviewed 8ac60064 -->
- HLT-4: **Reviewed 2026-11-08** Findings become tagged issues, under my control. Each finding can be filed as one GitHub issue on the Backlog milestone, tagged with its group: health:size, health:criteria, health:docs, health:hygiene, health:performance (the Cost rule and the judge's savings), health:mine. A preview first lists exactly what would be opened, updated, closed or reopened, and nothing is written until I confirm or name the groups to file. A repeat updates its issue, a fix closes it, a return reopens it. <!-- reviewed f81a6284 -->
- HLT-5: **Reviewed 2026-11-08** Judge and next steps. After the rules, a separate judge section, marked as suggestions and never part of the verdict, reviews three things: criteria quality (whether each criterion is clear, testable and high-level enough, whether any conflict or overlap, and whether a feature is missing one, suggesting better wording that only I can apply); test quality (whether each criterion's tests and each defect's test really prove what they claim, or are weak, miss cases or test the wrong thing, suggesting stronger or missing tests for both categories); and performance and tokens (where the framework's skill steps, prompts, scripts, waits and retries could cut delivery time or token use, ranked by the savings). It ends with ranked next steps from the judgments, the warnings and the failures. <!-- reviewed 52d7f085 -->
- HLT-6: **Reviewed 2026-11-09** Health keeps itself honest and the repo lean. Every health rule has a negative control that proves it can fire; the check flags a land test run over its time budget and names the slowest rows to move to nightly; and it flags stale worktrees and branches that exist only on this machine. <!-- reviewed 6dfdb920 -->

## Non-goals

- It changes nothing in the repo: check is read-only, preview writes nothing, and only file --group writes, as GitHub issues. It prints the commands that remove stale worktrees and branches and never runs them.
- The judge's suggestions never change the verdict.
- Its rules are fixed, not set per repo, apart from the owner's private Mine rules.

## Success metrics

- Two runs on an unchanged repo print the same lines.
- Every finding in a group the owner files is one issue on the Backlog milestone, tagged with its group, closed when it is fixed.
- The verdict is never green while a rule could not be read.

## Tests

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| [same-lines](Tests#t-same-lines) | requirement | HLT-1 | Given an unchanged repo, when health runs twice, then both runs print the same lines. | PASS 2026-11-09 |
| [check-writes-nothing](Tests#t-check-writes-nothing) | requirement | HLT-1 | Given a repo, when the health check runs, then it writes no file and makes no commit. | PASS 2026-11-09 |
| [size-fail](Tests#t-size-fail) | requirement | HLT-2 | Given a script over 20 KB, when health runs, then it is a FAIL with a fix. | PASS 2026-11-09 |
| [stale-page-row](Tests#t-stale-page-row) | requirement | HLT-2 | Given a stale wiki page, when health runs, then it shows as a docs row naming the page. | PASS 2026-11-09 |
| [no-row-fail](Tests#t-no-row-fail) | requirement | HLT-2 | Given a criterion with no test row, when health runs, then it is a FAIL. | PASS 2026-11-09 |
| [defect-health](Tests#t-defect-health) | requirement | HLT-2 | Given a closed issue or finding with no defect test, when health runs, then it is flagged. | PASS 2026-11-09 |
| [cost-time-warn](Tests#t-cost-time-warn) | requirement | HLT-2 | Given a goal over its time budget, when health runs, then it is a Cost warning naming its slowest steps. | PASS 2026-11-09 |
| [cost-unread-tokens](Tests#t-cost-unread-tokens) | requirement | HLT-2 | Given no tokens recorded, when the Cost rule runs, then it prints UNREAD. | PASS 2026-11-09 |
| [unread-not-green](Tests#t-unread-not-green) | requirement | HLT-3 | Given a health rule that cannot be read, when health runs, then it is never shown green. | PASS 2026-11-09 |
| [report-header](Tests#t-report-header) | requirement | HLT-3 | Given a repo with findings in several groups, when health check runs, then the report header names every group it ran and the one it skipped. | not run |
| [no-token-would](Tests#t-no-token-would) | requirement | HLT-4 | Given no token and no --live flag, when health previews its findings, then it prints only WOULD lines and writes nothing. | PASS 2026-11-09 |
| [update-in-place](Tests#t-update-in-place) | requirement | HLT-4 | Given an existing health issue, when a later health run happens, then it updates that issue and opens no other. | PASS 2026-11-09 |
| [fixed-closes](Tests#t-fixed-closes) | requirement | HLT-4 | Given a finding with an open issue, when the finding is fixed, then its issue is closed. | PASS 2026-11-09 |
| [repeat-no-second](Tests#t-repeat-no-second) | requirement | HLT-4 | Given a finding with an open issue, when the finding repeats, then no second issue is opened. | PASS 2026-11-09 |
| [unread-closes-none](Tests#t-unread-closes-none) | requirement | HLT-4 | Given a rule that could not be read, when health runs, then none of its issues are closed. | PASS 2026-11-09 |
| [preview-writes-nothing](Tests#t-preview-writes-nothing) | requirement | HLT-4 | Given findings in several groups, when health preview runs, then it lists each issue it would open, update, close or reopen with its tag and makes no write call. | not run |
| [file-one-group](Tests#t-file-one-group) | requirement | HLT-4 | Given open issues in several groups, when health files only the docs group, then only the docs issue is closed and no other group's issue changes. | not run |
| [judge-section-format](Tests#t-judge-section-format) | requirement | HLT-5 | Given the judge, when it runs, then it prints its three reviews in a section marked as suggestions. | PASS 2026-11-09 |
| [judge-verdict-unchanged](Tests#t-judge-verdict-unchanged) | requirement | HLT-5 | Given a failing or garbage judge, when health runs, then the verdict and exit code are unchanged. | PASS 2026-11-09 |
| [judge-needs-you](Tests#t-judge-needs-you) | requirement | HLT-5 | Given suggested criterion wording, when the board is printed, then it is listed under Needs you for the owner to apply. | PASS 2026-11-09 |
| [hlt6-controls-fire](Tests#t-hlt6-controls-fire) | requirement | HLT-6 | Given every health rule, when health check runs its controls, then each rule's negative control makes it fire. | not run |
| [hlt6-cannot-fire](Tests#t-hlt6-cannot-fire) | requirement | HLT-6 | Given a rule broken so it can never report, when health check runs its controls, then that rule is reported as one that cannot fire, with how to look. | not run |
| [hlt6-refused](Tests#t-hlt6-refused) | requirement | HLT-6 | Given a new rule with no negative control, when health.py starts, then it refuses before any report and names the control to add. | not run |
| [hlt6-test-time](Tests#t-hlt6-test-time) | requirement | HLT-6 | Given a land lane recorded over test_budget_seconds, when health check runs, then it warns and names the slowest rows and scripts to move to nightly. | not run |
| [hlt6-test-quiet](Tests#t-hlt6-test-quiet) | requirement | HLT-6 | Given a land lane within test_budget_seconds, when health check runs, then the test-time rule passes. | not run |
| [hlt6-run-times](Tests#t-hlt6-run-times) | requirement | HLT-6 | Given a regression run, when it saves its lane record, then the record holds each row's time and the total. | not run |
| [hlt6-judge-time](Tests#t-hlt6-judge-time) | requirement | HLT-6 | Given a lane record, when the judge gathers its facts, then its performance review sees the land lane's total and slowest rows as well as tokens. | not run |
| [hlt6-worktrees](Tests#t-hlt6-worktrees) | requirement | HLT-6 | Given a loop worktree no live goal names, when health check runs, then it lists it with the command that removes it, and leaves a live goal's worktree alone. | not run |
| [hlt6-branches](Tests#t-hlt6-branches) | requirement | HLT-6 | Given a local branch on no remote older than stale_branch_days, when health check runs, then it lists it with a quoted delete and a data-loss warning, and leaves a young branch alone. | not run |
| [hlt6-removes-nothing](Tests#t-hlt6-removes-nothing) | requirement | HLT-6 | Given stale worktrees and branches, when health check runs, then nothing is removed. | not run |
| [hlt6-clean-quiet](Tests#t-hlt6-clean-quiet) | requirement | HLT-6 | Given no stale worktree or branch, when health check runs, then both rules pass. | not run |
| [hlt6-never-filed](Tests#t-hlt6-never-filed) | requirement | HLT-6 | Given stale worktrees, when health previews the hygiene group, then no test-time, worktree or branch row would be filed. | not run |
| - | requirement | HLT-6 | no passing test | not enforced |
