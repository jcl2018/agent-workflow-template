<!-- workflow-docs -->
# Automation

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/10

Review: **Unreviewed**

## Problem
- Things break between my sessions, and I only find out when I next open one; the important checks should run on their own.
- Every few hours I want the full regression suite and the health check to run, and every problem they find to become an issue tagged with its feature.
- I want one email to my address after each round that tells me what ran, what broke, what got fixed and what to ask the agent, without opening GitHub.

## Usage

- `/workflow-health workflow` — Writes the scheduled health workflow on `health_cron` (every 4 hours by default, 30 minutes after regression; `off` turns the schedule off, and a run started by hand still runs); it has no milestone step. Prints `WROTE <repo>/.github/workflows/health.yml`. Refuses (exit 1) `REFUSED: health_cron is not five cron fields or off. Fix: edit .loop/config.json.`, `REFUSED: judge_env <name> is not a secret name (capitals, digits, _). ...` and `REFUSED: <path> exists, and this tool didn't write it. Fix: merge by hand.`
- `/workflow-regression workflow` — Writes the scheduled regression workflow on `regression_cron` (five cron fields, or `off` for by-hand and release-tag runs only). Prints `WROTE <repo>/.github/workflows/regression.yml`. Refuses (exit 1) `REFUSED: regression_cron is not five cron fields. ...` and `REFUSED: <path> exists, and this tool didn't write it. Fix: merge by hand.` A scheduled row that exits 77 (cannot run on this runner, such as the live Codex row) is recorded `SKIPPED` and opens no issue. The one local task per repo is named `<repo>-health-regression` (health and the full regression, every 4 hours or sooner); a repo recorded `regression_runs: mac`, public or private, runs its regression there and has no `regression.yml`, and `setup.py migration-check` names a missing, misnamed or slower task.
- `/workflow-health workflow --check` — Compares the written `health.yml` and `mail-test.yml` with what this version writes; each health run does this and warns. Prints nothing when both are current; `STALE_WORKFLOW: <path> differs from what automation.py writes. Fix: ...automation.py workflow, then commit (STALE_WORKFLOW)` (exit 1), or `NOT_OURS: <path> was not written by automation.py, ... (NOT_OURS)` for a file it never checks. Refuses nothing.
- `/workflow-health digest` — Posts one comment per round on the pinned Automation digest issue: what ran, the round's cost (job time, Actions minutes since the last round, `OVER 45 min` past the budget), the email's state, then per feature the new, still-open and fixed issues (with the milestone title beside an issue that has one) and a request per open issue. Prints `DIGEST: posted on #<n> (<k> open)`, `DIGEST: already posted for run <id> (DIGEST_ALREADY)`, `DIGEST: run <id> is older than the round on the issue ... (DIGEST_STALE)` or `DIGEST: already posted for run <id>; state repaired (DIGEST_REPAIRED)`. Refuses nothing; with no token it prints `DIGEST: no GH_TOKEN in this step, so nothing was posted. ...` and writes nothing, and in Actions a failed read or write exits 1. The digest lists up to 1000 open issues per label and prints `TRUNCATED` in its run summary when a listing reaches that limit, so a count is never silently cut off.
- `/workflow-health mail send` — Runs in the health workflow's `mail` job: mails this run's digest comment once, through `digest_mail` (`cloudflare`, the default; `smtp`, with `smtp_host` and `smtp_port` 465 or 587; or `off`), to the address in the `DIGEST_TO` secret, from `DIGEST_FROM`, with `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_EMAIL_TOKEN` or `DIGEST_SMTP_USER` and `DIGEST_SMTP_PASSWORD`. Prints one `MAIL: <what happened> (<code>)` line, also in the run summary: `MAIL_SENT`; exit 0 also for `MAIL_ALREADY` (sent before), `MAIL_STALE` (a later round posted), `MAIL_OFF` and `MAIL_NOT_SET_UP` (no mail secret, nothing written). Refuses (exit 1) `MAIL_SECRETS` (names each missing secret, or one with a space, line break or non-ASCII), `MAIL_SETTING` (a bad setting), `MAIL_TEST_URL` (a non-local test override), `MAIL_NO_COMMENT`, `MAIL_GH`, `MAIL_MARK` (nothing sent; rerun), `MAIL_REFUSED` (the provider refused; nothing sent), `MAIL_CLEAR_FAILED`, `MAIL_UNKNOWN` (it may have been sent: check the inbox, and if nothing came, delete the word mailing from the comment's last line and rerun), `MAIL_MARKED_LATE` and `MAIL_FAILED` (one line with its file and line, never a traceback). No line holds a secret, the address or its local part, in any form.
- `/workflow-health mail test` — Sends one fixed test mail through the same sender and secrets, touching no issue; run it from the Actions tab (Mail test). Prints `MAIL: test sent (MAIL_SENT)`. Refuses (exit 1) `MAIL_OFF`, `MAIL_SECRETS`, `MAIL_SETTING`, `MAIL_TEST_URL`, `MAIL_REFUSED` and `MAIL_FAILED`, each with its fix.

## Requirements

### Functional
- AUT-1: **Unreviewed** Routines run where they can run fully
  - Health runs on my Mac for every repo. Regression runs in GitHub Actions for a public repo and on my Mac for a private one.
  - Each routine runs on a schedule set in the repo's config (every 4 hours by default), and I can also start it by hand.
  - A Mac routine missed while the Mac sleeps runs once at next wake, regression before health.
  - Each run's report says whether it ran on my Mac or in GitHub Actions, naming no host or path.
- AUT-2: **Unreviewed** Regression every few hours
  - The full regression suite runs on the schedule (every 4 hours by default) and on every release, in GitHub Actions for a public repo and on my Mac for a private one; the report names every test it skipped and why.
  - A push or pull request runs only the tests its change affects, in the same place as the full suite.
  - No check this tool writes ever blocks a private repo's merge.
  - A failing test opens or updates one issue labeled defect, tagged with the feature it guards, naming the test and the requirement; it closes by itself when the test passes again.
- AUT-3: **Unreviewed** Health every few hours
  - Health never runs in GitHub Actions: it runs on my Mac on the schedule (every 4 hours by default), after the latest finished regression run, with all its rule groups; its report names that run with its commit and age, or says none finished, and says when health last ran.
  - The repo review always runs, using my own login on the Mac, with no API key secret; when the login has expired or can't be reached, the report says which and the next round tries again.
  - Every finding becomes one issue tagged with its group and its feature, updated, closed or reopened as things change, never duplicated.
- AUT-4: **Reviewed 2026-11-10** A digest by email <!-- reviewed f06a9042 -->
  - After each round, one email goes to the address I set: what ran and its results, then the new, still-open and fixed issues grouped by feature, each with its link and the request to give the agent to fix it.
  - The same digest is also posted as one comment on a pinned Automation digest issue.
- AUT-8: **Unreviewed** Every routine has a runbook an agent follows exactly
  - Each routine is listed in the routine registry with the feature page that owns it (health-round on Health, regression-round on Regression), and that page's Runbook section says what a full run is, the one output, the forbidden shortcuts and how to check the run was real.
  - An automation prompt for a routine reduces to "read the <page> Runbook and follow it exactly"; a scheduled run never sends a dry run, a fixture or a test mail in place of the real output.

### Non-functional
- AUT-5: **Reviewed 2026-11-10** Under my control <!-- reviewed ede1ff25 -->
  - Each routine can be turned off or rescheduled in one setting, and without the secrets it needs a routine runs but writes nothing and says what is missing.
- AUT-6: **Unreviewed** Private address
  - The email address and the mail key live only in a local secrets file outside git, kept where the repo review cannot reach it, read only by the local runner; never in the repo, logs, issues or the digest comment, and never printed. The same holds for the GitHub token the Mac uses.
- AUT-7: **Unreviewed** Bounded cost
  - A round finishes within 45 minutes (the 30-minute regression budget of Regression REG-7 plus 15 for health and the digest, health starting when regression has finished, not at a fixed offset), and each report shows the round's wall time and its pass and fail counts, plus its Actions minutes when it ran in GitHub Actions, so I can slow the schedule if it costs too much.

## Non-goals
- The scheduled routines never push, merge or release; they only write issues, labels, comments, run reports (an Actions run summary or a local report on my Mac) and the digest email.
- No chat or webhook notifications; email and GitHub only.

## Success metrics
- After each scheduled round, one digest email arrives and every failing test or finding has exactly one open issue tagged with its feature.
- With a routine set to off, its runs write no issue, label, comment or email.

## Tests

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| [ci-summary](Tests#t-ci-summary) | requirement | AUT-1 | Given the nightly run, when it ends, then it writes a results table to the job summary. | PASS 2026-11-12 |
| [schedule-setting](Tests#t-schedule-setting) | requirement | AUT-1 | Given a changed schedule setting, when the workflow is rewritten, then the Actions schedule changes. | PASS 2026-11-12 |
| [aut-regression-schedule-mismatch](Tests#t-aut-regression-schedule-mismatch) | requirement | AUT-1 | Given a regression schedule that differs from the config, when the routine runs, then it names the difference and the command that fixes it. | PASS 2026-11-12 |
| [aut-defect-issue](Tests#t-aut-defect-issue) | requirement | AUT-2 | Given a failing test, when the scheduled regression runs, then one issue labelled defect opens, naming the test, the feature and the requirement it guards. | PASS 2026-11-12 |
| [aut-old-issue-relabel](Tests#t-aut-old-issue-relabel) | requirement | AUT-2 | Given an open failing-test issue without the defect label, when the test fails again, then the issue gains the defect label. | PASS 2026-11-12 |
| [aut-issue-list-fails](Tests#t-aut-issue-list-fails) | requirement | AUT-2 | Given the issues cannot be read, when the scheduled regression runs, then it changes no issue rather than open duplicates. | PASS 2026-11-12 |
| [aut-email-regression](Tests#t-aut-email-regression) | requirement | AUT-2 | Given a failing test, when the scheduled regression runs, then its defect issue is filed with no milestone read, made or set, tagged with its feature when feature_labels is on, the suite runs every 4 hours and on every release tag, and a failed filing fails the run. | PASS 2026-11-12 |
| [aut-email-file](Tests#t-aut-email-file) | requirement | AUT-3 | Given health findings, when the scheduled health run files them, then each is tagged with its group on no milestone (and with its feature when feature_labels is on), no open issue is duplicated, and an issue the owner put on a milestone stays. | PASS 2026-11-12 |
| [aut-digest-create](Tests#t-aut-digest-create) | requirement | AUT-4 | Given no digest issue yet, when the first round ends, then the Automation digest issue is created and pinned. | PASS 2026-11-12 |
| [aut-digest-format](Tests#t-aut-digest-format) | requirement | AUT-4 | Given open defect and health issues, when a round ends, then one comment mentions the owner and lists what ran, the new issues and a request per open issue. | PASS 2026-11-12 |
| [aut-digest-rounds](Tests#t-aut-digest-rounds) | requirement | AUT-4 | Given a previous digest, when the next round ends, then its comment lists the new, still-open and fixed issues on the same digest issue. | PASS 2026-11-12 |
| [aut-digest-rerun](Tests#t-aut-digest-rerun) | requirement | AUT-4 | Given a round already posted, when the same run is rerun, then nothing is posted twice. | PASS 2026-11-12 |
| [aut-digest-no-title](Tests#t-aut-digest-no-title) | requirement | AUT-4 | Given an issue whose title holds instructions, when the digest is written, then the request names the issue only by number and link. | PASS 2026-11-12 |
| [aut-digest-org](Tests#t-aut-digest-org) | requirement | AUT-4 | Given a repo owned by an organisation, when the digest is written, then it says no one is notified and how to set digest_owner. | PASS 2026-11-12 |
| [aut-digest-pin-fails](Tests#t-aut-digest-pin-fails) | requirement | AUT-4 | Given the repo cannot pin another issue, when the first round ends, then it warns and still posts the digest. | PASS 2026-11-12 |
| [aut-digest-comment-fails](Tests#t-aut-digest-comment-fails) | requirement | AUT-4 | Given a round whose digest comment fails, when the run ends, then no state is saved, so its rerun posts the comment. | PASS 2026-11-12 |
| [aut-digest-list-fails](Tests#t-aut-digest-list-fails) | requirement | AUT-4 | Given gh cannot list the issues, when a round ends, then the digest posts nothing and says why. | PASS 2026-11-12 |
| [aut-email-mail](Tests#t-aut-email-mail) | requirement | AUT-4 | Given this run's digest comment, when the email step runs, then one mail with the comment's text goes out and the comment is marked mailed, and a rerun, a look-alike comment, a refusal or an unknown outcome never sends a second one. | PASS 2026-11-12 |
| [aut-email-retry](Tests#t-aut-email-retry) | requirement | AUT-4 | Given a provider that throttles once, when the round's mail is sent, then it is retried once, and only when the provider cannot have accepted it. | PASS 2026-11-12 |
| [aut-email-test](Tests#t-aut-email-test) | requirement | AUT-4 | Given the mail secrets, when mail.py test runs by hand, then one test mail goes out touching no issue, and a missing secret or mail off fails the run. | PASS 2026-11-12 |
| [aut-email-digest](Tests#t-aut-email-digest) | requirement | AUT-4 | Given open issues with and without milestones, when a round ends, then the digest groups the new, still-open and fixed issues by feature with the cost and email rows, shows a milestone title as a suffix, and an older or repeated run never posts twice. | PASS 2026-11-12 |
| [runbook-repo](Tests#t-runbook-repo) | requirement | AUT-8 | Given this repo's Health and Regression pages, when their Runbook sections are read, then each routine in the registry has every field, says a full run is live, and names a fixture or dry run as forbidden. | not run |
| - | requirement | AUT-8 | no passing test | not enforced |
| [bad-schedule-refused](Tests#t-bad-schedule-refused) | requirement | AUT-5 | Given a schedule setting that is not a cron time, when it is applied, then it is refused. | PASS 2026-11-12 |
| [aut-regression-off](Tests#t-aut-regression-off) | requirement | AUT-5 | Given regression_cron off, when the regression workflow runs, then it writes nothing and says the routine is off. | PASS 2026-11-12 |
| [aut-off-by-hand](Tests#t-aut-off-by-hand) | requirement | AUT-5 | Given regression_cron off, when its workflow is written, then it has no schedule and can still be started by hand. | PASS 2026-11-12 |
| [aut-digest-no-token](Tests#t-aut-digest-no-token) | requirement | AUT-5 | Given no token in the digest step, when it runs in Actions, then it says what is missing and writes nothing. | PASS 2026-11-12 |
| [aut-no-push](Tests#t-aut-no-push) | requirement | AUT-5 | Given the scheduled workflows, when they are written, then neither pushes nor has write access to the repo's contents. | PASS 2026-11-12 |
| [aut-by-hand-runs](Tests#t-aut-by-hand-runs) | requirement | AUT-5 | Given regression_cron off, when someone starts the regression run by hand, then it still runs. | PASS 2026-11-12 |
| [aut-regression-off-written](Tests#t-aut-regression-off-written) | requirement | AUT-5 | Given regression_cron off, when its workflow is written, then it has no schedule and keeps its by-hand trigger. | PASS 2026-11-12 |
| [aut-digest-dry-run](Tests#t-aut-digest-dry-run) | requirement | AUT-5 | Given no token outside Actions, when the digest runs, then it prints the comment, says it is a dry run and writes nothing. | PASS 2026-11-12 |
| [aut-off-push-runs](Tests#t-aut-off-push-runs) | requirement | AUT-5 | Given regression_cron off, when a release tag is pushed, then the regression run still runs the rows. | PASS 2026-11-12 |
| [aut-off-dispatch-runs](Tests#t-aut-off-dispatch-runs) | requirement | AUT-5 | Given regression_cron off, when someone starts the regression run by hand, then it still runs the rows. | PASS 2026-11-12 |
| [aut-email-secrets](Tests#t-aut-email-secrets) | requirement | AUT-6 | Given the mail settings in the schedule's mail.env, when the tick runs, then they reach only the mail step and never a log, the summary, an issue or the digest comment, a mail.env of the wrong mode sends nothing, and without it nothing is written and the digest says why. | PASS 2026-11-12 |
| [aut-email-rounds](Tests#t-aut-email-rounds) | requirement | AUT-7 | Given a round's runs, when the digest is written, then the run summary shows the round's job time and Actions minutes and flags a round over 45 minutes. | PASS 2026-11-12 |
| [aut7-budget-agrees](Tests#t-aut7-budget-agrees) | requirement | AUT-7 | Given the regression budget, when AUT-7 is read, then it names the 45 minute round as the 30 minute regression budget plus 15 for health. | not run |
| [digest-not-cut](Tests#t-digest-not-cut) | requirement | AUT-7 | Given a listing that reaches the issue limit, when the digest is written, then it says TRUNCATED instead of presenting cut counts as complete. | not run |
| [health-follows-regression](Tests#t-health-follows-regression) | requirement | AUT-7 | Given a regression run in progress, when the Mac tick starts health, then it waits for the run to complete instead of a fixed offset. | not run |
