<!-- workflow-docs -->
# Automation

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/10

Review: **Unreviewed**

## Problem

Skills: `workflow-health` (`automation.py`) and `workflow-regression`. For the owner of a repo that uses the loop: regression and health run on a schedule in GitHub Actions, file what they find as GitHub issues, and send one digest through GitHub's own notifications, so nothing waits for a session to be open.

## Usage

- `/workflow-setup` writes both workflows: `.github/workflows/regression.yml` on `regression_cron` and `.github/workflows/health.yml` on `health_cron` (every 4 hours by default, health 30 minutes after regression). Start either by hand from the Actions tab. A schedule change in `.loop/config.json` takes effect when the workflow is written again, and a run whose schedule differs from the config says so.
- Set `regression_cron` or `health_cron` to `off` to turn that routine off: its next run writes nothing and says it is off.
- A failing test opens or updates one issue labelled `defect` (and `regression`, the tool's own label), naming the test, the feature and the requirement it guards; it closes itself when the test passes again. Health files its findings as `health:<group>` issues for the groups a runner can read (size, criteria, docs, hygiene).
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
