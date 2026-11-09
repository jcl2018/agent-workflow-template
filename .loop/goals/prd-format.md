# Make every feature page a short PRD with Given/When/Then tests, with the owner's new DOC-1, DOC-2 and DOC-3 wording approved in chat on 2026-11-08

- Slug: prd-format
- Touches: skills/workflow-docs, docs/wiki, .loop/docs.tsv, .loop/regression.tsv, skills/workflow-setup, dev/toy, README.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. DOC-1, DOC-2 and DOC-3 are unreviewed and rewritten word for word as follows, then marked Reviewed 2026-11-08 with criteria.py review --user once the owner confirms in the worker session: DOC-1 "PRD template. One template defines every feature page as a short PRD: Problem (who it's for and what it solves, two or three lines); Usage (the commands and how to use each, left out when nothing applies); Requirements (up to the repo's limit, default 6, each with an ID); Non-goals (what the feature deliberately won't do); Success metrics (how we know it works, one to three measurable lines); Tests (for each requirement, one or more Given/When/Then scenarios, each with its test, last result and date, and not enforced when no test passes). Nothing else goes on the page." DOC-2 "The PRD is mine. I review the PRD as a whole (Problem, Usage, Requirements, Non-goals and Success metrics) and mark it Reviewed with a date; only I can do that. After it, nothing in Problem, Requirements, Non-goals or Success metrics changes unless I un-review it; Usage updates with the commands, and any change to it shows as changed since my review, under Needs you, until I review it again." DOC-3 "Tests follow on their own. Once I review a PRD, the loop writes Given/When/Then scenarios and tests for each requirement, links each to a regression row, and keeps them in step when a requirement changes; I never write or manage tests."
2. The template sheet and the docs check enforce the PRD sections in that order, and the review lock covers Problem, Requirements, Non-goals and Success metrics together, while a Usage change marks the page changed since review and lists it on the board (under Issues until board-graph adds Needs you)
3. All feature pages are converted: Summary becomes Problem, Criteria become Requirements with the same IDs and their Reviewed stamps kept, and Non-goals and Success metrics are added as Unreviewed drafts for the owner
4. Every existing test row appears under its requirement as one or more Given/When/Then scenarios with its test, last result and date
5. A prd command drafts a new feature's PRD from a one-line idea, marked Unreviewed
6. A toy test proves the section order, the lock over all four reviewed parts, and the scenario format; docs check and health stay green

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
