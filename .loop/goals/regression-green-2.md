# The template's scheduled regression on GitHub goes green: the six rows failing on every run (breaking-asks, lanes-headers, lanes-repo-narrow, one-way-to-run, prd-repo-green, toy-no-leftovers) are each traced to a test that assumes this Mac or a regression in code, and fixed where they are wrong; stale per-row regression issues for rows that now pass are closed by the workflow (owner, 2026-11-11, asking whether the template's automations are implemented); prd: Regression

- Slug: regression-green-2
- Touches: dev/toy, .loop/regression.tsv, .github/workflows/regression.yml, docs/wiki/Regression.md, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. a regression run on GitHub ends with those six rows passing and no new failure
2. each fix names whether the test or the code was wrong; a code regression gets a failing-then-passing row
3. open regression issues match the rows failing on the latest run

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
