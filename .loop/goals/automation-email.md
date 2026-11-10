# The scheduled regression and health rounds file every issue on its feature's milestone and email the owner one digest per round (owner, 2026-11-10: "apply your recommended")

- Slug: automation-email
- Touches: skills/workflow-health, skills/workflow-regression, skills/workflow-setup, .github, .loop/config.json, .loop/regression.tsv, dev/toy, docs/wiki/Automation.md

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
