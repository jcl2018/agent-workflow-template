# Make the release step refresh every wiki page a goal's commits leave stale, and publish the wiki now

- Slug: wiki-sync
- Touches: skills/workflow-release/scripts/wiki.py, skills/workflow-docs, docs/wiki, .loop/docs.tsv, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. Before the merge, the release step refreshes every page that docs.py check would call stale after the goal's commits, not only pages mapped to touched paths, and refuses to merge while one stays stale
2. The Documentation page is brought up to date, docs.py publish succeeds, and the GitHub wiki matches docs/wiki
3. A toy test where a goal's commit makes an unmapped page stale proves the release step refreshes it and publishes

## Verify by hand

1. Run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: it prints `DOCS OK`.
2. Run `python3 skills/workflow-release/scripts/wiki.py prepare wiki-sync`.
   Expect: it prints `WIKI CURRENT`, the same verdict as step 1.
3. Run `bash dev/toy/test-wiki.sh`.
   Expect: every line is PASS, including `prepare lists the unmapped stale page` and `merge publishes the refreshed page`.
