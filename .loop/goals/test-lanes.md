# Run the full regression suite once per goal, in qa, and let ship and release reuse that run

- Slug: test-lanes
- Touches: skills/workflow-delivery, skills/workflow-regression, skills/loop-files.md, docs/wiki/Regression.md, .loop/regression.tsv, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A new criterion REG-6, marked temporary until the PRD format replaces the criteria pages, says a goal runs the full suite once, in qa; ship and release reuse qa's recorded run when no code changed since it, and otherwise run only the rows for the files changed after it
2. The qa step writes a test record (the run, its per-row result, the commit it ran on) that the ship skill's own reuse check accepts, so ship does not rerun the suite when nothing changed
3. The release step reruns only the affected rows when merging the base branch changed something, and the full suite still runs in GitHub Actions
4. A toy test proves ship reuses an unchanged qa run, reruns only the affected rows after a code change, and never reuses a failing or missing run

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
