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

1. Open `skills/workflow-docs/references/template.md` and read the rules block and the Deployments bullet.
   Expect: `deployments_section`, `deployments_page`, `deployments_delivery`, `deployments_access` and `deployments` in `format`.
2. Add this under a feature page's Success metrics (before `## Tests`) and run `/workflow-docs check`:
   `## Deployments` then `| Page | Link | Access | Shows | Live build |`, `|---|---|---|---|---|`, `| Site | https://example.test | public | the guide | \`1a2b3c4\` |`.
   Expect: `DOCS OK`. Change Access to `everyone` and run it again: a `Deployments: DOC-14 Page Access public or sign-in` line.
3. Put an email address in a Delivery table's Recipients cell and run the check.
   Expect: `Delivery Recipients a group, never an address`, and the address itself is not printed.
4. Read DOC-14 on the Documentation wiki page.
   Expect: Reviewed, with the pages and deliveries wording.
5. Pipe `git pull --ff-only` and then `git pull` into `python3 skills/workflow-monitoring/scripts/govern_hook.py check`.
   Expect: `PASS`, then `BLOCK: git pull`.

## Owner's words

- 2026-11-10, approving ("a"): "A feature page that ships something people can open has a Deployments section (optional otherwise): one row per public or private page, with its link, who can open it (public or sign-in), what it shows, and the live build (the sha in build.txt). A check fails when a listed public link doesn't answer or the live build isn't the promoted one."
- 2026-11-10, widening: "the newsletter also gets a deployment for the delivery… send the attachment to that email" (relayed by the operation session: Delivery rows, recipients as a group, never an address).
- DOC-14's title and sub-bullets were written by the worker from those words and stamped with the owner's "a" as the operation session asked; please confirm them in this review. The live-link and promoted-build check stays in the deploying repo for now.

## Also closes

Closes #495: the govern hook passes `git pull --ff-only` (also with `-C <dir>`) and still refuses plain pull and every other form, with negative-control rows.
