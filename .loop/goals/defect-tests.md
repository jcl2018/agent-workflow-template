# Give Regression a second category of defect tests, with the owner's new REG-1 and REG-2 wording approved in chat on 2026-11-08

- Slug: defect-tests
- Touches: skills/workflow-regression, skills/workflow-delivery, skills/workflow-health, docs/wiki, .loop/regression.tsv, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. REG-1 and REG-2 are unreviewed and rewritten word for word as follows, then marked Reviewed 2026-11-08 with criteria.py review --user, since the owner approved this wording in chat: REG-1 "Two kinds of tests. The suite has two categories: criteria tests, which prove each Reviewed criterion, and defect tests, one for every finding, issue or bug that gets fixed, which prove it stays fixed. A criterion with no passing test shows as not enforced, and a fix isn't finished until its defect test exists and passes." REG-2 "Test format. Every test is listed in one fixed format: its category (criterion or defect), what it guards (the criterion's words, or a link to the finding or issue it came from), what it checks in one plain line, when it runs, its last result and date, and whether it has been seen failing once."
2. DEL-1 is unreviewed and rewritten word for word as follows, then marked Reviewed 2026-11-08 with criteria.py review --user, since the owner approved this wording in chat: DEL-1 "The loop. I give one sentence and the done lines, and a worker runs it unattended through these steps, in order: freeze the done lines, office-hours (shape the idea), plan, build, review, qa, ship, pull request, release. Review is the only gate. Each step can be mapped to any skill or plugin I choose, in a private setting outside the repo, and my preferred skill suite is the default; each step runs that skill in its unattended mode. It won't start without the flow set up, and it stops and says why after 3 failed tries."
3. The delivery flow has no checks step: goal.py and flow.py go from build to review, review is the only gate, require_checks and the checks list are removed from the config and docs, and every step (office-hours, plan, build, review, qa, ship, pull request, release) can be mapped in the private flow file, with a default suite and per-step overrides
4. Every regression row has a category, criterion or defect, and defect rows link to their GitHub issue or finding; the Tests tables show defect tests in their own part on the page whose code they guard
5. When a goal fixes an issue or finding, delivery adds its defect test, seen failing on the old code and passing on the fix, before the issue closes
6. A health rule flags each closed issue or finding with no defect test
7. A worker finishes its goal by running the release step itself (version bump, release note, docs, merge where auto_merge is on) instead of ending with its pull request waiting, as happened with pull requests 61 and 62
8. Defect tests exist for issues 35 and 58, the worker that skipped its own release step, and the pull request body that said checks passed with no checks
9. A toy test proves each line above, and the repo checks pass

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
