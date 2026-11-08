# Make the nightly regression suite pass on GitHub and enforce DEL-4 and REG-3

- Slug: regression-green
- Touches: .loop/regression.tsv, .github, skills/workflow-regression, skills/workflow-setup, skills/workflow-release, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. The tests wiki-release, wiki-release-pycache and adopt-set-1 to adopt-set-5 pass in the GitHub Actions regression run, and issues 58, 68, 69, 70, 71, 72 and 74 close by themselves on the next run
2. DEL-4 and REG-3 each have a criterion test, seen failing once and passing now, so the health check no longer fails on them
3. The repo's own checks and the regression suite pass locally and on GitHub

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
