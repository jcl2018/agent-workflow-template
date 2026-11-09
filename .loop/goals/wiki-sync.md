# Make the release step refresh every wiki page a goal's commits leave stale, and publish the wiki now

- Slug: wiki-sync
- Touches: skills/workflow-release/scripts/wiki.py, skills/workflow-docs, docs/wiki, .loop/docs.tsv, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. Before the merge, the release step refreshes every page that docs.py check would call stale after the goal's commits, not only pages mapped to touched paths, and refuses to merge while one stays stale
2. The Documentation page is brought up to date, docs.py publish succeeds, and the GitHub wiki matches docs/wiki
3. A toy test where a goal's commit makes an unmapped page stale proves the release step refreshes it and publishes

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
