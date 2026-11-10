# The scheduled regression and health rounds file every issue on its feature's milestone and email the owner one digest per round (owner, 2026-11-10: "apply your recommended")

- Slug: automation-email
- Touches: skills/workflow-health, skills/workflow-regression, skills/workflow-setup, .github, .loop/config.json, .loop/regression.tsv, dev/toy, docs/wiki/Automation.md, .loop/docs.tsv, README.md, listing.json

## Done lines

Frozen. A wrong done line needs a new goal.

1. AUT-4: after each scheduled round one email goes to the address in a GitHub secret through Cloudflare Email Service, listing what ran and its results, then new, still-open and fixed issues grouped by feature, each with its link and the request to give the agent; the pinned digest issue gets the same text; a rerun sends nothing twice
2. AUT-2: a failing test's defect issue sits on the milestone of the feature it guards; the full suite runs every 4 hours by default and on every release
3. AUT-3: the scheduled health run files each finding on its feature's milestone (Backlog only when none fits) through health's own filing, never duplicating an open issue
4. AUT-6: the address and mail key appear only in GitHub secrets, never in the repo, logs, issues or the digest comment; without them the email step writes nothing and says what is missing
5. AUT-7: the run summary shows each round's duration and Actions minutes and flags a round over 45 minutes
6. Each requirement above has a regression row seen failing then passing, listed in the Automation Tests table

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Pick a sender and add its secrets in Settings, Secrets and variables, Actions: DIGEST_TO, DIGEST_FROM and either
   CLOUDFLARE_ACCOUNT_ID with CLOUDFLARE_EMAIL_TOKEN (a domain onboarded to Cloudflare Email Sending), or
   DIGEST_SMTP_USER with DIGEST_SMTP_PASSWORD plus `"digest_mail": "smtp"` in `.loop/config.json`. Time how long it takes.
   Expect: under five minutes once the domain or app password exists.
2. In the Actions tab, run the mail-test workflow.
   Expect: its log ends `MAIL: test sent (MAIL_SENT)`, and a mail titled "Automation digest: test from <owner/repo>"
   arrives within a minute.
3. Run the health workflow by hand.
   Expect: a new comment on the pinned Automation digest issue, grouped under milestone headings, with `round cost` and
   `email` rows; the run summary has a `## Round` line; one mail arrives with the same text as the comment.
4. Re-run that same health run (Re-run all jobs).
   Expect: no second comment and no second mail; the Email the digest step says `already sent for run ... (MAIL_ALREADY)`.
5. Open the health and regression issues on GitHub.
   Expect: each sits on its feature's milestone (Backlog only when no feature fits). Move one to Backlog by hand, run the
   health workflow again, and it stays on Backlog.
6. Search the run logs, the digest comment and the issues for your address.
   Expect: it appears nowhere.
