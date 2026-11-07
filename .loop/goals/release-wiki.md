# Make the release step, the last step of every goal, bring the wiki up to date, so pages never go stale after a merge, and fix the pages that are stale now

- Slug: release-wiki
- Touches: skills/workflow-release, skills/workflow-docs, skills/workflow-delivery, docs/wiki, .loop/docs.tsv, .loop/regression.tsv, dev/toy, README.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. Before a goal's pull request merges, the release step updates every wiki page that the goal's changed paths map to in .loop/docs.tsv, commits the update on the goal's branch, and docs.py check reports no stale page for those paths
2. After the merge, the release step publishes the wiki to GitHub by itself; if publish refuses, the goal's report says which page and why, and it shows under Needs you
3. The Monitoring, Regression and Release pages are brought up to date with what is merged now, and docs.py publish succeeds
4. The Release wiki page says the release step updates and publishes the wiki, with its criteria marked Unreviewed and regression rows
5. A toy test proves a goal that changes a mapped path ends with that page updated and no stale page, and every script stays under 20 KB

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
