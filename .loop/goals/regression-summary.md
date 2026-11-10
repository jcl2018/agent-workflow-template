# Show every test grouped by feature with what it is about, everywhere tests are shown, and fix issue 92, with the owner's new REG-2 wording approved in chat on 2026-11-08

- Slug: regression-summary
- Touches: skills/workflow-regression, .github, .loop/regression.tsv, docs/wiki, skills/workflow-health/scripts/health.py, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. REG-2 is unreviewed and rewritten word for word as follows, then marked Reviewed 2026-11-08 with criteria.py review --user, since the owner approved this wording in chat: REG-2 "Test format. Every test is listed in one fixed format, grouped by feature, wherever tests are shown (the wiki, the GitHub run summary, the health report): its category (requirement or defect); what it guards (the requirement's ID and words, or a link to the issue or finding it came from, with that issue's state); what it checks in one plain line; when it runs; its last result and date; and whether it has been seen failing once."
2. Toy tests never write to the real GITHUB_STEP_SUMMARY; a defect test linked to issue 92 proves it, seen failing once and passing now, and issue 92 closes when this merges
3. The GitHub regression run summary shows one header with totals and the run time, then one table per feature with each test's name, kind, what it guards (requirement ID and words, or issue link and state), what it checks, and result
4. The wiki Tests tables and the health report list tests in the same grouped format
5. Every regression row has a plain one-line description, so the every-row-described test passes and issue 91 closes by itself
6. A toy test proves the summary format on a made-up mix of requirement and defect tests across two features
7. Per DOC-3, each done line above is recorded on its PRD page as one or more Given/When/Then scenarios under the requirement it serves, each linked to its regression row with its last result

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
