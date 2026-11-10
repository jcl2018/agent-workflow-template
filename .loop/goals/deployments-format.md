# Feature pages may carry an optional Deployments section, as the owner approved (owner, 2026-11-10: "a")

- Slug: deployments-format
- Touches: skills/workflow-docs, docs/wiki/Documentation.md, .loop/regression.tsv, skills/workflow-monitoring/scripts/govern_hook.py

## Done lines

Frozen. A wrong done line needs a new goal.

1. The rules block allows an optional `## Deployments` section after Success metrics (like Usage, optional). Its table has the columns Page | Link | Access | Shows | Live build. criteria.py contract and docs.py check accept a page with or without it, and refuse a malformed table, naming it.
2. The Documentation page gets the owner's wording as a new requirement, marked Reviewed with "a", plus a test.
3. A regression row for each, seen failing then passing.
4. Also fix #495 in the same goal: govern_hook passes `git pull --ff-only` and still blocks plain `git pull`, with negative-control rows.

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
