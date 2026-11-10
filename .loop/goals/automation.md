# Add the Automation feature: scheduled regression and health in GitHub Actions with a digest through GitHub's built-in notifications, with the owner's criteria approved in chat on 2026-11-08

- Slug: automation
- Touches: .github, skills/workflow-regression, skills/workflow-health, skills/workflow-setup, docs/wiki, .loop/docs.tsv, .loop/config.json, .loop/regression.tsv, dev/toy, README.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. A new feature page Automation exists as a PRD (Problem, Usage, Requirements, Non-goals and Success metrics; the drafts other than the requirements Unreviewed for the owner) with a GitHub milestone, and these requirements word for word, each marked Reviewed 2026-11-08 with criteria.py review --user since the owner approved them in chat: AUT-1 "Routines run in GitHub Actions. Every routine runs as a GitHub Actions workflow on a schedule set in the repo's config, every few hours by default, and I can also start it by hand from the Actions tab; each run shows its report in the run summary." AUT-2 "Regression on a schedule. The full regression suite runs on the schedule; a failing test opens or updates one GitHub issue labeled defect, linked to the test and the feature it guards, and it closes by itself when the test passes again." AUT-3 "Health on a schedule. The health check runs on the schedule and files its findings as issues tagged with their group, updating or closing them as things change; the judge runs too when the repo has an agent key set as a secret, otherwise it is skipped and the report says so." AUT-4 "A digest through GitHub notifications. After each scheduled round, one comment on a pinned Automation digest issue lists what ran and its results, the new, still-open and fixed issues, and for each open issue the request to give the agent to fix it; GitHub's built-in notifications email it to me, with no extra setup." AUT-5 "Under my control. Each routine can be turned off or rescheduled in one setting, and without the secrets it needs a routine runs but writes nothing and says what is missing."
2. REG-4 and REG-5 are unreviewed and reworded, then marked Reviewed 2026-11-08 with criteria.py review --user since the owner approved moving the schedule to Automation: REG-4 says only that one command runs the suite the same way for me, the loop and GitHub Actions; REG-5 says each failing test's issue is labeled defect
3. Two scheduled GitHub Actions workflows, regression and health, run on schedules from .loop/config.json (default every 4 hours) and by hand, each writing its report to the run summary; regression failures open or update defect issues; health files tagged findings; the judge step runs only when an agent key secret exists
4. After each scheduled round a comment on a pinned Automation digest issue lists results, new, open and fixed issues, and a fix request per open issue, mentioning the repo owner so GitHub notifies them
5. Turning a routine off in the config stops its workflow from writing anything, and a toy test with stub gh calls proves the digest format, the defect labeling and the off switch; docs check and health stay green
6. Per DOC-3, each done line above is recorded on its PRD page as one or more Given/When/Then scenarios under the requirement it serves, each linked to its regression row with its last result

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
