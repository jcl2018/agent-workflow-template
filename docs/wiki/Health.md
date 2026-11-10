<!-- workflow-docs -->
# Health

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/4

Review: **Unreviewed**

## Problem

Skill: `workflow-health`. A check of the repo's health with fixed rules, so the same repo always gets the same answer. `check` is read-only and prints one formal report; `preview` lists the issues it would file and writes nothing; `file --group NAME` files only the named groups as issues on the Backlog milestone, each tagged `health:<group>`. It runs `workflow-docs` and `workflow-regression` and reports on what they say, and adds closed issues and findings with no defect test, script size, old findings, stuck runs, merged branches and goals over their time or token budget (the performance group). The merged-branch warning's fix is `worker.py cleanup`. A Mine group runs the owner's own rules from a private setting outside the repo. `check` prints a header naming the groups run and skipped, every rule of each group with its state and a fix on each non-pass line, and one `HEALTH:` line; the Cost rule is shown as performance. `judge` prints that report, then a separate judge section of suggestions on criteria quality, test quality and performance and tokens, with ranked next steps; it never changes the verdict. Like the other scripts, the health modules never wait on a terminal prompt. On Agensi a script can't reach its siblings, so the criteria and docs rules print `UNREAD`, and the verdict says so; a lone `health.py` prints the bare rows and verdict without the formal report, and `preview` and `file` refuse unless `file.py` is beside it. A filed Mine issue names only the rule and its state; the rule's output stays local.

## Usage

- `/workflow-health check` prints the formal report ending in a `HEALTH:` line; "check only the docs health" limits it to one group.
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

#### HLT-1

One command, run by group; fixed rules; same answer twice; changes nothing.

