<!-- /autoplan restore point: "<private path>" -->
# Plan: automation-email

Source: `.loop/goals/automation-email.design.md` (spec review: 2 rounds, CONVERGENCE; the 2 blocking fixes left at the
cap applied and verified; 4 minor concerns resolved below). Done lines: `.loop/goals/automation-email.md`.
PRD: the owner-approved Automation PRD of 2026-11-10 (AUT-1..AUT-7), held privately by the operation session.

## Implementation plan

1. **`.loop/docs.tsv`**: add `skills/workflow-health/scripts/mail.py` and `skills/workflow-health/scripts/rounds.py` to
   the Automation row, so both map to the Automation page (longest prefix wins over `skills/workflow-health`).

2. **New `skills/workflow-health/scripts/rounds.py`** (standard library + gh; about 4 KB). Round cost for AUT-7.
   - `round_cost(health_run_id, now=None)` returns a dict: `regression` (`{url, seconds, minutes, running}` or None),
     `health` (`{seconds, minutes}`), `seconds`, `minutes`, `partial` (bool), `over` (bool), `budget`.
   - The round's regression run: `gh run list --workflow regression.yml --limit 20 --json
     databaseId,createdAt,status,url`, the newest whose `createdAt` is before this health run's `createdAt`
     (`gh run view <health_run_id> --json createdAt`) and no more than 6 hours before it, whatever its event. None
     (regression off, or no run in that window): `regression: no run found`, and the round is health only. A tag or
     by-hand regression run inside the window is the round's run when it is the newest, in place of the scheduled one.
   - Job time: `gh run view <id> --json jobs`; per job `completedAt - startedAt`, or `now - startedAt` while it runs;
     a job not started counts 0.
   - Two numbers, each named for what it measures:
     - **Round duration** (drives the 45-minute flag) = the round's regression run's job time + this health run's job
       time so far.
     - **Actions minutes since the last round** (the spend) = every regression and health run created after the
       previous round's health run (the marker's `run`, its `createdAt` from `gh run view`) up to now, each job's
       minutes rounded up (`ceil(seconds / 60)`), summed. A tag, by-hand or extra run is counted here even when it is
       not the round's own regression run, so no work drops out of the spend. With no previous round (first digest),
       the window is the round's own two runs.
   - The flag compares round duration (seconds) with 45 minutes; the minutes line is shown beside it and never drives
     the flag, so the two never disagree on a unit.
   - Health counts its own jobs "so far" (now = the moment the digest is written); the mail step after it (at most
     about a minute with one retry) is not counted, and the wiki's Usage says the figure runs "through the digest".
   - `budget` is 45 minutes, fixed by AUT-7 (`BUDGET_MINUTES = 45` in rounds.py, no setting). `over` = `seconds > budget * 60`; a partial round (regression still running) is flagged only when
     its partial time already passes the budget.
   - `line(cost)`: `round 31 min (regression 24 min, health 7 min so far); 52 Actions minutes since the last round`; with a running regression
     `regression still running, partial`; over: prefix `OVER 45 min: slow a routine down or turn it off. `.
   - Outside Actions (no run id) or when gh can't read: `None`, and the caller says `round cost: not read`.

3. **`skills/workflow-health/scripts/automation.py digest`**: grouping, marker grammar, round cost.
   - `open_issues()` asks gh for `number,url,milestone` and returns `{number: (url, milestone_number)}`.
   - Milestone titles: `gh api repos/{owner}/{repo}/milestones?state=all&per_page=100` once per digest, into
     `{number: title}`; unknown or 0 -> `No milestone`.
   - Marker: `<!-- automation-digest run=R open=N:M,N:M -->`. `parse(body)` reads `key=value` tokens in any order
     (`run`, `open`, and on a comment's marker the bare flags `mailing` and `mailed`); `open` items are `N` (old form, milestone 0) or `N:M`. `marker(run, open)` writes
     `run` then `open`. Values are checked with regexes (`[0-9]+`, `none`, `local`), so nothing a title holds is ever
     written into the comment.
   - `compose(...)`: the routine table gets a `round cost` row and an `email` row: `not set up (add the DIGEST_TO and
     DIGEST_FROM secrets)` when the digest step's `DIGEST_MAIL_SET` is not `true`, `off` when `digest_mail` is off,
     otherwise the previous round's mail outcome read from the previous round's comment marker (`sent`, `not sent`, or
     `may have been sent` for `mailing` without `mailed`). The owner sees a silent or broken mailer in the comment and
     in the next mail, not only in Actions; then one `### <milestone title>` section per milestone
     that has a new, still-open or fixed issue (sorted: feature milestones by title, then Backlog, then No milestone),
     each with **New**, **Still open** and **Fixed**, then that milestone's open issues one per line, each with its
     link and its request (`- [#N](url): `/workflow-delivery go "Fix #N"``), so every issue in a feature group carries
     its link and the request to give the agent. The flat `### Ask the agent` section goes. A fixed issue is grouped by
     the milestone it had in the previous marker.
   - The run summary: when `GITHUB_STEP_SUMMARY` is set, append `## Round` with `line(cost)`; over budget also prints
     `::warning::` with the same line.
   - The digest rewrites the body as `intro + marker(run, open)` (no `mailed`, a new round).
   - `digest_issue()` finds the issue with `parse()` (any key order, old or new form), replacing the fixed-order
     `STATE` regex, so a body written `run=` first is still found. Both live in rounds.py (below).
   - `rounds.py` holds a round's state as well as its cost, from the start: `parse()`, `marker()` and
     `digest_issue()` live there, and both automation.py and mail.py import them, so automation.py stays well under
     20 KB (target < 18 KB) and the import path never moves.
   - `parse()` accepts an empty `open=` (the new issue's seed body `open= run=none`) as no open issues.
   - Order on every run: (1) the body already holds `run=R`: print `DIGEST: already posted for run R`, exit 0, and
     leave the body alone (today's early exit, kept first). (2) Otherwise the digest reads this run's comment the way
     mail.py does (bot author, marker with `run=R`). If one exists (an earlier attempt posted it but couldn't save
     the body), it posts nothing new, writes `run=R open=<that comment's open>` (the body never holds mail flags; those
     live on the comment), and says `DIGEST: already posted for run R; state repaired`. (3) Otherwise it posts.

4. **New `skills/workflow-health/scripts/mail.py`** (standard library only: urllib, smtplib, email; about 7 KB).
   - `mail.py send [--root DIR]`, run by the workflow step `Email the digest`.
   - Settings: `digest_mail` = `cloudflare` (default) | `smtp` | `off`; `smtp_host` (default `smtp.gmail.com`),
     `smtp_port` (default 465; 587 uses STARTTLS).
   - Secrets by env name: `DIGEST_TO`, `DIGEST_FROM`; cloudflare `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_EMAIL_TOKEN`;
     smtp `SMTP_USER`, `SMTP_PASSWORD`. Missing: `MAIL: skipped, missing secrets: <names>. Fix: add them in Settings,
     Secrets and variables, Actions.` exit 0, nothing written. `off`: `MAIL: off (digest_mail in .loop/config.json)`,
     exit 0.
   - Finds the digest issue with rounds.py's `digest_issue()` (label `automation`, title `Automation digest`, oldest
     with the marker), then this run's comment (below).
   - **The mail state of a round lives on that round's own comment**, not the issue body, so a later round never
     erases it: the comment's marker line gains `mailing` and then `mailed` (`<!-- automation-digest run=R open=...
     mailed -->`), edited with `gh api -X PATCH repos/{owner}/{repo}/issues/comments/<id>` (the job token may edit its
     own comment; the visible text is unchanged). A rerun of any old job therefore still finds its own record.
   - The comment's marker has `mailed` -> `MAIL: already sent for run R`, exit 0; `mailing` without `mailed` ->
     `MAIL: a mail for run R may already have been sent (an earlier attempt stopped mid-send); not resending`, exit 1.
   - At-most-once: before sending, it writes `mailing` into the comment's marker; if that write fails it sends nothing
     (`MAIL: couldn't mark run R as sending, so nothing was sent`, exit 1). After a send the provider refused (a known
     failure), it removes `mailing` so a rerun may try again. After an accepted send it writes `mailed`. A crash
     between the two leaves `mailing`, so a rerun never sends a second mail; the cost is a possibly missed mail, which
     the step's red exit and the next digest's `email: may have been sent` row show.
   - Finds this run's comment: `gh api "repos/{owner}/{repo}/issues/N/comments?since=<health run createdAt>&per_page=100"`
     (the run's createdAt from `gh run view $DIGEST_RUN --json createdAt`; falls back to the last two pages). Keeps
     only comments by `github-actions[bot]` whose last non-blank line is a marker with `run=R`; takes the newest.
     None -> `MAIL: no digest comment for run R, so nothing was sent`, exit 1.
   - Body: drop the leading `@login ` mention and the marker line. Text part = that markdown. HTML part = each line
     escaped, `[x](url)` links as anchors, `**x**` as bold, table rows as a `<table>`, headings as `<h3>`.
   - Subject: `Automation digest: N new, S still open, K fixed (<owner/repo>)`, counted from the comment by summing
     every match of `^\*\*(New|Still open|Fixed)\*\* \((\d+)\)` over the groups.
   - Senders: `send_cloudflare(to, frm, subject, text, html)` posts JSON `{to, from, subject, text, html}` to
     `https://api.cloudflare.com/client/v4/accounts/<id>/email/sending/send` with `Authorization: Bearer`; success is
     HTTP 2xx and `success: true` with the address in `delivered` or `queued`; a permanent bounce is a failure.
     `send_smtp(...)`: `SMTP_SSL` on 465, `SMTP` + `starttls()` on 587, login, `send_message`. Timeout 30 s each.
   - Test-only override: `DIGEST_MAIL_API` replaces the Cloudflare base URL only when it starts with
     `http://127.0.0.1:` or `http://localhost:`; any other value is refused (`MAIL: DIGEST_MAIL_API must be a local test
     server`), exit 1. The generated workflow never sets it, and a test greps the workflow for it.
   - Errors: `MAIL: cloudflare refused it: <code> <message>` / `MAIL: smtp refused it: <class>: <text>`, exit 1, after
     `scrub(text)` replaces each secret value (and the address) with `***`, cut to 200 characters.
   - Success: mark the comment `mailed`; then, when the issue body still holds an older run than R (the digest's body
     write failed), write `run=R open=<from this run's comment marker>` so a rerun of the digest posts nothing. A body
     that already holds R or a newer run is left alone. Print `MAIL: sent for run R` (never the address), exit 0. If the `mailed` write fails:
     `MAIL: sent for run R, but couldn't mark the comment mailed; it keeps mailing, so a rerun won't send again`,
     exit 1.
   - Every outcome line also goes to `GITHUB_STEP_SUMMARY` when set.
   - One top-level handler wraps `send` and `test`: any exception not handled above (urllib, smtplib, JSON, OSError)
     prints `MAIL: failed: <ExceptionClass>: <scrubbed message>` and exits 1, never a traceback, so no URL, address or
     key reaches the log through a crash.
   - The Cloudflare contract (endpoint, `{to, from, subject, text, html}`, Bearer token, `success` and
     `result.delivered|queued|permanent_bounces`, error codes) is the one on the Cloudflare Email Service REST API page,
     read 2026-11-10; `DIGEST_FROM` must be on a domain onboarded to Email Sending, which the wiki's Usage says.

5. **`.github/workflows/health.yml` through `automation.py workflow`** (the template `WORKFLOW`):
   - `File the findings as tagged issues`: `milestone.py new --all --live` instead of `new backlog --live`.
   - `Post the digest`: env gains `DIGEST_MAIL_SET: ${{ secrets.DIGEST_TO != '' && secrets.DIGEST_FROM != '' }}` (a
     true/false only, never a value); the digest now writes `## Round` to the summary.
   - New step after it:
     ```yaml
      - name: Email the digest
        if: always() && steps.routine.outputs.on == 'true'
        env:
          GH_TOKEN: ${{ github.token }}
          DIGEST_RUN: ${{ github.run_id }}
          DIGEST_TO: ${{ secrets.DIGEST_TO }}
          DIGEST_FROM: ${{ secrets.DIGEST_FROM }}
          CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          CLOUDFLARE_EMAIL_TOKEN: ${{ secrets.CLOUDFLARE_EMAIL_TOKEN }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
        run: python3 skills/workflow-health/scripts/mail.py send
     ```
   - Permissions stay `contents: read, issues: write, actions: read`. `timeout-minutes: 30` stays.
   - Regenerate `.github/workflows/health.yml`; the existing "committed workflow matches" row keeps it honest.

6. **`skills/workflow-health/scripts/file.py`**: feature milestones for findings (AUT-3).
   - `feature_of(root, item)`: milestone.py's `features(root)` (imported from the same folder); the page whose path is
     the longest prefix of `item["subject"]` (exact path or `path/` prefix), else the page whose name equals the subject
     case-insensitively, else `Backlog`.
   - `held()` also reads `milestone` (`{number,title}`). `plan()` adds `milestone` (title) to each open act; for an
     existing open issue, or one this plan reopens, whose milestone is empty or `Backlog` and differs from the
     computed one, a `move` act. An issue on any other milestone is left alone.
   - Why file.py doesn't create milestones itself: the health workflow's `milestone.py new --all --live` step runs
     first and creates Backlog and every feature milestone, so file.py only reads them (and falls back to Backlog);
     the regression workflow has no such step and stays self-contained, so it creates the one milestone it needs.
   - `apply()`: one `gh api repos/{owner}/{repo}/milestones?state=all&per_page=100` read into `{title: number}`; open
     via `gh api -X POST repos/{owner}/{repo}/issues -f title=... -f body=... -f "labels[]=health" -f "labels[]=<tag>"
     -F milestone=<number>`; move via `gh api -X PATCH repos/{owner}/{repo}/issues/N -F milestone=<number>`. A title
     with no milestone (not created yet) falls back to Backlog's number, and to none if Backlog is missing too, with a
     `NOTE:` line.
   - `preview` and `words()` name the milestone (`open issue ... on Automation`, `move #N to Automation`).
   - The issue body's advice stays true: `milestone.py move` places an issue, and the automation never moves it back.

7. **`skills/workflow-regression/scripts/actions.py`**: defect issues on feature milestones (AUT-2).
   - In the inline filing script: read features from `.loop/docs.tsv` (page != Home, not `#`); read milestones once
     with `gh api "repos/{owner}/{repo}/milestones?state=all&per_page=100"`.
   - `place(feature)`: `feature` is the row's map cell 0 (`guards[row][0]`, from `tests.py list --tsv`); the page when
     it is a docs.tsv feature, else `Backlog` (also for an empty cell, `-` or `Other`). A missing milestone of that set is
     created (`gh api -X POST .../milestones -f title=...`); nothing outside the set is ever created; a closed one is
     used as is.
   - Create: `gh api -X POST repos/{owner}/{repo}/issues` with title, body, labels `regression` and `defect`, and
     `-F milestone=<number>`; its URL is printed as before.
   - An existing open issue with no milestone or on Backlog is moved with `PATCH ... -F milestone=<number>`; one on any
     other milestone is left alone. The issue list asks for `milestone` too.
   - Regenerate `.github/workflows/regression.yml` with `regression.py workflow` (after merging main, since lane-control
     edits it).
   - The schedule stays `17 */4 * * *` plus `push: tags: ["v*"]`; rows prove both. Publishing a release creates its tag
     with the owner's credentials, which starts the run (v0.19.0, v0.20.0 and v0.21.0 each started one on 2026-11-10).
     No `release:` trigger is added: it would run the suite twice per release.

8. **Settings (`skills/workflow-setup/scripts/settings.py` TABLE)**: `digest_mail` ("cloudflare"), `smtp_host`
   ("smtp.gmail.com"), `smtp_port` (465), each with a one-line explanation. The SMTP option is in scope by the
   operation session's brief of 2026-11-10 ("Cloudflare Email by default, plus an SMTP option"). `seed.py`'s health
   line says "health, digest and email run on ...". `.loop/config.json` sets `criteria_max` to 7 (the approved PRD has
   seven requirements, AUT-1..AUT-7; outside the done lines but needed for the page to pass docs check) and gains
   `digest_mail: "cloudflare"`.

9. **Tests: new `dev/toy/test-automation-email.sh GROUP`** (stub gh + a local HTTP stub for Cloudflare + a local SMTP
   stub with `smtpd`-free `socketserver`), each case printing one `PASS:` line used by a row. GROUP is one of `mail`,
   `digest`, `rounds`, `file`, `regression`, `mailtest`, or `all`; each row passes its own group, so a land run starts
   each harness once per group rather than once per row (about 6 harness runs, not 35). Pure functions (`parse`,
   `marker`, the round sums, the subject count, the retry classifier) are checked inside the `digest`, `rounds` and
   `mail` groups with `python3 -c` calls, without stubs. Extra cases from the CEO review: a rerun of an old run's job
   after a newer round has posted sends nothing (its comment says `mailed`); the HTML part of a real digest has no
   leftover `**`, `](` or `|---|`; the `email` row reads `not set up`, `off`, `sent`, `may have been sent`; Actions
   minutes count a by-hand regression run that is not the round's own run.
   - mail: sends one mail with the comment's text for this run; a look-alike comment by another author is ignored;
     newest of two bot comments wins; already-mailed run sends nothing; a failed send writes no `mailed`; a send whose
     `mailed` write fails sends nothing on a rerun; missing secrets name them and write nothing; `off` writes nothing;
     no comment for R exits 1; SMTP sender works; secrets and the address never appear in stdout, stderr, the summary,
     the comment or the issue body; `DIGEST_MAIL_API` refuses a non-local URL; the workflow never sets it.
   - digest: grouped by milestone; fixed issue under its previous milestone; old marker reads; tokens in any order; a
     milestone titled `Ops, team: A` round-trips (by number) and its title appears only in the heading.
   - rounds: sum of job times; running regression is partial; tag/by-hand run counts; no regression run; minutes rounded
     per job; over 45 flagged in the digest, the summary and a warning.
   - file.py: a finding under `skills/workflow-health/scripts/automation.py` files on Automation; unmapped on Backlog;
     an open Backlog issue moves; an owner-placed issue stays; a closed feature milestone is used; no duplicate.
   - regression workflow: a failing row's issue goes on its feature's milestone; `Other` goes to Backlog; an owner-placed
     issue stays; a missing feature milestone is created, nothing else; the default schedule is every 4 hours and tags
     `v*` trigger it.

10. **Rows and the wiki page**: one `regression.py add` row per PASS line above, `--goal AUT-n` by this map: mail and
    digest cases, E1 and E3 -> AUT-4, except secrets, scrubbing, missing secrets and `DIGEST_MAIL_API` -> AUT-6;
    rounds -> AUT-7; file.py -> AUT-3; regression workflow -> AUT-2. Each of AUT-2, 3, 4, 6 and 7 gets at least one
    new row. Each is seen red with
    `regression.py red ID --break <cmd>` (a sed that removes the behavior); `docs/wiki/Automation.md` takes the approved
    PRD's Problem, Requirements (AUT-1..AUT-7, one line each, marked Reviewed 2026-11-10 with `criteria.py review
    --user --date 2026-11-10`, the owner's approval relayed by the operation session), Non-goals and Success metrics;
    Usage gains the email setup (secrets by name, the Cloudflare domain and token, the SMTP option, `digest_mail off`);
    `criteria.py render` rewrites Tests. Existing AUT rows keep their ids.


<!-- autoplan-accepted:ceo -->
- E1 (mail test): `mail.py test` sends one sample mail ("Automation digest: test from <owner/repo>", a fixed body with no issue data) through the configured sender, with the same secret checks, scrubbing and outcome lines as `send`, and writes no state. It runs from its own workflow, `.github/workflows/mail-test.yml` (written by `automation.py workflow` beside health.yml, header `# Written by workflow-health`), triggered only by `workflow_dispatch`, `permissions: contents: read`, one job: checkout, setup-python, `mail.py test` with the mail secrets in env. health.yml gains no input and no guards. Verify: a toy case where `mail.py test` sends one test mail through the Cloudflare stub and touches no issue (no gh call), and a missing secret names it; the rendered mail-test.yml is dispatch-only, has no `issues: write`, and equals the committed file.
- E3 (one retry): a send is retried once after 30 s (`DIGEST_MAIL_RETRY_SECONDS` overrides the wait for tests, 0..30) only when the provider cannot have accepted the mail: Cloudflare HTTP 429 (code 10004) or HTTP 503 (code 10100), decided by the HTTP status; a refused connection or DNS failure before any request is sent; an SMTP 4xx reply before DATA (`SMTPConnectError`, `SMTPHeloError`, `SMTPSenderRefused` or `SMTPRecipientsRefused` with a 4xx code; `SMTPDataError` and `SMTPServerDisconnected` after DATA are not retried). HTTP 500, a timeout after the request was sent, an SMTP error after DATA, any other 4xx, an auth error or a permanent bounce is not retried, so a retry never sends the same mail twice. Verify: a toy case where the stub fails once with 429 then accepts, which sends one mail and says `MAIL: sent for run R (after 1 retry)`; one where it fails with 401, which sends nothing and is not retried; one where it fails with 500, which is not retried.
- Crash between send and `mailed`: a toy case where the stub accepts the mail and the comment's `mailed` write fails; a rerun sends no second mail and says it may already have been sent (AUT-4).
- Rerun after a failed body write: a toy case where the digest's body write fails, then the job is rerun; the rerun posts no second comment and sends no second mail, the body ends `run=R`, and the run's comment marker ends `mailed` (AUT-4).
- Old-run rerun: a toy case where round R2 has posted, then R1's job is rerun; R1's comment says `mailed`, so nothing is sent (AUT-4).
- Owner inbox check (Verify by hand, filled at build): set the secrets in a fresh fork, run the Mail test workflow, and see the mail arrive; note the setup time.
- Regression filing checks results: every `gh api` create, PATCH and milestone POST in the inline filing script checks its exit code and prints `FAILED <what>: <stderr, 160 chars>` on error, carrying on with the next row (AUT-2).
<!-- /autoplan-accepted:ceo -->

<!-- autoplan-accepted:dx -->
- DX-1: `mail.py test` exits 1 with `(MAIL_SECRETS)` or `(MAIL_OFF)` and a Fix line whenever it cannot send (missing secrets, `digest_mail: off`); it never exits 0 without an accepted send. Supersedes E1's "same ... outcome lines as send" for these two cases. Verify: toy cases for missing secret and off, both exit 1.
- DX-2: in `send`, exit 0 only when no mail secret is set at all (`MAIL: not set up ... (MAIL_NOT_SET_UP)`) or `digest_mail` is off; any partial set (addresses without provider secrets, or provider secrets without addresses) exits 1 naming the missing ones `(MAIL_SECRETS)`. Supersedes item 4's "Missing: ... exit 0". AUT-6's "without them the email step writes nothing and says what is missing" holds in both cases. Verify: toy cases none-set (exit 0, nothing written) and partial (exit 1, nothing written, names listed).
- DX-3: the inline regression filing counts failed gh writes and, after the last row, prints `FILED <k> issue writes; FAILED <m>` and exits 1 when m > 0 (in addition to today's exit 1 on red rows). Verify: a toy case where `gh api` fails once makes the step exit 1 and names the row.
- DX-4: the digest's repair writes the body only when the body's `run` is older than R (run ids compared as integers; `none`/`local` count as oldest); a body holding a newer run is left alone. Supersedes item 3's order step (2) wording. Verify: the old-run rerun case also asserts the body still holds R2.
- DX-5: `automation.py workflow --check` prints `STALE_WORKFLOW: <path> differs from what automation.py writes. Fix: python3 skills/workflow-health/scripts/automation.py workflow, then commit` and exits 1 when health.yml or mail-test.yml is missing or differs (only for files headed `# Written by workflow-health`; a hand-written one is reported `NOT_OURS` and never rewritten). The health workflow's routine step runs it and turns a non-zero result into a `::warning::` and a summary line (the run still proceeds). Usage gives the upgrade sequence (update skills, run `automation.py workflow`, review the diff, commit, push, set secrets, run Mail test) and the rollback note. Verify: toy cases for stale, current and hand-written files.
- DX-6: every outcome line ends with a stable code in parentheses and, for any non-success, a `Fix:` sentence and the recovery (safe to rerun / do not rerun / check first), in the existing `REFUSED ... Fix: ... (CODE)` style. Codes: MAIL_SENT, MAIL_ALREADY, MAIL_OFF, MAIL_NOT_SET_UP, MAIL_SECRETS, MAIL_SETTING, MAIL_NO_COMMENT, MAIL_GH, MAIL_MARK, MAIL_UNKNOWN, MAIL_REFUSED, MAIL_MARKED_LATE, MAIL_TEST_URL, MAIL_FAILED; DIGEST_ALREADY, DIGEST_REPAIRED; ROUND_UNREAD; FILE_FAILED; STALE_WORKFLOW, NOT_OURS. MAIL_REFUSED maps 401/403 to "check the token's Email Sending permission", a sender-domain error to "onboard DIGEST_FROM's domain", SMTP auth to "use an app password". MAIL_UNKNOWN's Fix names the inbox check and the exact comment edit. MAIL_FAILED adds the innermost frame `file:line in function` (no values). `round cost: not read` gives its reason (`no run id`, or gh's stderr cut to 120 characters, scrubbed). The wiki's troubleshooting table lists every code. Verify: each toy case asserts its code; a grep check that every code in mail.py appears in the wiki table.
- DX-7: before any work, `digest_mail` outside cloudflare|smtp|off, `smtp_port` other than 465 or 587, or `DIGEST_MAIL_RETRY_SECONDS` outside 0..30 exits 1 `(MAIL_SETTING)` naming the value and the allowed ones. Verify: toy case per setting.
- DX-8: the digest's `email` row checks `digest_mail: off` first (`off`), then sender readiness from three booleans the digest step receives (`MAIL_ADDR_SET`, `MAIL_CF_SET`, `MAIL_SMTP_SET`, each `${{ secrets.X != '' && ... }}`, values never), then shows the previous round's outcome labeled `previous round: sent | not sent | may have been sent`. Supersedes item 5's single `DIGEST_MAIL_SET`. Verify: toy cases for off-without-secrets, cloudflare-missing-token, previous sent.
- DX-9: comment lookup uses `gh api --paginate "repos/{owner}/{repo}/issues/N/comments?since=<run createdAt>&per_page=100"` and scans every page; the "last two pages" fallback goes. Verify: a toy case with the matching comment on the second page.
- DX-10: the spend figure is named `Actions minutes of runs started since the last round` everywhere (comment, summary, wiki), and the wiki says a run still going at a round's cut-off is counted by the round in which it started. Supersedes "Actions minutes since the last round" wording in item 2.
- DX-11: regression rows are one per test group, not one per PASS line: `test-automation-email.sh GROUP` exits 0 only when every case in its group passes, and each row runs one group, so a land run starts one harness per row. Groups: `mail` (AUT-4), `secrets` (AUT-6), `rounds` (AUT-7), `file` (AUT-3), `regression` (AUT-2), `mailtest` (AUT-4), `upgrade` (AUT-4), `retry` (AUT-4). Supersedes item 10's "one regression.py add row per PASS line". Each row is still seen failing then passing.
- DX-12: the wiki's Usage leads with an Email quickstart: prerequisites (a domain onboarded to Cloudflare Email Sending and a token with the Email Sending send permission, or a Gmail account with 2-step verification and an app password), the exact `gh secret set` lines for each sender, the `digest_mail` setting, `gh workflow run mail-test.yml`, the expected `MAIL: test sent (MAIL_SENT)` line, and that DIGEST_TO holds one address. Then the troubleshooting table (DX-6) and the email-row states with the owner's next step.
- DX-13: SMTP secrets are `DIGEST_SMTP_USER` and `DIGEST_SMTP_PASSWORD` (not bare SMTP_*). Supersedes those names in items 4 and 5.
- DX-16: `scrub()` replaces each secret value and the address case-insensitively, and the address's local part on its own; the DIGEST_MAIL_API refusal shows the scheme and host it got. Verify: the leak case includes an upper-cased address in a stub error.
<!-- /autoplan-accepted:dx -->

<!-- autoplan-accepted:eng -->
- Eng-C1: update the two existing assertions in dev/toy/test-automation.sh for aut-digest-format and aut-digest-rounds to the grouped form and the new marker, keep their row ids, and add stub routes (milestones, comments, runs, PATCH) so every other existing digest row passes unchanged.
- Eng-C4: seed.py adds `.github/workflows/mail-test.yml` beside health.yml under the same condition (health skill present).
- H1: every digest run compares the body's run with R as integers (`none`/`local` oldest) before anything else: body run > R -> post nothing, write nothing, `DIGEST: run R is older than the round on the issue (run S); nothing posted (DIGEST_STALE)`, exit 0; body run == R -> DIGEST_ALREADY; else repair or post. Verify: old-run rerun with no comment for R1 after R2 posted: no comment, body still R2, no mail (mail.py finds no comment: exit 1 MAIL_NO_COMMENT is acceptable, and the mail step's Fix names the stale digest).
- H2: placement memory. A created issue records where the automation put it: health issues' marker becomes `<!-- loop-health KEY placed=<milestone number or 0> -->`, regression issues' marker `<!-- loop-regression ID placed=<number or 0> -->`. The automation moves an open issue only when its current milestone equals its recorded placement (legacy issues without `placed=`: health counts as Backlog's number, regression as 0) and the computed milestone differs; it then updates `placed=`. An issue the owner moved anywhere else, Backlog included, stays. Supersedes items 6 and 7's "no milestone or on Backlog" rule. Verify: owner moves an Automation issue to Backlog -> it stays; a legacy Backlog health issue -> moves to its feature; a legacy no-milestone regression issue -> moves.
- H3: SMTP testing: `DIGEST_SMTP_TEST_PORT` (test-only, honoured only when smtp_host is 127.0.0.1 or localhost; bypasses the 465/587 check; never set by any workflow, grep-tested) connects without TLS for the end-to-end case; a `python3 -c` case replaces `smtplib.SMTP_SSL`/`smtplib.SMTP` with fakes and asserts 465 uses SMTP_SSL and 587 calls starttls() before login.
- H4: the accepted blocks (ceo, dx, eng) are the build's source of truth where they say "supersedes". DX-11's groups gain `digest` (AUT-4): grouping, fixed under its old milestone, marker order and the `Ops, team: A` title. The final env: the digest step gets `MAIL_ADDR_SET: ${{ secrets.DIGEST_TO != '' && secrets.DIGEST_FROM != '' }}`, `MAIL_CF_SET: ${{ secrets.CLOUDFLARE_ACCOUNT_ID != '' && secrets.CLOUDFLARE_EMAIL_TOKEN != '' }}`, `MAIL_SMTP_SET: ${{ secrets.DIGEST_SMTP_USER != '' && secrets.DIGEST_SMTP_PASSWORD != '' }}`; the mail step and mail-test.yml get `DIGEST_TO`, `DIGEST_FROM`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_EMAIL_TOKEN`, `DIGEST_SMTP_USER`, `DIGEST_SMTP_PASSWORD` (plus `GH_TOKEN` and `DIGEST_RUN` for the mail step only).
- M1: the two workflow templates (health.yml, mail-test.yml) move to a new `skills/workflow-health/scripts/templates.py` (added to the Automation row of docs.tsv); if mail.py passes 18 KB, its HTML/subject rendering moves to `mail_render.py` (also mapped). The build runs `health.py check --group size` and every new or changed script stays under 20 KB.
- M2: the round figure is named "job time" (sum of the round's jobs, each job's completedAt - startedAt); the wiki says so. Both workflows have one job today, so job time equals each run's run time.
- M3: the spend list uses `gh run list --workflow W --created ">=<prev createdAt>" --limit 200` per workflow and prints `NOTE: more than 200 runs since the last round; the spend is a lower bound` when capped; when the previous run can't be read (expired, `none`, `local`), the window is the round's own two runs and the line says `(first round counted)`. Every milestone list uses `gh api --paginate --slurp`.
- M4: the HTML part turns `[x](url)` into a link only when url starts with `https://github.com/`; anything else stays text; hrefs are escaped. Verify: a comment with a `javascript:` link renders as text.
- M5: `milestone.page_of(root, path)` returns the docs.tsv page whose path is the longest prefix of `path` (exact or `path/` prefix), else the page whose name equals the subject case-insensitively, else "" (caller uses Backlog); file.py uses it. Verify: `skills/workflow-health/scripts/mail.py` -> Automation, `skills/workflow-health/scripts/health.py` -> Health.
- M7: if removing `mailing` after a known refusal fails: `MAIL: refused and couldn't clear the sending mark on <comment url> (MAIL_CLEAR_FAILED). Fix: delete the word mailing from that comment's last line, then rerun this job (nothing was sent).`, exit 1. Verify: toy case.
- L1: `digest_issue()` accepts only an issue authored by `github-actions[bot]` (as well as title, label and marker); the oldest such issue wins.
- L4: the Cloudflare endpoint, response fields and retryable statuses live in one constant block at the top of mail.py with the docs URL beside it.
<!-- /autoplan-accepted:eng -->
## Review record

### Phase 1: CEO review (SELECTIVE EXPANSION, autoplan override), Step 0

Pre-review audit: base `main` (GitHub). HEAD c6b1dce = origin/main e145b43 + the goal file and the design. No TODOS.md
in this repo (backlog lives in GitHub issues and `.loop/findings.md`). Open work touching the same files: lane-control
(regression.yml, health rules) and docs-format (`.loop/docs.tsv`), both noted by the operation session: merge main
before the pull request. Recently touched: automation.py, file.py, actions.py and both workflows all came in with
PR #177 (a23c125) on 2026-11-10; nothing has landed on them since (`git log origin/main --since=2026-11-09`).
Prior learning applied: milestone-ensure-writes-wiki (confidence 9/10, 2026-11-10): `milestone.ensure()` rewrites a
tracked wiki page through `link_page()`, so file.py must import only `features()` from milestone.py, never `ensure()`.
Taste calibration: good references are `automation.py` (one script, a dry-run path, state kept on GitHub, every gh call
checked) and `file.py`'s plan/preview/apply split (preview has no write path). Avoid: the regression workflow's inline
filing script's habit of ignoring gh return codes (`gh("issue", "create", ...)` with no check), which this plan touches.
Landscape: search not run for this step (an internal tool; the conventional pattern, a CI job that posts a summary and
sends one transactional mail through a provider API or SMTP, is the plan's pattern). In-distribution knowledge only.

#### 0A. Premise challenge

The real problem: the owner learns about breakage only when opening a session. The outcome they asked for: one mail per
round that says what ran, what broke, what got fixed and what to ask, and issues that sit where the feature work is
(milestones). Doing nothing: PR #177's comment already reaches the owner through GitHub's own notification mail, but
(a) it isn't grouped by feature, (b) GitHub's notification mail depends on the owner's watch settings, and (c) the owner
approved a direct email in the new PRD. The plan solves the pain directly, not a proxy.

| Premise | Claim | Receipt | Verdict |
|---|---|---|---|
| P1 | automation.py is 16,070 bytes, so mail and cost go in new scripts | `wc -c` [measured: wc] | verified |
| P2 | regression issues get no milestone today | actions.py:146-150 (`gh("issue","create",... "--label","defect")`, no milestone) | verified |
| P3 | health files everything on Backlog today | file.py:139 (`"--milestone", BACKLOG`) | verified |
| P4 | the digest state lives in the issue body marker `open=..., run=...` | automation.py:32 (`STATE`), :258 (`issue edit --body intro+marker`) | verified |
| P5 | AUT-2's schedule is already every 4 h plus tags | regression.yml:4-7 | verified |
| P6 | tests.py's map names a feature page per row, `Other` when none | tests.py `list --tsv` output col 1 (`Automation`, `Delivery`) | verified |
| P7 | the health job has `issues: write, actions: read` | health.yml:8-11 | verified |
| P8 | `milestone.features()` is pure (reads docs.tsv only) | milestone.py:40-50 | verified |
| P9 | gh can set a milestone by number only through the REST API | gh `issue create --milestone` takes a title [estimated: gh docs] | unverified |
| P10 | the Cloudflare REST send API takes `{to, from, subject, text, html}` with a Bearer token | developers.cloudflare.com email-service REST API page, read 2026-11-10 | verified |

unverified=1 (P9: the plan avoids the question by always using the REST API, so either answer works).

#### 0B. Existing code leverage

| Sub-problem | Existing code | Plan |
|---|---|---|
| Find the digest issue | automation.py `digest_issue()` | reuse in mail.py (import) |
| Read/write the marker | automation.py `STATE`, `compose()` | extend; shared parser lives in one place |
| Feature table | milestone.py `features()` | import (never `ensure()`) |
| Milestone create | milestone.py `ensure()` (writes wiki) | the health workflow already calls `milestone.py new`; file.py reads `state=all` itself |
| Issue filing plan/apply | file.py `plan()/apply()` | extend with milestone + move |
| Regression filing | actions.py inline script | extend inline (self-contained by design) |
| Run summary lines | both workflows' summary steps | `## Round` appended by the digest |
| Settings table | settings.py `TABLE` | four new rows |

REALITY: premise-table pass 10 premises, unverified=1 (P9, avoided by design) automation.py:32
REALITY: already-done pass nothing on origin/main since 2026-11-09 touches automation.py/file.py/actions.py/workflows; no commit greps mail/milestone filing a23c125
REALITY: surface-check pass `regression.py workflow`, `automation.py workflow|digest`, `milestone.py new --all --live`, `criteria.py review --user --date`, `regression.py add|red` exist per their --help; new `mail.py send` is planned skills/workflow-health/scripts/milestone.py:9
REALITY: binding-decisions pass suite-decision-search returned no branch decisions; the plan has no Binding decisions section; owner decisions are the PRD (2026-11-10) and the operation's brief .loop/goals/automation-email.md:1
REALITY: numbers pass 16,070/20,246/12,213/8,109 bytes [measured: wc]; 45 min [PRD AUT-7]; 4 h cron [measured: regression.yml:5]; regression run 33.4 min on 2026-11-10 [measured: gh run view 42790770283] .github/workflows/regression.yml:5
REALITY: deferred-asks pass no linked issue; the PRD's AUT-1 and AUT-5 are met by PR #177 and kept docs/wiki/Automation.md:22
REALITY: pr-count pass no .the suite/ship-policy.json; one PR for the goal .loop/goals/automation-email.md:1

Note from the numbers row: the last regression run took 33.4 min of job time on its own [measured]. With health added, a
round is likely near or over 45 min today, so the flag will fire on day one. That is the PRD's intent (show it so the
owner can slow the schedule), not a plan defect; the wiki says how to slow a routine.

#### 0C. Dream state

```
  CURRENT STATE                     THIS PLAN                              12-MONTH IDEAL
  scheduled rounds post a flat ---> issues on feature milestones,    --->  each round's mail is the owner's
  comment; issues on Backlog or     one mail per round grouped by          whole status: what broke, who/what
  no milestone; cost unknown        feature, cost shown and flagged        fixes it, cost trend, one click to
                                                                           start the fix goal
```
The plan moves straight toward the ideal; the gap left is the cost trend over rounds and one-click fix links.

#### 0D. Alternatives

No new approach decision was needed: the design's Approach A (two new scripts) was chosen at the idea step with B and C
ruled out for stated reasons (key exposure and size; a deployed service against the PRD's non-goals).

#### 0E. Mode

Mode: SELECTIVE EXPANSION (autoplan override); approved decisions: none. The plan adds capability (mail, milestones,
cost) to an existing system across about 12 files [estimated: 2 new scripts, automation.py, file.py, actions.py,
settings.py, seed.py, two workflows, config, docs.tsv, wiki page, regression.tsv, one new toy test], under the 15-file
reduction threshold, so cherry-picks are offered one by one and the baseline is hardened.

#### 0F/0G. Expansion candidates (cherry-pick ceremony; auto-decided by P1/P2/P3)

HOLD checks first: complexity is 12 files and 2 new modules (mail.py, rounds.py); each is a separate concern (secrets
isolation, size limit), so fewer parts would put the mail key in the digest step. Minimum change for the goal is the
plan as written; nothing in it is deferrable without breaking a done line.

| # | Proposal | Effort | Risk | Decision | Reasoning |
|---|---|---|---|---|---|
| E1 | `mail.py test`: send one sample mail by hand from the Actions tab, to prove the secrets before a round | S | low | ACCEPTED | P2: in blast radius, < 1 day; the owner's first setup otherwise waits up to 4 h to learn a secret is wrong. Runs only by `workflow_dispatch` with an input `mail_test: true`. |
| E2 | Cost trend: keep the last 6 rounds' minutes in the marker and show a sparkline | M | low | DEFERRED | P3: outside the done lines; marker grammar would grow. Logged as a finding note for later. |
| E3 | Retry a failed send once after 30 s | S | low | ACCEPTED | P1: a transient 429/503 from the provider would otherwise lose the round's mail until a rerun; the REST error table lists 429 and 503 as retryable. |
| E4 | HTML mail with feature colours and a summary line at the top | S | low | SKIPPED | P5: plain escaped HTML meets AUT-4; styling adds nothing the owner asked for. |
| E5 | Mail only when something changed (new or fixed), else skip | S | med | SKIPPED | Contradicts AUT-4 ("after each round, one email"). |
| E6 | A `digest_mail_to_name` / reply-to setting | S | low | SKIPPED | YAGNI. |

#### 0H. CEO plan and spec review

CEO summary: `<private path>`.

#### 0I. Temporal interrogation

```
  HOUR 1 (foundations):  the marker grammar and the milestone-number lookup are shared by automation.py and mail.py:
                         put parse/marker in rounds.py? No: in automation.py, imported by mail.py (same folder).
  HOUR 2-3 (core logic): the comment author filter needs the REST login string `github-actions[bot]`; gh issue view
                         --json comments returns `author.login` = `github-actions` (no [bot]); use the REST API.
  HOUR 4-5 (integration): regression.yml is generated and lane-control edits it: regenerate after merging main.
                         The health workflow's step list is asserted by test-automation.sh's step() helper.
  HOUR 6+ (polish/tests): a local Cloudflare stub (http.server on 127.0.0.1) and an SMTP stub (socketserver, plain
                         SMTP lines) inside the toy test; secret-scrub assertions over every output file.
```
Effort: human team ~3 days; CC ~3-4 hours.

#### 0H result

Spec review: 3 launches (7/10, 7/10, 8/10), 29 findings (round 1: 15 minor; round 2: 1 blocking, 7 minor; round 3:
2 blocking, 4 minor), stop at the cap. The 2 round-3 blocking fixes are applied and checked in the plan text (issues
verified: 2 of 2; not reviewer-confirmed). Document approval: auto-decided A (both inputs carry the exact decisions).

#### Step 0.5: dual voices

Native CEO voice (Claude subagent, INPUT ceo 76ab0621..., full read of 209 lines): 11 findings (1 critical, 5 high,
5 medium). Codex CEO voice (gpt-6-astra, OUTSIDE_STATUS completed): 6 findings (1 critical, 4 high, 1 medium).

```
CEO DUAL VOICES — CONSENSUS TABLE:
  Dimension                            Claude  Codex  Consensus
  1. Premises valid?                    no      no     CONFIRMED: issue (delivery state, round membership)
  2. Right problem to solve?            partly  yes    DISAGREE (Claude: GitHub mail may suffice; Codex: keep email)
  3. Scope calibration correct?         no      partly CONFIRMED: issue (over-built mail state; test cost)
  4. Alternatives sufficiently explored? no     no     CONFIRMED: issue (native notifications, Marketplace action)
  5. Competitive/market risks covered?  n/a     partly DISAGREE (build-vs-buy vs onboarding friction)
  6. 6-month trajectory sound?          no      no     CONFIRMED: issue (state erased by later rounds; test runtime)
```

Dispositions (each one row in the Decision Audit Trail):
- C-1 (Codex 1, critical): enforce a hard 45-minute stop. The frozen done line asks to show and flag; a hard stop would
  cut the full suite short (AUT-2) since regression alone took 33.4 min [measured]. Kept as flag; TASTE decision d1
  at the final gate.
- C-2 + N-F6: round membership and spend. ACCEPTED: round duration (flag) and Actions minutes since the last round
  (spend, every run counted) are separate numbers, each named.
- C-3 + N-F5: delivery state erased by the next round. ACCEPTED: the mail state moves onto the round's own comment.
  The "possibly missed" side is shown in the next digest's `email` row.
- N-F4: switch to at-least-once. REJECTED: contradicts the frozen done line "a rerun sends nothing twice".
- N-F3 + C-3/C-5: silent misconfiguration. ACCEPTED: an `email` row in every digest (`not set up`, `off`, outcome).
- C-5: real onboarding proof. ACCEPTED as a Verify by hand step (fresh fork, Mail test workflow, inbox).
- N-F1/N-F2: use GitHub notifications or a Marketplace mail action. REJECTED: the owner approved a direct email
  through Cloudflare in the 2026-11-10 PRD (AUT-4); a third-party action would hold the mail key (supply chain).
  Both models do not agree to change the owner's direction (Codex keeps both transports), so no User Challenge.
- N-F7: split into four PRs. REJECTED: one goal, one pull request (pr-count row); the done lines are one goal.
- N-F8: hand-written HTML drifts. ACCEPTED as a test (no leftover Markdown in the HTML of a real digest).
- N-F9: criteria_max and relayed review outside the done lines. ACCEPTED as TASTE decision d2 at the gate.
- N-F10 + C-6: test cost. ACCEPTED: one harness per group, pure functions checked without stubs.
- N-F11: mail_test guards on five steps. ACCEPTED: a separate dispatch-only `mail-test.yml` (TASTE d3).
- C-4: digest value (lead with change, "Fixed" means "no longer open"). PARTLY: groups already lead with New; the
  "Fixed" meaning is today's (PR #177) and AUT-4's word; noted in NOT in scope.

#### Review sections

Current scope: mode SELECTIVE EXPANSION (autoplan override). Accepted: E1 (as mail-test.yml), E3 (safe retries),
the consensus items above. Deferred: E2 (cost trend). Rejected: E4, E5, E6, at-least-once, PR split, native-only
delivery. Pending for the owner: d1, d2, d3.

**Section 1: Architecture.**
```
                       +-------------------- health.yml (every 4 h, :47) -----------------------+
 regression.yml (:17)  | routine -> health check -> milestone.py new --all -> file.py (findings  |
  rows -> issues on    |   on feature milestones) -> judge? -> automation.py digest ------------+--> comment R
  feature milestones   |                                  |  uses rounds.py (state + cost)      |    (marker run/open
  (inline, actions.py) |                                  v                                     |     + mailing/mailed)
                       |                           ## Round in summary                          |
                       |   mail.py send (secrets only here) --reads comment R--> Cloudflare | SMTP --> owner inbox
                       +-------------------------------------------------------------------------+
 mail-test.yml (dispatch only) -> mail.py test -> provider -> inbox
```
Data flow paths for the mail: happy (comment R found, sent, comment marked mailed); nil (no digest issue or no
comment R: exit 1, nothing sent); empty (no open issues: the digest still lists what ran and the email row; one
mail); error (provider refuses: mailing removed, exit 1; crash: mailing stays, never resent). State machine of a
round's comment marker: `posted -> mailing -> mailed`, `mailing -> posted` only on a known refusal; `mailed` is
terminal; `posted -> mailed` without `mailing` is impossible (mailing is written first or nothing is sent).
Coupling: mail.py and automation.py share rounds.py (justified: one marker grammar). Security boundary: only the mail
step and mail-test.yml hold the mail secrets; the digest gets one boolean. Single point of failure: the job token's
`issues: write` (both the digest and the mail state need it). Rollback: set `digest_mail` off (mail stops, digest
stays) or revert the PR; regression/health filing reverts with it. Value test: the `email` row and `## Round` are
product observability (Prime Directive 5), not process artifacts. Findings: 2 (state on comment; separate test
workflow), both applied above.

**Section 2: Error and rescue map** (registry below). 14 paths, 0 gaps after the applied fixes. The catch-all in
mail.py is deliberate and named: it exists to keep tracebacks (with URLs and addresses) out of logs, prints the
exception class, and exits 1.

**Section 3: Security.**
| Threat | Likelihood | Impact | Mitigated |
|---|---|---|---|
| Third party posts a look-alike digest comment to phish the owner | Med (public repo) | High | yes: only `github-actions[bot]` comments with the exact run marker |
| Secret value in logs through an error or traceback | Med | High | yes: scrub() and the top-level handler; GitHub masks secrets too |
| `DIGEST_MAIL_API` pointed at an attacker host | Low | High | yes: local URLs only; never set by the workflow; tested |
| A milestone or issue title injecting into the comment or mail | Med | Med | yes: titles only in headings, escaped in HTML; marker carries numbers |
| An issue title as an instruction in the request to the agent | Med | Med | yes (PR #177): requests name issues by number and link only |
| Header injection in the mail subject | Low | Med | yes: subject built from counts and the repo name only |
| A row command reading the mail secrets | Low | High | yes: regression rows run in a separate workflow with no mail secrets |
Findings: 0 open.

**Section 4: Data flow and edge cases.** Mail flow: INPUT (comment R) -> VALIDATION (bot author, marker run=R) ->
TRANSFORM (strip mention and marker, text + HTML) -> PERSIST (comment marker mailing/mailed) -> OUTPUT (provider).
Shadow paths: nil (no comment: exit 1), empty body (only the table: still sent), too long (25 MiB limit; a digest
is a few KB), timeout (not retried after the request was sent), duplicate (mailing/mailed), stale (an old run's
rerun: its own comment's marker), encoding (UTF-8 text and HTML). Async ordering: invariant "at most one mail per
round". Schedules: (a) two attempts of the same run (rerun while the first still runs) are prevented by the
workflow's `concurrency: group: health, cancel-in-progress: false` (one health run at a time); (b) round R2's digest
vs R1's mail rerun touch different comments; the body write only moves forward (`run` older than R is the only
case mail.py writes it). Regression test: the old-run rerun and the crash cases. Findings: 0 open.

**Section 5: Code quality.** Fits existing patterns (plan/apply in file.py, dry-run-free gh helpers in automation.py).
Reuse: digest_issue/parse move once into rounds.py. The new inline regression filing must check gh return codes,
which today's inline script doesn't: the plan's create goes through `gh api` and prints a FAILED line on error.
Finding 1 (applied as obligation below).

**Section 6: Tests.** Diagram:
```
 NEW                         TYPE         HAPPY                      FAILURE                   EDGE
 rounds.round_cost           unit(py -c)  sum of two runs            gh unreadable -> None     running reg, no reg, tag run
 rounds.parse/marker         unit         new form                   garbage -> no state       old form, empty open, order
 automation digest grouping  toy          grouped by milestone       gh list fails (exists)    fixed under old milestone
 automation email row        toy          sent                       may have been sent        not set up, off
 mail.py send                toy+stub     one mail, marked mailed    provider 401/500          429 retry, crash, old rerun
 mail.py secrets             toy          missing -> named, exit 0   scrub on error            DIGEST_MAIL_API refused
 mail.py test / mail-test.yml toy+stub    one test mail              missing secret            no gh call
 file.py milestones          toy          feature milestone          no milestone -> Backlog   owner-placed stays, closed
 regression filing           toy          feature milestone          gh api fails -> FAILED    Other -> Backlog, created
 schedule                    grep         17 */4 + tags v*           -                         -
```
Each new behavior has a happy, a failure and an edge case in the plan. Flakiness: the local stubs bind port 0 and the
retry wait is 0 in tests; no real network. Findings: 0 open.

**Section 7: Performance.** Gh calls per digest: one issue list per label, one milestone list, two run views, up to 20
runs listed for the spend; mail.py: one comment page, two PATCHes. Bounded; no loops over history (the comment read
uses `since=`). Findings: 0.

**Section 8: Observability.** Every mail outcome is one `MAIL:` line in the log and the summary; the digest's `email`
row reports the previous round's outcome to the owner; `## Round` and `::warning::` show cost. Runbook (wiki Usage):
`not set up` -> add secrets; `may have been sent` -> check the inbox, then nothing to do; `refused` -> check the token
or domain; over 45 min -> slow a routine. Findings: 0 open.

**Section 9: Deployment.** No migration. Old digest bodies (`open=12,9 run=R`) read as milestone 0. The first round
after merge counts its spend window as its own two runs. Rollout: merge, then the owner adds secrets and runs Mail
test; until then every mail step says `not set up` and writes nothing. Rollback: `digest_mail: off`, or revert.
Findings: 0.

**Section 10: Trajectory.** Debt: one more marker grammar (documented in rounds.py), one hand-written HTML renderer
(tested). Reversibility 4/5 (a revert restores the old marker reader too, and old bodies stay readable). Next: E2 cost
trend; a mail per changed condition only if the owner asks. The cherry-picks accepted were the right ones; the
rejected at-least-once option was load-bearing for nothing.

**Section 11: Design.** SKIPPED (no UI scope).

#### Required outputs (CEO)

REALITY: premise-table pass 10 premises, unverified=1 (P9, avoided by design) automation.py:32
REALITY: already-done pass nothing on origin/main since 2026-11-09 touches these files a23c125
REALITY: surface-check pass every named command exists per --help; mail.py is new skills/workflow-health/scripts/milestone.py:9
REALITY: binding-decisions pass no branch decisions; owner decisions are the PRD and the brief .loop/goals/automation-email.md:1
REALITY: numbers pass sizes [measured: wc -c skills/workflow-health/scripts/automation.py]; 45 min .loop/goals/automation-email.md:14; regression 33.4 min [measured: gh run view 42790770283 --json jobs] skills/workflow-regression/scripts/actions.py:90
REALITY: deferred-asks pass no linked issue docs/wiki/Automation.md:22
REALITY: pr-count pass one PR .loop/goals/automation-email.md:1

NOT in scope:
- Deferred: E2 cost trend over rounds (outside the done lines; this repo has no TODOS.md, so it is noted here and in
  the CEO plan).
- Deferred: a hard 45-minute stop on a round (pending d1; the done line asks to flag).
- Rejected: E4 styled HTML, E5 mail only on change (contradicts AUT-4), E6 reply-to, at-least-once delivery (contradicts
  the done line), native notifications only and a Marketplace action (owner chose Cloudflare; key exposure), one PR
  per feature (one goal).
- Unchanged: "Fixed" keeps PR #177's meaning (no longer open), the PRD's word.

What already exists: digest_issue/compose/STATE (automation.py), features() (milestone.py), plan/apply/preview
(file.py), the inline filing script (actions.py), settings TABLE (settings.py), the stub-gh toy harness
(test-automation.sh). All reused or extended.

Dream state delta: after this plan the owner gets one trustworthy mail per round with feature grouping, cost and
spend; still missing are a cost trend and verified-fix tracking.

Error and rescue registry:
```
 CODEPATH                  | FAILURE                         | CLASS / SIGNAL           | RESCUED | ACTION                              | OWNER SEES
 mail.send secrets         | a secret missing                | env empty                | Y       | skip, name them, exit 0             | MAIL: skipped ... + email row
 mail.send find comment    | no digest issue / no comment R  | none found               | Y       | exit 1                              | MAIL: no digest comment
 mail.send gh read         | gh fails                        | non-zero exit            | Y       | exit 1                              | MAIL: gh couldn't read
 mail.send mark mailing    | PATCH fails                     | non-zero exit            | Y       | send nothing, exit 1                | MAIL: couldn't mark
 send_cloudflare           | 429 / 503                       | HTTPError                | Y       | retry once after 30 s               | (after 1 retry)
 send_cloudflare           | 401/403/400/500                 | HTTPError + code         | Y       | remove mailing, exit 1, scrubbed    | MAIL: cloudflare refused it
 send_cloudflare           | permanent bounce                | result.permanent_bounces | Y       | remove mailing, exit 1              | refused
 send_smtp                 | 4xx before DATA / no connect    | SMTP*Refused, ConnectErr | Y       | retry once                          | (after 1 retry)
 send_smtp                 | auth / after DATA / disconnect  | SMTPAuth/DataError       | Y       | exit 1 (mailing kept after DATA)    | MAIL: smtp refused it
 mail top-level            | anything else                   | Exception (named)        | Y       | scrubbed one line, exit 1           | MAIL: failed: <Class>
 mail.send mark mailed     | PATCH fails after send          | non-zero exit            | Y       | exit 1, mailing kept (no resend)    | MAIL: sent ... couldn't mark
 rounds.round_cost         | gh can't read runs              | non-zero / bad JSON      | Y       | None                                | round cost: not read
 file.apply milestone      | milestone missing               | lookup miss              | Y       | Backlog number, NOTE line           | NOTE
 regression filing         | gh api create/patch fails       | non-zero exit            | Y       | FAILED line, run continues          | log line
```
Failure modes registry:
```
 CODEPATH            | FAILURE MODE                  | RESCUED? | TEST? | USER SEES?            | LOGGED?
 mail.send           | duplicate mail on rerun       | Y        | Y     | nothing (no resend)   | Y
 mail.send           | missed mail after crash       | Y        | Y     | email row next round  | Y
 mail.send           | phishing look-alike comment   | Y        | Y     | nothing sent from it  | Y
 mail.send           | secret in logs                | Y        | Y     | ***                   | Y
 digest              | body write fails              | Y        | Y     | repaired next attempt | Y
 rounds              | wrong run paired              | Y        | Y     | spend counts all runs | Y
 file/regression     | owner's milestone overwritten | Y        | Y     | stays                 | Y
 file/regression     | closed milestone              | Y        | Y     | used as is            | Y
```
0 critical gaps.

Diagrams produced: architecture, data flow with shadow paths, comment-marker state machine (Sections 1 and 4).
Stale diagram audit: docs/wiki/Automation.md has no ASCII diagram; the workflow-health and workflow-regression SKILL.md
files have none for these paths. None stale.

Implementation tasks (CEO):
- [ ] **T1 (P1, human ~4h / CC ~30min)** — mail.py — per-round state on the comment, at-most-once, safe retries, scrub
  - Surfaced by: Step 0.5 C-3, Section 2. Files: skills/workflow-health/scripts/mail.py, rounds.py. Verify: `bash dev/toy/test-automation-email.sh mail`
- [ ] **T2 (P1, human ~2h / CC ~15min)** — rounds.py — round duration and spend since the last round
  - Surfaced by: C-2/N-F6. Files: skills/workflow-health/scripts/rounds.py. Verify: `... rounds`
- [ ] **T3 (P1, human ~1h / CC ~10min)** — automation.py — email row and DIGEST_MAIL_SET
  - Surfaced by: N-F3/C-5. Files: automation.py, health.yml. Verify: `... digest`
- [ ] **T4 (P2, human ~1h / CC ~10min)** — mail-test.yml written by automation.py
  - Surfaced by: N-F11. Files: automation.py, .github/workflows/mail-test.yml. Verify: `... mailtest`
- [ ] **T5 (P2, human ~1h / CC ~10min)** — regression filing checks gh results
  - Surfaced by: Section 5. Files: actions.py. Verify: `... regression`

```
  +====================================================================+
  |            MEGA PLAN REVIEW — COMPLETION SUMMARY                   |
  +====================================================================+
  | Mode selected        | SELECTIVE EXPANSION                         |
  | System Audit         | parallel edits to regression.yml, docs.tsv  |
  | Step 0               | A (two scripts); E1, E3 accepted            |
  | Section 1  (Arch)    | 2 issues found                              |
  | Section 2  (Errors)  | 14 error paths mapped, 0 GAPS               |
  | Section 3  (Security)| 7 threats, 0 open, 0 High open              |
  | Section 4  (Data/UX) | 7 edge cases mapped, 0 unhandled            |
  | Section 5  (Quality) | 1 issue found                               |
  | Section 6  (Tests)   | Diagram produced, 0 gaps                    |
  | Section 7  (Perf)    | 0 issues found                              |
  | Section 8  (Observ)  | 0 gaps found                                |
  | Section 9  (Deploy)  | 0 risks flagged                             |
  | Section 10 (Future)  | Reversibility: 4/5, debt items: 2           |
  | Section 11 (Design)  | SKIPPED (no UI scope)                       |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (8 items)                           |
  | What already exists  | written                                     |
  | Dream state delta    | written                                     |
  | Error/rescue registry| 14 rows, 0 CRITICAL GAPS                    |
  | Failure modes        | 8 total, 0 CRITICAL GAPS                    |
  | TODOS.md updates     | 0 items (no TODOS.md; E2 noted)             |
  | Scope proposals      | 6 proposed, 2 accepted                      |
  | CEO plan             | written                                     |
  | Outside voice        | codex (gpt-6-astra) completed               |
  | Lake Score           | N/A                                         |
  | Diagrams produced    | 3 (architecture, data flow, state machine)  |
  | Stale diagrams found | 0                                           |
  | Unresolved decisions | 3 (d1, d2, d3: taste, for the final gate)   |
  | Reality rows         | 7/7 rows (PLAN_REALITY), 1 unverified       |
  +====================================================================+
```


### Phase 2: Design review

Skipped: no UI scope (the scope tool found no rendered file or visual noun; the only UI term was "form").

### Phase 2.5: DX review (DX POLISH, autoplan override), Step 0

Product type (auto-detected, auto-confirmed P6): a Claude Code skill pack whose surface here is a CLI (`mail.py`,
`automation.py workflow`) plus GitHub Actions workflows (Platform). Primary: Claude Code skill / CLI.

```
TARGET DEVELOPER PERSONA
========================
Who:       a solo developer who adopted the loop template in their own repo (the template's README audience:
           "for the owner of a repo that uses the loop"), working with AI agents; second reader: the worker agent
           that reads MAIL:/DIGEST: lines unattended.
Context:   they merged this release, or are adopting the template, and want the round's mail without opening GitHub.
Tolerance: ~10 minutes of setup, once; zero tolerance for a mailer that fails silently.
Expects:   secret names listed in one place, one button to prove it works, and mail that says what to do.
```

Empathy narrative (predicted, grounded in README.md:59-61 and docs/wiki/Automation.md:14-18): "I read that the digest
'GitHub emails you'. I upgrade the skills with update.py and wait four hours. Nothing new arrives, because update.py
copies skills only (update.py:5-11) and my health.yml is the old one without a mail step. I find the wiki's Usage,
see seven secret names and a Cloudflare domain requirement, pick SMTP because I already have a Gmail app password,
set `digest_mail` to smtp, add four secrets, and then I have to wait for the next round to know if it worked. If a
secret is wrong I see a red step in a run I never open." Observed: README.md:61 and update.py:5-11. Predicted: the
wait and the silent failure (the plan's Mail test workflow and email row answer them).

Competitive benchmark (no web research this step: in-distribution knowledge, labeled estimated):
| Tool | Start -> result | Time + evidence type | DX choice | Source |
|---|---|---|---|---|
| GitHub notifications (today's digest) | watch issue -> mail | ~1 min, estimated | zero setup, mail depends on watch settings | automation.py:273 |
| A Marketplace SMTP action in a workflow | add action + 3 secrets -> mail on next run | ~5-10 min, estimated | YAML only; third-party action holds the password | in-distribution |
| Cloudflare Email REST from CI | onboard domain + token -> curl | domain onboarding unknown (DNS), then ~3 min | provider API | developers.cloudflare.com REST page |
| This plan (SMTP path) | app password + 4 secrets + `digest_mail: smtp` + Mail test -> inbox | ~6-8 min, estimated | one test button | plan items 4, 8, E1 |
| This plan (Cloudflare path) | onboarded domain + token + 4 secrets + Mail test -> inbox | ~4 min after onboarding, estimated | one test button | plan items 4, E1 |

TTHW target (auto-decided, P5): Competitive, 2-5 minutes from "credentials in hand" to "test mail in inbox"; domain
onboarding and app-password creation are outside the clock and named as prerequisites.

Magical moment (auto-decided, existing capability): run the Mail test workflow from the Actions tab and see the mail
within a minute (E1). The round mail then carries an `email` row, so the owner knows it keeps working.

Mode: DX POLISH (override): an enhancement to an existing product.

Developer journey (trace and friction):
```
STAGE           | DEVELOPER DOES                               | FRICTION POINTS                              | STATUS
1. Discover     | reads README Automation paragraph, wiki Usage| README says "GitHub emails you" (stale)      | fixed (README line, touches asked)
2. Install      | update.py, or setup on a new repo            | update.py doesn't rewrite workflows; old     | fixed (stale-workflow warning + upgrade line)
                |                                              | health.yml has no mail step, silently        |
3. Hello World  | adds secrets, runs Mail test                 | which secrets for which sender               | fixed (one table in Usage; missing ones named)
4. Real Usage   | reads the round mail                         | -                                            | ok
5. Debug        | reads MAIL:/DIGEST: lines, email row         | lines lack stable codes and fix lines        | fixed (codes + Fix:)
6. Upgrade      | next template release                        | marker grammar change                        | ok (old form reads)
```

First-time developer report (SMTP path, predicted from the plan):
```
T+0:00  Opens wiki Automation Usage, finds "Email" with a secrets table.
T+1:00  Adds SMTP_USER, SMTP_PASSWORD, DIGEST_TO, DIGEST_FROM; sets digest_mail to smtp in .loop/config.json, commits.
T+3:00  Actions tab -> Mail test -> Run workflow.
T+4:00  Mail arrives. (If a secret is missing: the step names it with MAIL_NOT_SET_UP and the Fix line.)
T+4:30  Done; the next round mail shows "email | sent".
```

#### Step 0.5: DX dual voices

Native DX voice (Claude subagent, INPUT dx fa2d36af..., full read of 238 lines): getting started 6, API 7, errors 4
(capped: 3 CAP4, 6 CAP6), docs 6, escape hatches 5. Codex DX voice (gpt-6-astra, completed): TTHW 5, errors 4 (CAP4),
API 6, docs 5, upgrade 4; 9 findings.

```
DX DUAL VOICES — CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Getting started < 5 min?          no(6)   no(5)  CONFIRMED: needs a copy-paste quickstart
  2. API/CLI naming guessable?         yes(7)  yes(6) CONFIRMED: ok, small fixes (secret names, readiness)
  3. Error messages actionable?        no(4)   no(4)  CONFIRMED: CAP4 green test; codes, fixes, recovery missing
  4. Docs findable & complete?         no(6)   no(5)  CONFIRMED: quickstart + troubleshooting table
  5. Upgrade path safe?                n/a     no(4)  single-voice (Codex): workflows not rewritten on update
  6. Dev environment friction-free?    n/a     n/a    N/A (neither scored it separately)
```
Single-voice High (Codex): existing adopters update and get no mail step; accepted (it matches the native empathy
narrative's own finding in Step 0).

Dispositions (Decision Audit Trail rows):
- DX-1 (both, CAP4): `mail.py test` exits 1 when anything stops it sending (off, missing secrets). ACCEPTED.
- DX-2 (native CAP4): partial secrets in `send` exit 1 and name what's missing; exit 0 only when no mail secret is set
  at all (never set up) or `digest_mail` is off. ACCEPTED.
- DX-3 (native CAP4): the regression filing counts failures and exits 1 after the last row when any filing failed.
  ACCEPTED.
- DX-4 (Codex High): an old run's digest rerun never rewinds the body; repair only when the body's run is older (run
  ids compared as integers). ACCEPTED.
- DX-5 (Codex High + Step 0): upgrade activation: a stale tool-written workflow is reported in every run, the Usage
  gives the upgrade sequence and the rollback note. ACCEPTED.
- DX-6 (both): stable codes, a `Fix:` line and a recovery class on every MAIL/DIGEST/FILED line; a trace pointer on the
  catch-all; reasons on `round cost: not read`. ACCEPTED.
- DX-7 (native): bad `digest_mail`, `smtp_port` or `DIGEST_MAIL_RETRY_SECONDS` rejected before any work. ACCEPTED.
- DX-8 (Codex): email row checks `off` first, readiness per sender, history labeled "previous round". ACCEPTED.
- DX-9 (Codex): comment lookup paginates within the `since` window. ACCEPTED.
- DX-10 (Codex): spend line names itself a creation-window figure. ACCEPTED.
- DX-11 (Codex): one row per test group, each group one harness run, so rows equal harness starts. ACCEPTED.
- DX-12 (both): copy-paste quickstart, token permission, Gmail app-password note, troubleshooting table. ACCEPTED.
- DX-13 (native low): SMTP secrets renamed `DIGEST_SMTP_USER`, `DIGEST_SMTP_PASSWORD`. ACCEPTED (consistency).
- DX-14 (native): `mail.py preview`. REJECTED (DX POLISH: no new subcommand; Mail test and the comment itself show the
  text).
- DX-15 (native): `mail.py clear` to unstick `mailing`. REJECTED as code; the Fix line gives the exact human edit.
- DX-16 (native): scrub case-insensitive and the address's local part; `DIGEST_MAIL_API` refusal shows scheme and host.
  ACCEPTED.

#### DX passes (before -> after)

Pass 1 Getting started 5 -> 8: quickstart with `gh secret set` lines and `gh workflow run mail-test.yml`, Mail test
fails loudly; prerequisites (onboarded domain or app password) named. Residual: Cloudflare onboarding time is outside
our control.
Pass 2 API/CLI 6 -> 8: `send`/`test`, consistent `DIGEST_*` secret names, settings validated; no new subcommands.
Pass 3 Errors 4 (capped) -> 8. Matrix after fixes:
```
ERROR PATH MATRIX (agent-ready-v1)
Path                         | Class       | what | fix | recovery | code | context | trace | redaction | channel | Cap
mail send: secrets partial   | validation  | pass | pass| N/A      | pass | N/A     | N/A   | pass      | pass(1) | -
mail test: cannot send       | validation  | pass | pass| N/A      | pass | N/A     | N/A   | pass      | pass(1) | -   (was CAP4)
mail send: mailing w/o mailed| unknown out | pass | pass| pass     | pass | pass    | N/A   | pass      | pass(1) | -   (was CAP6)
mail send: provider refused  | dependency  | pass | pass| pass     | pass | pass    | N/A   | pass      | pass(1) | -   (was CAP6)
mail: unexpected exception   | unexpected  | pass | pass| pass     | pass | pass    | pass  | pass      | pass(1) | -   (was CAP6)
regression filing failed     | dependency  | pass | pass| pass     | pass | pass    | N/A   | pass      | pass(1) | -   (was CAP4)
```
Corrected lines (examples):
`MAIL: test not sent: missing secrets DIGEST_SMTP_PASSWORD (MAIL_SECRETS). Fix: gh secret set DIGEST_SMTP_PASSWORD, then run the Mail test workflow again.` exit 1.
`MAIL: a mail for run 123 may already have been sent: an earlier attempt stopped after sending began (side effects: unknown) (MAIL_UNKNOWN). Fix: check your inbox for "Automation digest" near 12:47 UTC; if none arrived, delete the word mailing from the last line of <comment url> and rerun this job.` exit 1.
Pass 4 Docs 5 -> 8: Usage leads with a quickstart, then a troubleshooting table keyed by code, each email-row state
with the owner's next step.
Pass 5 Upgrade 4 -> 7: stale-workflow warning (`STALE_WORKFLOW`), upgrade sequence, rollback note (an old checkout
cannot read the new marker: restore the body's first line or close the digest issue). Residual: no automatic rewrite
(update.py stays skills-only by design).
Pass 6 Dev environment 7 -> 8: local stubs, `DIGEST_MAIL_API` for local tests only, groups runnable alone.
Pass 7 Community 6 -> 6: no change in scope (template repo, MIT, wiki); no findings.
Pass 8 Measurement 4 -> 6: the fresh-fork timing in Verify by hand measures the TTHW clock once; the email row keeps
delivery visible per round. No telemetry (not asked).

```
+====================================================================+
|              DX PLAN REVIEW — SCORECARD                             |
+====================================================================+
| Dimension            | Score  | Prior  | Trend  |
|----------------------|--------|--------|--------|
| Getting Started      |  8/10  |  5/10  |  ↑     |
| API/CLI/SDK          |  8/10  |  6/10  |  ↑     |
| Error Messages       |  8/10  |  4/10  |  ↑     |
| Documentation        |  8/10  |  5/10  |  ↑     |
| Upgrade Path         |  7/10  |  4/10  |  ↑     |
| Dev Environment      |  8/10  |  7/10  |  ↑     |
| Community            |  6/10  |  6/10  |  =     |
| DX Measurement       |  6/10  |  4/10  |  ↑     |
+--------------------------------------------------------------------+
| TTHW                 | ~4 min | ~7 min |  ↑     |
| Competitive Rank     | Competitive                                 |
| Magical Moment       | designed via the Mail test workflow         |
| Product Type         | Claude Code skill / CLI + Actions           |
| Mode                 | POLISH                                      |
| Overall DX           |  7.4/10 | 5.1/10 | ↑    |
+====================================================================+
| DX PRINCIPLE COVERAGE                                               |
| Zero Friction      | covered (quickstart, one button)               |
| Learn by Doing     | covered (Mail test)                            |
| Fight Uncertainty  | covered (codes, Fix lines, email row)          |
| Opinionated + Escape Hatches | covered (cloudflare default, smtp, off) |
| Code in Context    | covered (gh commands in Usage)                 |
| Magical Moments    | covered (test mail within a minute)            |
| Agents Are Users   | covered (one result line per outcome, codes)   |
+====================================================================+
```

DX implementation checklist:
```
[x] Time to hello world < 5 min (credentials in hand)   [ ] measured once in a fresh fork (Verify by hand)
[x] Installation: existing workflows rewritten by one command, stale ones reported
[x] First run produces meaningful output (Mail test)
[x] Every MAIL/DIGEST/FILED line meets the agent-ready contract
[x] Names guessable; every setting has a default; bad values rejected
[x] Usage has copy-paste commands; troubleshooting table by code
[x] Upgrade sequence and rollback note in Usage and the changelog
[x] Works in CI without special configuration (secrets only)
[ ] TypeScript types: n/a (Python standard library)
```

NOT in scope (DX): `mail.py preview` and `mail.py clear` (no new subcommands in POLISH; the comment and the Fix line
cover both); telemetry on setup time.

What already exists (DX): the REFUSED ... Fix: ... (CODE) line style (guards.py), the SCHEDULE warning in the routine
step (health.yml), the dry-run digest print (automation.py), wiki Usage bullets.

Implementation tasks (DX):
- [ ] **T6 (P1, human ~2h / CC ~15min)** — mail.py — codes, Fix lines, recovery, validation, test exits 1. Verify: `... secrets`, `... mailtest`
- [ ] **T7 (P1, human ~1h / CC ~10min)** — automation.py — stale-workflow check, per-sender readiness, run-order repair. Verify: `... digest`
- [ ] **T8 (P2, human ~1h / CC ~10min)** — docs/wiki/Automation.md — quickstart, troubleshooting, upgrade, rollback. Verify: docs check

### Phase 3: Eng review, Step 0 (Scope Challenge)

Scope gate: autoplan reviews the active plan, `.loop/goals/automation-email.plan.md`.

A. What already solves each sub-problem (read in code):
- Digest posting, rerun guard, owner mention: automation.py:236-275 (`cmd_digest`), :193-213 (`compose`). Extended.
- Issue state stub harness: dev/toy/test-automation.sh:27-40 (a stub `gh` that serves files and logs calls). Reused by the
  new test file, extended with `api` routes (milestones, comments, runs, PATCH).
- Feature table: milestone.py:40-50 `features()`; file.py plan/apply :96-171; health.py:329-347 `cmd_file`.
- Inline regression filing: actions.py:63-180 (the heredoc the workflow carries), `guards` map from tests.py `list --tsv`
  (cell 0 = feature page, measured: `tests.py list --tsv` prints `Automation	aut-digest-create	...`).
- gh 2.92.0 supports `api --paginate --slurp` and `run list --created` (checked with `--help`).

Complexity check (counted, planned changes): new files 4 (rounds.py, mail.py, mail-test.yml, test-automation-email.sh);
edited 12 (automation.py, file.py, actions.py, settings.py, seed.py, health.yml, regression.yml, .loop/config.json,
.loop/docs.tsv, .loop/regression.tsv, docs/wiki/Automation.md, dev/toy/test-automation.sh) plus README.md if the
operation widens touches: 16-17 files, 2 new modules. The gate trips (8+ files, 2+ new modules).

B. Complexity selectors (auto-decided, P2 never reduce, P5):
- Feature cuts: none proposed (every file serves a done line or an accepted review obligation).
- Structure (`plan-eng-review-structure`): Original arrangement (rounds.py for state + cost, mail.py for sending) vs
  Smaller arrangement (one new `digest_mail.py` holding state, cost and mail). The smaller one puts secrets-handling code
  next to state code imported by the secret-free digest step and lands near 20 KB; it fails the size rule's intent and
  P5. Auto-decided: Original arrangement. Scope record: feature answers: none (no cuts); structure: A (original,
  auto-decided P5); accepted scope: the plan as amended by CEO and DX; pending remedies: d1, d2, d3 (gate).

C. Findings (Scope Challenge):
1. [CRITICAL] (confidence: 9/10) dev/toy/test-automation.sh:56-60 — existing rows aut-digest-format and aut-digest-rounds
   assert the flat format (`**New** (2): [#5](...), [#9](...)`, marker `open=5,9 run=101`). Grouping by milestone and
   the new marker change both. REGRESSION RULE: the existing digest behaviors (owner mention, what ran, per-issue
   request by number only, rerun guard, org owner, pin failure, comment failure, list failure) must keep their rows;
   the two format assertions change intentionally to the grouped form and the new marker. Auto-decided (P1): update
   those two assertions in place, keep their row ids, and add a stub route for the milestone list so the other rows
   run unchanged.
2. [INFORMATIONAL] (confidence: 8/10) mail.py comment lookup — `gh api --paginate` prints one JSON array per page
   back to back; parse with `--paginate --slurp` (one array of pages), checked present in gh 2.92.0. Auto-decided.
3. [INFORMATIONAL] (confidence: 8/10) toy SMTP stub — smtplib needs TLS on 465 and STARTTLS on 587, and a plain-socket
   stub can't serve either without a certificate. Auto-decided: a test-only `DIGEST_SMTP_TEST_PORT` that, only with
   `smtp_host` 127.0.0.1 or localhost, connects without TLS to that port; never set by any workflow (grep test), the
   same guard as `DIGEST_MAIL_API`.
4. [INFORMATIONAL] (confidence: 7/10) skills/workflow-setup/scripts/seed.py:99-102 — setup adds health.yml for a new
   repo but nothing adds mail-test.yml. Auto-decided: seed.py adds mail-test.yml with health.yml (same condition).

REALITY: premise-table pass 6 code premises verified by reading (automation.py:236, file.py:139, actions.py:146, milestone.py:40, seed.py:99, test-automation.sh:56), unverified=0 skills/workflow-health/scripts/automation.py:236
REALITY: already-done pass git log origin/main --since=2026-11-09 shows no change to these paths after a23c125 skills/workflow-regression/scripts/actions.py:63
REALITY: surface-check pass gh 2.92.0 `api --paginate --slurp`, `run list --created` present per --help; `regression.py workflow`, `automation.py workflow` exist skills/workflow-health/scripts/automation.py:282
REALITY: binding-decisions pass none on the branch; owner decisions from the PRD and the operation brief carried .loop/goals/automation-email.md:14
REALITY: numbers pass 16-17 files and 2 new modules [measured: plan items 1-10 + accepted blocks]; automation.py 16,070 bytes [measured: wc -c skills/workflow-health/scripts/automation.py] skills/workflow-health/scripts/automation.py:1
REALITY: deferred-asks pass no linked issue; E2 and the hard stop recorded in NOT in scope .loop/goals/automation-email.md:14
REALITY: pr-count pass one pull request for one goal .loop/goals/automation-email.md:1

#### Step 0.5: Eng dual voices

Native Eng voice (Claude subagent, INPUT eng e8e55f04..., full read of 253 lines): 4 high, 7 medium, 4 low.
Codex Eng voice: unavailable (usage limit until 06:01; `turn.failed`), so this phase is [single-model]; no further Codex
calls this run.

```
ENG DUAL VOICES — CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Architecture sound?               mostly  N/A    N/A (outside voice unavailable)
  2. Test coverage sufficient?         no      N/A    N/A
  3. Perf risks + budget/bench named?  partly  N/A    N/A
  4. Security threats covered?         mostly  N/A    N/A
  5. Error paths handled?              mostly  N/A    N/A
  6. Deployment risk manageable?       yes     N/A    N/A
```
Single-voice High findings flagged: H1 (stale old-round post), H2 (owner's Backlog undone).

Dispositions: H1 ACCEPTED (stale guard in every digest step). H2 ACCEPTED (placement memory). H3 ACCEPTED (test-only
plain port plus a fake-class check of the TLS choice). H4 ACCEPTED (the accepted blocks are the build's source of truth;
corrections listed below; `digest` group restored). M1 ACCEPTED (planned split, size check). M2 ACCEPTED (named "job
time"). M3 ACCEPTED (paged listings, cap note, fallback). M4 ACCEPTED (href allowlist). M5 ACCEPTED (one resolver,
`milestone.page_of`). M6 factual correction: regression.yml already has `issues: write` (regression.yml:11); the
rendered-workflow row checks it. M7 ACCEPTED (own code). L1 ACCEPTED (bot-authored digest issue). L2 kept as designed,
noted in Usage. L3 noted for the tests. L4 ACCEPTED (one constant block).

#### Section 1: Architecture

```
                     .loop/config.json      .loop/docs.tsv
                            |                    |
                            v                    v
  regression.yml  --->  actions.py inline filer (features, milestones by number)  ---> issues on feature milestones
  (17 */4, tags)                                                                       (placed=<title> marker)
  health.yml (47 */4)
    routine (+ automation.py workflow --check -> STALE_WORKFLOW warning)
    health.py check -> milestone.py new --all -> file.py (milestone.page_of) -> issues
    judge?
    automation.py digest --imports--> rounds.py (parse/marker/digest_issue/round_cost) --> comment R + body state
    mail.py send ------imports-----> rounds.py ; reads comment R (bot, paged) ; sender (cloudflare | smtp)
  mail-test.yml (dispatch) -> mail.py test -> sender
  templates.py (health.yml + mail-test.yml text) <-- automation.py workflow / --check
```
Two shapes: (A) rounds.py owns round state + cost, mail.py owns sending, templates.py owns workflow text; (B) one
digest_mail.py owning everything. Pick A: each module hides one decision (state grammar; provider protocol; YAML text)
behind a small surface (`parse/marker/digest_issue/round_cost`; `send/test`; `render`). Red flags screened: information
leakage (marker grammar) avoided by keeping it only in rounds.py; split ownership of the body state: digest writes it,
mail.py writes it only on repair through the same `marker()`; hand-synced list: the outcome codes live once in mail.py
and a test checks the wiki table against them. Production failure per integration: Cloudflare 429/503 (retried once),
GitHub API hiccup during PATCH (MAIL_MARK, nothing sent), regression milestone POST 422 when a closed one exists
(prevented: state=all lookup).

#### Section 2: Code quality

[INFORMATIONAL] (confidence: 8/10) skills/workflow-health/scripts/automation.py:20-110 — the health.yml template is about
4.5 KB of the 16 KB file; with mail-test.yml beside it the file would pass 18 KB. Accepted: both templates move to
templates.py. [INFORMATIONAL] (confidence: 7/10) skills/workflow-health/scripts/milestone.py:143-152 — `goal_feature`
matches the first prefix, not the longest; file.py needs the longest. Accepted: add `page_of(root, path)` (longest
prefix, then page name) to milestone.py for file.py; `goal_feature` unchanged (out of scope, noted). Dispositions above.

#### Section 3: Tests

Framework: shell toy tests with a stub gh (CLAUDE.md has no Testing section; repo convention dev/toy/test-*.sh).
```
CODE PATHS                                             USER FLOWS
[+] rounds.py                                          [+] Owner sets up mail
  ├── parse/marker  [GAP->planned ★★★] old/new/empty     ├── [GAP->planned ★★★] Mail test sends (cloudflare, smtp)
  ├── digest_issue  [GAP->planned ★★] bot-authored        └── [GAP->planned ★★★] Mail test fails loudly (missing, off)
  └── round_cost    [GAP->planned ★★★] sum/partial/none  [+] A round
[+] automation.py digest                                  ├── [EXISTING ★★★ -> updated] create/pin/rerun/org/pin-fail
  ├── grouping      [GAP->planned ★★★] fixed under old   ├── [GAP->planned ★★★] grouped mail arrives once
  ├── email row     [GAP->planned ★★★] 4 states          └── [GAP->planned ★★★] rerun / old-run rerun / crash
  ├── repair/stale  [GAP->planned ★★★] older/newer/none  [+] Upgrade
  └── --check       [GAP->planned ★★★] stale/ours/not    └── [GAP->planned ★★] stale workflow warned
[+] mail.py send/test                                   [+] Filing
  ├── secrets       [GAP->planned ★★★] none/partial/all   ├── [GAP->planned ★★★] finding on feature milestone
  ├── comment find  [GAP->planned ★★★] bot/lookalike/p2  └── [GAP->planned ★★★] defect on feature milestone
  ├── state flags   [GAP->planned ★★★] mailing/mailed/clear-fail
  ├── senders       [GAP->planned ★★★] 2xx/429/401/500, smtp plain + TLS choice (fake class)
  ├── html          [GAP->planned ★★] links allowlisted, no leftover markdown
  └── scrub         [GAP->planned ★★★] values, upper-case address, crash frame
[+] file.py page_of/placement  [GAP->planned ★★★] longest prefix, placed vs owner-moved, closed milestone
[+] actions.py filer           [GAP->planned ★★★] feature/Other/created/owner-placed/FAILED exit 1
COVERAGE (planned): all new paths have a planned ★★ or ★★★ case; existing digest rows keep their cases (2 assertions
updated in place).
```
Regression rule: existing digest behavior (owner mention, what ran, number-only requests, rerun guard, org owner, pin
failure, comment failure, list failure) keeps its rows; two format assertions change intentionally (grouped form, new
marker). Test plan artifact written: <private path>

#### Section 4: Performance

Per round: gh calls bounded (2 issue lists, 1 paged milestone list, 2-3 run views, 1 paged run list with `--created`,
1 paged comment list with `since=`, 2-3 PATCHes). No loop over history. Scale: ~6 rounds/day; the comment list since a
run's start holds 1-3 comments. Not a hot path; no benchmark needed (unknown scale beyond that marked unknown).

#### Required outputs (Eng)

NOT in scope: `goal_feature`'s first-prefix match (milestone.py:143), creating milestones only on demand (L2), the
docs-format rows in docs.tsv (another goal), a cost trend, a hard 45-minute stop (gate d1).
What already exists: listed in Step 0 A.
Failure modes (new paths): stale old-round post (now DIGEST_STALE, tested), owner Backlog undone (placement memory,
tested), clearing `mailing` fails (MAIL_CLEAR_FAILED, tested), comment beyond page 1 (paged, tested), spend run list
capped (NOTE, tested), unsafe link in mail (allowlist, tested). Critical gaps: 0.
Worktree parallelization: Lane A rounds.py -> automation.py/templates.py -> mail.py (shared rounds.py, sequential);
Lane B file.py + milestone.page_of (independent); Lane C actions.py + regression.yml (independent); then tests, rows,
wiki. Built sequentially in one worker session.

Implementation tasks (Eng):
- [ ] **T9 (P1)** — automation.py — stale guard in every digest step (H1). Verify: `... mail` old-run case with no comment.
- [ ] **T10 (P1)** — file.py, actions.py — placement memory (H2). Verify: `... file`, `... regression` owner-Backlog cases.
- [ ] **T11 (P1)** — test harness — SMTP plain test port + fake-class TLS check (H3). Verify: `... retry`, `... mail`.
- [ ] **T12 (P2)** — templates.py split, size check (M1). Verify: health size rule PASS for all scripts.

Completion summary (Eng): Step 0 scope accepted as-is; reality rows 7/7, 0 unverified; Architecture 2 issues; Code
quality 2 issues; Tests diagram produced, all planned gaps covered; Performance 0 issues; NOT in scope written; What
already exists written; TODOS.md: none (no TODOS.md; deferrals in NOT in scope); failure modes 0 critical gaps;
unresolved decisions 0 in Eng; outside voice codex unavailable (usage limit); parallelization 3 lanes, built
sequentially; Lake Score N/A.

<!-- baseline edits record kept privately -->

<!-- autoplan-accepted:ceo -->
- E1 (mail test): `mail.py test` sends one sample mail ("Automation digest: test from <owner/repo>", a fixed body with no issue data) through the configured sender, with the same secret checks, scrubbing and outcome lines as `send`, and writes no state. It runs from its own workflow, `.github/workflows/mail-test.yml` (written by `automation.py workflow` beside health.yml, header `# Written by workflow-health`), triggered only by `workflow_dispatch`, `permissions: contents: read`, one job: checkout, setup-python, `mail.py test` with the mail secrets in env. health.yml gains no input and no guards. Verify: a toy case where `mail.py test` sends one test mail through the Cloudflare stub and touches no issue (no gh call), and a missing secret names it; the rendered mail-test.yml is dispatch-only, has no `issues: write`, and equals the committed file.
- E3 (one retry): a send is retried once after 30 s (`DIGEST_MAIL_RETRY_SECONDS` overrides the wait for tests, 0..30) only when the provider cannot have accepted the mail: Cloudflare HTTP 429 (code 10004) or HTTP 503 (code 10100), decided by the HTTP status; a refused connection or DNS failure before any request is sent; an SMTP 4xx reply before DATA (`SMTPConnectError`, `SMTPHeloError`, `SMTPSenderRefused` or `SMTPRecipientsRefused` with a 4xx code; `SMTPDataError` and `SMTPServerDisconnected` after DATA are not retried). HTTP 500, a timeout after the request was sent, an SMTP error after DATA, any other 4xx, an auth error or a permanent bounce is not retried, so a retry never sends the same mail twice. Verify: a toy case where the stub fails once with 429 then accepts, which sends one mail and says `MAIL: sent for run R (after 1 retry)`; one where it fails with 401, which sends nothing and is not retried; one where it fails with 500, which is not retried.
- Crash between send and `mailed`: a toy case where the stub accepts the mail and the comment's `mailed` write fails; a rerun sends no second mail and says it may already have been sent (AUT-4).
- Rerun after a failed body write: a toy case where the digest's body write fails, then the job is rerun; the rerun posts no second comment and sends no second mail, the body ends `run=R`, and the run's comment marker ends `mailed` (AUT-4).
- Old-run rerun: a toy case where round R2 has posted, then R1's job is rerun; R1's comment says `mailed`, so nothing is sent (AUT-4).
- Owner inbox check (Verify by hand, filled at build): set the secrets in a fresh fork, run the Mail test workflow, and see the mail arrive; note the setup time.
- Regression filing checks results: every `gh api` create, PATCH and milestone POST in the inline filing script checks its exit code and prints `FAILED <what>: <stderr, 160 chars>` on error, carrying on with the next row (AUT-2).
<!-- /autoplan-accepted:ceo -->

<!-- autoplan-accepted:dx -->
- DX-1: `mail.py test` exits 1 with `(MAIL_SECRETS)` or `(MAIL_OFF)` and a Fix line whenever it cannot send (missing secrets, `digest_mail: off`); it never exits 0 without an accepted send. Supersedes E1's "same ... outcome lines as send" for these two cases. Verify: toy cases for missing secret and off, both exit 1.
- DX-2: in `send`, exit 0 only when no mail secret is set at all (`MAIL: not set up ... (MAIL_NOT_SET_UP)`) or `digest_mail` is off; any partial set (addresses without provider secrets, or provider secrets without addresses) exits 1 naming the missing ones `(MAIL_SECRETS)`. Supersedes item 4's "Missing: ... exit 0". AUT-6's "without them the email step writes nothing and says what is missing" holds in both cases. Verify: toy cases none-set (exit 0, nothing written) and partial (exit 1, nothing written, names listed).
- DX-3: the inline regression filing counts failed gh writes and, after the last row, prints `FILED <k> issue writes; FAILED <m>` and exits 1 when m > 0 (in addition to today's exit 1 on red rows). Verify: a toy case where `gh api` fails once makes the step exit 1 and names the row.
- DX-4: the digest's repair writes the body only when the body's `run` is older than R (run ids compared as integers; `none`/`local` count as oldest); a body holding a newer run is left alone. Supersedes item 3's order step (2) wording. Verify: the old-run rerun case also asserts the body still holds R2.
- DX-5: `automation.py workflow --check` prints `STALE_WORKFLOW: <path> differs from what automation.py writes. Fix: python3 skills/workflow-health/scripts/automation.py workflow, then commit` and exits 1 when health.yml or mail-test.yml is missing or differs (only for files headed `# Written by workflow-health`; a hand-written one is reported `NOT_OURS` and never rewritten). The health workflow's routine step runs it and turns a non-zero result into a `::warning::` and a summary line (the run still proceeds). Usage gives the upgrade sequence (update skills, run `automation.py workflow`, review the diff, commit, push, set secrets, run Mail test) and the rollback note. Verify: toy cases for stale, current and hand-written files.
- DX-6: every outcome line ends with a stable code in parentheses and, for any non-success, a `Fix:` sentence and the recovery (safe to rerun / do not rerun / check first), in the existing `REFUSED ... Fix: ... (CODE)` style. Codes: MAIL_SENT, MAIL_ALREADY, MAIL_OFF, MAIL_NOT_SET_UP, MAIL_SECRETS, MAIL_SETTING, MAIL_NO_COMMENT, MAIL_GH, MAIL_MARK, MAIL_UNKNOWN, MAIL_REFUSED, MAIL_MARKED_LATE, MAIL_TEST_URL, MAIL_FAILED; DIGEST_ALREADY, DIGEST_REPAIRED; ROUND_UNREAD; FILE_FAILED; STALE_WORKFLOW, NOT_OURS. MAIL_REFUSED maps 401/403 to "check the token's Email Sending permission", a sender-domain error to "onboard DIGEST_FROM's domain", SMTP auth to "use an app password". MAIL_UNKNOWN's Fix names the inbox check and the exact comment edit. MAIL_FAILED adds the innermost frame `file:line in function` (no values). `round cost: not read` gives its reason (`no run id`, or gh's stderr cut to 120 characters, scrubbed). The wiki's troubleshooting table lists every code. Verify: each toy case asserts its code; a grep check that every code in mail.py appears in the wiki table.
- DX-7: before any work, `digest_mail` outside cloudflare|smtp|off, `smtp_port` other than 465 or 587, or `DIGEST_MAIL_RETRY_SECONDS` outside 0..30 exits 1 `(MAIL_SETTING)` naming the value and the allowed ones. Verify: toy case per setting.
- DX-8: the digest's `email` row checks `digest_mail: off` first (`off`), then sender readiness from three booleans the digest step receives (`MAIL_ADDR_SET`, `MAIL_CF_SET`, `MAIL_SMTP_SET`, each `${{ secrets.X != '' && ... }}`, values never), then shows the previous round's outcome labeled `previous round: sent | not sent | may have been sent`. Supersedes item 5's single `DIGEST_MAIL_SET`. Verify: toy cases for off-without-secrets, cloudflare-missing-token, previous sent.
- DX-9: comment lookup uses `gh api --paginate "repos/{owner}/{repo}/issues/N/comments?since=<run createdAt>&per_page=100"` and scans every page; the "last two pages" fallback goes. Verify: a toy case with the matching comment on the second page.
- DX-10: the spend figure is named `Actions minutes of runs started since the last round` everywhere (comment, summary, wiki), and the wiki says a run still going at a round's cut-off is counted by the round in which it started. Supersedes "Actions minutes since the last round" wording in item 2.
- DX-11: regression rows are one per test group, not one per PASS line: `test-automation-email.sh GROUP` exits 0 only when every case in its group passes, and each row runs one group, so a land run starts one harness per row. Groups: `mail` (AUT-4), `secrets` (AUT-6), `rounds` (AUT-7), `file` (AUT-3), `regression` (AUT-2), `mailtest` (AUT-4), `upgrade` (AUT-4), `retry` (AUT-4). Supersedes item 10's "one regression.py add row per PASS line". Each row is still seen failing then passing.
- DX-12: the wiki's Usage leads with an Email quickstart: prerequisites (a domain onboarded to Cloudflare Email Sending and a token with the Email Sending send permission, or a Gmail account with 2-step verification and an app password), the exact `gh secret set` lines for each sender, the `digest_mail` setting, `gh workflow run mail-test.yml`, the expected `MAIL: test sent (MAIL_SENT)` line, and that DIGEST_TO holds one address. Then the troubleshooting table (DX-6) and the email-row states with the owner's next step.
- DX-13: SMTP secrets are `DIGEST_SMTP_USER` and `DIGEST_SMTP_PASSWORD` (not bare SMTP_*). Supersedes those names in items 4 and 5.
- DX-16: `scrub()` replaces each secret value and the address case-insensitively, and the address's local part on its own; the DIGEST_MAIL_API refusal shows the scheme and host it got. Verify: the leak case includes an upper-cased address in a stub error.
<!-- /autoplan-accepted:dx -->

<!-- autoplan-accepted:eng -->
- Eng-C1: update the two existing assertions in dev/toy/test-automation.sh for aut-digest-format and aut-digest-rounds to the grouped form and the new marker, keep their row ids, and add stub routes (milestones, comments, runs, PATCH) so every other existing digest row passes unchanged.
- Eng-C4: seed.py adds `.github/workflows/mail-test.yml` beside health.yml under the same condition (health skill present).
- H1: every digest run compares the body's run with R as integers (`none`/`local` oldest) before anything else: body run > R -> post nothing, write nothing, `DIGEST: run R is older than the round on the issue (run S); nothing posted (DIGEST_STALE)`, exit 0; body run == R -> DIGEST_ALREADY; else repair or post. Verify: old-run rerun with no comment for R1 after R2 posted: no comment, body still R2, no mail (mail.py finds no comment: exit 1 MAIL_NO_COMMENT is acceptable, and the mail step's Fix names the stale digest).
- H2: placement memory. A created issue records where the automation put it: health issues' marker becomes `<!-- loop-health KEY placed=<milestone number or 0> -->`, regression issues' marker `<!-- loop-regression ID placed=<number or 0> -->`. The automation moves an open issue only when its current milestone equals its recorded placement (legacy issues without `placed=`: health counts as Backlog's number, regression as 0) and the computed milestone differs; it then updates `placed=`. An issue the owner moved anywhere else, Backlog included, stays. Supersedes items 6 and 7's "no milestone or on Backlog" rule. Verify: owner moves an Automation issue to Backlog -> it stays; a legacy Backlog health issue -> moves to its feature; a legacy no-milestone regression issue -> moves.
- H3: SMTP testing: `DIGEST_SMTP_TEST_PORT` (test-only, honoured only when smtp_host is 127.0.0.1 or localhost; bypasses the 465/587 check; never set by any workflow, grep-tested) connects without TLS for the end-to-end case; a `python3 -c` case replaces `smtplib.SMTP_SSL`/`smtplib.SMTP` with fakes and asserts 465 uses SMTP_SSL and 587 calls starttls() before login.
- H4: the accepted blocks (ceo, dx, eng) are the build's source of truth where they say "supersedes". DX-11's groups gain `digest` (AUT-4): grouping, fixed under its old milestone, marker order and the `Ops, team: A` title. The final env: the digest step gets `MAIL_ADDR_SET: ${{ secrets.DIGEST_TO != '' && secrets.DIGEST_FROM != '' }}`, `MAIL_CF_SET: ${{ secrets.CLOUDFLARE_ACCOUNT_ID != '' && secrets.CLOUDFLARE_EMAIL_TOKEN != '' }}`, `MAIL_SMTP_SET: ${{ secrets.DIGEST_SMTP_USER != '' && secrets.DIGEST_SMTP_PASSWORD != '' }}`; the mail step and mail-test.yml get `DIGEST_TO`, `DIGEST_FROM`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_EMAIL_TOKEN`, `DIGEST_SMTP_USER`, `DIGEST_SMTP_PASSWORD` (plus `GH_TOKEN` and `DIGEST_RUN` for the mail step only).
- M1: the two workflow templates (health.yml, mail-test.yml) move to a new `skills/workflow-health/scripts/templates.py` (added to the Automation row of docs.tsv); if mail.py passes 18 KB, its HTML/subject rendering moves to `mail_render.py` (also mapped). The build runs `health.py check --group size` and every new or changed script stays under 20 KB.
- M2: the round figure is named "job time" (sum of the round's jobs, each job's completedAt - startedAt); the wiki says so. Both workflows have one job today, so job time equals each run's run time.
- M3: the spend list uses `gh run list --workflow W --created ">=<prev createdAt>" --limit 200` per workflow and prints `NOTE: more than 200 runs since the last round; the spend is a lower bound` when capped; when the previous run can't be read (expired, `none`, `local`), the window is the round's own two runs and the line says `(first round counted)`. Every milestone list uses `gh api --paginate --slurp`.
- M4: the HTML part turns `[x](url)` into a link only when url starts with `https://github.com/`; anything else stays text; hrefs are escaped. Verify: a comment with a `javascript:` link renders as text.
- M5: `milestone.page_of(root, path)` returns the docs.tsv page whose path is the longest prefix of `path` (exact or `path/` prefix), else the page whose name equals the subject case-insensitively, else "" (caller uses Backlog); file.py uses it. Verify: `skills/workflow-health/scripts/mail.py` -> Automation, `skills/workflow-health/scripts/health.py` -> Health.
- M7: if removing `mailing` after a known refusal fails: `MAIL: refused and couldn't clear the sending mark on <comment url> (MAIL_CLEAR_FAILED). Fix: delete the word mailing from that comment's last line, then rerun this job (nothing was sent).`, exit 1. Verify: toy case.
- L1: `digest_issue()` accepts only an issue authored by `github-actions[bot]` (as well as title, label and marker); the oldest such issue wins.
- L4: the Cloudflare endpoint, response fields and retryable statuses live in one constant block at the top of mail.py with the docs URL beside it.
<!-- /autoplan-accepted:eng -->

### Phase 4: Final gate (stopped here; the plan step approves nothing)

## URGENT, outside this plan

None.

Decisions: 64 total (61 auto-decided in the review record above, 3 taste choices d1-d3, 0 user challenges).
Review scores: CEO SELECTIVE EXPANSION, 2 of 6 cherry-picks accepted, 0 critical gaps, Codex completed (6 concerns),
native completed (11), consensus 4/6 confirmed; Design skipped (no UI scope); DX 5.1 -> 7.4/10, TTHW ~7 -> ~4 min, Codex
completed (9), native completed (16), consensus 4/6; Eng 15 native findings (4 high, all accepted), Codex unavailable
(usage limit), consensus N/A. CYCLE: actual 27m (estimate 28m).
Cross-phase themes: delivery state across reruns (CEO, Eng H1), owner control over placement (CEO, Eng H2), test cost
(CEO, DX), upgrade/activation and silent mailer (CEO, DX).
Deferred: E2 cost trend; a hard 45-minute stop (d1); milestones only on demand (Eng L2); goal_feature's first-prefix
match. No TODOS.md in this repo; recorded in NOT in scope.

Gate (gate_rev 1, rec_hash c9b75b74a884): d1 a (flag only), d2 a (criteria_max 7, stamp Reviewed 2026-11-10), d3 a
(separate mail-test.yml) as auto defaults; plan1 approval pending for the owner.

<!-- AUTONOMOUS DECISION LOG -->
## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | CEO | Mode SELECTIVE EXPANSION | Mechanical | override | autoplan override | other modes |
| 2 | CEO | Approach A (two scripts) | Mechanical | P5 | settled at idea step | B one script, C worker |
| 3 | CEO | E1 mail test accepted | Mechanical | P2 | in blast radius, <1 day | defer |
| 4 | CEO | E2 cost trend deferred | Mechanical | P3 | outside done lines | add |
| 5 | CEO | E3 one retry accepted | Mechanical | P1 | transient errors lose mail | skip |
| 6 | CEO | E4-E6 skipped | Mechanical | P5/P4 | not asked / contradicts AUT-4 | add |
| 7 | CEO | Spec r1 fixes (15 minor) applied | Mechanical | P1 | completeness | keep |
| 8 | CEO | 45 min hard-coded, no setting | Mechanical | P5 | AUT-7 fixes it | setting |
| 9 | CEO | Drop preview mode | Mechanical | P4 | not required | keep |
| 10 | CEO | Keep SMTP (operator brief) | Mechanical | P6 | brief asked for it | cut |
| 11 | CEO | Spec r2 blocking: rerun after failed body write | Mechanical | P1 | AUT-4 nothing twice | none |
| 12 | CEO | Spec r3 blocking: mailing flag, digest order | Mechanical | P1 | AUT-4 nothing twice | at-least-once |
| 13 | CEO | 0H document approval A | Mechanical | P6 | inputs match decisions | revise |
| 14 | CEO | C-1 hard stop -> taste d1 | Taste | P1/P5 | done line says flag | enforce now |
| 15 | CEO | C-2/N-F6 duration vs spend split | Mechanical | P1 | both voices | single number |
| 16 | CEO | C-3/N-F5 state on the round's comment | Mechanical | P1 | later rounds erase body | body state |
| 17 | CEO | N-F4 at-least-once rejected | Mechanical | done line | contradicts AUT-4 | adopt |
| 18 | CEO | email row in digest | Mechanical | P1 | silent mailer visible | Actions only |
| 19 | CEO | inbox check in Verify by hand | Mechanical | P1 | real onboarding proof | none |
| 20 | CEO | N-F1/N-F2 native-only / Marketplace rejected | Mechanical | owner | PRD chose Cloudflare | change |
| 21 | CEO | N-F7 PR split rejected | Mechanical | pr-count | one goal one PR | split |
| 22 | CEO | N-F8 HTML leftover test | Mechanical | P1 | drift caught | none |
| 23 | CEO | N-F9 config/review stamps -> taste d2 | Taste | P6 | outside done lines | silent |
| 24 | CEO | N-F10/C-6 grouped harness | Mechanical | P5 | test cost | per row |
| 25 | CEO | N-F11 separate mail-test.yml -> taste d3 | Taste | P5 | guard sprawl | input |
| 26 | CEO | Regression filing checks gh results | Mechanical | P1 | silent failures | none |
| 27 | DX | Product type skill/CLI + Actions | Mechanical | P6 | evidence | other |
| 28 | DX | Persona template adopter + agent | Mechanical | P6 | README audience | other |
| 29 | DX | TTHW target Competitive 2-5 min | Mechanical | P5 | fewer steps | champion |
| 30 | DX | Magical moment = Mail test | Mechanical | P5 | existing vehicle | new |
| 31 | DX | Mode POLISH | Mechanical | override | enhancement | expansion |
| 32 | DX | DX-1 test exits 1 | Mechanical | P1 | CAP4 both voices | exit 0 |
| 33 | DX | DX-2 partial secrets exit 1 | Mechanical | P1 | CAP4 | skip |
| 34 | DX | DX-3 filing exit 1 on failures | Mechanical | P1 | CAP4 | exit 0 |
| 35 | DX | DX-4 no body rewind | Mechanical | P1 | Codex high | repair always |
| 36 | DX | DX-5 stale workflow check | Mechanical | P1 | upgrade gap | none |
| 37 | DX | DX-6 codes/Fix/recovery | Mechanical | P1 | agent-ready | prose only |
| 38 | DX | DX-7 settings validated | Mechanical | P1 | undefined values | none |
| 39 | DX | DX-8 readiness per sender | Mechanical | P1 | misdiagnosis | single bool |
| 40 | DX | DX-9 paginate comments | Mechanical | P1 | missed comment | two pages |
| 41 | DX | DX-10 spend named creation-window | Mechanical | P5 | honesty | complete claim |
| 42 | DX | DX-11 one row per group | Mechanical | P5 | harness reruns | per line |
| 43 | DX | DX-12 quickstart + troubleshooting | Mechanical | P1 | both voices | none |
| 44 | DX | DX-13 DIGEST_SMTP_* names | Mechanical | P5 | consistency | SMTP_* |
| 45 | DX | DX-14 preview rejected | Mechanical | POLISH | no new subcommand | add |
| 46 | DX | DX-15 clear rejected (Fix line instead) | Mechanical | P5 | precise human edit | add |
| 47 | DX | DX-16 scrub case-insensitive | Mechanical | P1 | leak | exact only |
| 48 | Eng | Structure: original arrangement | Mechanical | P5 | smaller fails size/secret isolation | one module |
| 49 | Eng | C1 update two digest assertions | Mechanical | P1 | regression rule | new rows |
| 50 | Eng | C2 paginate --slurp | Mechanical | P5 | gh output shape | manual |
| 51 | Eng | C3 SMTP test port | Mechanical | P5 | TLS stub impossible | none |
| 52 | Eng | C4 seed adds mail-test.yml | Mechanical | P1 | new repos | none |
| 53 | Eng | H1 stale guard | Mechanical | P1 | correctness | none |
| 54 | Eng | H2 placement memory | Mechanical | P1 | owner control | Backlog rule |
| 55 | Eng | H3 fake-class TLS check | Mechanical | P1 | coverage | none |
| 56 | Eng | H4 accepted blocks authoritative; digest group | Mechanical | P5 | contradictions | silent |
| 57 | Eng | M1 templates.py split | Mechanical | P5 | 20 KB rule | inline |
| 58 | Eng | M2 "job time" name | Mechanical | P5 | parallel jobs | wall time |
| 59 | Eng | M3 paged lists, cap note | Mechanical | P1 | silent loss | limit 20 |
| 60 | Eng | M4 href allowlist | Mechanical | P1 | unsafe link | any href |
| 61 | Eng | M5 one resolver page_of | Mechanical | P4 | duplicate mapping | new copy |
| 62 | Eng | M6 permissions fact | Mechanical | fact | already issues: write | change |
| 63 | Eng | M7 MAIL_CLEAR_FAILED | Mechanical | P1 | stuck flag | none |
| 64 | Eng | L1 bot-authored digest issue; L4 constants block | Mechanical | P1/P5 | spoofing; one place | none |

## REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | ISSUES OPEN (not persisted to the log: logged only on approval) | 6 proposals, 2 accepted, 1 deferred |
| Outside Review | codex (gpt-6-astra) via /autoplan | Independent 2nd opinion | 3 | CEO completed, DX completed, Eng unavailable | CEO 6 findings; DX 9 findings; Eng no completed external review (usage limit) |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | ISSUES OPEN (not persisted) | 15 issues, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | skipped (no UI scope) | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 1 | ISSUES OPEN (not persisted) | score: 5.1/10 → 7.4/10, TTHW: ~7 min → ~4 min |

- **OUTSIDE COVERAGE:** codex, ceo phase, completed, 6 findings; codex, dx phase, completed, 9 findings; codex, eng phase,
  unavailable (usage limit until 06:01), no completed external review.
- **CROSS-MODEL:** CEO: Claude subagent and codex agreed on delivery state, round accounting and test cost; disagreed on
  native-notification sufficiency and enforcement of the 45-minute limit. DX: agreed on the green Mail test (CAP4),
  error contract and docs; codex alone raised the upgrade activation gap. Eng: no cross-model comparison.
- **VERDICT:** no review CLEAR yet: the plan awaits the owner's approval at the gate (plan1); eng review required.

**UNRESOLVED DECISIONS:**
- plan1: approve the automation-email plan (owner)
