<!-- workflow-docs -->
# Health

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/4

Review: **Reviewed 2026-11-13** <!-- prd P=b4d391e0 R=4bb528ed N=e89b4f3b M=39cf9800 U=03828777 -->

## Problem
- My rules, requirements and standards are spread across many pages and sometimes conflict, and I can't see where the repo falls short of its own PRDs.
- I want a reviewer that reads everything (every PRD page, the README, milestones, open issues, tests and code) and tells me per feature what conflicts, what's missing and what's slow, alongside fixed checks that give the same answer every time.
- Its findings should land as issues tagged with their group (and their feature when feature_labels is on), previewed first, so I can triage them in one place later.

## Runbook

### health-round
- **Serves:** HLT-2, HLT-3, HLT-4, HLT-5, AUT-1, AUT-3, AUT-4.
- **Schedule:** on the owner's Mac only (AUT-1, AUT-3): the one launch agent `com.workflow-loop.schedule` runs `automation.py local tick` every 4 hours by default (`health_cron` in `.loop/config.json`; an every-N-hours or fixed-hours shape, `off` stops it). To run a round by hand use `python3 skills/workflow-health/scripts/automation.py local tick --repo PATH` (a hand run of one repo that is not due still runs). There is no health workflow in GitHub Actions: a leftover `.github/workflows/health.yml` is a WARN of the `scheduled` rule, remove it with `git rm`.
- **Steps:** `local tick` does the whole round in order, one command each, in a checkout of `origin/<base>` under the schedule home (the working tree is never touched): probe `gh auth status` and the API; Check (`health.py check`, every group the Mac can read); File (the same command with `file`); Judge (`health.py judge`, on the Mac's own `claude` login); Digest (`automation.py digest`); Mail (`mail.py send`). Start it with `automation.py local tick`, preview with `--dry-run`. Do not rebuild the round from separate commands: a hand digest with a token posts for real on the pinned issue.
- **Full run:** a full run reads the live repo and its live open issues, runs all twelve groups (performance, controls, Mine and hygiene read the Mac's own records and files, which only the Mac has), runs the full regression live for a private repo (`regression_runs` is `mac`) or takes the newest suite time for a public one, and ends with the real `HEALTH:` verdict line. It files every finding as one issue tagged with its group (and with `feature:<Page>` only when `feature_labels` is true, off by default), re-checks the open review issues against this run's findings, posts the digest comment and mails it. The judge is skipped, and the report says `JUDGE: skipped, ...`, only when `claude` is not logged in; the round is still a full run. Each repo's tick is capped by `LOOP_TICK_MINUTES` and the whole tick by `LOOP_TICK_TOTAL_MINUTES`, within AUT-7's budget.
- **Output:** one digest comment on the pinned Automation digest issue, and one email of that same comment when `~/.workflow-loop/schedule/mail.env` (mode 0600, `DIGEST_TO=...` lines) exists, through `digest_mail`. The tick prints `SKILLS:`, `JUDGE:` and `REGRESSION:` lines and writes its log in the schedule home.
- **Never:** never send a fixture, a sample or a test mail in place of the round's digest; never run `preview` or any dry run as the scheduled round; never skip a group to save time; never invent the verdict or the issue list; never fake a skipped judge or an off mail to make the round look complete; never push, merge or release; never put the address or a key in any text.
- **Check:** the tick printed a real `HEALTH: green|not green (...)` line and `local status` shows `last_run` as this round and `OK` for the plist, gh and claude (`OVERDUE`, `MISSED` and `SKIPPED` mean the Mac slept, was offline or logged out); the digest comment names this run's id and its cost line (the suite time in it is the newest suite-time artifact, which can belong to an earlier regression run); the mail step prints one `MAIL:` line: `MAIL_SENT`, or `MAIL_ALREADY` on a rerun, are done, while `MAIL_OFF` (`digest_mail` is off in the config), `MAIL_SECRETS` and `MAIL_NOT_SET_UP` mean no mail is set up, and `MAIL_FAILED`, `MAIL_REFUSED` and `MAIL_UNKNOWN` mean the send did not go: report the code and never send by another route; `DIGEST_ALREADY` and `DIGEST_STALE` mean this round was already posted or an older run came in, so post nothing again; an issue the report names exists on GitHub with its group tag. A repeated finding whose issue differs only in the body's trailing newline is the same issue: the round files `SAME #<n>`, not an update.

## Requirements

### Functional
- HLT-2: **Reviewed 2026-11-13** The rules <!-- reviewed 4c8e3124 -->
  - Health checks exactly these groups, each with the angle its tests take:
  - Requirements (my angle: is every promise I approved proven?): every Reviewed requirement has a test seen failing and passing now; done lines have tests; none stays not enforced over 7 days.
  - Traceability (an auditor's angle: can I follow any work end to end?): requirement to test to last run; issue to feature; pull request to goal to done lines; release to the issues it fixed.
  - Consistency (a reader's angle: do the pages agree?): IDs unique across pages; no reference to a missing ID; a command named the same in its skill's command reference and the README; no two requirements that contradict.
  - Docs (a newcomer's angle: does each page match the template and the code?): template sections and limits; each skill's command reference matches the real commands and output; Home complete.
  - Freshness (my angle when I come back: is anything out of date?): the nightly suite ran in the last 24 hours; no merged work unreleased over 3 days; pages updated after their code changed; no finding older than 30 days.
  - Tests (a skeptic's angle: do the tests prove anything?): every row seen failing once; no flaky rows; no row skipped over 7 days; slowest rows named; no test touches the network.
  - Performance (my clock's and my wallet's angle: is it fast and cheap enough?): goal runs and the full suite within their time limits; goals within their time and token budgets; the health check within its limit.
  - Security and privacy (a leak's angle: can anything private escape?): no private names, paths, emails or keys in tracked files; secrets only in the environment or secrets; the commit scan hook installed; workflows with least permissions.
  - Size (a maintainer's angle: can someone still read this?): scripts under 20 KB with a warning from 90%; SKILL.md under 150 lines; requirements per page within the limit.
  - Hygiene (a janitor's angle: is anything left lying around?): open findings within the cap; no wait on me over 24 hours; no merged or stale branches or worktrees; no idle worker sessions.
  - Adoption (another repo's angle: would this work installed fresh?): config valid; every check runs at least one test; template version current; the local schedule installed and, for a public repo, the regression workflow present and firing.
  - Controls (the checker's own angle: can each rule fire?): every rule has a negative control run against a deliberately broken copy.
  - Mine (my private angle): rules I add in a private setting.
  - At most 12 groups plus Mine; adding one means retiring one or raising the cap on purpose.
- HLT-3: **Reviewed 2026-11-10** Formal report <!-- reviewed a5cc0046 -->
  - A header listing every group it ran (and any skipped), then each group with every rule marked pass, warn, fail or unread with its fix, then one verdict. A rule that can't read its data is never shown as passing.
- HLT-4: **Reviewed 2026-11-13** Findings become issues tagged with their group, and their feature when feature_labels is on <!-- reviewed 283dffa7 -->
  - Each finding, from a rule or from the review, is one GitHub issue tagged with its group or kind and, when feature_labels is on (it is off by default), the feature it is about. A FAIL (except a performance one) and a review conflict is a defect, labelled `defect`, on no milestone; every other finding (a WARN, a performance FAIL, a drift, weak-test or saving finding, a review gap, an unread rule) is a backlog item, labelled `backlog`, on its feature's milestone "Backlog: <Feature>", or on "Backlog: Other" when it fits no feature. An issue I move to another milestone stays there.
  - A preview lists exactly what would be opened, updated, closed or reopened, and nothing is written until I confirm or name the groups or features to file, behind an explicit `--live`.
  - A repeat updates its issue, a fix closes it, a return reopens it, and an existing open issue that already covers a finding is linked, not duplicated.
  - A finding's issue body and comment are passed to gh in a file (`--body-file`), never on the command line.
  - Health reads only the issues a command needs, a page of 100 at a time: triage the open health issues, `file` the health issues and the open ones. A repo with thousands of issues lists within the time limit, and a page that fails, or a listing past 20,000 issues, refuses with one line naming it.
- HLT-5: **Reviewed 2026-11-10** Repo review <!-- reviewed 28f88bd6 -->
  - A reviewer, separate from the rules and never part of the verdict, reads every PRD page, the README, milestones, open issues, tests and code, feature by feature, and reports:
  - Conflicts: two requirements that contradict each other, or a page that breaks a reviewed rule (for example DOC-1's Problem length).
  - Gaps: a feature with no non-functional requirement where one is expected (performance, safety, privacy), an untested requirement, an open issue that fits no requirement, a done line with no test.
  - Drift: code or Usage that does something its PRD doesn't say, or a requirement the code no longer meets.
  - Weak tests: a test that doesn't really prove what it claims, misses a case or tests the wrong thing.
  - Savings: where skill steps, prompts, scripts, waits and retries could cut time or tokens, ranked by size.
  - It ends with ranked next steps per feature. Wording changes it suggests are only applied by me.
- HLT-6: **Reviewed 2026-11-10** Health keeps itself honest and the repo lean <!-- reviewed 25886c54 -->
  - Every health rule has a negative control that proves it can fire; the check flags a land test run over its time budget and names the slowest rows to move to nightly; and it flags stale worktrees and branches that exist only on this machine.
- HLT-8: **Reviewed 2026-11-10** Triage <!-- reviewed 6ae689c8 -->
  - Open findings are shown per feature with their kind, age and count, so I can see where the repo is weakest.
  - When I close a batch (for example "won't fix the docs findings older than a week"), each is closed with my words as the reason, and the review doesn't refile it unless the evidence changes.

### Non-functional
- HLT-1: **Reviewed 2026-11-10** Deterministic and read-only <!-- reviewed 3dd44499 -->
  - The rule check gives the same answer twice on an unchanged repo and changes nothing; only file writes, and only GitHub issues.
- HLT-7: **Reviewed 2026-11-10** Fast check <!-- reviewed 4a290e53 -->
  - The rule check without controls finishes in under 60 seconds.
- HLT-9: **Reviewed 2026-11-10** Evidence or nothing <!-- reviewed 43ca94e2 -->
  - Every review finding names its feature and cites its evidence (a page and requirement ID, a file and line, a test row or an issue link); a finding without evidence is dropped, and nothing is filed twice.

## Non-goals
- It never changes code, pages or requirements; it reports and files issues.
- The review's suggestions never change the verdict.
- It prints the commands that remove stale worktrees and branches and never runs them.

## Success metrics
- Two rule checks on an unchanged repo print the same lines.
- After the first full review, every feature's findings are issues tagged with that feature, each with its evidence, and none is a duplicate.
- The verdict is never green while a rule could not be read.

## Tests

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| [size-fail](Tests#t-size-fail) | requirement | HLT-2 | Given a script over 20 KB, when health runs, then it is a FAIL with a fix. | PASS 2026-11-12 |
| [stale-page-row](Tests#t-stale-page-row) | requirement | HLT-2 | Given a stale wiki page, when health runs, then it shows as a docs row naming the page. | PASS 2026-11-12 |
| [no-row-fail](Tests#t-no-row-fail) | requirement | HLT-2 | Given a criterion with no test row, when health runs, then it is a FAIL. | PASS 2026-11-12 |
| [defect-health](Tests#t-defect-health) | requirement | HLT-2 | Given a closed issue or finding with no defect test, when health runs, then it is flagged. | PASS 2026-11-12 |
| [cost-time-warn](Tests#t-cost-time-warn) | requirement | HLT-2 | Given a goal over its time budget, when health runs, then it is a Cost warning naming its slowest steps. | PASS 2026-11-12 |
| [cost-unread-tokens](Tests#t-cost-unread-tokens) | requirement | HLT-2 | Given no tokens recorded, when the Performance rule runs, then it prints INFO and leaves the token check out, never red. | PASS 2026-11-12 |
| [hlt2-twelve-groups](Tests#t-hlt2-twelve-groups) | requirement | HLT-2 | Given a repo, when health checks it, then it runs exactly the twelve groups plus Mine, each heading with its angle, and every rule's negative control fires. | not run |
| [health-not-enforced-warn](Tests#t-health-not-enforced-warn) | requirement | HLT-2 | Given a Reviewed requirement with no test, when health runs within 7 days of its Reviewed date, then it warns as not enforced. | PASS 2026-11-10 |
| [health-not-enforced-fail](Tests#t-health-not-enforced-fail) | requirement | HLT-2 | Given a Reviewed requirement with no test for 8 days, when health runs, then it fails. | PASS 2026-11-10 |
| [hlt2-defect-exempt-health](Tests#t-hlt2-defect-exempt-health) | requirement | HLT-2 | Given a closed issue labelled health or backlog, when Traceability checks defect tests, then it is exempt; a closed bug without a defect test still fails. | not run |
| [aut-prompt-warns](Tests#t-aut-prompt-warns) | requirement | HLT-2 | Given an installed scheduled-task prompt that holds steps beyond the Runbook pointer, when health checks the Adoption group, then it warns. | not run |
| [machine-local-health-warn](Tests#t-machine-local-health-warn) | requirement | HLT-2 | Given a red proof owed to another machine for 9 days, when health checks, then it warns and never fails. | not run |
| [unread-not-green](Tests#t-unread-not-green) | requirement | HLT-3 | Given a health rule that cannot be read, when health runs, then it is never shown green. | PASS 2026-11-12 |
| [report-header](Tests#t-report-header) | requirement | HLT-3 | Given a repo with findings in several groups, when health check runs, then the report header names every group it ran and the one it skipped. | PASS 2026-11-10 |
| [no-token-would](Tests#t-no-token-would) | requirement | HLT-4 | Given no token and no --live flag, when health previews its findings, then it prints only WOULD lines and writes nothing. | PASS 2026-11-12 |
| [fixed-closes](Tests#t-fixed-closes) | requirement | HLT-4 | Given a finding with an open issue, when the finding is fixed, then its issue is closed. | PASS 2026-11-12 |
| [repeat-no-second](Tests#t-repeat-no-second) | requirement | HLT-4 | Given a finding with an open issue, when the finding repeats, then no second issue is opened. | PASS 2026-11-12 |
| [unread-closes-none](Tests#t-unread-closes-none) | requirement | HLT-4 | Given a rule that could not be read, when health runs, then none of its issues are closed. | PASS 2026-11-12 |
| [preview-writes-nothing](Tests#t-preview-writes-nothing) | requirement | HLT-4 | Given findings in several groups, when health preview runs, then it lists each issue it would open, update, close or reopen with its tag and makes no write call. | PASS 2026-11-10 |
| [file-one-group](Tests#t-file-one-group) | requirement | HLT-4 | Given open issues in several groups, when health files only the docs group, then only the docs issue is closed and no other group's issue changes. | PASS 2026-11-10 |
| [hlt4-feature-milestones](Tests#t-hlt4-feature-milestones) | requirement | HLT-4 | Given findings about a feature and about none, when they are previewed and filed, then each is a tagged issue on no milestone, a repeat updates, a fix closes, a return reopens, an old marker moves, and an issue that names the subject is linked once instead of duplicated. | not run |
| [backlog-item-home](Tests#t-backlog-item-home) | requirement | HLT-4 | Given a size finding about the Calc feature, when health files it, then the issue is labelled backlog on Backlog: Calc, and a repeat opens no second issue and leaves a milestone the owner chose. | not run |
| [backlog-defect-home](Tests#t-backlog-defect-home) | requirement | HLT-4 | Given a FAIL finding, when health files it, then the issue is labelled defect and sits on no milestone. | not run |
| [judge-section-format](Tests#t-judge-section-format) | requirement | HLT-5 | Given the judge, when it runs, then it prints its three reviews in a section marked as suggestions. | PASS 2026-11-12 |
| [judge-verdict-unchanged](Tests#t-judge-verdict-unchanged) | requirement | HLT-5 | Given a failing or garbage judge, when health runs, then the verdict and exit code are unchanged. | PASS 2026-11-12 |
| [judge-needs-you](Tests#t-judge-needs-you) | requirement | HLT-5 | Given suggested criterion wording, when the board is printed, then it is listed under Needs you for the owner to apply. | PASS 2026-11-12 |
| [hlt5-review-evidence](Tests#t-hlt5-review-evidence) | requirement | HLT-5 | Given a judge that answers with good and unverifiable citations, when review runs, then each finding names its feature, angle and evidence, an unverifiable one is dropped and counted, and nothing is written. | not run |
| [judge-session-first](Tests#t-judge-session-first) | requirement | HLT-5 | Given a session runs the review, when the judge is needed, then the session answers it (the prompt handed over, its saved reply used), claude -p never runs, and the report says judge: session. | not run |
| [judge-claude-p-fallback](Tests#t-judge-claude-p-fallback) | requirement | HLT-5 | Given no session, as in the scheduled GitHub Actions run, when the review needs the judge, then it runs judge_command (claude -p) and the report says judge: claude -p (no session). | not run |
| [hlt6-controls-fire](Tests#t-hlt6-controls-fire) | requirement | HLT-6 | Given every health rule, when health check runs its controls, then each rule's negative control makes it fire. | PASS 2026-11-10 |
| [hlt6-cannot-fire](Tests#t-hlt6-cannot-fire) | requirement | HLT-6 | Given a rule broken so it can never report, when health check runs its controls, then that rule is reported as one that cannot fire, with how to look. | PASS 2026-11-10 |
| [hlt6-refused](Tests#t-hlt6-refused) | requirement | HLT-6 | Given a new rule with no negative control, when health.py starts, then it refuses before any report and names the control to add. | PASS 2026-11-10 |
| [hlt6-test-time](Tests#t-hlt6-test-time) | requirement | HLT-6 | Given a land lane recorded over test_budget_minutes, when health check runs, then it warns and names the slowest rows and scripts to move to nightly. | PASS 2026-11-10 |
| [hlt6-test-quiet](Tests#t-hlt6-test-quiet) | requirement | HLT-6 | Given a land lane within test_budget_minutes, when health check runs, then the test-time rule passes. | PASS 2026-11-10 |
| [hlt6-run-times](Tests#t-hlt6-run-times) | requirement | HLT-6 | Given a regression run, when it saves its lane record, then the record holds each row's time and the total. | PASS 2026-11-10 |
| [hlt6-judge-time](Tests#t-hlt6-judge-time) | requirement | HLT-6 | Given a lane record, when the judge gathers its facts, then its performance review sees the land lane's total and slowest rows as well as tokens. | PASS 2026-11-10 |
| [hlt6-worktrees](Tests#t-hlt6-worktrees) | requirement | HLT-6 | Given a loop worktree no live goal names, when health check runs, then it lists it with the command that removes it, and leaves a live goal's worktree alone. | PASS 2026-11-10 |
| [hlt6-branches](Tests#t-hlt6-branches) | requirement | HLT-6 | Given a local branch on no remote older than stale_branch_days, when health check runs, then it lists it with a quoted delete and a data-loss warning, and leaves a young branch alone. | PASS 2026-11-10 |
| [hlt6-removes-nothing](Tests#t-hlt6-removes-nothing) | requirement | HLT-6 | Given stale worktrees and branches, when health check runs, then nothing is removed. | PASS 2026-11-10 |
| [hlt6-clean-quiet](Tests#t-hlt6-clean-quiet) | requirement | HLT-6 | Given no stale worktree or branch, when health check runs, then both rules pass. | PASS 2026-11-10 |
| [hlt6-never-filed](Tests#t-hlt6-never-filed) | requirement | HLT-6 | Given stale worktrees, when health previews the hygiene group, then no test-time, worktree or branch row would be filed. | PASS 2026-11-10 |
| [hlt6-controls-lean](Tests#t-hlt6-controls-lean) | requirement | HLT-6 | Given every rule and a stale loop worktree, when health checks, then each control fires and the worktree is flagged with the command that removes it, which health never runs. | not run |
| [hlt8-triage](Tests#t-hlt8-triage) | requirement | HLT-8 | Given open health findings, when triage runs, then it lists them per feature by kind, count and age, and a closed batch carries the owner's words and is not refiled until its evidence changes. | PASS 2026-11-10 |
| [hlt8-triage-one-issue](Tests#t-hlt8-triage-one-issue) | requirement | HLT-8 | Given two open health findings, when triage --close --issue N runs with --yes, then only that issue closes, with the owner's words, and a number that is not an open finding closes nothing. | not run |
| [same-lines](Tests#t-same-lines) | requirement | HLT-1 | Given an unchanged repo, when health runs twice, then both runs print the same lines. | PASS 2026-11-12 |
| [check-writes-nothing](Tests#t-check-writes-nothing) | requirement | HLT-1 | Given a repo, when the health check runs, then it writes no file and makes no commit. | PASS 2026-11-12 |
| [hlt1-same-answer](Tests#t-hlt1-same-answer) | requirement | HLT-1 | Given an unchanged repo, when health checks it twice, then both print the same lines and no file changes. | not run |
| [hlt7-fast-check](Tests#t-hlt7-fast-check) | requirement | HLT-7 | Given this repo, when health checks it without controls, then it finishes in under 60 seconds, and a check past 60 seconds warns. | PASS 2026-11-12 |
| [hlt9-evidence-or-nothing](Tests#t-hlt9-evidence-or-nothing) | requirement | HLT-9 | Given review findings, when they are checked and filed, then each names its feature and cited evidence, one with no verifiable evidence is dropped, and nothing is filed twice. | PASS 2026-11-10 |
| [hlt9-located-evidence](Tests#t-hlt9-located-evidence) | requirement | HLT-9 | Given a judge finding, when its citations are checked, then only a file and line or a test row keeps it; a requirement id, an issue link or a file with no line alone is dropped. | not run |
| [hlt9-review-recheck](Tests#t-hlt9-review-recheck) | requirement | HLT-9 | Given an open review issue the answered review no longer raises, when file runs, then it is closed; an unanswered judge closes nothing. | not run |
| [health-tokens-124](Tests#t-health-tokens-124) | defect | [#124](https://github.com/jcl2018/agent-workflow-template/issues/124) closed (2026-11-11) | Given goals that predate token recording and done lines from before adoption, when health and sync run, then neither keeps the repo red. | not run |
| [health-unreviewed-warn-issue-118](Tests#t-health-unreviewed-warn-issue-118) | defect | [#118](https://github.com/jcl2018/agent-workflow-template/issues/118) closed (2026-11-11) | Given an Unreviewed requirement with no test, when health runs, then it warns and never fails. | PASS 2026-11-10 |
| [health-docs-159](Tests#t-health-docs-159) | defect | [#159](https://github.com/jcl2018/agent-workflow-template/issues/159) closed (2026-11-11) | Given the health skill's docs, when they are read, then they describe check's twelve groups, review, filing and triage, and no stale run chart. | not run |
| [judge-cause-158](Tests#t-judge-cause-158) | defect | [#158](https://github.com/jcl2018/agent-workflow-template/issues/158) closed (2026-11-11) | Given a judge command that fails, when review runs, then JUDGE UNAVAILABLE names the command's last output and stderr lines. | not run |
