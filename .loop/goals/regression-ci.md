# Add the regression workflow so the rows run on GitHub

- Slug: regression-ci
- Level: 1
- Touches: .github/workflows/regression.yml, docs/ROADMAP.md, FINDINGS.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. A file at .github/workflows/regression.yml is written by the regression skill's workflow command and runs the rows on a schedule, on a version tag and by hand
2. The roadmap and FINDINGS say what the first Codex level 0 run and the CI-like run of the rows proved

## Verify by hand

1. Open the repo's Actions tab on GitHub, pick regression, and choose Run workflow on `main`.
   Expect: the run ends green, and every row prints PASS in its log.

## Design

Commit the file `regression.py workflow` writes, unchanged, so the skill stays its one owner. It adds a daily run, so a
failing row opens an issue with no one watching. What could go wrong: a row that only passes on a Mac. Running every row
with an empty home folder, no git identity and a token set found none, but only a real run on GitHub proves it.

## Plan

1. Run `regression.py workflow`, proved by the file in the diff and its triggers.
2. Record the Codex run and the CI-like run in FINDINGS and the roadmap, proved by the diff.
