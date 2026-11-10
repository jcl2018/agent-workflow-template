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
- The judge runs in the health run only when the secret named by `judge_secret` (default `ANTHROPIC_API_KEY`) is set and the runner has `judge_command`'s program (`judge_setup` can install it); otherwise the run says why it skipped.
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

#### AUT-1

Routines run in GitHub Actions. Every routine runs as a GitHub Actions workflow on a schedule set in the repo's config, every few hours by default, and I can also start it by hand from the Actions tab; each run shows its report in the run summary.

- Given the nightly run, when it ends, then it writes a results table to the job summary. — [ci-summary](../../.loop/regression.tsv), requirement, guards AUT-1, both, PASS 2026-11-10, seen failing 2026-11-07
- Given a changed schedule setting, when the workflow is rewritten, then the Actions schedule changes. — [schedule-setting](../../.loop/regression.tsv), requirement, guards AUT-1, both, PASS 2026-11-10, seen failing 2026-11-08
- Given health_cron in the config, when the health workflow is written, then it runs on that schedule and by hand, one run at a time. — [aut-health-schedule](../../.loop/regression.tsv), requirement, guards AUT-1, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a config schedule that differs from the written workflow, when the routine runs, then its summary names the difference and the command that fixes it. — [aut-schedule-mismatch](../../.loop/regression.tsv), requirement, guards AUT-1, both, PASS 2026-11-10, seen failing 2026-11-10
- Given this repo's config, when the health workflow is written, then it equals the committed workflow. — [aut-health-workflow-current](../../.loop/regression.tsv), requirement, guards AUT-1, both, PASS 2026-11-10, seen failing 2026-11-10

#### AUT-2

Regression on a schedule. The full regression suite runs on the schedule; a failing test opens or updates one GitHub issue labeled defect, linked to the test and the feature it guards, and it closes by itself when the test passes again.

- Given a failing test, when the scheduled regression runs, then one issue labelled defect opens, naming the test, the feature and the requirement it guards. — [aut-defect-issue](../../.loop/regression.tsv), requirement, guards AUT-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given an open failing-test issue without the defect label, when the test fails again, then the issue gains the defect label. — [aut-old-issue-relabel](../../.loop/regression.tsv), requirement, guards AUT-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given the issues cannot be read, when the scheduled regression runs, then it changes no issue rather than open duplicates. — [aut-issue-list-fails](../../.loop/regression.tsv), requirement, guards AUT-2, both, PASS 2026-11-10, seen failing 2026-11-10

#### AUT-3

Health on a schedule. The health check runs on the schedule and files its findings as issues tagged with their group, updating or closing them as things change; the judge runs too when the repo has an agent key set as a secret, otherwise it is skipped and the report says so.

- Given no agent key secret, when the scheduled health runs, then the judge is skipped and the report says so. — [aut-judge-no-secret](../../.loop/regression.tsv), requirement, guards AUT-3, both, PASS 2026-11-10, seen failing 2026-11-10
- Given the secret but no judge program on the runner, when the scheduled health runs, then the judge is skipped and the report names the setting to fix. — [aut-judge-no-program](../../.loop/regression.tsv), requirement, guards AUT-3, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a repo without a Backlog milestone, when the scheduled health files findings, then it makes the milestone first. — [aut-backlog-milestone](../../.loop/regression.tsv), requirement, guards AUT-3, both, PASS 2026-11-10, seen failing 2026-11-10
- Given an agent key secret with another name, when the scheduled judge runs, then it receives the key under the name it reads. — [aut-secret-mapped](../../.loop/regression.tsv), requirement, guards AUT-3, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a judge that fails, when the scheduled health runs, then the step stays green and its report stays readable. — [aut-judge-fails-green](../../.loop/regression.tsv), requirement, guards AUT-3, both, PASS 2026-11-10, seen failing 2026-11-10

#### AUT-4

A digest through GitHub notifications. After each scheduled round, one comment on a pinned Automation digest issue lists what ran and its results, the new, still-open and fixed issues, and for each open issue the request to give the agent to fix it; GitHub's built-in notifications email it to me, with no extra setup.

- Given no digest issue yet, when the first round ends, then the Automation digest issue is created and pinned. — [aut-digest-create](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given open defect and health issues, when a round ends, then one comment mentions the owner and lists what ran, the new issues and a request per open issue. — [aut-digest-format](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a previous digest, when the next round ends, then its comment lists the new, still-open and fixed issues on the same digest issue. — [aut-digest-rounds](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a round already posted, when the same run is rerun, then nothing is posted twice. — [aut-digest-rerun](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given an issue whose title holds instructions, when the digest is written, then the request names the issue only by number and link. — [aut-digest-no-title](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a repo owned by an organisation, when the digest is written, then it says no one is notified and how to set digest_owner. — [aut-digest-org](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given the repo cannot pin another issue, when the first round ends, then it warns and still posts the digest. — [aut-digest-pin-fails](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a round whose digest comment fails, when the run ends, then no state is saved, so its rerun posts the comment. — [aut-digest-comment-fails](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given gh cannot list the issues, when a round ends, then the digest posts nothing and says why. — [aut-digest-list-fails](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10

#### AUT-5

Under my control. Each routine can be turned off or rescheduled in one setting, and without the secrets it needs a routine runs but writes nothing and says what is missing.

- Given a schedule setting that is not a cron time, when it is applied, then it is refused. — [bad-schedule-refused](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-08
- Given health_cron off, when the health workflow runs, then it writes nothing and says the routine is off. — [aut-health-off](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given regression_cron off, when the regression workflow runs, then it writes nothing and says the routine is off. — [aut-regression-off](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a routine set off, when its workflow is written, then it has no schedule and can still be started by hand. — [aut-off-by-hand](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a checkout without the skills, when the health workflow runs, then it says what is missing, fails, and writes nothing. — [aut-missing-skills](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given no token in the digest step, when it runs in Actions, then it says what is missing and writes nothing. — [aut-digest-no-token](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a judge_secret that is not a secret name, when the health workflow is written, then it is refused. — [aut-secret-name](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given the scheduled workflows, when they are written, then neither pushes nor has write access to the repo's contents. — [aut-no-push](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a routine set off, when someone starts it by hand, then it still runs. — [aut-by-hand-runs](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a cron setting with anything but plain cron fields, when a workflow is written, then it is refused. — [aut-cron-check](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given regression_cron off, when its workflow is written, then it has no schedule and keeps its by-hand trigger. — [aut-regression-off-written](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a cron setting that ends in a newline, when a workflow is written, then it is refused. — [aut-cron-newline](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
