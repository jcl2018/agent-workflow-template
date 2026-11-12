# Fix the Regression PRD and tooling for rows a platform can't run: a row the local platform can't run is skipped with its reason and is never counted as seen red; its red proof runs on a capable runner (Linux CI or a Linux session) and the result is written back to the row; the PR lists the exact red commands still owed

- Slug: red-off-platform-prd
- Touches: docs/wiki/Regression.md, skills/workflow-regression

## Done lines

Frozen. A wrong done line needs a new goal.

1. docs/wiki/Regression.md holds a new Unreviewed requirement for off-platform red proof, and workflow-docs check prints DOCS OK
2. regression.py can record a red result proven on another runner, naming the runner and commit, and a Windows skip can never set seen red

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
