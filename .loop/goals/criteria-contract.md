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

1. Run `bash dev/toy/test-criteria.sh`.
   Expect: it ends with ALL PASS.
2. Run `python3 skills/workflow-docs/scripts/docs.py criteria Delivery`.
   Expect: it prints a FORMAT line and `NEXT DEL-1`.

## Design

The contract is opt-in per repo with `"criteria": true` in `.loop/config.json`, so existing wiki repos and toy tests keep working; this repo's own wiki is not switched on. `docs.py` holds the section/id rules. A criterion is `- ID: text` under `## Criteria`; `## Enforced by` repeats the id with a regression row id. A regression row belongs to a criterion when its id or `--goal` equals the criterion id. `regression.py sync` and `release.py cut` each read the pages themselves (scripts stay standalone); cut runs the row's command and refuses when missing, draft or failing, and only when `.loop/docs.tsv` exists and pages carry criteria. Risk: duplicated page parsing in three scripts.

## Plan

1. docs.py contract and criteria command: proved by dev/toy/test-criteria.sh (lines 1, 2, 5).
2. regression.py sync gaps: test-criteria.sh (line 3).
3. release.py cut refusal: test-criteria.sh; existing test-release.sh/test-docs.sh show repos without criteria are unchanged (line 4).
4. SKILL.md rules (line 5); all toy checks via goal.py check (line 6).

## Evidence

- release.py cannot read its own location (package rule), so cut checks criteria inline; that took it past the toy test's stricter 20000-byte bound, so dev/toy/test-release.sh now uses 20480, the package and goal.py limit.
- The contract is opt-in: `"criteria": true` in `.loop/config.json`. This repo's own wiki is not switched on.
