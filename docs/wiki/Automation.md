<!-- workflow-docs -->
# Automation

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/10

Review: **Reviewed 2026-11-13** <!-- prd P=a45649a4 R=ff34edf0 N=e081872e M=4670eeeb U=772c7699 -->

## Problem
- Things break between my sessions, and I only find out when I next open one; the important checks should run on their own.
- Every few hours I want the full regression suite and the health check to run, and every problem they find to become an issue tagged with its group, and with its feature when feature_labels is on.
- I want one email to my address after each round that tells me what ran, what broke, what got fixed and what to ask the agent, without opening GitHub.

## Usage

- `/workflow-health workflow` — Removed: health runs on the Mac now, on `health_cron` (`off`, an every-N-hours shape such as `47 */4 * * *`, or fixed hours such as `47 8,20 * * *`; the Health page's `local install` registers it), so no repo has a health workflow. Prints `REMOVED: health runs on the Mac now; run automation.py local install (SCHEDULE_REMOVED_WORKFLOW)` and exits 2. A leftover `.github/workflows/health.yml` is a WARN of the `scheduled` rule: `git rm` it. Off macOS the launch agent cannot be loaded (`SCHEDULE_PLATFORM`), but the tick's code (`workflows.py`) imports and runs on native Windows; the launchd user id falls back to 0 where `os.getuid` does not exist.
- `/workflow-regression workflow` — Writes the scheduled regression workflow on `regression_cron` (five cron fields, or `off` for by-hand and release-tag runs only), for a public repo only: a private repo's regression runs on the Mac, so it prints `NOT WRITTEN: this repo is private; its regression runs on the Mac (local schedule)` and writes nothing (the Regression page has the whole entry). Prints `WROTE <repo>/.github/workflows/regression.yml`. Refuses (exit 1) `REFUSED: regression_cron is not five cron fields. ...` and `REFUSED: <path> exists, and this tool didn't write it. Fix: merge by hand.` Its run is split over eight parallel jobs and ends in one combined summary, and a newer run on the same ref cancels the one it supersedes; it keeps one open issue a row, files none for a row skipped for time and stops writing at a rate-limit reply; a run by hand with `cleanup` set closes the backlog of duplicate, skipped-only and removed-row issues, paced, until it prints `CLEANUP closed 0 issues`. A scheduled row that exits 77 (cannot run on this runner, such as the live Codex row) is recorded `SKIPPED` and opens no issue. The one local task per repo is named `<repo>-health-regression` (health and the full regression, every 4 hours or sooner); a repo recorded `regression_runs: mac`, public or private, runs its regression there and has no `regression.yml`, and `setup.py migration-check` names a missing, misnamed or slower task. A row that runs past its time limit has the processes then running (pid, parent, state, wait channel, command) written at the end of its log before it is killed, so a hang names what it is stuck on.
- `/workflow-health digest` — Posts one comment per round on the pinned Automation digest issue: what ran, the round's cost (job time, Actions minutes since the last round, `OVER 45 min` past the budget), the email's state, then per feature the new, still-open and fixed issues (with the milestone title beside an issue that has one) and a request per open issue. Prints `DIGEST: posted on #<n> (<k> open)`, `DIGEST: already posted for run <id> (DIGEST_ALREADY)`, `DIGEST: run <id> is older than the round on the issue ... (DIGEST_STALE)` or `DIGEST: already posted for run <id>; state repaired (DIGEST_REPAIRED)`. Refuses nothing; with no token it prints `DIGEST: no GH_TOKEN in this step, so nothing was posted. ...` and writes nothing, and in Actions a failed read or write exits 1. The digest lists up to 1000 open issues per label and prints `TRUNCATED` in its run summary when a listing reaches that limit, so a count is never silently cut off.
- `/workflow-health mail send` — Runs as the last step of the Mac tick: mails this run's digest comment once, through `digest_mail` (`cloudflare`, the default; `smtp`, with `smtp_host` and `smtp_port` 465 or 587; or `off`), to the address `DIGEST_TO`, from `DIGEST_FROM`, with `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_EMAIL_TOKEN` or `DIGEST_SMTP_USER` and `DIGEST_SMTP_PASSWORD`, all read from the schedule's `~/.workflow-loop/schedule/mail.env` (mode 0600). Prints one `MAIL: <what happened> (<code>)` line, also in the tick log: `MAIL_SENT`; exit 0 also for `MAIL_ALREADY` (sent before), `MAIL_STALE` (a later round posted), `MAIL_OFF` and `MAIL_NOT_SET_UP` (no mail secret, nothing written). Refuses (exit 1) `MAIL_SECRETS` (names each missing secret, or one with a space, line break or non-ASCII), `MAIL_SETTING` (a bad setting), `MAIL_TEST_URL` (a non-local test override), `MAIL_NO_COMMENT`, `MAIL_GH`, `MAIL_MARK` (nothing sent; rerun), `MAIL_REFUSED` (the provider refused; nothing sent), `MAIL_CLEAR_FAILED`, `MAIL_UNKNOWN` (it may have been sent: check the inbox, and if nothing came, delete the word mailing from the comment's last line and rerun), `MAIL_MARKED_LATE` and `MAIL_FAILED` (one line with its file and line, never a traceback). No line holds a secret, the address or its local part, in any form.
- `/workflow-health mail test` — Sends one fixed test mail through the same sender and variables, touching no issue; run it by hand with the `mail.env` variables set in the environment. Prints `MAIL: test sent (MAIL_SENT)`. Refuses (exit 1) `MAIL_OFF`, `MAIL_SECRETS`, `MAIL_SETTING`, `MAIL_TEST_URL`, `MAIL_REFUSED` and `MAIL_FAILED`, each with its fix.

## Requirements

### Functional
- AUT-1: **Reviewed 2026-11-13** Routines run where they can run fully <!-- reviewed 0b1d52ef -->
  - Health runs on my Mac for every repo. Regression runs in GitHub Actions for a public repo and on my Mac for a private one.
  - Each routine runs on a schedule set in the repo's config (every 4 hours by default), and I can also start it by hand.
  - A routine missed while the Mac sleeps runs once at the next wake, and the digest says it was missed.
  - Each run's report says whether it ran on my Mac or in GitHub Actions.
  - A long issue body or comment is passed to gh in a file (`--body-file`), never on the command line, so a routine writes the same on native Windows.
- AUT-2: **Reviewed 2026-11-13** Regression every few hours <!-- reviewed edabe328 -->
  - The full regression suite runs on the schedule (every 4 hours by default), in GitHub Actions for a public repo (which also runs it on every release tag) and on my Mac for a private one; the report names every test it skipped and why.
  - A push or pull request runs only the tests its change affects (Regression, REG-4), in the same place as the full suite.
  - No GitHub Actions check this tool writes is needed to merge a private repo; where its ruleset requires named checks, the pull request lane posts them as commit statuses itself, success when the lane passes and failure when it fails, so a failing lane holds that merge and a passing one releases it.
  - A failing test opens or updates one issue labeled defect, tagged with the feature it guards when feature_labels is on, naming the test and the requirement; it closes by itself when the test passes again.
- AUT-3: **Reviewed 2026-11-13** Health every few hours <!-- reviewed e0fc7032 -->
  - Health never runs in GitHub Actions: it runs on my Mac on the schedule (every 4 hours by default), after the latest finished regression run, with all its rule groups; its report names that run with its commit and age, or says none finished, and says when health last ran.
  - The repo review always runs, using my own login on the Mac, with no API key secret; when the login has expired or can't be reached, the report says which and the next round tries again.
  - Every finding becomes one issue tagged with its group and, when feature_labels is on, its feature, updated, closed or reopened as things change, never duplicated.
- AUT-4: **Reviewed 2026-11-10** A digest by email <!-- reviewed f06a9042 -->
  - After each round, one email goes to the address I set: what ran and its results, then the new, still-open and fixed issues grouped by feature, each with its link and the request to give the agent to fix it.
  - The same digest is also posted as one comment on a pinned Automation digest issue.
- AUT-8: **Reviewed 2026-11-13** Every routine has a runbook an agent follows exactly <!-- reviewed f0151127 -->
  - Each routine is listed in the routine registry with the feature page that owns it (health-round on Health, regression-round on Regression), and that page's Runbook section says what a full run is, the one output, the forbidden shortcuts and how to check the run was real.
  - An automation prompt for a routine reduces to "read the <page> Runbook and follow it exactly"; a scheduled run never sends a dry run, a fixture or a test mail in place of the real output.

### Non-functional
- AUT-5: **Reviewed 2026-11-13** Under my control <!-- reviewed 27ec344d -->
  - Each routine can be turned off or rescheduled in one setting. It writes to GitHub only with `--live` (the scheduled workflows pass it), and without the secrets it needs a routine runs but writes nothing and says what is missing.
- AUT-6: **Reviewed 2026-11-13** Private address <!-- reviewed a54e4796 -->
  - The email address and the mail key live only in a local secrets file outside git, kept where the repo review cannot reach it, read only by the local runner; never in the repo, logs, issues or the digest comment, and never printed. The same holds for the GitHub token the Mac uses.
- AUT-7: **Reviewed 2026-11-13** Bounded cost <!-- reviewed b5e1e5be -->
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
| [ls-private-tick](Tests#t-ls-private-tick) | requirement | AUT-1 | Given a toy repo whose regression_runs is mac and one failing row, when the tick runs, then health runs, the regression runs live, one issue is filed for the failing row, the digest is posted and the tick says REGRESSION: runs on the Mac. | not run |
| [ls-public-tick](Tests#t-ls-public-tick) | requirement | AUT-1 | Given a toy repo whose regression_runs is actions, when the tick runs, then health runs, no regression runs the tick says REGRESSION: runs in GitHub Actions and the newest suite-time artifact is fetched into the git common dir. | not run |
| [ls-missed-run](Tests#t-ls-missed-run) | requirement | AUT-1 | Given a registry whose last run is older than the interval plus an hour, when the digest is composed, then it says Last ran and MISSED, a recent last run says no MISSED, a repo whose tick started 20 minutes after another's is still due at the next fire, a run id of 12 digits not starting 20 is an Actions id, and one coalesced fire after sleep makes every overdue repo due. | not run |
| [aut-regression-schedule-mismatch](Tests#t-aut-regression-schedule-mismatch) | requirement | AUT-1 | Given a regression schedule that differs from the config, when the routine runs, then it names the difference and the command that fixes it. | PASS 2026-11-12 |
| [aut-defect-issue](Tests#t-aut-defect-issue) | requirement | AUT-2 | Given a failing test, when the scheduled regression runs, then one issue labelled defect opens, naming the test, the feature and the requirement it guards. | PASS 2026-11-12 |
| [aut-old-issue-relabel](Tests#t-aut-old-issue-relabel) | requirement | AUT-2 | Given an open failing-test issue without the defect label, when the test fails again, then the issue gains the defect label. | PASS 2026-11-12 |
| [aut-issue-list-fails](Tests#t-aut-issue-list-fails) | requirement | AUT-2 | Given a page of the open regression issues cannot be read, when the scheduled regression runs, then it changes no issue rather than open duplicates. | PASS 2026-11-12 |
| [st-pass](Tests#t-st-pass) | requirement | AUT-2 | Given a private repo whose rules require two checks and a lane that passed, when the pr lane posts, then one success per required check is posted with a description naming the local run and no target_url. | not run |
| [st-fail-never-success](Tests#t-st-fail-never-success) | requirement | AUT-2 | Given a lane that failed, when it posts, then only failure is posted, only for a head already on the remote, never success, and an unpushed head posts nothing. | not run |
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
| [capture-row-ci](Tests#t-capture-row-ci) | defect | [#3789](https://github.com/jcl2018/agent-workflow-template/issues/3789) closed (2026-11-13) | Given a failing row that ends in grep -q and prints nothing, when the scheduled workflow files its issue, then the body holds the row's last 40 output lines, not an empty block (#3789). | not run |
