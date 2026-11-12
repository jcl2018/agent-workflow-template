# The wiki-release regression row passes on main again: test-wiki.sh's toy goal reaches a pull request and merges without a stale-page refusal after the settings-table release (v0.27.17), the cause is traced to the test or the code and the wrong side is fixed

- Slug: wiki-release-fix
- Touches: dev/toy/test-wiki.sh, skills/workflow-release/scripts/merge.py, skills/workflow-docs/scripts, skills/workflow-setup/scripts, .loop/regression.tsv, docs/wiki/Tests.md, docs/wiki/Documentation.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. bash dev/toy/ci-env.sh bash dev/toy/test-wiki.sh passes in full on main
2. the fix names whether the test or the code was wrong and which v0.27.17 change caused it
3. no new file under skills/

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
