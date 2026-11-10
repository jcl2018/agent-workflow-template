<!-- workflow-docs -->
# Automation

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/10

Review: **Unreviewed**

## Problem

Skills: `workflow-health` (`automation.py`) and `workflow-regression`. For the owner of a repo that uses the loop: regression and health run on a schedule in GitHub Actions, file what they find as GitHub issues, and send one digest through GitHub's own notifications, so nothing waits for a session to be open.

## Usage

- `/workflow-setup` writes both workflows: `.github/workflows/regression.yml` on `regression_cron` and `.github/workflows/health.yml` on `health_cron` (every 4 hours by default, health 30 minutes after regression). Start either by hand from the Actions tab. A schedule change in `.loop/config.json` takes effect when the workflow is written again, and a run whose schedule differs from the config says so.
- Set `regression_cron` or `health_cron` to `off` to turn that routine off: its scheduled runs write nothing and say it is off; a run you start by hand (or a release tag, for regression) still runs.
- A failing test opens or updates one issue labelled `defect` (and `regression`, the tool's own label), naming the test, the feature and the requirement it guards; it closes itself when the test passes again. Health files its findings as `health:<group>` issues for the groups a runner can read (size, criteria, docs).
- The judge runs in the health run only when the secret named by `judge_env` (default `ANTHROPIC_API_KEY`) is set and the runner has `judge_command`'s program (`judge_setup` can install it; it runs with the key unset, but the step still holds the key, so put only trusted commands there); otherwise the run says why it skipped.
- After each health run, one comment on the pinned `Automation digest` issue lists what ran, the new, still-open and fixed issues, and a request per open issue to give the agent; it mentions `digest_owner` (default: the repo owner), so GitHub's notifications email it. Every-4-hours runs use Actions minutes: slow a routine down or turn it off in the config.

## Requirements

- AUT-1: **Reviewed 2026-11-08** Routines run in GitHub Actions. Every routine runs as a GitHub Actions workflow on a schedule set in the repo's config, every few hours by default, and I can also start it by hand from the Actions tab; each run shows its report in the run summary. <!-- reviewed 0b9dc6bd -->
- AUT-2: **Reviewed 2026-11-08** Regression on a schedule. The full regression suite runs on the schedule; a failing test opens or updates one GitHub issue labeled defect, linked to the test and the feature it guards, and it closes by itself when the test passes again. <!-- reviewed 94fdb343 -->
- AUT-3: **Reviewed 2026-11-08** Health on a schedule. The health check runs on the schedule and files its findings as issues tagged with their group, updating or closing them as things change; the judge runs too when the repo has an agent key set as a secret, otherwise it is skipped and the report says so. <!-- reviewed 12e2c23c -->
- AUT-4: **Reviewed 2026-11-08** A digest through GitHub notifications. After each scheduled round, one comment on a pinned Automation digest issue lists what ran and its results, the new, still-open and fixed issues, and for each open issue the request to give the agent to fix it; GitHub's built-in notifications email it to me, with no extra setup. <!-- reviewed dff75b7e -->
- AUT-5: **Reviewed 2026-11-08** Under my control. Each routine can be turned off or rescheduled in one setting, and without the secrets it needs a routine runs but writes nothing and says what is missing. <!-- reviewed dbcd5835 -->

## Non-goals

- The scheduled routines never push to the repo, merge, or release; they only write issues, labels, comments and run summaries.
- No notification service beyond GitHub's own (no email, chat or webhook setup).

## Success metrics

- After a scheduled round, the digest issue has one new comment for that round, and every failing test has exactly one open defect issue.
- With a routine set to off, its runs write no issue, label or comment.

## Tests

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| [ci-summary](Tests#t-ci-summary) | requirement | AUT-1 | Given the nightly run, when it ends, then it writes a results table to the job summary. | PASS 2026-11-10 |
| [schedule-setting](Tests#t-schedule-setting) | requirement | AUT-1 | Given a changed schedule setting, when the workflow is rewritten, then the Actions schedule changes. | PASS 2026-11-10 |
| [aut-health-schedule](Tests#t-aut-health-schedule) | requirement | AUT-1 | Given health_cron in the config, when the health workflow is written, then it runs on that schedule and by hand, one run at a time. | PASS 2026-11-10 |
| [aut-schedule-mismatch](Tests#t-aut-schedule-mismatch) | requirement | AUT-1 | Given a config schedule that differs from the written workflow, when the routine runs, then its summary names the difference and the command that fixes it. | PASS 2026-11-10 |
| [aut-health-workflow-current](Tests#t-aut-health-workflow-current) | requirement | AUT-1 | Given this repo's config, when the health workflow is written, then it equals the committed workflow. | PASS 2026-11-10 |
| [aut-regression-schedule-mismatch](Tests#t-aut-regression-schedule-mismatch) | requirement | AUT-1 | Given a regression schedule that differs from the config, when the routine runs, then it names the difference and the command that fixes it. | PASS 2026-11-10 |
| [aut-setup-health-only-with-skill](Tests#t-aut-setup-health-only-with-skill) | requirement | AUT-1 | Given setup in a repo, when it plans the workflows, then it offers the health workflow only when the workflow-health skill is in the repo. | PASS 2026-11-10 |
| [aut-defect-issue](Tests#t-aut-defect-issue) | requirement | AUT-2 | Given a failing test, when the scheduled regression runs, then one issue labelled defect opens, naming the test, the feature and the requirement it guards. | PASS 2026-11-10 |
| [aut-old-issue-relabel](Tests#t-aut-old-issue-relabel) | requirement | AUT-2 | Given an open failing-test issue without the defect label, when the test fails again, then the issue gains the defect label. | PASS 2026-11-10 |
| [aut-issue-list-fails](Tests#t-aut-issue-list-fails) | requirement | AUT-2 | Given the issues cannot be read, when the scheduled regression runs, then it changes no issue rather than open duplicates. | PASS 2026-11-10 |
| [aut-judge-no-secret](Tests#t-aut-judge-no-secret) | requirement | AUT-3 | Given no agent key secret, when the scheduled health runs, then the judge is skipped and the report says so. | PASS 2026-11-10 |
| [aut-judge-no-program](Tests#t-aut-judge-no-program) | requirement | AUT-3 | Given the secret but no judge program on the runner, when the scheduled health runs, then the judge is skipped and the report names the setting to fix. | PASS 2026-11-10 |
| [aut-backlog-milestone](Tests#t-aut-backlog-milestone) | requirement | AUT-3 | Given a repo without a Backlog milestone, when the scheduled health files findings, then it makes the milestone first. | PASS 2026-11-10 |
| [aut-secret-mapped](Tests#t-aut-secret-mapped) | requirement | AUT-3 | Given an agent key secret with another name, when the scheduled judge runs, then it receives the key under the name it reads. | PASS 2026-11-10 |
| [aut-judge-fails-green](Tests#t-aut-judge-fails-green) | requirement | AUT-3 | Given a judge that fails, when the scheduled health runs, then the step stays green and its report stays readable. | PASS 2026-11-10 |
| [aut-digest-create](Tests#t-aut-digest-create) | requirement | AUT-4 | Given no digest issue yet, when the first round ends, then the Automation digest issue is created and pinned. | PASS 2026-11-10 |
| [aut-digest-format](Tests#t-aut-digest-format) | requirement | AUT-4 | Given open defect and health issues, when a round ends, then one comment mentions the owner and lists what ran, the new issues and a request per open issue. | PASS 2026-11-10 |
| [aut-digest-rounds](Tests#t-aut-digest-rounds) | requirement | AUT-4 | Given a previous digest, when the next round ends, then its comment lists the new, still-open and fixed issues on the same digest issue. | PASS 2026-11-10 |
| [aut-digest-rerun](Tests#t-aut-digest-rerun) | requirement | AUT-4 | Given a round already posted, when the same run is rerun, then nothing is posted twice. | PASS 2026-11-10 |
| [aut-digest-no-title](Tests#t-aut-digest-no-title) | requirement | AUT-4 | Given an issue whose title holds instructions, when the digest is written, then the request names the issue only by number and link. | PASS 2026-11-10 |
| [aut-digest-org](Tests#t-aut-digest-org) | requirement | AUT-4 | Given a repo owned by an organisation, when the digest is written, then it says no one is notified and how to set digest_owner. | PASS 2026-11-10 |
| [aut-digest-pin-fails](Tests#t-aut-digest-pin-fails) | requirement | AUT-4 | Given the repo cannot pin another issue, when the first round ends, then it warns and still posts the digest. | PASS 2026-11-10 |
| [aut-digest-comment-fails](Tests#t-aut-digest-comment-fails) | requirement | AUT-4 | Given a round whose digest comment fails, when the run ends, then no state is saved, so its rerun posts the comment. | PASS 2026-11-10 |
| [aut-digest-list-fails](Tests#t-aut-digest-list-fails) | requirement | AUT-4 | Given gh cannot list the issues, when a round ends, then the digest posts nothing and says why. | PASS 2026-11-10 |
| [bad-schedule-refused](Tests#t-bad-schedule-refused) | requirement | AUT-5 | Given a schedule setting that is not a cron time, when it is applied, then it is refused. | PASS 2026-11-10 |
| [aut-health-off](Tests#t-aut-health-off) | requirement | AUT-5 | Given health_cron off, when the health workflow runs, then it writes nothing and says the routine is off. | PASS 2026-11-10 |
| [aut-regression-off](Tests#t-aut-regression-off) | requirement | AUT-5 | Given regression_cron off, when the regression workflow runs, then it writes nothing and says the routine is off. | PASS 2026-11-10 |
| [aut-off-by-hand](Tests#t-aut-off-by-hand) | requirement | AUT-5 | Given a routine set off, when its workflow is written, then it has no schedule and can still be started by hand. | PASS 2026-11-10 |
| [aut-missing-skills](Tests#t-aut-missing-skills) | requirement | AUT-5 | Given a checkout without the skills, when the health workflow runs, then it says what is missing, fails, and writes nothing. | PASS 2026-11-10 |
| [aut-digest-no-token](Tests#t-aut-digest-no-token) | requirement | AUT-5 | Given no token in the digest step, when it runs in Actions, then it says what is missing and writes nothing. | PASS 2026-11-10 |
| [aut-secret-name](Tests#t-aut-secret-name) | requirement | AUT-5 | Given a judge_env that is not a secret name, when the health workflow is written, then it is refused. | PASS 2026-11-10 |
| [aut-no-push](Tests#t-aut-no-push) | requirement | AUT-5 | Given the scheduled workflows, when they are written, then neither pushes nor has write access to the repo's contents. | PASS 2026-11-10 |
| [aut-by-hand-runs](Tests#t-aut-by-hand-runs) | requirement | AUT-5 | Given a routine set off, when someone starts it by hand, then it still runs. | PASS 2026-11-10 |
| [aut-cron-check](Tests#t-aut-cron-check) | requirement | AUT-5 | Given a cron setting with anything but plain cron fields, when a workflow is written, then it is refused. | PASS 2026-11-10 |
| [aut-regression-off-written](Tests#t-aut-regression-off-written) | requirement | AUT-5 | Given regression_cron off, when its workflow is written, then it has no schedule and keeps its by-hand trigger. | PASS 2026-11-10 |
| [aut-cron-newline](Tests#t-aut-cron-newline) | requirement | AUT-5 | Given a cron setting that ends in a newline, when a workflow is written, then it is refused. | PASS 2026-11-10 |
| [aut-foreign-workflow](Tests#t-aut-foreign-workflow) | requirement | AUT-5 | Given a health workflow the tool didn't write, when the health workflow is written, then it is refused and left unchanged. | PASS 2026-11-10 |
| [aut-digest-dry-run](Tests#t-aut-digest-dry-run) | requirement | AUT-5 | Given no token outside Actions, when the digest runs, then it prints the comment, says it is a dry run and writes nothing. | PASS 2026-11-10 |
| [aut-off-push-runs](Tests#t-aut-off-push-runs) | requirement | AUT-5 | Given regression_cron off, when a release tag is pushed, then the regression run still runs the rows. | PASS 2026-11-10 |
| [aut-off-dispatch-runs](Tests#t-aut-off-dispatch-runs) | requirement | AUT-5 | Given regression_cron off, when someone starts the regression run by hand, then it still runs the rows. | PASS 2026-11-10 |
