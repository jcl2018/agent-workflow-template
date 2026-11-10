<!-- workflow-docs -->
# Automation

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/10

Review: **Reviewed 2026-11-10** <!-- prd P=9fba2846 R=f97d5503 N=d6d10cdd M=dad3088c U=4dbbe9de -->

## Problem

Skills: `workflow-health` and `workflow-regression`. For the owner of a repo that uses the loop: things break between my sessions, and I find out only when I next open one.
Every few hours the full regression suite and the health check should run on their own, and every problem they find should become an issue on its feature's milestone.
After each round one email should tell me what ran, what broke, what got fixed and what to ask the agent, without opening GitHub.

## Usage

- `/workflow-setup` writes the workflows: `.github/workflows/regression.yml` on `regression_cron`, `.github/workflows/health.yml` on `health_cron` (every 4 hours by default, health 30 minutes after regression) and `.github/workflows/mail-test.yml` (by hand only). Start any of them by hand from the Actions tab. A schedule change in `.loop/config.json` takes effect when the workflow is written again (`/workflow-health workflow`, `/workflow-regression workflow`), and a run whose schedule differs from the config says so.
- Set `regression_cron` or `health_cron` to `off` to turn that routine off: its scheduled runs write nothing and say it is off; a run you start by hand (or a release tag, for regression) still runs. Set `digest_mail` to `off` to stop the email only.
- A failing test opens or updates one issue labelled `defect` (and `regression`), naming the test, the feature and the requirement it guards, on that feature's milestone (a `.loop/docs.tsv` page; Backlog when the test's page is none); it closes itself when the test passes again. Health files its findings as `health:<group>` issues for the groups a runner can read (size, criteria, docs), on the milestone of the feature whose path holds the finding (the longest path in `.loop/docs.tsv` wins), Backlog when none fits. The automation places an issue once and moves it only while it is still where it put it, so an issue you move (Backlog included) stays.
- The judge runs in the health run only when the secret named by `judge_env` (default `ANTHROPIC_API_KEY`) is set and the runner has `judge_command`'s program (`judge_setup` can install it; it runs with the key unset, but the step still holds the key, so put only trusted commands there); otherwise the run says why it skipped.
- After each health run, one comment on the pinned `Automation digest` issue lists what ran, the round's cost and the email's state, then per milestone the new, still-open and fixed issues, each open one with its link and the request to give the agent. It mentions `digest_owner` (default: the repo owner). The Email the digest step then mails that same comment, at most once per round.
- The round's cost is job time: the round's regression run plus this health run so far, through the digest (both workflows have one job). Over 45 minutes it is flagged `OVER 45 min` in the comment, the run summary and a warning; slow a routine down or turn it off. Beside it, the Actions minutes of runs started since the last round (each job rounded up to a minute; a run still going at a round's cut-off is counted by the round in which it started).

### Email quickstart

1. Pick a sender. Cloudflare (default): a domain onboarded to Cloudflare Email Sending, and an API token with the Email Sending send permission. SMTP: for Gmail, turn on 2-step verification and make an app password; set `"digest_mail": "smtp"` in `.loop/config.json` (`smtp_host` defaults to smtp.gmail.com, `smtp_port` to 465; 587 uses STARTTLS).
2. Add the secrets (Settings, Secrets and variables, Actions, or `gh`). `DIGEST_TO` holds one address, `DIGEST_FROM` an address on the onboarded domain (or your Gmail address).
   - Cloudflare: `gh secret set DIGEST_TO`, `gh secret set DIGEST_FROM`, `gh secret set CLOUDFLARE_ACCOUNT_ID`, `gh secret set CLOUDFLARE_EMAIL_TOKEN`.
   - SMTP: `gh secret set DIGEST_TO`, `gh secret set DIGEST_FROM`, `gh secret set DIGEST_SMTP_USER`, `gh secret set DIGEST_SMTP_PASSWORD`.
3. Run `gh workflow run mail-test.yml` (or Actions, mail-test, Run workflow; `/workflow-health mail test` sends one from your machine with the same secrets in its environment). The step prints `MAIL: test sent (MAIL_SENT)` and the mail arrives within a minute; anything else prints one line with a code and a Fix (below).

The address and keys live only in those secrets: the digest step gets three true/false values, only the email step and the mail-test job read them, and no line, issue or comment ever shows their values. The digest comment's `email` row says `not set up` (with the secrets still missing), `off`, or the previous round's `sent`, `not sent` or `may have been sent`.

### Mail and digest codes

| Code | Means | Do |
|---|---|---|
| `MAIL_SENT` | Sent (the test, or this round's mail) | Nothing |
| `MAIL_ALREADY` | This round's mail went out before (a rerun) | Nothing |
| `MAIL_OFF` | `digest_mail` is off (the test fails on it) | Set `digest_mail` to cloudflare or smtp to mail |
| `MAIL_NOT_SET_UP` | No mail secret is set, so nothing was sent or written | Follow the quickstart to get mail |
| `MAIL_SECRETS` | Some secrets are set and some are missing (named) | `gh secret set NAME` for each, then rerun |
| `MAIL_SETTING` | A bad `digest_mail`, `smtp_port` or test setting | Fix `.loop/config.json` as the line says |
| `MAIL_TEST_URL` | A test-only server address was set outside a test | Unset `DIGEST_MAIL_API` |
| `MAIL_STALE` | This run is older than the round on the digest issue (a late rerun), so there is nothing to mail | Nothing |
| `MAIL_NO_COMMENT` | No digest comment for this run (the digest step failed or didn't post) | See the Post the digest step; rerun once it has posted |
| `MAIL_GH` | gh couldn't read the digest issue or its comments; nothing was sent | Rerun the job |
| `MAIL_MARK` | Couldn't mark the round as sending; nothing was sent | Rerun the job |
| `MAIL_REFUSED` | The provider refused it (bad token, sender domain, SMTP login); nothing was sent | Fix what the line names, then rerun |
| `MAIL_CLEAR_FAILED` | Refused, and the sending mark couldn't be cleared | Delete the word `mailing` from the comment's last line, then rerun |
| `MAIL_UNKNOWN` | The mail may have been accepted (a 5xx, a timeout after sending, a crash mid-send); it stays marked so no rerun sends twice | Check your inbox; if none arrived, delete the word `mailing` from that comment's last line and rerun |
| `MAIL_MARKED_LATE` | Sent, but the comment couldn't be marked mailed; it stays marked sending, so no rerun sends again | Nothing |
| `MAIL_FAILED` | An unexpected error (one line with the file and line, never a traceback) | Rerun; if it fails again, report the line |
| `DIGEST_ALREADY` | This run's digest is already posted | Nothing |
| `DIGEST_REPAIRED` | An earlier attempt posted the comment but couldn't save the state; the state was repaired from it, nothing posted | Nothing |
| `DIGEST_STALE` | An older run was rerun after a newer round posted; nothing posted | Nothing |
| `ROUND_UNREAD` | The round's cost couldn't be read (the reason follows) | Nothing; the next round reads it again |
| `FILE_FAILED` | A regression issue write failed; the step fails after the last row | Rerun the regression workflow |
| `STALE_WORKFLOW` | A workflow file is older than the skills (each health run warns) | `/workflow-health workflow`, then commit |
| `NOT_OURS` | A workflow file wasn't written by automation.py, so it is never checked or rewritten | Merge by hand if you want the new steps |

### Upgrading and rolling back

Updating the skills from a newer package doesn't rewrite the workflows. After an update, ask for `/workflow-health workflow` and `/workflow-regression workflow`, review the diff, commit and push, set the secrets, and run the Mail test; until then every health run warns `STALE_WORKFLOW`. The digest issue's state now reads `run=... open=N:M`; a checkout from before this change can't read it, so to roll back, close the Automation digest issue (the old code makes a new one).

## Requirements

- AUT-1: **Reviewed 2026-11-10** Routines run in GitHub Actions. Every routine runs as a GitHub Actions workflow on a schedule set in the repo's config, every few hours by default, and I can also start it by hand from the Actions tab; each run shows its report in the run summary. <!-- reviewed 0b9dc6bd -->
- AUT-2: **Reviewed 2026-11-10** Regression every few hours. The full regression suite runs on the schedule (every 4 hours by default) and on every release. A failing test opens or updates one issue labeled defect, on the milestone of the feature it guards, naming the test and the requirement; it closes by itself when the test passes again. <!-- reviewed a815178c -->
- AUT-3: **Reviewed 2026-11-10** Health every few hours. The health check runs on the schedule, after regression, with all its rule groups, and the repo review too when an agent key is set as a secret (otherwise skipped, and the report says so). Every finding becomes one issue tagged with its group, on the milestone of the feature it is about (Backlog only when none fits), updated, closed or reopened as things change, never duplicated. <!-- reviewed b09dc036 -->
- AUT-4: **Reviewed 2026-11-10** A digest by email. After each round, one email goes to the address I set: what ran and its results, then the new, still-open and fixed issues grouped by feature, each with its link and the request to give the agent to fix it. The same digest is also posted as one comment on a pinned Automation digest issue. <!-- reviewed 6ec601f1 -->
- AUT-5: **Reviewed 2026-11-10** Under my control. Each routine can be turned off or rescheduled in one setting, and without the secrets it needs a routine runs but writes nothing and says what is missing. <!-- reviewed dbcd5835 -->
- AUT-6: **Reviewed 2026-11-10** Private address. The email address and the mail key live only in GitHub secrets, never in the repo, logs, issues or the digest comment. <!-- reviewed db254bd2 -->
- AUT-7: **Reviewed 2026-11-10** Bounded cost. A round finishes within 45 minutes, and the run summary shows its Actions minutes, so I can slow the schedule if it costs too much. <!-- reviewed 6e60052e -->

## Non-goals

- The scheduled routines never push, merge or release; they only write issues, labels, comments, run summaries and the digest email.
- No chat or webhook notifications; email and GitHub only.

## Success metrics

- After each scheduled round, one digest email arrives and every failing test or finding has exactly one open issue on its feature's milestone.
- With a routine set to off, its runs write no issue, label, comment or email.

## Tests

#### AUT-1

Routines run in GitHub Actions. Every routine runs as a GitHub Actions workflow on a schedule set in the repo's config, every few hours by default, and I can also start it by hand from the Actions tab; each run shows its report in the run summary.

- Given the nightly run, when it ends, then it writes a results table to the job summary. — [ci-summary](../../.loop/regression.tsv), requirement, guards AUT-1, both, PASS 2026-11-10, seen failing 2026-11-07
- Given a changed schedule setting, when the workflow is rewritten, then the Actions schedule changes. — [schedule-setting](../../.loop/regression.tsv), requirement, guards AUT-1, both, PASS 2026-11-10, seen failing 2026-11-08
- Given health_cron in the config, when the health workflow is written, then it runs on that schedule and by hand, one run at a time. — [aut-health-schedule](../../.loop/regression.tsv), requirement, guards AUT-1, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a config schedule that differs from the written workflow, when the routine runs, then its summary names the difference and the command that fixes it. — [aut-schedule-mismatch](../../.loop/regression.tsv), requirement, guards AUT-1, both, PASS 2026-11-10, seen failing 2026-11-10
- Given this repo's config, when the health workflow is written, then it equals the committed workflow. — [aut-health-workflow-current](../../.loop/regression.tsv), requirement, guards AUT-1, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a regression schedule that differs from the config, when the routine runs, then it names the difference and the command that fixes it. — [aut-regression-schedule-mismatch](../../.loop/regression.tsv), requirement, guards AUT-1, both, PASS 2026-11-10, seen failing 2026-11-10
- Given setup in a repo, when it plans the workflows, then it offers the health workflow only when the workflow-health skill is in the repo. — [aut-setup-health-only-with-skill](../../.loop/regression.tsv), requirement, guards AUT-1, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a workflow older than the skills, when a health run starts, then it warns with the command that rewrites it and still runs. — [aut-email-upgrade](../../.loop/regression.tsv), requirement, guards AUT-1, both, PASS 2026-11-10, seen failing 2026-11-10

#### AUT-2

Regression every few hours. The full regression suite runs on the schedule (every 4 hours by default) and on every release. A failing test opens or updates one issue labeled defect, on the milestone of the feature it guards, naming the test and the requirement; it closes by itself when the test passes again.

- Given a failing test, when the scheduled regression runs, then one issue labelled defect opens, naming the test, the feature and the requirement it guards. — [aut-defect-issue](../../.loop/regression.tsv), requirement, guards AUT-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given an open failing-test issue without the defect label, when the test fails again, then the issue gains the defect label. — [aut-old-issue-relabel](../../.loop/regression.tsv), requirement, guards AUT-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given the issues cannot be read, when the scheduled regression runs, then it changes no issue rather than open duplicates. — [aut-issue-list-fails](../../.loop/regression.tsv), requirement, guards AUT-2, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a failing test, when the scheduled regression runs, then its defect issue goes on the milestone of the feature it guards, the suite runs every 4 hours and on every release tag, and a failed filing fails the run. — [aut-email-regression](../../.loop/regression.tsv), requirement, guards AUT-2, both, PASS 2026-11-10, seen failing 2026-11-10

#### AUT-3

Health every few hours. The health check runs on the schedule, after regression, with all its rule groups, and the repo review too when an agent key is set as a secret (otherwise skipped, and the report says so). Every finding becomes one issue tagged with its group, on the milestone of the feature it is about (Backlog only when none fits), updated, closed or reopened as things change, never duplicated.

- Given no agent key secret, when the scheduled health runs, then the judge is skipped and the report says so. — [aut-judge-no-secret](../../.loop/regression.tsv), requirement, guards AUT-3, both, PASS 2026-11-10, seen failing 2026-11-10
- Given the secret but no judge program on the runner, when the scheduled health runs, then the judge is skipped and the report names the setting to fix. — [aut-judge-no-program](../../.loop/regression.tsv), requirement, guards AUT-3, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a repo without a Backlog milestone, when the scheduled health files findings, then it makes the milestone first. — [aut-backlog-milestone](../../.loop/regression.tsv), requirement, guards AUT-3, both, PASS 2026-11-10, seen failing 2026-11-10
- Given an agent key secret with another name, when the scheduled judge runs, then it receives the key under the name it reads. — [aut-secret-mapped](../../.loop/regression.tsv), requirement, guards AUT-3, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a judge that fails, when the scheduled health runs, then the step stays green and its report stays readable. — [aut-judge-fails-green](../../.loop/regression.tsv), requirement, guards AUT-3, both, PASS 2026-11-10, seen failing 2026-11-10
- Given health findings, when the scheduled health run files them, then each goes on its feature's milestone (Backlog when none fits), no open issue is duplicated, and an issue the owner moved stays. — [aut-email-file](../../.loop/regression.tsv), requirement, guards AUT-3, both, PASS 2026-11-10, seen failing 2026-11-10

#### AUT-4

A digest by email. After each round, one email goes to the address I set: what ran and its results, then the new, still-open and fixed issues grouped by feature, each with its link and the request to give the agent to fix it. The same digest is also posted as one comment on a pinned Automation digest issue.

- Given no digest issue yet, when the first round ends, then the Automation digest issue is created and pinned. — [aut-digest-create](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given open defect and health issues, when a round ends, then one comment mentions the owner and lists what ran, the new issues and a request per open issue. — [aut-digest-format](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a previous digest, when the next round ends, then its comment lists the new, still-open and fixed issues on the same digest issue. — [aut-digest-rounds](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a round already posted, when the same run is rerun, then nothing is posted twice. — [aut-digest-rerun](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given an issue whose title holds instructions, when the digest is written, then the request names the issue only by number and link. — [aut-digest-no-title](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a repo owned by an organisation, when the digest is written, then it says no one is notified and how to set digest_owner. — [aut-digest-org](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given the repo cannot pin another issue, when the first round ends, then it warns and still posts the digest. — [aut-digest-pin-fails](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a round whose digest comment fails, when the run ends, then no state is saved, so its rerun posts the comment. — [aut-digest-comment-fails](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given gh cannot list the issues, when a round ends, then the digest posts nothing and says why. — [aut-digest-list-fails](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given this run's digest comment, when the email step runs, then one mail with the comment's text goes out and the comment is marked mailed, and a rerun, a look-alike comment, a refusal or an unknown outcome never sends a second one. — [aut-email-mail](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a provider that throttles once, when the round's mail is sent, then it is retried once, and only when the provider cannot have accepted it. — [aut-email-retry](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given the mail secrets, when the Mail test workflow runs, then one test mail goes out touching no issue, and a missing secret or mail off fails the run. — [aut-email-test](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10
- Given open issues on milestones, when a round ends, then the digest groups the new, still-open and fixed issues by feature with the cost and email rows, and an older or repeated run never posts twice. — [aut-email-digest](../../.loop/regression.tsv), requirement, guards AUT-4, both, PASS 2026-11-10, seen failing 2026-11-10

#### AUT-5

Under my control. Each routine can be turned off or rescheduled in one setting, and without the secrets it needs a routine runs but writes nothing and says what is missing.

- Given a schedule setting that is not a cron time, when it is applied, then it is refused. — [bad-schedule-refused](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-08
- Given health_cron off, when the health workflow runs, then it writes nothing and says the routine is off. — [aut-health-off](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given regression_cron off, when the regression workflow runs, then it writes nothing and says the routine is off. — [aut-regression-off](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a routine set off, when its workflow is written, then it has no schedule and can still be started by hand. — [aut-off-by-hand](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a checkout without the skills, when the health workflow runs, then it says what is missing, fails, and writes nothing. — [aut-missing-skills](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given no token in the digest step, when it runs in Actions, then it says what is missing and writes nothing. — [aut-digest-no-token](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a judge_env that is not a secret name, when the health workflow is written, then it is refused. — [aut-secret-name](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given the scheduled workflows, when they are written, then neither pushes nor has write access to the repo's contents. — [aut-no-push](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a routine set off, when someone starts it by hand, then it still runs. — [aut-by-hand-runs](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a cron setting with anything but plain cron fields, when a workflow is written, then it is refused. — [aut-cron-check](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given regression_cron off, when its workflow is written, then it has no schedule and keeps its by-hand trigger. — [aut-regression-off-written](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a cron setting that ends in a newline, when a workflow is written, then it is refused. — [aut-cron-newline](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given a health workflow the tool didn't write, when the health workflow is written, then it is refused and left unchanged. — [aut-foreign-workflow](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given no token outside Actions, when the digest runs, then it prints the comment, says it is a dry run and writes nothing. — [aut-digest-dry-run](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given regression_cron off, when a release tag is pushed, then the regression run still runs the rows. — [aut-off-push-runs](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10
- Given regression_cron off, when someone starts the regression run by hand, then it still runs the rows. — [aut-off-dispatch-runs](../../.loop/regression.tsv), requirement, guards AUT-5, both, PASS 2026-11-10, seen failing 2026-11-10

#### AUT-6

Private address. The email address and the mail key live only in GitHub secrets, never in the repo, logs, issues or the digest comment.

- Given the mail secrets, when the email step runs or fails, then their values never reach a log, the summary, an issue or the digest comment, and without them it writes nothing and names what is missing. — [aut-email-secrets](../../.loop/regression.tsv), requirement, guards AUT-6, both, PASS 2026-11-10, seen failing 2026-11-10

#### AUT-7

Bounded cost. A round finishes within 45 minutes, and the run summary shows its Actions minutes, so I can slow the schedule if it costs too much.

- Given a round's runs, when the digest is written, then the run summary shows the round's job time and Actions minutes and flags a round over 45 minutes. — [aut-email-rounds](../../.loop/regression.tsv), requirement, guards AUT-7, both, PASS 2026-11-10, seen failing 2026-11-10
