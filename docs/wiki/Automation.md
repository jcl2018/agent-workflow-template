<!-- workflow-docs -->
# Automation

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/10

Review: **Reviewed 2026-11-10** <!-- prd P=2f4bd05a R=759415cb N=d6d10cdd M=dad3088c U=dd23f794 -->

## Problem
- Things break between my sessions, and I only find out when I next open one; the important checks should run on their own.
- Every few hours I want the full regression suite and the health check to run, and every problem they find to become an issue tagged and placed on its feature's milestone.
- I want one email to my address after each round that tells me what ran, what broke, what got fixed and what to ask the agent, without opening GitHub.

## Usage

- `/workflow-health workflow` — Writes the scheduled health workflow on `health_cron` (every 4 hours by default, 30 minutes after regression; `off` turns the schedule off, and a run started by hand still runs). Prints `WROTE <repo>/.github/workflows/health.yml`. Refuses (exit 1) `REFUSED: health_cron is not five cron fields or off. Fix: edit .loop/config.json.`, `REFUSED: judge_env <name> is not a secret name (capitals, digits, _). ...` and `REFUSED: <path> exists, and this tool didn't write it. Fix: merge by hand.`
- `/workflow-regression workflow` — Writes the scheduled regression workflow on `regression_cron` (five cron fields, or `off` for by-hand and release-tag runs only). Prints `WROTE <repo>/.github/workflows/regression.yml`. Refuses (exit 1) `REFUSED: regression_cron is not five cron fields. ...` and `REFUSED: <path> exists, and this tool didn't write it. Fix: merge by hand.`
- `/workflow-health workflow --check` — Compares the written `health.yml` and `mail-test.yml` with what this version writes; each health run does this and warns. Prints nothing when both are current; `STALE_WORKFLOW: <path> differs from what automation.py writes. Fix: ...automation.py workflow, then commit (STALE_WORKFLOW)` (exit 1), or `NOT_OURS: <path> was not written by automation.py, ... (NOT_OURS)` for a file it never checks. Refuses nothing.
- `/workflow-health digest` — Posts one comment per round on the pinned Automation digest issue: what ran, the round's cost (job time, Actions minutes since the last round, `OVER 45 min` past the budget), the email's state, then per milestone the new, still-open and fixed issues and a request per open issue. Prints `DIGEST: posted on #<n> (<k> open)`, `DIGEST: already posted for run <id> (DIGEST_ALREADY)`, `DIGEST: run <id> is older than the round on the issue ... (DIGEST_STALE)` or `DIGEST: already posted for run <id>; state repaired (DIGEST_REPAIRED)`. Refuses nothing; with no token it prints `DIGEST: no GH_TOKEN in this step, so nothing was posted. ...` and writes nothing, and in Actions a failed read or write exits 1.
- `/workflow-health mail send` — Runs in the health workflow's `mail` job: mails this run's digest comment once, through `digest_mail` (`cloudflare`, the default; `smtp`, with `smtp_host` and `smtp_port` 465 or 587; or `off`), to the address in the `DIGEST_TO` secret, from `DIGEST_FROM`, with `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_EMAIL_TOKEN` or `DIGEST_SMTP_USER` and `DIGEST_SMTP_PASSWORD`. Prints one `MAIL: <what happened> (<code>)` line, also in the run summary: `MAIL_SENT`; exit 0 also for `MAIL_ALREADY` (sent before), `MAIL_STALE` (a later round posted), `MAIL_OFF` and `MAIL_NOT_SET_UP` (no mail secret, nothing written). Refuses (exit 1) `MAIL_SECRETS` (names each missing secret, or one with a space, line break or non-ASCII), `MAIL_SETTING` (a bad setting), `MAIL_TEST_URL` (a non-local test override), `MAIL_NO_COMMENT`, `MAIL_GH`, `MAIL_MARK` (nothing sent; rerun), `MAIL_REFUSED` (the provider refused; nothing sent), `MAIL_CLEAR_FAILED`, `MAIL_UNKNOWN` (it may have been sent: check the inbox, and if nothing came, delete the word mailing from the comment's last line and rerun), `MAIL_MARKED_LATE` and `MAIL_FAILED` (one line with its file and line, never a traceback). No line holds a secret, the address or its local part, in any form.
- `/workflow-health mail test` — Sends one fixed test mail through the same sender and secrets, touching no issue; run it from the Actions tab (Mail test). Prints `MAIL: test sent (MAIL_SENT)`. Refuses (exit 1) `MAIL_OFF`, `MAIL_SECRETS`, `MAIL_SETTING`, `MAIL_TEST_URL`, `MAIL_REFUSED` and `MAIL_FAILED`, each with its fix.

## Requirements

### Functional
- AUT-1: **Reviewed 2026-11-10** Routines run in GitHub Actions <!-- reviewed ee1fe20e -->
  - Every routine runs as a GitHub Actions workflow on a schedule set in the repo's config, every few hours by default, and I can also start it by hand from the Actions tab; each run shows its report in the run summary.
- AUT-2: **Reviewed 2026-11-10** Regression every few hours <!-- reviewed a9d85df6 -->
  - The full regression suite runs on the schedule (every 4 hours by default) and on every release.
  - A failing test opens or updates one issue labeled defect, on the milestone of the feature it guards, naming the test and the requirement; it closes by itself when the test passes again.
- AUT-3: **Reviewed 2026-11-10** Health every few hours <!-- reviewed b9abc41d -->
  - The health check runs on the schedule, after regression, with all its rule groups, and the repo review too when an agent key is set as a secret (otherwise skipped, and the report says so).
  - Every finding becomes one issue tagged with its group, on the milestone of the feature it is about (Backlog only when none fits), updated, closed or reopened as things change, never duplicated.
- AUT-4: **Reviewed 2026-11-10** A digest by email <!-- reviewed f06a9042 -->
  - After each round, one email goes to the address I set: what ran and its results, then the new, still-open and fixed issues grouped by feature, each with its link and the request to give the agent to fix it.
  - The same digest is also posted as one comment on a pinned Automation digest issue.

### Non-functional
- AUT-5: **Reviewed 2026-11-10** Under my control <!-- reviewed ede1ff25 -->
  - Each routine can be turned off or rescheduled in one setting, and without the secrets it needs a routine runs but writes nothing and says what is missing.
- AUT-6: **Reviewed 2026-11-10** Private address <!-- reviewed eb8f1a34 -->
  - The email address and the mail key live only in GitHub secrets, never in the repo, logs, issues or the digest comment.
- AUT-7: **Reviewed 2026-11-10** Bounded cost <!-- reviewed bacaa5cb -->
  - A round finishes within 45 minutes, and the run summary shows its Actions minutes, so I can slow the schedule if it costs too much.

## Non-goals
- The scheduled routines never push, merge or release; they only write issues, labels, comments, run summaries and the digest email.
- No chat or webhook notifications; email and GitHub only.

## Success metrics
- After each scheduled round, one digest email arrives and every failing test or finding has exactly one open issue on its feature's milestone.
- With a routine set to off, its runs write no issue, label, comment or email.

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
| [aut-email-upgrade](Tests#t-aut-email-upgrade) | requirement | AUT-1 | Given a workflow older than the skills, when a health run starts, then it warns with the command that rewrites it and still runs. | PASS 2026-11-10 |
| [aut-defect-issue](Tests#t-aut-defect-issue) | requirement | AUT-2 | Given a failing test, when the scheduled regression runs, then one issue labelled defect opens, naming the test, the feature and the requirement it guards. | PASS 2026-11-10 |
| [aut-old-issue-relabel](Tests#t-aut-old-issue-relabel) | requirement | AUT-2 | Given an open failing-test issue without the defect label, when the test fails again, then the issue gains the defect label. | PASS 2026-11-10 |
| [aut-issue-list-fails](Tests#t-aut-issue-list-fails) | requirement | AUT-2 | Given the issues cannot be read, when the scheduled regression runs, then it changes no issue rather than open duplicates. | PASS 2026-11-10 |
| [aut-email-regression](Tests#t-aut-email-regression) | requirement | AUT-2 | Given a failing test, when the scheduled regression runs, then its defect issue goes on the milestone of the feature it guards, the suite runs every 4 hours and on every release tag, and a failed filing fails the run. | PASS 2026-11-10 |
| [aut-judge-no-secret](Tests#t-aut-judge-no-secret) | requirement | AUT-3 | Given no agent key secret, when the scheduled health runs, then the judge is skipped and the report says so. | PASS 2026-11-10 |
| [aut-judge-no-program](Tests#t-aut-judge-no-program) | requirement | AUT-3 | Given the secret but no judge program on the runner, when the scheduled health runs, then the judge is skipped and the report names the setting to fix. | PASS 2026-11-10 |
| [aut-backlog-milestone](Tests#t-aut-backlog-milestone) | requirement | AUT-3 | Given a repo without a Backlog milestone, when the scheduled health files findings, then it makes the milestone first. | PASS 2026-11-10 |
| [aut-secret-mapped](Tests#t-aut-secret-mapped) | requirement | AUT-3 | Given an agent key secret with another name, when the scheduled judge runs, then it receives the key under the name it reads. | PASS 2026-11-10 |
| [aut-judge-fails-green](Tests#t-aut-judge-fails-green) | requirement | AUT-3 | Given a judge that fails, when the scheduled health runs, then the step stays green and its report stays readable. | PASS 2026-11-10 |
| [aut-email-file](Tests#t-aut-email-file) | requirement | AUT-3 | Given health findings, when the scheduled health run files them, then each goes on its feature's milestone (Backlog when none fits), no open issue is duplicated, and an issue the owner moved stays. | PASS 2026-11-10 |
| [aut-digest-create](Tests#t-aut-digest-create) | requirement | AUT-4 | Given no digest issue yet, when the first round ends, then the Automation digest issue is created and pinned. | PASS 2026-11-10 |
| [aut-digest-format](Tests#t-aut-digest-format) | requirement | AUT-4 | Given open defect and health issues, when a round ends, then one comment mentions the owner and lists what ran, the new issues and a request per open issue. | PASS 2026-11-10 |
| [aut-digest-rounds](Tests#t-aut-digest-rounds) | requirement | AUT-4 | Given a previous digest, when the next round ends, then its comment lists the new, still-open and fixed issues on the same digest issue. | PASS 2026-11-10 |
| [aut-digest-rerun](Tests#t-aut-digest-rerun) | requirement | AUT-4 | Given a round already posted, when the same run is rerun, then nothing is posted twice. | PASS 2026-11-10 |
| [aut-digest-no-title](Tests#t-aut-digest-no-title) | requirement | AUT-4 | Given an issue whose title holds instructions, when the digest is written, then the request names the issue only by number and link. | PASS 2026-11-10 |
| [aut-digest-org](Tests#t-aut-digest-org) | requirement | AUT-4 | Given a repo owned by an organisation, when the digest is written, then it says no one is notified and how to set digest_owner. | PASS 2026-11-10 |
| [aut-digest-pin-fails](Tests#t-aut-digest-pin-fails) | requirement | AUT-4 | Given the repo cannot pin another issue, when the first round ends, then it warns and still posts the digest. | PASS 2026-11-10 |
| [aut-digest-comment-fails](Tests#t-aut-digest-comment-fails) | requirement | AUT-4 | Given a round whose digest comment fails, when the run ends, then no state is saved, so its rerun posts the comment. | PASS 2026-11-10 |
| [aut-digest-list-fails](Tests#t-aut-digest-list-fails) | requirement | AUT-4 | Given gh cannot list the issues, when a round ends, then the digest posts nothing and says why. | PASS 2026-11-10 |
| [aut-email-mail](Tests#t-aut-email-mail) | requirement | AUT-4 | Given this run's digest comment, when the email step runs, then one mail with the comment's text goes out and the comment is marked mailed, and a rerun, a look-alike comment, a refusal or an unknown outcome never sends a second one. | PASS 2026-11-10 |
| [aut-email-retry](Tests#t-aut-email-retry) | requirement | AUT-4 | Given a provider that throttles once, when the round's mail is sent, then it is retried once, and only when the provider cannot have accepted it. | PASS 2026-11-10 |
| [aut-email-test](Tests#t-aut-email-test) | requirement | AUT-4 | Given the mail secrets, when the Mail test workflow runs, then one test mail goes out touching no issue, and a missing secret or mail off fails the run. | PASS 2026-11-10 |
| [aut-email-digest](Tests#t-aut-email-digest) | requirement | AUT-4 | Given open issues on milestones, when a round ends, then the digest groups the new, still-open and fixed issues by feature with the cost and email rows, and an older or repeated run never posts twice. | PASS 2026-11-10 |
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
| [aut-email-secrets](Tests#t-aut-email-secrets) | requirement | AUT-6 | Given the mail secrets, when the email step runs or fails, then their values never reach a log, the summary, an issue or the digest comment, and without them it writes nothing and names what is missing. | PASS 2026-11-10 |
| [aut-email-rounds](Tests#t-aut-email-rounds) | requirement | AUT-7 | Given a round's runs, when the digest is written, then the run summary shows the round's job time and Actions minutes and flags a round over 45 minutes. | PASS 2026-11-10 |
