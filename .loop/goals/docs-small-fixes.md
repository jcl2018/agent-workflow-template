# Two small doc defects on main are fixed: test-deployments.sh hardcodes "8 pages" while the wiki now has 9, and the README names /workflow-docs init, /workflow-release cut and /workflow-release leave that no page's Usage names (from tonight's issue-cleanup triage and a worker report)

- Slug: docs-small-fixes
- Touches: dev/toy/test-deployments.sh, docs/wiki/Documentation.md, docs/wiki/Delivery.md, docs/wiki/Setup.md, README.md, .loop/regression.tsv, docs/wiki/Tests.md, .loop/regression-known.tsv

## Done lines

Frozen. A wrong done line needs a new goal.

1. test-deployments.sh counts the wiki pages instead of hardcoding 8, and passes on main
2. each command the README names appears in its page's Usage, or the README stops naming it
3. no new file under skills/; Reviewed lines untouched

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
