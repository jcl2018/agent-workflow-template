# Routines run where they can run fully, as the Automation page (AUT-1..3) now says: health (all groups plus the agent review) runs every 4 hours on the owner's Mac for every repo and never in GitHub Actions; the full regression runs every 4 hours in GitHub Actions for a public repo and on the Mac for a private one; a push or pull request runs only the affected rows; no GitHub check blocks a private repo's merge; issues and the digest are filed as before (owner, 2026-11-11: "for public repo, because that's free ... in the private repo, I want it to be completely in the local machine, like in the Mac, so it will never block, and it shouldn't block the check in that case. So basically you should mimic the scheduled run for them, and both of them will send the issue")

- Slug: local-schedule
- Touches: skills/workflow-regression, skills/workflow-health, skills/workflow-setup, dev/toy, .loop/regression.tsv, docs/wiki/Regression.md, docs/wiki/Health.md, docs/wiki/Setup.md, docs/wiki/Tests.md, .loop/config.json, skills/workflow-regression/scripts/narrow.py, skills/workflow-regression/scripts/lanes.py, docs/wiki/Delivery.md, docs/wiki/Documentation.md, docs/wiki/Guardrails.md, docs/wiki/Home.md, .loop/START.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. setup installs one local 4-hourly schedule per repo (a user launch agent, no root) that runs health with the judge for every repo and the nightly regression for a private repo, filing issues and the digest exactly as the GitHub workflows did; it writes no health workflow for any repo and removes the template's own health.yml; a public repo keeps the GitHub regression workflow; toy tests prove each choice
2. a private repo gets no scheduled or push-triggered GitHub regression, and setup names any required status check that would still block a merge, for the owner to remove (setup never edits rulesets or branch protection)
3. on push or pull request, regression runs only the affected rows (the REG-4 selection), and the full suite runs only on the schedule
4. when the Mac is asleep a missed run happens at the next wake, and the issue or digest says when it last ran
5. the judge runs locally with the owner's own claude login, never needing an API key secret; the owner's one-time steps (load, stop, uninstall the schedule) are in Usage
6. no token, path or private name in any committed file
7. a private repo merges with no click and no bypass: its goal's pr lane, after passing on the PR head, posts its result as commit statuses named after every required status check the repo's ruleset or branch protection lists (for example checks and scan), with the lane's real pass or fail and a description naming the local run, and merge.py merges normally; a toy test proves a failed lane posts failure and never success, and a public repo never posts these

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
