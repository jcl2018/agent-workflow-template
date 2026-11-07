# Make each feature page two parts, criteria the owner reviews and a test table the regression suite enforces, using Documentation as the template and then every other feature

- Slug: criteria-tests
- Touches: docs/wiki, skills/workflow-docs, skills/workflow-regression, skills/workflow-release, skills/workflow-health, .loop/docs.tsv, .loop/regression.tsv, .github, dev/toy, README.md, skills/loop-files.md, listing.json

## Done lines

Frozen. A wrong done line needs a new goal.

1. Each feature page has a Criteria section of at most 6 short, high-level, PRD-style statements in plain words with no script names, each marked Unreviewed or Reviewed with a date
2. docs.py check fails when a goal changes the wording of a Reviewed criterion; changing one requires the owner to mark it Unreviewed first, and the SKILL file says so
3. Under the criteria, a Tests table lists for each criterion the tests that enforce it, each linked to a regression row with its last run status and date, and a criterion with no passing test shows as not enforced
4. Every criterion has at least one regression row, and the regression workflow on GitHub runs them all and shows status and run history
5. Feature pages drop everything else, such as charts and command detail, or move it to README and the SKILL files, so a page is only Summary, Criteria and Tests
6. Documentation is converted first as the template, then Delivery, Monitoring, Regression, Release and Health, and docs.py check passes on all of them with existing criteria kept as Unreviewed unless already reviewed
7. A toy test proves the format check, the reviewed-criterion lock and the not-enforced marker, and every script stays under 20 KB

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
