# Make the nightly regression suite pass on GitHub and enforce DEL-4 and REG-3

- Slug: regression-green
- Touches: .loop/regression.tsv, .github, skills/workflow-regression, skills/workflow-setup, skills/workflow-release, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. The tests wiki-release, wiki-release-pycache and adopt-set-1 to adopt-set-5 pass in the GitHub Actions regression run, and issues 58, 68, 69, 70, 71, 72 and 74 close by themselves on the next run
2. DEL-4 and REG-3 each have a criterion test, seen failing once and passing now, so the health check no longer fails on them
3. The repo's own checks and the regression suite pass locally and on GitHub

## Verify by hand

1. Run `dev/toy/ci-env.sh bash dev/toy/test-wiki.sh` and `dev/toy/ci-env.sh bash dev/toy/test-adopt.sh`.
   Expect: both end with every line PASS (the first prints `PASS: merge publishes the wiki`, the second `ALL PASS`), with no bytecode setting and no git identity.
2. Open the Delivery and Regression wiki pages and find DEL-4 and REG-3 in their Tests tables.
   Expect: each lists a test (`pr-body-criterion`, `workflow-same-as-run`), not "not enforced".
3. Run `python3 skills/workflow-health/scripts/health.py check`.
   Expect: no FAIL line for DEL-4 or REG-3.
4. After merge, open the next GitHub Actions regression run and the issues list.
   Expect: the run is green and issues 58, 68, 69, 70, 71, 72 and 74 are closed with "Passing again".
