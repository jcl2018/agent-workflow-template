# Make feature pages a criteria contract that docs and release enforce

- Slug: criteria-contract
- Level: standard
- Touches: skills/workflow-docs, skills/workflow-regression, skills/workflow-release, listing.json, dev/toy, skills/loop-files.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. docs.py check fails a feature page unless it has exactly the sections Summary, Commands, Criteria and Enforced by, in that order, and allows only the pages Delivery, Documentation, Monitoring, Regression and Release, plus Home
2. A criterion is one line with a stable id such as DEL-1, and docs.py check fails on a duplicate id, or a criterion with no row in Enforced by
3. regression.py sync reads criteria ids from the wiki pages and reports each one with no regression row as a gap
4. With .loop/docs.tsv present, release.py cut refuses when a criterion's regression row is missing or failing, and repos with no criteria behave as they do today
5. A docs.py criteria command prints the format and the next free id for a page, and skills/workflow-docs/SKILL.md gives the rules for writing criteria, including that only the owner approves a changed criterion
6. Fixtures in the toy tests prove each line above, and the repo checks pass

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->

## Design

## Plan
