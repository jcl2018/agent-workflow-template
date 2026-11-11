# No in-loop test run, review or ship step goes past a time budget; a test run that would go past it is split into tiers and the rest left to the scheduled full suite, never a full run in the loop. This goal lands before lane-control, which then builds its lanes on it (owner, 2026-11-11: "I don't want each review or test to go past a certain limit. If that's too much, you should split it into different tier of testing. It can be a config, but I guess the limit for here it should be no less than 15 minutes. If something is more than that, you should just let it go instead of doing a full run. It should apply to all the review and ship sessions." and "I do want the budget to be implemented first, because the test lane will depend on that")

- Slug: step-budget
- Touches: skills/workflow-delivery, skills/workflow-regression, skills/workflow-health, skills/workflow-monitoring, dev/toy, .loop/config.json, .loop/regression.tsv, docs/wiki/Regression.md, docs/wiki/Delivery.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. REG-7 reads, Unreviewed: "Every in-loop test run (qa, ship and the pull-request lane) stays within a time budget, a setting that defaults to 15 minutes and can't be set lower. A run that would go past it, including changes the row picker can't map such as a deleted file, runs the affected tier that fits and leaves the rest to the scheduled full suite, saying what it left; the loop never runs the full suite. The scheduled full suite finishes in under 30 minutes, and health flags it when it doesn't."
2. DEL-8 adds, Unreviewed: "Each review and ship step has a time limit, a setting no lower than 15 minutes; a step that reaches it finishes with what it has done, records what it left, and the goal goes on instead of restarting."
3. A deleted or unmapped file no longer forces a FULL lane: it selects the rows that named the file, plus the runners, and trims to the tier that fits the budget, listing every row it left
4. Two settings in .loop/config.json, test_budget_minutes (default 15) and step_budget_minutes for review and ship (default 30), each refusing a value under 15 with a fix line; a headless step stops at min(flow file limit, step budget); a session-run step is given its budget in its step instructions and an overrun is recorded
5. The board and health show any run or step that hit its budget and what it left
6. Each change has a regression row seen failing then passing, and the goal's own pr lane runs within the budget

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