- Given an unchanged repo, when health runs twice, then both runs print the same lines. — [same-lines](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a repo, when the health check runs, then it writes no file and makes no commit. — [check-writes-nothing](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07

#### HLT-2

The rules. Health checks exactly these rules: Size (every script stays under 20 KB, with a warning from 90%); Criteria (every criterion has a test seen failing once and passing now; done lines with no test are a warning); Docs (every required doc matches the template and the code; a stale page is a warning, any other gap fails); Hygiene (no more than 5 open findings, no goal waiting on me over 24 hours, no leftover merged branches); Cost (a goal over its time or token budget is a warning, naming the slowest or costliest steps); Mine (any rules I add of my own, named in a private setting). Adding a rule means retiring one or raising the cap on purpose. A rule may run an existing command to get its data.

- Given a script over 20 KB, when health runs, then it is a FAIL with a fix. — [size-fail](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a stale wiki page, when health runs, then it shows as a docs row naming the page. — [stale-page-row](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a criterion with no test row, when health runs, then it is a FAIL. — [no-row-fail](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a closed issue or finding with no defect test, when health runs, then it is flagged. — [defect-health](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given a goal over its time budget, when health runs, then it is a Cost warning naming its slowest steps. — [cost-time-warn](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given no tokens recorded, when the Cost rule runs, then it prints UNREAD. — [cost-unread-tokens](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08

#### HLT-3

Formal report. Health prints one formal report: a header listing every rule group it ran (and any skipped), then each group in a fixed order with every rule it checked, marked pass, warn, fail or unread, each non-pass line with its fix, then one verdict. A rule that can't read its data is never shown as passing.

- Given a health rule that cannot be read, when health runs, then it is never shown green. — [unread-not-green](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a repo with findings in several groups, when health check runs, then the report header names every group it ran and the one it skipped. — [report-header](../../.loop/regression.tsv), both, not run, seen failing 2026-11-09

#### HLT-4

Findings become tagged issues, under my control. Each finding can be filed as one GitHub issue on the Backlog milestone, tagged with its group: health:size, health:criteria, health:docs, health:hygiene, health:performance (the Cost rule and the judge's savings), health:mine. A preview first lists exactly what would be opened, updated, closed or reopened, and nothing is written until I confirm or name the groups to file. A repeat updates its issue, a fix closes it, a return reopens it.

- Given no token and no --live flag, when health previews its findings, then it prints only WOULD lines and writes nothing. — [no-token-would](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given an existing health issue, when a later health run happens, then it updates that issue and opens no other. — [update-in-place](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a finding with an open issue, when the finding is fixed, then its issue is closed. — [fixed-closes](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a finding with an open issue, when the finding repeats, then no second issue is opened. — [repeat-no-second](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a rule that could not be read, when health runs, then none of its issues are closed. — [unread-closes-none](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given findings in several groups, when health preview runs, then it lists each issue it would open, update, close or reopen with its tag and makes no write call. — [preview-writes-nothing](../../.loop/regression.tsv), both, not run, seen failing 2026-11-09
- Given open issues in several groups, when health files only the docs group, then only the docs issue is closed and no other group's issue changes. — [file-one-group](../../.loop/regression.tsv), both, not run, seen failing 2026-11-09

#### HLT-5

Judge and next steps. After the rules, a separate judge section, marked as suggestions and never part of the verdict, reviews three things: criteria quality (whether each criterion is clear, testable and high-level enough, whether any conflict or overlap, and whether a feature is missing one, suggesting better wording that only I can apply); test quality (whether each criterion's tests and each defect's test really prove what they claim, or are weak, miss cases or test the wrong thing, suggesting stronger or missing tests for both categories); and performance and tokens (where the framework's skill steps, prompts, scripts, waits and retries could cut delivery time or token use, ranked by the savings). It ends with ranked next steps from the judgments, the warnings and the failures.

- Given the judge, when it runs, then it prints its three reviews in a section marked as suggestions. — [judge-section-format](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given a failing or garbage judge, when health runs, then the verdict and exit code are unchanged. — [judge-verdict-unchanged](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given suggested criterion wording, when the board is printed, then it is listed under Needs you for the owner to apply. — [judge-needs-you](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08

#### HLT-6

Health keeps itself honest and the repo lean. Every health rule has a negative control that proves it can fire; the check flags a land test run over its time budget and names the slowest rows to move to nightly; and it flags stale worktrees and branches that exist only on this machine.

- Given every health rule, when health check runs its controls, then each rule's negative control makes it fire. — [hlt6-controls-fire](../../.loop/regression.tsv), both, not run, seen failing no
- Given a rule broken so it can never report, when health check runs its controls, then that rule is reported as one that cannot fire, with how to look. — [hlt6-cannot-fire](../../.loop/regression.tsv), both, not run, seen failing no
- Given a new rule with no negative control, when health.py starts, then it refuses before any report and names the control to add. — [hlt6-refused](../../.loop/regression.tsv), both, not run, seen failing no
- Given a land lane recorded over test_budget_seconds, when health check runs, then it warns and names the slowest rows and scripts to move to nightly. — [hlt6-test-time](../../.loop/regression.tsv), both, not run, seen failing no
- Given a land lane within test_budget_seconds, when health check runs, then the test-time rule passes. — [hlt6-test-quiet](../../.loop/regression.tsv), both, not run, seen failing no
- Given a regression run, when it saves its lane record, then the record holds each row's time and the total. — [hlt6-run-times](../../.loop/regression.tsv), both, not run, seen failing no
- Given a lane record, when the judge gathers its facts, then its performance review sees the land lane's total and slowest rows as well as tokens. — [hlt6-judge-time](../../.loop/regression.tsv), both, not run, seen failing no
- Given a loop worktree no live goal names, when health check runs, then it lists it with the command that removes it, and leaves a live goal's worktree alone. — [hlt6-worktrees](../../.loop/regression.tsv), both, not run, seen failing no
- Given a local branch on no remote older than stale_branch_days, when health check runs, then it lists it with a quoted delete and a data-loss warning, and leaves a young branch alone. — [hlt6-branches](../../.loop/regression.tsv), both, not run, seen failing no
- Given stale worktrees and branches, when health check runs, then nothing is removed. — [hlt6-removes-nothing](../../.loop/regression.tsv), both, not run, seen failing no
- Given no stale worktree or branch, when health check runs, then both rules pass. — [hlt6-clean-quiet](../../.loop/regression.tsv), both, not run, seen failing no
- Given stale worktrees, when health previews the hygiene group, then no test-time, worktree or branch row would be filed. — [hlt6-never-filed](../../.loop/regression.tsv), both, not run, seen failing no
- **not enforced**: no passing test
