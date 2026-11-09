<!-- workflow-docs -->
# Health

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/4

Review: **Unreviewed**

## Problem

Skill: `workflow-health`. A check of the repo's health with fixed rules, so the same repo always gets the same answer. `check` is read-only; `run` files what it finds as issues on the Backlog milestone. It runs `workflow-docs` and `workflow-regression` and reports on what they say, and adds closed issues and findings with no defect test, script size, old findings, stuck runs, merged branches and goals over their time or token budget (Cost). The merged-branch warning's fix is `worker.py cleanup`. A Mine group runs the owner's own rules from a private setting outside the repo. `check` prints one fixed report ending in one `HEALTH:` line. `judge` prints that report, then a separate judge section of suggestions on criteria quality, test quality and performance and tokens, with ranked next steps; it never changes the verdict. Like the other scripts, the health modules never wait on a terminal prompt. On Agensi a script can't reach its siblings, so the criteria and docs rules print `UNREAD`, and the verdict says so.

## Usage

- `/workflow-health check` prints the one fixed report ending in a `HEALTH:` line; "check only the docs health" limits it to one group.
- `/workflow-health judge` adds the judge section of suggestions and ranked next steps; it never changes the verdict.
- `/workflow-health run` files each finding as an issue on the Backlog milestone; without a token it only previews.

## Requirements

- HLT-1: **Reviewed 2026-11-08** One command, run by group; fixed rules; same answer twice; changes nothing. <!-- reviewed ea097218 -->
- HLT-2: **Reviewed 2026-11-08** The rules. Health checks exactly these rules: Size (every script stays under 20 KB, with a warning from 90%); Criteria (every criterion has a test seen failing once and passing now; done lines with no test are a warning); Docs (every required doc matches the template and the code; a stale page is a warning, any other gap fails); Hygiene (no more than 5 open findings, no goal waiting on me over 24 hours, no leftover merged branches); Cost (a goal over its time or token budget is a warning, naming the slowest or costliest steps); Mine (any rules I add of my own, named in a private setting). Adding a rule means retiring one or raising the cap on purpose. A rule may run an existing command to get its data. <!-- reviewed ec941e9a -->
- HLT-3: **Reviewed 2026-11-08** One printout template like the status block: groups, findings pass/warn/fail/unread, fix line each, one verdict; unread never green. <!-- reviewed d67b7618 -->
- HLT-4: **Reviewed 2026-11-08** Findings go to the Backlog: one issue each on the Backlog milestone; repeat updates, fix closes, return reopens; no token = preview. <!-- reviewed e8e3261e -->
- HLT-5: **Reviewed 2026-11-08** Judge and next steps. After the rules, a separate judge section, marked as suggestions and never part of the verdict, reviews three things: criteria quality (whether each criterion is clear, testable and high-level enough, whether any conflict or overlap, and whether a feature is missing one, suggesting better wording that only I can apply); test quality (whether each criterion's tests and each defect's test really prove what they claim, or are weak, miss cases or test the wrong thing, suggesting stronger or missing tests for both categories); and performance and tokens (where the framework's skill steps, prompts, scripts, waits and retries could cut delivery time or token use, ranked by the savings). It ends with ranked next steps from the judgments, the warnings and the failures. <!-- reviewed 52d7f085 -->

## Non-goals

- It changes nothing in the repo: check is read-only, and run only files issues.
- The judge's suggestions never change the verdict.
- Its rules are fixed, not set per repo, apart from the owner's private Mine rules.

## Success metrics

- Two runs on an unchanged repo print the same lines.
- Every finding is one issue on the Backlog milestone, closed when it is fixed.
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

One printout template like the status block: groups, findings pass/warn/fail/unread, fix line each, one verdict; unread never green.

- Given a health rule that cannot be read, when health runs, then it is never shown green. — [unread-not-green](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07

#### HLT-4

Findings go to the Backlog: one issue each on the Backlog milestone; repeat updates, fix closes, return reopens; no token = preview.

- Given no token, when milestones runs, then it only prints what it would do. — [no-token-would](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given an existing health issue, when a later health run happens, then it updates that issue and opens no other. — [update-in-place](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a finding with an open issue, when the finding is fixed, then its issue is closed. — [fixed-closes](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a finding with an open issue, when the finding repeats, then no second issue is opened. — [repeat-no-second](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07
- Given a rule that could not be read, when health runs, then none of its issues are closed. — [unread-closes-none](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-07

#### HLT-5

Judge and next steps. After the rules, a separate judge section, marked as suggestions and never part of the verdict, reviews three things: criteria quality (whether each criterion is clear, testable and high-level enough, whether any conflict or overlap, and whether a feature is missing one, suggesting better wording that only I can apply); test quality (whether each criterion's tests and each defect's test really prove what they claim, or are weak, miss cases or test the wrong thing, suggesting stronger or missing tests for both categories); and performance and tokens (where the framework's skill steps, prompts, scripts, waits and retries could cut delivery time or token use, ranked by the savings). It ends with ranked next steps from the judgments, the warnings and the failures.

- Given the judge, when it runs, then it prints its three reviews in a section marked as suggestions. — [judge-section-format](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given a failing or garbage judge, when health runs, then the verdict and exit code are unchanged. — [judge-verdict-unchanged](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given suggested criterion wording, when the board is printed, then it is listed under Needs you for the owner to apply. — [judge-needs-you](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
